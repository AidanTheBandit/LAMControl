import os
import json
import logging
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from flask_socketio import SocketIO, emit
from functools import wraps
from utils import config, journal as journal_module

class LAMWebServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.app = Flask(__name__)
        self.app.secret_key = self._get_or_create_secret_key()
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        self.host = host
        self.port = port
        self.pending_prompts = []
        self.processed_prompts = []
        self.system_stats = {
            'uptime': datetime.now(timezone.utc),
            'total_prompts': 0,
            'processed_prompts': 0,
            'failed_prompts': 0
        }
        self.authenticated_sessions = set()
        self.setup_routes()
        self.setup_socketio_events()
        
        # Load or create admin credentials
        self.admin_credentials = self._load_admin_credentials()
        
    def _get_or_create_secret_key(self):
        """Get or create a secret key for Flask sessions"""
        secret_file = os.path.join(config.config.get('cache_dir', 'cache'), 'flask_secret.key')
        
        if os.path.exists(secret_file):
            with open(secret_file, 'r') as f:
                return f.read().strip()
        else:
            # Create cache directory if it doesn't exist
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
            # Create default admin credentials
            default_username = "admin"
            default_password = secrets.token_urlsafe(16)  # Generate random password
            
            # Hash the password
            password_hash = hashlib.sha256(default_password.encode()).hexdigest()
            
            credentials = {
                "username": default_username,
                "password_hash": password_hash
            }
            
            # Create cache directory if it doesn't exist
            os.makedirs(os.path.dirname(creds_file), exist_ok=True)
            
            with open(creds_file, 'w') as f:
                json.dump(credentials, f)
            
            logging.info(f"Created admin credentials - Username: {default_username}, Password: {default_password}")
            print(f"\n=== ADMIN CREDENTIALS ===")
            print(f"Username: {default_username}")
            print(f"Password: {default_password}")
            print(f"Please save these credentials securely!")
            print(f"=========================\n")
            
            return credentials
    
    def _verify_password(self, username: str, password: str) -> bool:
        """Verify admin credentials"""
        if username != self.admin_credentials["username"]:
            return False
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == self.admin_credentials["password_hash"]
    
    def require_auth(self, f):
        """Decorator to require authentication"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'authenticated' not in session or not session['authenticated']:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    def setup_socketio_events(self):
        """Setup SocketIO events for real-time updates"""
        
        @self.socketio.on('connect')
        def handle_connect():
            if 'authenticated' in session and session['authenticated']:
                emit('status', {'message': 'Connected to LAMControl'})
            else:
                return False  # Reject connection if not authenticated
        
        @self.socketio.on('request_stats')
        def handle_stats_request():
            if 'authenticated' in session and session['authenticated']:
                stats = self.get_system_stats()
                emit('stats_update', stats)

    def get_system_stats(self):
        """Get current system statistics"""
        uptime = datetime.now(timezone.utc) - self.system_stats['uptime']
        return {
            'uptime': str(uptime).split('.')[0],  # Remove microseconds
            'total_prompts': self.system_stats['total_prompts'],
            'processed_prompts': self.system_stats['processed_prompts'],
            'failed_prompts': self.system_stats['failed_prompts'],
            'pending_prompts': len([p for p in self.pending_prompts if not p['processed']]),
            'success_rate': (self.system_stats['processed_prompts'] / max(1, self.system_stats['total_prompts'])) * 100
        }

    def broadcast_prompt_update(self):
        """Broadcast prompt update to all connected clients"""
        try:
            self.socketio.emit('prompt_update', {
                'prompts': self.pending_prompts,
                'stats': self.get_system_stats()
            })
        except Exception as e:
            logging.error(f"Error broadcasting update: {e}")

    def add_processed_prompt(self, prompt_data: dict, response: str = None, error: str = None):
        """Add a processed prompt to the history"""
        processed_prompt = {
            **prompt_data,
            'completed_at': datetime.now(timezone.utc).isoformat(),
            'response': response,
            'error': error,
            'success': error is None
        }
        
        self.processed_prompts.append(processed_prompt)
        
        # Update stats
        if error:
            self.system_stats['failed_prompts'] += 1
        else:
            self.system_stats['processed_prompts'] += 1
        
        # Keep only last 100 processed prompts
        if len(self.processed_prompts) > 100:
            self.processed_prompts = self.processed_prompts[-100:]
        
        self.broadcast_prompt_update()
    
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
        
        @self.app.route('/api/prompt', methods=['POST'])
        def receive_prompt():
            """Endpoint for R1 to send prompts"""
            try:
                data = request.get_json()
                
                if not data or 'prompt' not in data:
                    return jsonify({'error': 'No prompt provided'}), 400
                
                prompt_data = {
                    'id': secrets.token_hex(8),
                    'prompt': data['prompt'],
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': data.get('source', 'r1'),
                    'processed': False,
                    'metadata': data.get('metadata', {})
                }
                
                self.pending_prompts.append(prompt_data)
                self.system_stats['total_prompts'] += 1
                
                logging.info(f"Received prompt from {prompt_data['source']}: {data['prompt']}")
                
                # Broadcast update to connected clients
                self.broadcast_prompt_update()
                
                return jsonify({
                    'status': 'success',
                    'message': 'Prompt received and queued for processing',
                    'id': prompt_data['id'],
                    'timestamp': prompt_data['timestamp']
                })
                
            except Exception as e:
                logging.error(f"Error receiving prompt: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/prompts', methods=['GET'])
        @self.require_auth
        def get_prompts():
            """Get pending prompts (for admin dashboard)"""
            return jsonify({
                'pending': self.pending_prompts,
                'processed': self.processed_prompts[-20:],  # Last 20 processed
                'stats': self.get_system_stats()
            })
        
        @self.app.route('/api/prompts/<prompt_id>/mark_processed', methods=['POST'])
        @self.require_auth
        def mark_prompt_processed(prompt_id):
            """Mark a prompt as processed"""
            data = request.get_json() or {}
            for prompt in self.pending_prompts:
                if prompt['id'] == prompt_id:
                    prompt['processed'] = True
                    prompt['completed_at'] = datetime.now(timezone.utc).isoformat()
                    
                    # Add to processed prompts
                    self.add_processed_prompt(
                        prompt, 
                        response=data.get('response'),
                        error=data.get('error')
                    )
                    
                    return jsonify({'status': 'success'})
            return jsonify({'error': 'Prompt not found'}), 404

        @self.app.route('/api/stats', methods=['GET'])
        @self.require_auth  
        def get_stats():
            """Get system statistics"""
            return jsonify(self.get_system_stats())

        @self.app.route('/api/prompt/<prompt_id>/status', methods=['GET'])
        def get_prompt_status(prompt_id):
            """Get status of a specific prompt (for R1 to check)"""
            # Check pending prompts
            for prompt in self.pending_prompts:
                if prompt['id'] == prompt_id:
                    return jsonify({
                        'id': prompt_id,
                        'status': 'processed' if prompt['processed'] else 'pending',
                        'timestamp': prompt['timestamp']
                    })
            
            # Check processed prompts
            for prompt in self.processed_prompts:
                if prompt['id'] == prompt_id:
                    return jsonify({
                        'id': prompt_id,
                        'status': 'completed',
                        'timestamp': prompt['timestamp'],
                        'completed_at': prompt.get('completed_at'),
                        'success': prompt.get('success', True),
                        'response': prompt.get('response'),
                        'error': prompt.get('error')
                    })
            
            return jsonify({'error': 'Prompt not found'}), 404
        
        @self.app.route('/api/test', methods=['POST'])
        @self.require_auth
        def test_prompt():
            """Test endpoint for sending prompts via web interface"""
            try:
                data = request.get_json()
                if not data or 'prompt' not in data:
                    return jsonify({'error': 'No prompt provided'}), 400
                
                prompt_data = {
                    'id': secrets.token_hex(8),
                    'prompt': data['prompt'],
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': 'web_admin',
                    'processed': False,
                    'metadata': {'test': True}
                }
                
                self.pending_prompts.append(prompt_data)
                self.system_stats['total_prompts'] += 1
                
                logging.info(f"Test prompt from admin: {data['prompt']}")
                
                # Broadcast update to connected clients
                self.broadcast_prompt_update()
                
                return jsonify({
                    'status': 'success',
                    'message': 'Test prompt added to queue',
                    'id': prompt_data['id'],
                    'timestamp': prompt_data['timestamp']
                })
                
            except Exception as e:
                logging.error(f"Error adding test prompt: {e}")
                return jsonify({'error': 'Internal server error'}), 500

        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'version': '2.0',
                'mode': 'web'
            })
    
    def get_next_prompt(self) -> Optional[Dict]:
        """Get the next unprocessed prompt with full data"""
        for prompt in self.pending_prompts:
            if not prompt['processed']:
                prompt['processed'] = True
                prompt['started_at'] = datetime.now(timezone.utc).isoformat()
                return prompt
        return None

    def mark_prompt_completed(self, prompt_id: str, response: str = None, error: str = None):
        """Mark a prompt as completed with response or error"""
        for prompt in self.pending_prompts:
            if prompt['id'] == prompt_id:
                self.add_processed_prompt(prompt, response, error)
                break
    
    def has_pending_prompts(self) -> bool:
        """Check if there are any pending prompts"""
        return any(not prompt['processed'] for prompt in self.pending_prompts)
    
    def _get_login_template(self):
        """Get the HTML template for login page"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LAMControl - Login</title>
    <style>
        body {
            background-color: #1a1a1a;
            color: #ffffff;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .login-container {
            background-color: #2d2d2d;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            width: 300px;
        }
        .logo {
            text-align: center;
            margin-bottom: 2rem;
        }
        .logo h1 {
            color: #ff6600;
            margin: 0;
            font-size: 2rem;
        }
        .form-group {
            margin-bottom: 1rem;
        }
        label {
            display: block;
            margin-bottom: 0.5rem;
            color: #cccccc;
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 0.75rem;
            border: none;
            border-radius: 5px;
            background-color: #333333;
            color: #ffffff;
            box-sizing: border-box;
        }
        input[type="text"]:focus, input[type="password"]:focus {
            outline: none;
            background-color: #404040;
        }
        .submit-btn {
            width: 100%;
            padding: 0.75rem;
            background-color: #ff6600;
            color: #ffffff;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: bold;
        }
        .submit-btn:hover {
            background-color: #e55a00;
        }
        .error {
            color: #ff4444;
            text-align: center;
            margin-top: 1rem;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <h1>LAMControl</h1>
        </div>
        <form method="POST">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit" class="submit-btn">Login</button>
        </form>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
    </div>
</body>
</html>
        '''
    
    def _get_dashboard_template(self):
        """Get the HTML template for admin dashboard"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LAMControl - Dashboard</title>
    <style>
        body {
            background-color: #1a1a1a;
            color: #ffffff;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid #333333;
        }
        .header h1 {
            color: #ff6600;
            margin: 0;
        }
        .logout-btn {
            background-color: #666666;
            color: #ffffff;
            padding: 0.5rem 1rem;
            text-decoration: none;
            border-radius: 5px;
        }
        .logout-btn:hover {
            background-color: #777777;
        }
        .dashboard-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
        }
        .panel {
            background-color: #2d2d2d;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        .panel h2 {
            color: #ff6600;
            margin-top: 0;
        }
        .prompt-list {
            max-height: 400px;
            overflow-y: auto;
        }
        .prompt-item {
            background-color: #333333;
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 5px;
            border-left: 4px solid #ff6600;
        }
        .prompt-item.processed {
            border-left-color: #66ff66;
            opacity: 0.7;
        }
        .prompt-meta {
            font-size: 0.8rem;
            color: #cccccc;
            margin-bottom: 0.5rem;
        }
        .test-form {
            margin-top: 1rem;
        }
        .test-input {
            width: 100%;
            padding: 0.75rem;
            border: none;
            border-radius: 5px;
            background-color: #333333;
            color: #ffffff;
            margin-bottom: 1rem;
            box-sizing: border-box;
        }
        .test-btn {
            background-color: #ff6600;
            color: #ffffff;
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }
        .test-btn:hover {
            background-color: #e55a00;
        }
        .refresh-btn {
            background-color: #0066cc;
            color: #ffffff;
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            margin-bottom: 1rem;
        }
        .refresh-btn:hover {
            background-color: #0052a3;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>LAMControl Dashboard</h1>
        <a href="/logout" class="logout-btn">Logout</a>
    </div>
    
    <div class="dashboard-grid">
        <div class="panel">
            <h2>Received Prompts</h2>
            <button class="refresh-btn" onclick="loadPrompts()">Refresh</button>
            <div id="prompt-list" class="prompt-list">
                Loading prompts...
            </div>
        </div>
        
        <div class="panel">
            <h2>Test Prompt</h2>
            <p>Send a test prompt to LAMControl for testing purposes.</p>
            <form class="test-form" onsubmit="sendTestPrompt(event)">
                <input type="text" id="test-prompt" class="test-input" placeholder="Enter test prompt..." required>
                <button type="submit" class="test-btn">Send Test Prompt</button>
            </form>
        </div>
    </div>

    <script>
        function loadPrompts() {
            fetch('/api/prompts')
                .then(response => response.json())
                .then(prompts => {
                    const promptList = document.getElementById('prompt-list');
                    if (prompts.length === 0) {
                        promptList.innerHTML = '<p>No prompts received yet.</p>';
                        return;
                    }
                    
                    promptList.innerHTML = prompts.map(prompt => `
                        <div class="prompt-item ${prompt.processed ? 'processed' : ''}">
                            <div class="prompt-meta">
                                ID: ${prompt.id} | 
                                Source: ${prompt.source} | 
                                Time: ${new Date(prompt.timestamp).toLocaleString()} |
                                Status: ${prompt.processed ? 'Processed' : 'Pending'}
                            </div>
                            <div><strong>Prompt:</strong> ${prompt.prompt}</div>
                        </div>
                    `).join('');
                })
                .catch(error => {
                    console.error('Error loading prompts:', error);
                    document.getElementById('prompt-list').innerHTML = '<p>Error loading prompts.</p>';
                });
        }
        
        function sendTestPrompt(event) {
            event.preventDefault();
            const prompt = document.getElementById('test-prompt').value;
            
            fetch('/api/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt: prompt })
            })
            .then(response => response.json())
            .then(result => {
                if (result.status === 'success') {
                    document.getElementById('test-prompt').value = '';
                    loadPrompts(); // Refresh the prompt list
                    alert('Test prompt sent successfully!');
                } else {
                    alert('Error sending test prompt: ' + result.error);
                }
            })
            .catch(error => {
                console.error('Error sending test prompt:', error);
                alert('Error sending test prompt.');
            });
        }
        
        // Load prompts on page load
        loadPrompts();
        
        // Auto-refresh prompts every 5 seconds
        setInterval(loadPrompts, 5000);
    </script>
</body>
</html>
        '''
    
    def run(self, debug=False):
        """Start the web server"""
        logging.info(f"Starting LAMControl web server on {self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=debug, threaded=True)
