"""
LAMControl Distributed Server

Central server that receives R1 prompts, processes them with LLM,
and distributes tasks to registered worker nodes.
"""

import os
import json
import logging
import secrets
import hashlib
import asyncio
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from functools import wraps
import requests

from utils import config, llm_parse, get_env


class WorkerNode:
    """Represents a registered worker node"""
    def __init__(self, worker_id: str, worker_type: str, capabilities: List[str], 
                 endpoint: str, api_key: str):
        self.worker_id = worker_id
        self.worker_type = worker_type
        self.capabilities = capabilities
        self.endpoint = endpoint
        self.api_key = api_key
        self.last_heartbeat = datetime.now(timezone.utc)
        self.status = "online"
        self.current_tasks = 0
        self.max_concurrent_tasks = 5
        
        # Additional fields for custom worker identification
        self.location = ""
        self.description = ""
        self.custom_name = ""


class DistributedLAMServer:
    """Central LAMControl server for distributed architecture"""
    
    def __init__(self, host='0.0.0.0', port=5000):
        self.app = Flask(__name__)
        self.app.secret_key = self._get_or_create_secret_key()
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        self.host = host
        self.port = port
        
        # Server state
        self.workers: Dict[str, WorkerNode] = {}
        self.pending_tasks = []
        self.completed_tasks = []
        self.task_queue = asyncio.Queue()
        
        # Statistics
        self.stats = {
            'uptime': datetime.now(timezone.utc),
            'total_prompts': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'active_workers': 0
        }
        
        self.admin_credentials = self._load_admin_credentials()
        self.setup_routes()
        self.setup_socketio_events()
        
        # Start background tasks
        self.setup_background_tasks()
    
    def _get_or_create_secret_key(self):
        """Get or create a secret key for Flask sessions"""
        secret_file = os.path.join(config.config.get('cache_dir', 'cache'), 'flask_secret.key')
        
        if os.path.exists(secret_file):
            with open(secret_file, 'r') as f:
                return f.read().strip()
        else:
            os.makedirs(os.path.dirname(secret_file), exist_ok=True)
            secret_key = secrets.token_hex(32)
            with open(secret_file, 'w') as f:
                f.write(secret_key)
            return secret_key
    
    def _load_admin_credentials(self):
        """Load or create admin credentials"""
        creds_file = os.path.join(config.config.get('cache_dir', 'cache'), 'admin_creds.json')
        
        if os.path.exists(creds_file):
            with open(creds_file, 'r') as f:
                creds = json.load(f)
                # Always print credentials on startup for convenience
                print(f"\n=== ADMIN CREDENTIALS ===")
                print(f"Username: {creds['username']}")
                print(f"Password: [Check admin_creds.json file for password]")
                print(f"Admin Dashboard: http://localhost:5000")
                print(f"R1 Login: http://localhost:5000/r1/login")
                print(f"========================\n")
                return creds
        else:
            os.makedirs(os.path.dirname(creds_file), exist_ok=True)
            username = 'admin'
            password = secrets.token_urlsafe(16)
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            creds = {
                'username': username,
                'password': password,  # Store plain password for display
                'password_hash': password_hash,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            with open(creds_file, 'w') as f:
                json.dump(creds, f, indent=2)
            
            # Log credentials for first time setup
            logging.info(f"Created admin credentials - Username: {username}, Password: {password}")
            print(f"\n=== ADMIN CREDENTIALS ===")
            print(f"Username: {username}")
            print(f"Password: {password}")
            print(f"Admin Dashboard: http://localhost:5000")
            print(f"R1 Login: http://localhost:5000/r1/login")
            print(f"Save these credentials safely!")
            print(f"========================\n")
            
            return creds
    
    def require_auth(self, f):
        """Decorator to require authentication"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'authenticated' not in session or not session['authenticated']:
                return jsonify({'error': 'Authentication required'}), 401
            return f(*args, **kwargs)
        return decorated_function
    
    def setup_background_tasks(self):
        """Setup background tasks for worker management"""
        def task_processor():
            """Process queued tasks"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._process_tasks())
        
        def heartbeat_checker():
            """Check worker heartbeats"""
            while True:
                self._check_worker_heartbeats()
                threading.Event().wait(30)  # Check every 30 seconds
        
        # Start background threads
        task_thread = threading.Thread(target=task_processor, daemon=True)
        heartbeat_thread = threading.Thread(target=heartbeat_checker, daemon=True)
        
        task_thread.start()
        heartbeat_thread.start()
    
    async def _process_tasks(self):
        """Async task processor"""
        while True:
            try:
                # Get task from queue
                task = await self.task_queue.get()
                await self._route_task_to_worker(task)
            except Exception as e:
                logging.error(f"Error processing task: {e}")
    
    def _check_worker_heartbeats(self):
        """Check if workers are still alive"""
        current_time = datetime.now(timezone.utc)
        offline_workers = []
        
        for worker_id, worker in self.workers.items():
            if (current_time - worker.last_heartbeat).seconds > 120:  # 2 minutes timeout
                worker.status = "offline"
                offline_workers.append(worker_id)
        
        if offline_workers:
            logging.warning(f"Workers gone offline: {offline_workers}")
            self.broadcast_worker_update()
    
    def setup_socketio_events(self):
        """Setup SocketIO events for real-time communication"""
        
        @self.socketio.on('connect')
        def handle_connect():
            if 'authenticated' in session and session['authenticated']:
                join_room('admin')
                emit('status', {'message': 'Connected to LAMControl Server'})
            else:
                return False
        
        @self.socketio.on('worker_heartbeat')
        def handle_worker_heartbeat(data):
            worker_id = data.get('worker_id')
            if worker_id in self.workers:
                self.workers[worker_id].last_heartbeat = datetime.now(timezone.utc)
                self.workers[worker_id].status = data.get('status', 'online')
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            if 'authenticated' not in session or not session['authenticated']:
                return redirect(url_for('login'))
            return render_template_string(self._get_dashboard_template())
        
        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')
                
                if self._verify_password(username, password):
                    session['authenticated'] = True
                    session['username'] = username
                    session.permanent = True  # Make session persistent for R1
                    return redirect(url_for('index'))
                else:
                    return render_template_string(self._get_login_template(), error="Invalid credentials")
            
            return render_template_string(self._get_login_template())
        
        @self.app.route('/logout')
        def logout():
            session.clear()
            return redirect(url_for('login'))
        
        # R1 API Endpoints
        @self.app.route('/api/prompt', methods=['POST'])
        def receive_prompt():
            """Main endpoint for R1 to send prompts"""
            try:
                data = request.get_json()
                if not data or 'prompt' not in data:
                    return jsonify({'error': 'No prompt provided'}), 400
                
                prompt_id = secrets.token_hex(8)
                prompt_data = {
                    'id': prompt_id,
                    'prompt': data['prompt'],
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': data.get('source', 'r1'),
                    'metadata': data.get('metadata', {})
                }
                
                # Process prompt with LLM
                response = self._process_prompt(prompt_data)
                
                return jsonify({
                    'status': 'success',
                    'id': prompt_id,
                    'response': response
                })
                
            except Exception as e:
                logging.error(f"Error processing prompt: {e}")
                return jsonify({'error': 'Failed to process prompt'}), 500
        
        @self.app.route('/api/prompt/<prompt_id>/status', methods=['GET'])
        def get_prompt_status(prompt_id):
            """Get status of a specific prompt"""
            # Find prompt in completed tasks
            for task in self.completed_tasks:
                if task.get('id') == prompt_id:
                    return jsonify({
                        'status': 'completed',
                        'id': prompt_id,
                        'result': task.get('result', {}),
                        'timestamp': task.get('timestamp')
                    })
            
            # Check if still pending
            for task in self.pending_tasks:
                if task.get('id') == prompt_id:
                    return jsonify({
                        'status': 'pending',
                        'id': prompt_id,
                        'timestamp': task.get('timestamp')
                    })
            
            return jsonify({'error': 'Prompt not found'}), 404
        
        # R1 Web Interface for browser navigation
        @self.app.route('/r1', methods=['GET', 'POST'])
        def r1_interface():
            """Simple interface for R1 to navigate and send prompts"""
            # Check if R1 is authenticated
            if 'r1_authenticated' not in session or not session['r1_authenticated']:
                return redirect(url_for('r1_login'))
            
            if request.method == 'POST':
                # Handle form submission from R1
                prompt = request.form.get('prompt', '').strip()
                if not prompt:
                    return render_template_string(self._get_r1_template(), 
                                                error="Please enter a command")
                
                try:
                    # Process the prompt
                    prompt_data = {
                        'id': secrets.token_hex(8),
                        'prompt': prompt,
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'source': 'r1_web',
                        'metadata': {'interface': 'web'}
                    }
                    
                    # Add to pending tasks for tracking
                    self.pending_tasks.append(prompt_data)
                    
                    response = self._process_prompt(prompt_data)
                    
                    return render_template_string(self._get_r1_template(), 
                                                success=f"Command sent: {prompt}",
                                                task_id=prompt_data['id'],
                                                response=response.get('message', 'Processing...'))
                
                except Exception as e:
                    logging.error(f"Error processing R1 prompt: {e}")
                    return render_template_string(self._get_r1_template(), 
                                                error="Failed to process command")
            
            return render_template_string(self._get_r1_template())
        
        # R1 Login page
        @self.app.route('/r1/login', methods=['GET', 'POST'])
        def r1_login():
            """Login page specifically for R1 device"""
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')
                
                if self._verify_password(username, password):
                    session['r1_authenticated'] = True
                    session['r1_username'] = username
                    session.permanent = True  # Make session persistent for R1
                    return redirect(url_for('r1_interface'))
                else:
                    return render_template_string(self._get_r1_login_template(), 
                                                error="Invalid credentials")
            
            # GET request - show login form
            return render_template_string(self._get_r1_login_template())
            
        @self.app.route('/r1/logout')
        def r1_logout():
            """R1 logout"""
            session.pop('r1_authenticated', None)
            return redirect(url_for('r1_login'))
        
        @self.app.route('/api/task/<task_id>/status', methods=['GET'])
        def get_task_status(task_id):
            """Get real-time status of a task (for R1 interface)"""
            # Check pending tasks
            for task in self.pending_tasks:
                if task.get('id') == task_id:
                    return jsonify({
                        'status': 'pending',
                        'id': task_id,
                        'timestamp': task.get('timestamp'),
                        'message': 'Task is being processed...'
                    })
            
            # Check completed tasks
            for task in self.completed_tasks:
                if task.get('id') == task_id:
                    return jsonify({
                        'status': 'completed',
                        'id': task_id,
                        'result': task.get('result', {}),
                        'timestamp': task.get('completed_at', task.get('timestamp')),
                        'worker_id': task.get('worker_id', 'unknown'),
                        'success': task.get('result', {}).get('success', False),
                        'message': task.get('result', {}).get('message', 'Task completed'),
                        'output': task.get('result', {}).get('output', '')
                    })
            
            return jsonify({'error': 'Task not found'}), 404
        
        # Worker Management Endpoints
        @self.app.route('/api/worker/register', methods=['POST'])
        def register_worker():
            """Register a new worker node"""
            try:
                data = request.get_json()
                
                # Validate required fields
                required_fields = ['worker_type', 'capabilities', 'endpoint']
                if not all(field in data for field in required_fields):
                    return jsonify({'error': 'Missing required fields: worker_type, capabilities, endpoint'}), 400
                
                # Use custom worker_name if provided, otherwise generate one
                custom_name = data.get('worker_name', '').strip()
                if custom_name:
                    worker_id = f"{custom_name}_{data['worker_type']}"
                else:
                    worker_id = f"{data['worker_type']}_{secrets.token_hex(4)}"
                
                # Check if worker already exists
                if worker_id in self.workers:
                    return jsonify({'error': f'Worker {worker_id} already registered'}), 409
                
                # Create worker node
                worker = WorkerNode(
                    worker_id=worker_id,
                    worker_type=data['worker_type'],
                    capabilities=data['capabilities'],
                    endpoint=data['endpoint'],
                    api_key=secrets.token_hex(16)
                )
                
                # Add location/description if provided
                worker.location = data.get('location', '')
                worker.description = data.get('description', '')
                worker.custom_name = custom_name
                
                self.workers[worker.worker_id] = worker
                self.stats['active_workers'] = len([w for w in self.workers.values() if w.status == 'online'])
                
                logging.info(f"Registered worker: {worker.worker_id} ({worker.worker_type}) at {worker.endpoint}")
                self.broadcast_worker_update()
                
                return jsonify({
                    'status': 'success',
                    'worker_id': worker.worker_id,
                    'api_key': worker.api_key,
                    'message': f'Worker {worker_id} registered successfully'
                })
                
            except Exception as e:
                logging.error(f"Error registering worker: {e}")
                return jsonify({'error': 'Failed to register worker'}), 500
        
        @self.app.route('/api/worker/<worker_id>/heartbeat', methods=['POST'])
        def worker_heartbeat(worker_id):
            """Receive heartbeat from worker"""
            if worker_id in self.workers:
                self.workers[worker_id].last_heartbeat = datetime.now(timezone.utc)
                self.workers[worker_id].status = 'online'
                
                # Update task count and status if provided
                data = request.get_json() or {}
                if 'current_tasks' in data:
                    self.workers[worker_id].current_tasks = data['current_tasks']
                if 'status' in data:
                    self.workers[worker_id].status = data['status']
                
                return jsonify({'status': 'success'})
            else:
                return jsonify({'error': 'Worker not found'}), 404
        
        @self.app.route('/api/workers', methods=['GET'])
        @self.require_auth
        def get_workers():
            """Get list of all workers (admin only)"""
            workers_data = []
            for worker in self.workers.values():
                workers_data.append({
                    'worker_id': worker.worker_id,
                    'worker_type': worker.worker_type,
                    'capabilities': worker.capabilities,
                    'status': worker.status,
                    'current_tasks': worker.current_tasks,
                    'last_heartbeat': worker.last_heartbeat.isoformat(),
                    'location': getattr(worker, 'location', ''),
                    'description': getattr(worker, 'description', ''),
                    'custom_name': getattr(worker, 'custom_name', ''),
                    'endpoint': worker.endpoint
                })
            
            return jsonify({
                'workers': workers_data,
                'total_workers': len(workers_data),
                'online_workers': len([w for w in workers_data if w['status'] == 'online'])
            })
        
        @self.app.route('/api/worker/<worker_id>/remove', methods=['DELETE'])
        @self.require_auth
        def remove_worker(worker_id):
            """Remove a worker (admin only)"""
            if worker_id in self.workers:
                del self.workers[worker_id]
                self.stats['active_workers'] = len([w for w in self.workers.values() if w.status == 'online'])
                logging.info(f"Removed worker: {worker_id}")
                self.broadcast_worker_update()
                return jsonify({'status': 'success', 'message': f'Worker {worker_id} removed'})
            else:
                return jsonify({'error': 'Worker not found'}), 404
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'workers': len(self.workers),
                'online_workers': len([w for w in self.workers.values() if w.status == 'online']),
                'uptime': (datetime.now(timezone.utc) - self.stats['uptime']).total_seconds(),
                'stats': self.stats
            })
    
    def _verify_password(self, username: str, password: str) -> bool:
        """Verify admin credentials"""
        if username != self.admin_credentials["username"]:
            return False
        
        # Check if we have a plain password stored (for new installs)
        if 'password' in self.admin_credentials:
            return password == self.admin_credentials['password']
        
        # Fallback to hash verification (for older installs)
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == self.admin_credentials["password_hash"]
    
    def _process_prompt(self, prompt_data: Dict) -> Dict:
        """Process prompt with LLM and route to appropriate worker"""
        try:
            # Use LLM to parse the prompt
            result = llm_parse.process_prompt(prompt_data['prompt'])
            
            if result.get('action') == 'x':
                # Not a command for LAMControl
                return {'status': 'ignored', 'message': 'Prompt sent to R1'}
            
            # Create task for worker routing
            task = {
                'id': prompt_data['id'],
                'prompt': prompt_data['prompt'],
                'action': result.get('action', ''),
                'parameters': result.get('parameters', {}),
                'timestamp': prompt_data['timestamp'],
                'source': prompt_data['source']
            }
            
            # Add to task queue for async processing
            asyncio.create_task(self.task_queue.put(task))
            
            self.stats['total_prompts'] += 1
            
            return {
                'status': 'success',
                'message': f"Command processed: {result.get('action', 'unknown')}",
                'action': result.get('action', ''),
                'task_id': task['id']
            }
            
        except Exception as e:
            logging.error(f"Error processing prompt: {e}")
            self.stats['failed_tasks'] += 1
            return {'status': 'error', 'message': str(e)}
    
    async def _route_task_to_worker(self, task: Dict):
        """Route task to appropriate worker node"""
        try:
            action = task.get('action', '').lower()
            
            # Determine worker type needed
            worker_type = None
            if any(keyword in action for keyword in ['browser', 'google', 'youtube', 'site', 'amazon']):
                worker_type = 'browser'
            elif any(keyword in action for keyword in ['computer', 'volume', 'media', 'run', 'power']):
                worker_type = 'computer'
            elif any(keyword in action for keyword in ['discord', 'telegram', 'messenger']):
                worker_type = 'messaging'
            elif action in ['ai', 'openinterpreter']:
                worker_type = 'ai'
            
            if not worker_type:
                logging.warning(f"No worker type determined for action: {action}")
                return
            
            # Find available worker
            available_workers = [
                w for w in self.workers.values()
                if w.worker_type == worker_type and w.status == 'online' 
                and w.current_tasks < w.max_concurrent_tasks
            ]
            
            if not available_workers:
                logging.warning(f"No available {worker_type} workers")
                self.stats['failed_tasks'] += 1
                return
            
            # Select worker with least load
            worker = min(available_workers, key=lambda w: w.current_tasks)
            
            # Send task to worker
            response = requests.post(
                f"{worker.endpoint}/execute",
                json={
                    'task_id': task['id'],
                    'action': action,
                    'parameters': task.get('parameters', {}),
                    'prompt': task['prompt']
                },
                headers={'Authorization': f"Bearer {worker.api_key}"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                task['result'] = result
                task['completed_at'] = datetime.now(timezone.utc).isoformat()
                task['worker_id'] = worker.worker_id
                
                self.completed_tasks.append(task)
                self.stats['completed_tasks'] += 1
                
                logging.info(f"Task {task['id']} completed by worker {worker.worker_id}")
            else:
                logging.error(f"Worker {worker.worker_id} failed to process task: {response.status_code}")
                self.stats['failed_tasks'] += 1
                
        except Exception as e:
            logging.error(f"Error routing task to worker: {e}")
            self.stats['failed_tasks'] += 1
    
    def broadcast_worker_update(self):
        """Broadcast worker status update to connected clients"""
        try:
            self.socketio.emit('worker_update', {
                'workers': [
                    {
                        'worker_id': w.worker_id,
                        'worker_type': w.worker_type,
                        'status': w.status,
                        'current_tasks': w.current_tasks
                    }
                    for w in self.workers.values()
                ]
            }, room='admin')
        except Exception as e:
            logging.error(f"Error broadcasting worker update: {e}")
    
    def _get_dashboard_template(self):
        """Get admin dashboard template with worker management"""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>LAMControl Distributed Server</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #fff; }
        .header { border-bottom: 2px solid #ff6600; padding-bottom: 10px; margin-bottom: 20px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: #2d2d2d; padding: 15px; border-radius: 5px; border-left: 4px solid #ff6600; }
        .workers { background: #2d2d2d; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .worker { padding: 10px; margin: 5px 0; background: #333; border-radius: 3px; display: flex; justify-content: space-between; align-items: center; }
        .worker.online { border-left: 4px solid #00ff00; }
        .worker.offline { border-left: 4px solid #ff0000; }
        .recent-tasks { background: #2d2d2d; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .r1-link { background: #ff6600; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0; }
        .worker-registration { background: #2d2d2d; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .form-group { margin: 10px 0; }
        .form-group label { display: block; margin-bottom: 5px; color: #ccc; }
        .form-group input, .form-group select { width: 100%; padding: 8px; border: 1px solid #555; background: #444; color: #fff; border-radius: 3px; }
        .btn { padding: 8px 15px; border: none; border-radius: 3px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn-primary { background: #007bff; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-success { background: #28a745; color: white; }
        .worker-info { flex-grow: 1; }
        .worker-actions { display: flex; gap: 10px; }
        .registration-form { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .registration-form .form-group.full-width { grid-column: 1 / -1; }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head>
<body>
    <div class="header">
        <h1>LAMControl Distributed Server</h1>
        <p>Central server managing worker nodes and R1 prompts</p>
        <a href="/r1/login" class="r1-link">R1 Login Page</a>
        <a href="/logout" class="r1-link" style="background: #dc3545;">Admin Logout</a>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <h3>Total Prompts</h3>
            <p id="total-prompts">0</p>
        </div>
        <div class="stat-card">
            <h3>Active Workers</h3>
            <p id="active-workers">0</p>
        </div>
        <div class="stat-card">
            <h3>Completed Tasks</h3>
            <p id="completed-tasks">0</p>
        </div>
        <div class="stat-card">
            <h3>Failed Tasks</h3>
            <p id="failed-tasks">0</p>
        </div>
    </div>
    
    <div class="worker-registration">
        <h2>Register New Worker</h2>
        <form id="workerForm" class="registration-form">
            <div class="form-group">
                <label for="worker_name">Custom Name:</label>
                <input type="text" id="worker_name" name="worker_name" placeholder="e.g., room_pc, living_room_pc" required>
            </div>
            <div class="form-group">
                <label for="worker_type">Worker Type:</label>
                <select id="worker_type" name="worker_type" required>
                    <option value="">Select type...</option>
                    <option value="browser">Browser Worker</option>
                    <option value="computer">Computer Worker</option>
                    <option value="messaging">Messaging Worker</option>
                    <option value="ai">AI Worker</option>
                </select>
            </div>
            <div class="form-group">
                <label for="endpoint">Endpoint URL:</label>
                <input type="url" id="endpoint" name="endpoint" placeholder="http://192.168.1.100:6001" required>
            </div>
            <div class="form-group">
                <label for="location">Location:</label>
                <input type="text" id="location" name="location" placeholder="e.g., Living Room, Home Office">
            </div>
            <div class="form-group full-width">
                <label for="description">Description:</label>
                <input type="text" id="description" name="description" placeholder="e.g., Main computer for web browsing">
            </div>
            <div class="form-group full-width">
                <button type="submit" class="btn btn-success">Register Worker</button>
            </div>
        </form>
        <div id="registration-result"></div>
    </div>
    
    <div class="workers">
        <h2>Worker Nodes</h2>
        <div id="workers-list">No workers registered</div>
    </div>
    
    <div class="recent-tasks">
        <h2>Recent Tasks</h2>
        <div id="recent-tasks">No recent tasks</div>
    </div>
    
    <script>
        const socket = io();
        
        function updateStats() {
            fetch('/api/workers')
            .then(response => response.json())
            .then(data => {
                document.getElementById('active-workers').textContent = data.online_workers;
                
                const workersList = document.getElementById('workers-list');
                if (data.workers.length === 0) {
                    workersList.innerHTML = 'No workers registered';
                } else {
                    workersList.innerHTML = data.workers.map(worker => 
                        `<div class="worker ${worker.status}">
                            <div class="worker-info">
                                <strong>${worker.custom_name || worker.worker_id}</strong> (${worker.worker_type})
                                <br>Status: ${worker.status} | Tasks: ${worker.current_tasks}
                                <br>Capabilities: ${worker.capabilities.join(', ')}
                                ${worker.location ? `<br>Location: ${worker.location}` : ''}
                                ${worker.description ? `<br>Description: ${worker.description}` : ''}
                                <br><small>Endpoint: ${worker.endpoint}</small>
                            </div>
                            <div class="worker-actions">
                                <button class="btn btn-danger" onclick="removeWorker('${worker.worker_id}')">Remove</button>
                            </div>
                        </div>`
                    ).join('');
                }
            })
            .catch(error => {
                console.error('Failed to load workers:', error);
            });
        }
        
        function removeWorker(workerId) {
            if (confirm(`Are you sure you want to remove worker: ${workerId}?`)) {
                fetch(`/api/worker/${workerId}/remove`, {
                    method: 'DELETE'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        updateStats();
                    } else {
                        alert('Failed to remove worker: ' + data.error);
                    }
                });
            }
        }
        
        // Worker registration form
        document.getElementById('workerForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const workerData = {
                worker_name: formData.get('worker_name'),
                worker_type: formData.get('worker_type'),
                endpoint: formData.get('endpoint'),
                location: formData.get('location'),
                description: formData.get('description'),
                capabilities: getCapabilitiesForType(formData.get('worker_type'))
            };
            
            fetch('/api/worker/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(workerData)
            })
            .then(response => response.json())
            .then(data => {
                const resultDiv = document.getElementById('registration-result');
                if (data.status === 'success') {
                    resultDiv.innerHTML = `<div style="color: #28a745; margin-top: 10px;">
                        <strong>Worker registered successfully!</strong><br>
                        Worker ID: ${data.worker_id}<br>
                        API Key: ${data.api_key}<br>
                        <small>Save the API key - it won't be shown again.</small>
                    </div>`;
                    e.target.reset();
                    updateStats();
                } else {
                    resultDiv.innerHTML = `<div style="color: #dc3545; margin-top: 10px;">
                        Error: ${data.error}
                    </div>`;
                }
            })
            .catch(error => {
                document.getElementById('registration-result').innerHTML = 
                    `<div style="color: #dc3545; margin-top: 10px;">Registration failed: ${error}</div>`;
            });
        });
        
        function getCapabilitiesForType(workerType) {
            const capabilities = {
                'browser': ['browsersite', 'browsergoogle', 'browseryoutube', 'browsergmail', 'browseramazon'],
                'computer': ['computervolume', 'computerrun', 'computermedia', 'computerpower'],
                'messaging': ['discordtext', 'facebooktext', 'telegram'],
                'ai': ['openinterpreter', 'ai_automation']
            };
            return capabilities[workerType] || [];
        }
        
        socket.on('worker_update', function(data) {
            updateStats();
        });
        
        // Update stats every 10 seconds
        setInterval(updateStats, 10000);
        updateStats();
    </script>
</body>
</html>
        '''
    
    def _get_login_template(self):
        """Get login template"""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>LAMControl - Login</title>
    <style>
        body { font-family: Arial, sans-serif; background: #1a1a1a; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-container { background: #2d2d2d; padding: 30px; border-radius: 10px; width: 300px; }
        .logo { text-align: center; margin-bottom: 20px; }
        .logo h1 { color: #ff6600; margin: 0; }
        input { width: 100%; padding: 10px; margin: 10px 0; border: none; border-radius: 5px; background: #333; color: #fff; }
        button { width: 100%; padding: 10px; background: #ff6600; color: white; border: none; border-radius: 5px; cursor: pointer; }
        .error { color: #ff4444; text-align: center; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <h1>LAMControl</h1>
            <p>Distributed Server</p>
        </div>
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        {{ '<!-- Error: ' + error + ' -->' if error else '' }}
    </div>
</body>
</html>
        '''
    
    def _get_r1_login_template(self, error=None):
        """Get R1 login template"""
        error_html = f"<div class='error'>{error}</div>" if error else ""
        
        return f'''
<!DOCTYPE html>
<html>
<head>
    <title>LAMControl - R1 Login</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: Arial, sans-serif; background: #f0f0f0; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
        .login-container {{ background: white; padding: 30px; border-radius: 10px; width: 400px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .logo {{ text-align: center; margin-bottom: 20px; }}
        .logo h1 {{ color: #ff6600; margin: 0; font-size: 28px; }}
        .logo p {{ color: #666; margin: 5px 0 0 0; }}
        .form-group {{ margin: 15px 0; }}
        label {{ display: block; margin-bottom: 5px; font-weight: bold; color: #333; }}
        input {{ width: 100%; padding: 15px; font-size: 16px; border: 2px solid #ddd; border-radius: 5px; box-sizing: border-box; }}
        button {{ width: 100%; padding: 15px; font-size: 16px; background: #ff6600; color: white; border: none; border-radius: 5px; cursor: pointer; }}
        button:hover {{ background: #e55a00; }}
        .error {{ background: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; margin: 10px 0; text-align: center; }}
        .info {{ background: #e7f3ff; color: #004085; padding: 15px; border-radius: 5px; margin: 15px 0; text-align: center; }}
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <h1>LAMControl</h1>
            <p>R1 Device Login</p>
        </div>
        
        <div class="info">
            <strong>For R1 Users:</strong><br>
            Log in once and your session will be saved.<br>
            You won't need to log in again on this device.
        </div>
        
        {error_html}
        
        <form method="POST">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required autofocus>
            </div>
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
        '''
    
    def _get_r1_template(self, success=None, error=None, response=None, task_id=None):
        """Get R1-friendly interface template with real-time status updates"""
        success_html = f"<div class='success'>{success}</div>" if success else ""
        error_html = f"<div class='error'>{error}</div>" if error else ""
        response_html = f"<div class='response'><strong>Response:</strong> {response}</div>" if response else ""
        
        return f'''
<!DOCTYPE html>
<html>
<head>
    <title>LAMControl</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }}
        .container {{ max-width: 700px; margin: 0 auto; background: white; padding: 25px; border-radius: 10px; }}
        h1 {{ color: #ff6600; text-align: center; margin-bottom: 20px; }}
        .form-group {{ margin: 15px 0; }}
        label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
        input[type="text"] {{ width: 100%; padding: 15px; font-size: 16px; border: 2px solid #ddd; border-radius: 5px; box-sizing: border-box; }}
        button {{ width: 100%; padding: 15px; font-size: 16px; background: #ff6600; color: white; border: none; border-radius: 5px; cursor: pointer; }}
        button:hover {{ background: #e55a00; }}
        .success {{ background: #d4edda; color: #155724; padding: 12px; border-radius: 5px; margin: 10px 0; }}
        .error {{ background: #f8d7da; color: #721c24; padding: 12px; border-radius: 5px; margin: 10px 0; }}
        .response {{ background: #e7f3ff; color: #004085; padding: 12px; border-radius: 5px; margin: 10px 0; }}
        .instructions {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .status-section {{ margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; }}
        .status-item {{ margin: 10px 0; padding: 10px; border-radius: 5px; }}
        .status-pending {{ background: #fff3cd; border-left: 4px solid #ffc107; }}
        .status-completed {{ background: #d1ecf1; border-left: 4px solid #17a2b8; }}
        .status-success {{ background: #d4edda; border-left: 4px solid #28a745; }}
        .status-failed {{ background: #f8d7da; border-left: 4px solid #dc3545; }}
        .worker-info {{ font-size: 0.9em; color: #666; margin-top: 5px; }}
        .output-box {{ background: #f8f9fa; padding: 10px; border-radius: 3px; margin-top: 8px; font-family: monospace; font-size: 0.9em; }}
        .refresh-btn {{ background: #6c757d; margin-top: 10px; padding: 8px 15px; font-size: 14px; }}
        .logout-link {{ float: right; margin-top: 10px; color: #dc3545; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>LAMControl Command Interface</h1>
        <a href="/r1/logout" class="logout-link">Logout</a>
        
        <div class="instructions">
            <strong>Instructions for R1:</strong>
            <ol>
                <li>Type your command in the text box below</li>
                <li>Click "Send Command" or press Enter</li>
                <li>Your command will be processed and sent to the appropriate device</li>
                <li>Task status will update automatically below</li>
            </ol>
        </div>
        
        {success_html}
        {error_html}
        {response_html}
        
        <form method="POST" id="commandForm">
            <div class="form-group">
                <label for="prompt">Enter your command:</label>
                <input type="text" 
                       id="prompt" 
                       name="prompt" 
                       placeholder="e.g., Turn on the lights, Play music on Spotify, Send a text to John..."
                       required
                       autofocus>
            </div>
            <button type="submit" id="submitBtn">Send Command</button>
        </form>
        
        <div class="status-section">
            <h3>Task Status</h3>
            <div id="taskStatus">
                {"<div class='status-pending'>Current Task: Processing...</div>" if task_id else "<div>No active tasks</div>"}
            </div>
            <button type="button" class="refresh-btn" onclick="refreshStatus()">Refresh Status</button>
        </div>
        
        <div class="instructions">
            <strong>Example commands:</strong>
            <ul>
                <li>"Turn on my desk lamp"</li>
                <li>"Play Weezer on YouTube"</li>
                <li>"Send a text to Mom saying I'll be late"</li>
                <li>"Set volume to 50 on my computer"</li>
                <li>"Open Google and search for pizza near me"</li>
            </ul>
        </div>
        
        <div class="status-section">
            <h3>Available Workers</h3>
            <div id="workerStatus">Loading worker information...</div>
        </div>
    </div>
    
    <script>
        let currentTaskId = "{task_id or ''}";
        let statusCheckInterval;
        
        // Auto-refresh status every 3 seconds if there's an active task
        if (currentTaskId) {{
            statusCheckInterval = setInterval(checkTaskStatus, 3000);
            checkTaskStatus(); // Check immediately
        }}
        
        function checkTaskStatus() {{
            if (!currentTaskId) return;
            
            fetch(`/api/task/${{currentTaskId}}/status`)
                .then(response => response.json())
                .then(data => {{
                    updateTaskStatus(data);
                    if (data.status === 'completed') {{
                        clearInterval(statusCheckInterval);
                        currentTaskId = '';
                    }}
                }})
                .catch(error => {{
                    console.error('Status check failed:', error);
                }});
        }}
        
        function updateTaskStatus(data) {{
            const statusDiv = document.getElementById('taskStatus');
            let statusClass = 'status-pending';
            let statusText = 'Processing...';
            
            if (data.status === 'completed') {{
                statusClass = data.success ? 'status-success' : 'status-failed';
                statusText = data.success ? 'Completed Successfully' : 'Failed';
            }}
            
            statusDiv.innerHTML = `
                <div class="${{statusClass}}">
                    <strong>Task Status:</strong> ${{statusText}}<br>
                    <strong>Task ID:</strong> ${{data.id}}<br>
                    ${{data.worker_id ? `<div class="worker-info">Processed by: ${{data.worker_id}}</div>` : ''}}
                    ${{data.message ? `<div class="worker-info">Message: ${{data.message}}</div>` : ''}}
                    ${{data.output ? `<div class="output-box">Output:<br>${{data.output}}</div>` : ''}}
                </div>
            `;
        }}
        
        function refreshStatus() {{
            // Refresh worker status
            fetch('/api/workers')
                .then(response => response.json())
                .then(data => {{
                    const workerDiv = document.getElementById('workerStatus');
                    if (data.workers && data.workers.length > 0) {{
                        workerDiv.innerHTML = data.workers.map(worker => `
                            <div class="status-item status-${{worker.status === 'online' ? 'success' : 'failed'}}">
                                <strong>${{worker.custom_name || worker.worker_id}}</strong> (${{worker.worker_type}})<br>
                                <span class="worker-info">Status: ${{worker.status}} | Tasks: ${{worker.current_tasks}}</span>
                                ${{worker.location ? `<br><span class="worker-info">Location: ${{worker.location}}</span>` : ''}}
                            </div>
                        `).join('');
                    }} else {{
                        workerDiv.innerHTML = '<div class="status-failed">No workers connected</div>';
                    }}
                }})
                .catch(error => {{
                    document.getElementById('workerStatus').innerHTML = '<div class="status-failed">Failed to load worker status</div>';
                }});
        }}
        
        // Refresh worker status on page load
        refreshStatus();
        
        // Form submission handling
        document.getElementById('commandForm').addEventListener('submit', function(e) {{
            document.getElementById('submitBtn').textContent = 'Processing...';
            document.getElementById('submitBtn').disabled = true;
        }});
    </script>
</body>
</html>
        '''
    
    def run(self, debug=False):
        """Start the distributed server"""
        # Set permanent session lifetime (7 days for R1)
        self.app.permanent_session_lifetime = 7 * 24 * 60 * 60  # 7 days in seconds
        
        logging.info(f"Starting LAMControl Distributed Server on {self.host}:{self.port}")
        print(f"\n=== LAMControl Distributed Server ===")
        print(f"Server running on: http://{self.host}:{self.port}")
        print(f"Admin Dashboard: http://{self.host}:{self.port}")
        print(f"R1 Login Page: http://{self.host}:{self.port}/r1/login")
        print(f"=====================================\n")
        
        self.socketio.run(self.app, host=self.host, port=self.port, debug=debug, allow_unsafe_werkzeug=True)


def main():
    """Main function to start the distributed server"""
    import argparse
    
    parser = argparse.ArgumentParser(description='LAMControl Distributed Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create and run server
    server = DistributedLAMServer(host=args.host, port=args.port)
    server.run(debug=args.debug)


if __name__ == "__main__":
    main()
