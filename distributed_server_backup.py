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
        
        self.setup_routes()
        self.setup_socketio_events()
        self.admin_credentials = self._load_admin_credentials()
        
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
                return json.load(f)
        else:
            os.makedirs(os.path.dirname(creds_file), exist_ok=True)
            username = 'admin'
            password = secrets.token_urlsafe(16)
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            creds = {
                'username': username,
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
        
        # Worker Management Endpoints
        @self.app.route('/api/worker/register', methods=['POST'])
        def register_worker():
            """Register a new worker node"""
            try:
                data = request.get_json()
                required_fields = ['worker_id', 'worker_type', 'capabilities', 'endpoint']
                
                if not all(field in data for field in required_fields):
                    return jsonify({'error': 'Missing required fields'}), 400
                
                worker = WorkerNode(
                    worker_id=data['worker_id'],
                    worker_type=data['worker_type'],
                    capabilities=data['capabilities'],
                    endpoint=data['endpoint'],
                    api_key=secrets.token_hex(16)
                )
                
                self.workers[worker.worker_id] = worker
                self.stats['active_workers'] = len([w for w in self.workers.values() if w.status == 'online'])
                
                logging.info(f"Registered worker: {worker.worker_id} ({worker.worker_type})")
                self.broadcast_worker_update()
                
                return jsonify({
                    'status': 'success',
                    'worker_id': worker.worker_id,
                    'api_key': worker.api_key
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
                
                # Update task count if provided
                data = request.get_json() or {}
                if 'current_tasks' in data:
                    self.workers[worker_id].current_tasks = data['current_tasks']
                
                return jsonify({'status': 'success'})
            else:
                return jsonify({'error': 'Worker not found'}), 404
        
        @self.app.route('/api/workers', methods=['GET'])
        @self.require_auth
        def get_workers():
            """Get list of all workers"""
            workers_data = []
            for worker in self.workers.values():
                workers_data.append({
                    'worker_id': worker.worker_id,
                    'worker_type': worker.worker_type,
                    'capabilities': worker.capabilities,
                    'status': worker.status,
                    'current_tasks': worker.current_tasks,
                    'last_heartbeat': worker.last_heartbeat.isoformat()
                })
            
            return jsonify({
                'workers': workers_data,
                'total_workers': len(workers_data),
                'online_workers': len([w for w in workers_data if w['status'] == 'online'])
            })
        
        # R1 Web Interface for browser navigation
        @self.app.route('/r1', methods=['GET', 'POST'])
        def r1_interface():
            """Simple interface for R1 to navigate and send prompts"""
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
                    
                    response = self._process_prompt(prompt_data)
                    
                    return render_template_string(self._get_r1_template(), 
                                                success=f"Command sent: {prompt}",
                                                response=response.get('message', 'Processing...'))
                
                except Exception as e:
                    logging.error(f"Error processing R1 prompt: {e}")
                    return render_template_string(self._get_r1_template(), 
                                                error="Failed to process command")
            
            return render_template_string(self._get_r1_template())
        
        # Auto-login route for R1 (with persistent session)
        @self.app.route('/r1/auth/<token>')
        def r1_auto_login(token):
            """Auto-login for R1 using a special token"""
            # Use a simple token for R1 auto-login (in production, make this more secure)
            if token == self._get_r1_token():
                session['authenticated'] = True
                session['username'] = 'r1_device'
                session.permanent = True  # Make session persistent
                return redirect(url_for('r1_interface'))
            else:
                return redirect(url_for('login'))
    
    def _get_r1_token(self):
        """Get or create R1 auto-login token"""
        token_file = os.path.join(config.config.get('cache_dir', 'cache'), 'r1_token.txt')
        
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                return f.read().strip()
        else:
            token = secrets.token_urlsafe(32)
            os.makedirs(os.path.dirname(token_file), exist_ok=True)
            with open(token_file, 'w') as f:
                f.write(token)
            return token
    
    def _verify_password(self, username: str, password: str) -> bool:
        """Verify admin credentials"""
        if username != self.admin_credentials["username"]:
            return False
        
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
        """Get admin dashboard template"""
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
        .worker { padding: 10px; margin: 5px 0; background: #333; border-radius: 3px; }
        .worker.online { border-left: 4px solid #00ff00; }
        .worker.offline { border-left: 4px solid #ff0000; }
        .recent-tasks { background: #2d2d2d; padding: 15px; border-radius: 5px; }
        .r1-link { background: #ff6600; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0; }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head>
<body>
    <div class="header">
        <h1>LAMControl Distributed Server</h1>
        <p>Central server managing worker nodes and R1 prompts</p>
        <a href="/r1/auth/''' + self._get_r1_token() + '''" class="r1-link">R1 Interface Link</a>
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
                            <strong>${worker.worker_id}</strong> (${worker.worker_type})
                            <br>Status: ${worker.status} | Tasks: ${worker.current_tasks}
                            <br>Capabilities: ${worker.capabilities.join(', ')}
                        </div>`
                    ).join('');
                }
            });
        }
        
        socket.on('worker_update', function(data) {
            updateStats();
        });
        
        // Update stats every 5 seconds
        setInterval(updateStats, 5000);
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
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
    </div>
</body>
</html>
        '''
    
    def _get_r1_template(self, success=None, error=None, response=None):
        """Get R1-friendly interface template"""
        return f'''
<!DOCTYPE html>
<html>
<head>
    <title>LAMControl</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
        h1 {{ color: #ff6600; text-align: center; }}
        .form-group {{ margin: 15px 0; }}
        label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
        input[type="text"] {{ width: 100%; padding: 15px; font-size: 16px; border: 2px solid #ddd; border-radius: 5px; }}
        button {{ width: 100%; padding: 15px; font-size: 16px; background: #ff6600; color: white; border: none; border-radius: 5px; cursor: pointer; }}
        button:hover {{ background: #e55a00; }}
        .success {{ background: #d4edda; color: #155724; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        .error {{ background: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        .response {{ background: #e7f3ff; color: #004085; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        .instructions {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>LAMControl Command Interface</h1>
        
        <div class="instructions">
            <strong>Instructions for R1:</strong>
            <ol>
                <li>Type your command in the text box below</li>
                <li>Click "Send Command" or press Enter</li>
                <li>Your command will be processed and sent to the appropriate device</li>
            </ol>
        </div>
        
        {"<div class='success'>" + success + "</div>" if success else ""}
        {"<div class='error'>" + error + "</div>" if error else ""}
        {"<div class='response'><strong>Response:</strong> " + response + "</div>" if response else ""}
        
        <form method="POST">
            <div class="form-group">
                <label for="prompt">Enter your command:</label>
                <input type="text" 
                       id="prompt" 
                       name="prompt" 
                       placeholder="e.g., Turn on the lights, Play music on Spotify, Send a text to John..."
                       required
                       autofocus>
            </div>
            <button type="submit">Send Command</button>
        </form>
        
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
    </div>
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
        print(f"R1 Interface: http://{self.host}:{self.port}/r1/auth/{self._get_r1_token()}")
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
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'version': '3.0-distributed',
                'workers': len(self.workers),
                'online_workers': len([w for w in self.workers.values() if w.status == 'online'])
            })
        
        # R1 Web Interface Routes (Public - No Auth Required)
        @self.app.route('/r1', methods=['GET'])
        def r1_interface():
            """R1 web interface - public page for R1 to interact with"""
            return render_template_string(self._get_r1_interface_template())
        
        @self.app.route('/r1/submit', methods=['POST'])
        def r1_submit():
            """R1 prompt submission endpoint"""
            try:
                # Handle both form data and JSON
                if request.is_json:
                    data = request.get_json()
                    prompt = data.get('prompt', '')
                else:
                    prompt = request.form.get('prompt', '')
                
                if not prompt.strip():
                    if request.is_json:
                        return jsonify({'error': 'No prompt provided'}), 400
                    else:
                        return render_template_string(self._get_r1_error_template(), 
                                                    prompt='', error='No prompt provided')
                
                prompt_id = secrets.token_hex(8)
                prompt_data = {
                    'id': prompt_id,
                    'prompt': prompt,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': 'r1_web',
                    'metadata': {}
                }
                
                # Process prompt with LLM and route to worker
                response = self._process_prompt(prompt_data)
                
                self.stats['total_prompts'] += 1
                
                # Return response for R1 to display
                if request.is_json:
                    return jsonify({
                        'status': 'success',
                        'id': prompt_id,
                        'response': response
                    })
                else:
                    # Return HTML response for web form submission
                    return render_template_string(self._get_r1_response_template(), 
                                                prompt=prompt, response=response, prompt_id=prompt_id)
                
            except Exception as e:
                logging.error(f"Error processing R1 prompt: {e}")
                if request.is_json:
                    return jsonify({'error': 'Failed to process prompt'}), 500
                else:
                    return render_template_string(self._get_r1_error_template(), 
                                                prompt=prompt if 'prompt' in locals() else '', error=str(e))
        
        @self.app.route('/r1/status/<prompt_id>', methods=['GET'])
        def r1_status(prompt_id):
            """Check status of R1 prompt - public endpoint"""
            # Implementation for status checking
            return jsonify({'status': 'completed', 'id': prompt_id})
    
    def _verify_password(self, username: str, password: str) -> bool:
        """Verify admin credentials"""
        if username != self.admin_credentials["username"]:
            return False
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == self.admin_credentials["password_hash"]
    
    def _process_prompt(self, prompt_data: dict) -> str:
        """Process a prompt using LLM and route to workers"""
        try:
            prompt = prompt_data['prompt']
            
            # Parse with LLM
            parsed_command = llm_parse.LLMParse(prompt)
            logging.info(f"LLM parsed command: {parsed_command}")
            
            if parsed_command == "x":
                return "I couldn't understand that command. Please try rephrasing."
            
            # Split multiple commands
            tasks = parsed_command.split("&&")
            responses = []
            
            for task in tasks:
                if task.strip() != "x":
                    response = self._route_task(task.strip())
                    responses.append(response)
            
            return "; ".join(responses) if responses else "Task completed successfully"
            
        except Exception as e:
            logging.error(f"Error processing prompt: {e}")
            return f"Error processing command: {str(e)}"
    
    def _route_task(self, task: str) -> str:
        """Route a task to the appropriate worker"""
        try:
            parts = task.split()
            if len(parts) < 2:
                return "Invalid task format"
            
            integration = parts[0].lower()
            
            # Find appropriate worker
            worker = self._find_worker_for_integration(integration)
            if not worker:
                return f"No worker available for {integration} integration"
            
            # Send task to worker
            response = self._send_task_to_worker(worker, task)
            return response
            
        except Exception as e:
            logging.error(f"Error routing task: {e}")
            return f"Error routing task: {str(e)}"
    
    def _find_worker_for_integration(self, integration: str) -> Optional[WorkerNode]:
        """Find an available worker that can handle the integration"""
        for worker in self.workers.values():
            if (worker.status == "online" and 
                integration in worker.capabilities and 
                worker.current_tasks < worker.max_concurrent_tasks):
                return worker
        return None
    
    def _send_task_to_worker(self, worker: WorkerNode, task: str) -> str:
        """Send a task to a specific worker"""
        try:
            payload = {
                'task': task,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            headers = {
                'Authorization': f'Bearer {worker.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{worker.endpoint}/execute",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', 'Task completed')
            else:
                return f"Worker error: {response.status_code}"
                
        except Exception as e:
            logging.error(f"Error sending task to worker: {e}")
            return f"Failed to communicate with worker: {str(e)}"
    
    async def _route_task_to_worker(self, task_data: dict):
        """Async version of task routing"""
        try:
            task = task_data.get('task', '')
            prompt_id = task_data.get('id', '')
            
            # Process the task synchronously for now
            response = self._route_task(task)
            
            # Update task completion status
            logging.info(f"Completed task {prompt_id}: {response}")
            
        except Exception as e:
            logging.error(f"Error in async task routing: {e}")
    
    def broadcast_worker_update(self):
        """Broadcast worker status update to admin clients"""
        try:
            self.socketio.emit('worker_update', {
                'workers': len(self.workers),
                'online': len([w for w in self.workers.values() if w.status == 'online'])
            }, room='admin')
        except Exception as e:
            logging.error(f"Error broadcasting worker update: {e}")
    
    def _get_login_template(self, error=None):
        """Login page template"""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>LAMControl Distributed Server</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 400px; margin: 50px auto; padding: 20px; }
        input { width: 100%; padding: 10px; margin: 10px 0; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; cursor: pointer; }
        .error { color: red; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>LAMControl Distributed Server</h1>
    <form method="POST">
        <input type="text" name="username" placeholder="Username" required>
        <input type="password" name="password" placeholder="Password" required>
        <button type="submit">Login</button>
    </form>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
</body>
</html>
        '''
    
    def _get_dashboard_template(self):
        """Admin dashboard template"""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>LAMControl Distributed Server</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .card { border: 1px solid #ddd; padding: 20px; border-radius: 8px; }
        .worker { margin: 10px 0; padding: 10px; border-left: 4px solid #007bff; }
        .worker.offline { border-left-color: #dc3545; }
        .status { font-weight: bold; }
        .online { color: green; }
        .offline { color: red; }
    </style>
</head>
<body>
    <h1>LAMControl Distributed Server Dashboard</h1>
    
    <div class="grid">
        <div class="card">
            <h2>System Status</h2>
            <p>Server Status: <span class="status online">Online</span></p>
            <p>Total Workers: <span id="totalWorkers">0</span></p>
            <p>Online Workers: <span id="onlineWorkers">0</span></p>
            <p>Total Prompts: <span id="totalPrompts">0</span></p>
        </div>
        
        <div class="card">
            <h2>Test Prompt</h2>
            <input type="text" id="testPrompt" placeholder="Enter test prompt..." style="width: 80%;">
            <button onclick="sendTestPrompt()">Send</button>
            <div id="testResult" style="margin-top: 10px;"></div>
        </div>
    </div>
    
    <div class="card">
        <h2>Registered Workers</h2>
        <div id="workersList"></div>
    </div>
    
    <p><a href="/logout">Logout</a></p>
    
    <script>
        const socket = io();
        
        socket.on('connect', function() {
            console.log('Connected to server');
            loadWorkers();
        });
        
        socket.on('worker_update', function(data) {
            document.getElementById('totalWorkers').textContent = data.workers;
            document.getElementById('onlineWorkers').textContent = data.online;
        });
        
        function loadWorkers() {
            fetch('/api/workers')
            .then(response => response.json())
            .then(data => {
                const workersList = document.getElementById('workersList');
                workersList.innerHTML = '';
                
                data.workers.forEach(worker => {
                    const workerDiv = document.createElement('div');
                    workerDiv.className = 'worker ' + (worker.status === 'online' ? 'online' : 'offline');
                    workerDiv.innerHTML = `
                        <strong>${worker.worker_id}</strong> (${worker.worker_type})
                        <br>Status: <span class="${worker.status}">${worker.status}</span>
                        <br>Capabilities: ${worker.capabilities.join(', ')}
                        <br>Current Tasks: ${worker.current_tasks}
                        <br>Last Heartbeat: ${new Date(worker.last_heartbeat).toLocaleString()}
                    `;
                    workersList.appendChild(workerDiv);
                });
                
                document.getElementById('totalWorkers').textContent = data.total_workers;
                document.getElementById('onlineWorkers').textContent = data.online_workers;
            });
        }
        
        function sendTestPrompt() {
            const prompt = document.getElementById('testPrompt').value;
            if (!prompt) return;
            
            fetch('/api/prompt', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({prompt: prompt, source: 'admin_test'})
            })
            .then(response => response.json())
            .then(data => {
                const result = document.getElementById('testResult');
                if (data.status === 'success') {
                    result.innerHTML = '<p style="color: green;">Success: ' + data.response + '</p>';
                } else {
                    result.innerHTML = '<p style="color: red;">Error: ' + data.error + '</p>';
                }
                document.getElementById('testPrompt').value = '';
            });
        }
        
        // Auto-refresh workers every 30 seconds
        setInterval(loadWorkers, 30000);
    </script>
</body>
</html>
        '''
    
    def _get_r1_interface_template(self):
        """R1 web interface template - simple form for R1 to use"""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>LAMControl - R1 Interface</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
            border: 1px solid rgba(255, 255, 255, 0.18);
        }
        h1 { 
            text-align: center; 
            margin-bottom: 30px;
            font-size: 2.5em;
            font-weight: 300;
        }
        .subtitle {
            text-align: center;
            margin-bottom: 40px;
            opacity: 0.8;
            font-size: 1.2em;
        }
        form { 
            display: flex; 
            flex-direction: column; 
            gap: 20px; 
        }
        textarea { 
            width: 100%; 
            padding: 20px; 
            font-size: 18px;
            border: none;
            border-radius: 15px;
            background: rgba(255, 255, 255, 0.9);
            color: #333;
            resize: vertical;
            min-height: 120px;
            box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        textarea:focus {
            outline: none;
            box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.1), 0 0 0 3px rgba(255, 255, 255, 0.3);
        }
        button { 
            padding: 20px 40px; 
            font-size: 20px;
            font-weight: 600;
            background: linear-gradient(135deg, #ff6b6b, #ffa500);
            color: white; 
            border: none; 
            border-radius: 15px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(255, 107, 107, 0.4);
        }
        button:active {
            transform: translateY(0);
        }
        .examples {
            margin-top: 30px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
        }
        .examples h3 {
            margin-top: 0;
            color: #ffa500;
        }
        .examples ul {
            margin: 0;
            padding-left: 20px;
        }
        .examples li {
            margin: 8px 0;
            opacity: 0.9;
        }
        .status {
            text-align: center;
            margin-top: 20px;
            padding: 15px;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.1);
        }
        @media (max-width: 600px) {
            body { padding: 10px; }
            .container { padding: 20px; }
            h1 { font-size: 2em; }
            textarea { font-size: 16px; padding: 15px; }
            button { font-size: 18px; padding: 15px 30px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🐰 LAMControl</h1>
        <div class="subtitle">Distributed AI Assistant Interface</div>
        
        <form action="/r1/submit" method="POST" id="promptForm">
            <textarea name="prompt" placeholder="Tell me what you'd like me to do..." required autofocus></textarea>
            <button type="submit" id="submitBtn">Send Command</button>
        </form>
        
        <div class="examples">
            <h3>Example Commands:</h3>
            <ul>
                <li>"Open YouTube and search for relaxing music"</li>
                <li>"Turn up the volume on my computer to 70%"</li>
                <li>"Send a message to John on Telegram saying I'm running late"</li>
                <li>"Search Google for the weather forecast"</li>
                <li>"Lock my computer"</li>
            </ul>
        </div>
        
        <div class="status" id="statusDiv" style="display: none;"></div>
    </div>
    
    <script>
        document.getElementById('promptForm').addEventListener('submit', function(e) {
            const btn = document.getElementById('submitBtn');
            const status = document.getElementById('statusDiv');
            
            btn.textContent = 'Processing...';
            btn.disabled = true;
            status.style.display = 'block';
            status.innerHTML = '⏳ Processing your command...';
            status.style.background = 'rgba(255, 165, 0, 0.2)';
        });
    </script>
</body>
</html>
        '''
    
    def _get_r1_response_template(self):
        """R1 response template"""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>LAMControl - Response</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
            border: 1px solid rgba(255, 255, 255, 0.18);
        }
        h1 { text-align: center; margin-bottom: 30px; font-size: 2.5em; font-weight: 300; }
        .success {
            background: rgba(40, 167, 69, 0.2);
            border: 1px solid rgba(40, 167, 69, 0.3);
            padding: 20px;
            border-radius: 15px;
            margin: 20px 0;
        }
        .prompt-box {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 15px;
            margin: 20px 0;
            border-left: 4px solid #ffa500;
        }
        .response-box {
            background: rgba(40, 167, 69, 0.1);
            padding: 20px;
            border-radius: 15px;
            margin: 20px 0;
            border-left: 4px solid #28a745;
        }
        .back-btn {
            display: inline-block;
            padding: 15px 30px;
            background: linear-gradient(135deg, #6c757d, #495057);
            color: white;
            text-decoration: none;
            border-radius: 10px;
            margin-top: 20px;
            transition: all 0.3s ease;
        }
        .back-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(108, 117, 125, 0.3);
            color: white;
            text-decoration: none;
        }
        .meta {
            font-size: 0.9em;
            opacity: 0.7;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ Command Completed</h1>
        
        <div class="prompt-box">
            <h3>Your Command:</h3>
            <p>{{ prompt }}</p>
        </div>
        
        <div class="response-box">
            <h3>Response:</h3>
            <p>{{ response }}</p>
            <div class="meta">Command ID: {{ prompt_id }}</div>
        </div>
        
        <a href="/r1" class="back-btn">Send Another Command</a>
    </div>
</body>
</html>
        '''
    
    def _get_r1_error_template(self):
        """R1 error template"""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>LAMControl - Error</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
            border: 1px solid rgba(255, 255, 255, 0.18);
        }
        h1 { text-align: center; margin-bottom: 30px; font-size: 2.5em; font-weight: 300; }
        .error {
            background: rgba(220, 53, 69, 0.2);
            border: 1px solid rgba(220, 53, 69, 0.3);
            padding: 20px;
            border-radius: 15px;
            margin: 20px 0;
            border-left: 4px solid #dc3545;
        }
        .prompt-box {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 15px;
            margin: 20px 0;
            border-left: 4px solid #ffa500;
        }
        .back-btn {
            display: inline-block;
            padding: 15px 30px;
            background: linear-gradient(135deg, #6c757d, #495057);
            color: white;
            text-decoration: none;
            border-radius: 10px;
            margin-top: 20px;
            transition: all 0.3s ease;
        }
        .back-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(108, 117, 125, 0.3);
            color: white;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>❌ Error</h1>
        
        {% if prompt %}
        <div class="prompt-box">
            <h3>Your Command:</h3>
            <p>{{ prompt }}</p>
        </div>
        {% endif %}
        
        <div class="error">
            <h3>Error Message:</h3>
            <p>{{ error }}</p>
        </div>
        
        <a href="/r1" class="back-btn">Try Again</a>
    </div>
</body>
</html>
        '''
    
    def run(self, debug=False):
        """Start the distributed server"""
        logging.info(f"Starting LAMControl Distributed Server on {self.host}:{self.port}")
        self.socketio.run(self.app, host=self.host, port=self.port, debug=debug)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    server = DistributedLAMServer()
    server.run()
