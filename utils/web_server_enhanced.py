import os
import json
import logging
import secrets
import hashlib
from datetime import datetime, timezone
from typing import Dict, Optional, List
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from flask_socketio import SocketIO, emit
from functools import wraps
from utils import config

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
        self.connected_integrations = [
            'Browser Automation',
            'Computer Control', 
            'Discord',
            'Telegram',
            'Google Services',
            'Facebook',
            'Open Interpreter'
        ]
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
            default_username = "admin"
            default_password = secrets.token_urlsafe(16)
            password_hash = hashlib.sha256(default_password.encode()).hexdigest()
            
            credentials = {
                "username": default_username,
                "password_hash": password_hash
            }
            
            os.makedirs(os.path.dirname(creds_file), exist_ok=True)
            with open(creds_file, 'w') as f:
                json.dump(credentials, f)
            
            logging.info(f"Created admin credentials - Username: {default_username}, Password: {default_password}")
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
                emit('status', {'message': 'Connected'})
            else:
                return False

    def get_system_stats(self):
        """Get current system statistics"""
        uptime = datetime.now(timezone.utc) - self.system_stats['uptime']
        return {
            'uptime': str(uptime).split('.')[0],
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
        
        if error:
            self.system_stats['failed_prompts'] += 1
        else:
            self.system_stats['processed_prompts'] += 1
        
        if len(self.processed_prompts) > 50:
            self.processed_prompts = self.processed_prompts[-50:]
        
        self.broadcast_prompt_update()
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            if 'authenticated' not in session or not session['authenticated']:
                return redirect(url_for('login'))
            return render_template_string(self._get_simple_template())
        
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
                self.broadcast_prompt_update()
                
                return jsonify({
                    'status': 'success',
                    'message': 'Prompt received',
                    'id': prompt_data['id']
                })
                
            except Exception as e:
                logging.error(f"Error receiving prompt: {e}")
                return jsonify({'error': 'Failed to process prompt'}), 500
        
        @self.app.route('/api/prompts', methods=['GET'])
        @self.require_auth
        def get_prompts():
            """Get prompts and stats"""
            return jsonify({
                'pending': self.pending_prompts,
                'processed': self.processed_prompts[-10:],
                'stats': self.get_system_stats(),
                'integrations': self.connected_integrations
            })
        
        @self.app.route('/api/prompt/<prompt_id>/status', methods=['GET'])
        def get_prompt_status(prompt_id):
            """Get status of a specific prompt"""
            for prompt in self.pending_prompts:
                if prompt['id'] == prompt_id:
                    return jsonify({
                        'id': prompt_id,
                        'status': 'processed' if prompt['processed'] else 'pending'
                    })
            
            for prompt in self.processed_prompts:
                if prompt['id'] == prompt_id:
                    return jsonify({
                        'id': prompt_id,
                        'status': 'completed',
                        'success': prompt.get('success', True),
                        'response': prompt.get('response'),
                        'error': prompt.get('error')
                    })
            
            return jsonify({'error': 'Prompt not found'}), 404
        
        @self.app.route('/api/send', methods=['POST'])
        @self.require_auth
        def send_prompt():
            """Send prompt from web interface"""
            try:
                data = request.get_json()
                if not data or 'prompt' not in data:
                    return jsonify({'error': 'No prompt provided'}), 400
                
                prompt_data = {
                    'id': secrets.token_hex(8),
                    'prompt': data['prompt'],
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': 'web',
                    'processed': False
                }
                
                self.pending_prompts.append(prompt_data)
                self.system_stats['total_prompts'] += 1
                
                logging.info(f"Web prompt: {data['prompt']}")
                self.broadcast_prompt_update()
                
                return jsonify({
                    'status': 'success',
                    'id': prompt_data['id']
                })
                
            except Exception as e:
                logging.error(f"Error sending prompt: {e}")
                return jsonify({'error': 'Failed to send prompt'}), 500

        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'version': '2.0'
            })
    
    def get_next_prompt(self) -> Optional[Dict]:
        """Get the next unprocessed prompt"""
        for prompt in self.pending_prompts:
            if not prompt['processed']:
                prompt['processed'] = True
                prompt['started_at'] = datetime.now(timezone.utc).isoformat()
                return prompt
        return None

    def mark_prompt_completed(self, prompt_id: str, response: str = None, error: str = None):
        """Mark a prompt as completed"""
        for prompt in self.pending_prompts:
            if prompt['id'] == prompt_id:
                self.add_processed_prompt(prompt, response, error)
                break
    
    def has_pending_prompts(self) -> bool:
        """Check if there are any pending prompts"""
        return any(not prompt['processed'] for prompt in self.pending_prompts)
    
    def _get_login_template(self):
        """Simple login page"""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>LAMControl Login</title>
</head>
<body>
    <h1>LAMControl Login</h1>
    <form method="POST">
        <p>Username: <input type="text" name="username" required></p>
        <p>Password: <input type="password" name="password" required></p>
        <p><input type="submit" value="Login"></p>
    </form>
    {% if error %}
    <p style="color: red;">{{ error }}</p>
    {% endif %}
</body>
</html>
        '''
    
    def _get_simple_template(self):
        """Simple R1-friendly interface"""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>LAMControl</title>
</head>
<body>
    <h1>LAMControl</h1>
    
    <h2>Send Command</h2>
    <form id="promptForm">
        <input type="text" id="promptInput" placeholder="Enter command..." required style="width: 300px;">
        <button type="submit">Send</button>
    </form>
    
    <div id="result" style="margin-top: 20px;"></div>
    
    <h2>Connected Integrations</h2>
    <ul id="integrations"></ul>
    
    <h2>Recent Commands</h2>
    <div id="recentCommands"></div>
    
    <p><a href="/logout">Logout</a></p>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        const socket = io();
        const resultDiv = document.getElementById('result');
        const integrationsDiv = document.getElementById('integrations');
        const recentDiv = document.getElementById('recentCommands');
        
        // Send prompt
        document.getElementById('promptForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const prompt = document.getElementById('promptInput').value;
            
            fetch('/api/send', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({prompt: prompt})
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    resultDiv.innerHTML = '<p style="color: green;">SUCCESS: Command sent</p>';
                    document.getElementById('promptInput').value = '';
                } else {
                    resultDiv.innerHTML = '<p style="color: red;">FAIL: ' + data.error + '</p>';
                }
            })
            .catch(error => {
                resultDiv.innerHTML = '<p style="color: red;">FAIL: Network error</p>';
            });
        });
        
        // Load data
        function loadData() {
            fetch('/api/prompts')
            .then(response => response.json())
            .then(data => {
                // Update integrations
                integrationsDiv.innerHTML = data.integrations.map(i => '<li>' + i + '</li>').join('');
                
                // Update recent commands
                const recent = data.processed.slice(-5);
                recentDiv.innerHTML = recent.map(p => 
                    '<p>' + p.prompt + ' - ' + (p.success ? 'SUCCESS' : 'FAIL') + '</p>'
                ).join('');
            });
        }
        
        // Socket events
        socket.on('prompt_update', function(data) {
            loadData();
        });
        
        // Load initial data
        loadData();
    </script>
</body>
</html>
        '''
    
    def run(self, debug=False):
        """Start the web server"""
        logging.info(f"Starting simple LAMControl web server on {self.host}:{self.port}")
        self.socketio.run(self.app, host=self.host, port=self.port, debug=debug)
