"""
LAMControl Worker Node Base Class

Base framework for creating worker nodes that can execute specific integrations
for the distributed LAMControl system.
"""

import os
import json
import logging
import secrets
import threading
import time
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from flask import Flask, request, jsonify
from abc import ABC, abstractmethod


class WorkerNodeBase(ABC):
    """Base class for all worker nodes"""
    
    def __init__(self, worker_type: str, capabilities: List[str], 
                 server_endpoint: str, worker_port: int = 6000):
        self.worker_id = f"{worker_type}_{secrets.token_hex(4)}"
        self.worker_type = worker_type
        self.capabilities = capabilities
        self.server_endpoint = server_endpoint
        self.worker_port = worker_port
        self.api_key = secrets.token_hex(16)
        
        # Flask app for receiving tasks
        self.app = Flask(f"LAMWorker_{self.worker_type}")
        self.setup_routes()
        
        # Worker state
        self.status = "starting"
        self.current_tasks = 0
        self.max_concurrent_tasks = 5
        self.task_history = []
        
        # Task handlers registry
        self.task_handlers: Dict[str, Callable] = {}
        self.register_task_handlers()
        
        logging.info(f"Initialized {self.worker_type} worker: {self.worker_id}")
    
    @abstractmethod
    def register_task_handlers(self):
        """Register task handlers specific to this worker type"""
        pass
    
    def register_handler(self, integration: str, handler: Callable):
        """Register a task handler for a specific integration"""
        self.task_handlers[integration] = handler
        logging.info(f"Registered handler for {integration}")
    
    def setup_routes(self):
        """Setup Flask routes for the worker"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            return jsonify({
                'status': 'healthy',
                'worker_id': self.worker_id,
                'worker_type': self.worker_type,
                'capabilities': self.capabilities,
                'current_tasks': self.current_tasks,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        @self.app.route('/execute', methods=['POST'])
        def execute_task():
            """Execute a task sent from the central server"""
            try:
                # Verify authorization
                auth_header = request.headers.get('Authorization')
                if not auth_header or not auth_header.startswith('Bearer '):
                    return jsonify({'error': 'Invalid authorization'}), 401
                
                token = auth_header.split(' ')[1]
                if token != self.api_key:
                    return jsonify({'error': 'Invalid API key'}), 401
                
                # Check task capacity
                if self.current_tasks >= self.max_concurrent_tasks:
                    return jsonify({'error': 'Worker at capacity'}), 429
                
                data = request.get_json()
                if not data or 'task' not in data:
                    return jsonify({'error': 'No task provided'}), 400
                
                task = data['task']
                task_id = secrets.token_hex(8)
                
                logging.info(f"Received task: {task}")
                
                # Execute task in background thread
                def execute_task_thread():
                    try:
                        self.current_tasks += 1
                        response = self._execute_task(task)
                        
                        # Log task completion
                        self.task_history.append({
                            'task_id': task_id,
                            'task': task,
                            'response': response,
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'success': True
                        })
                        
                    except Exception as e:
                        logging.error(f"Task execution error: {e}")
                        self.task_history.append({
                            'task_id': task_id,
                            'task': task,
                            'error': str(e),
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'success': False
                        })
                    finally:
                        self.current_tasks -= 1
                
                # Start task execution
                task_thread = threading.Thread(target=execute_task_thread)
                task_thread.daemon = True
                task_thread.start()
                
                return jsonify({
                    'status': 'accepted',
                    'task_id': task_id,
                    'message': 'Task execution started'
                })
                
            except Exception as e:
                logging.error(f"Error executing task: {e}")
                return jsonify({'error': 'Task execution failed'}), 500
        
        @self.app.route('/status', methods=['GET'])
        def get_status():
            """Get detailed worker status"""
            return jsonify({
                'worker_id': self.worker_id,
                'worker_type': self.worker_type,
                'capabilities': self.capabilities,
                'status': self.status,
                'current_tasks': self.current_tasks,
                'max_concurrent_tasks': self.max_concurrent_tasks,
                'task_history': self.task_history[-10:],  # Last 10 tasks
                'uptime': (datetime.now(timezone.utc) - self._start_time).total_seconds() if hasattr(self, '_start_time') else 0
            })
    
    def _execute_task(self, task: str) -> str:
        """Execute a task and return the response"""
        try:
            parts = task.split()
            if len(parts) < 2:
                return "Invalid task format"
            
            integration = parts[0].lower()
            
            if integration not in self.task_handlers:
                return f"Unsupported integration: {integration}"
            
            # Execute the task handler
            handler = self.task_handlers[integration]
            response = handler(task)
            
            return response or "Task completed successfully"
            
        except Exception as e:
            logging.error(f"Task execution error: {e}")
            raise e
    
    def register_with_server(self) -> bool:
        """Register this worker with the central server"""
        try:
            payload = {
                'worker_id': self.worker_id,
                'worker_type': self.worker_type,
                'capabilities': self.capabilities,
                'endpoint': f"http://localhost:{self.worker_port}",
                'api_key': self.api_key
            }
            
            response = requests.post(
                f"{self.server_endpoint}/api/worker/register",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logging.info(f"Successfully registered with server")
                self.status = "online"
                return True
            else:
                logging.error(f"Failed to register with server: {response.status_code}")
                return False
                
        except Exception as e:
            logging.error(f"Error registering with server: {e}")
            return False
    
    def start_heartbeat(self):
        """Start sending heartbeats to the server"""
        def heartbeat_loop():
            while True:
                try:
                    if self.status == "online":
                        response = requests.post(
                            f"{self.server_endpoint}/api/worker/{self.worker_id}/heartbeat",
                            json={'status': self.status, 'current_tasks': self.current_tasks},
                            timeout=5
                        )
                        
                        if response.status_code != 200:
                            logging.warning(f"Heartbeat failed: {response.status_code}")
                    
                except Exception as e:
                    logging.error(f"Heartbeat error: {e}")
                
                time.sleep(30)  # Send heartbeat every 30 seconds
        
        heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        logging.info("Started heartbeat thread")
    
    def run(self, debug=False):
        """Start the worker node"""
        self._start_time = datetime.now(timezone.utc)
        
        # Register with server
        if not self.register_with_server():
            logging.error("Failed to register with server, exiting")
            return
        
        # Start heartbeat
        self.start_heartbeat()
        
        # Start Flask app
        logging.info(f"Starting {self.worker_type} worker on port {self.worker_port}")
        self.app.run(host='0.0.0.0', port=self.worker_port, debug=debug, threaded=True)


class BrowserWorker(WorkerNodeBase):
    """Worker node for browser automation tasks"""
    
    def __init__(self, server_endpoint: str, worker_port: int = 6001):
        super().__init__(
            worker_type="browser",
            capabilities=["browser", "browsersite", "browsergoogle", "browseryoutube", 
                         "browsergmail", "browseramazon"],
            server_endpoint=server_endpoint,
            worker_port=worker_port
        )
    
    def register_task_handlers(self):
        """Register browser-specific task handlers"""
        from integrations.browser import BrowserSite, BrowserGoogle, BrowserYoutube, BrowserGmail, BrowserAmazon
        
        self.register_handler("browser", self._handle_browser_task)
    
    def _handle_browser_task(self, task: str) -> str:
        """Handle browser automation tasks"""
        try:
            from integrations import browser
            
            parts = task.split()
            if len(parts) < 3:
                return "Invalid browser task format"
            
            action = parts[1].lower()
            search_term = " ".join(parts[2:])
            
            if action == "site":
                browser.BrowserSite(search_term)
                return f"Opened website: {search_term}"
            elif action == "google":
                browser.BrowserGoogle(search_term)
                return f"Searched Google for: {search_term}"
            elif action == "youtube":
                browser.BrowserYoutube(search_term)
                return f"Searched YouTube for: {search_term}"
            elif action == "gmail":
                browser.BrowserGmail(search_term)
                return f"Searched Gmail for: {search_term}"
            elif action == "amazon":
                browser.BrowserAmazon(search_term)
                return f"Searched Amazon for: {search_term}"
            else:
                return f"Unsupported browser action: {action}"
                
        except Exception as e:
            logging.error(f"Browser task error: {e}")
            return f"Browser task failed: {str(e)}"


class ComputerWorker(WorkerNodeBase):
    """Worker node for computer control tasks"""
    
    def __init__(self, server_endpoint: str, worker_port: int = 6002):
        super().__init__(
            worker_type="computer",
            capabilities=["computer", "computervolume", "computerrun", 
                         "computermedia", "computerpower"],
            server_endpoint=server_endpoint,
            worker_port=worker_port
        )
    
    def register_task_handlers(self):
        """Register computer control task handlers"""
        self.register_handler("computer", self._handle_computer_task)
    
    def _handle_computer_task(self, task: str) -> str:
        """Handle computer control tasks"""
        try:
            from integrations import computer
            
            parts = task.split()
            if len(parts) < 3:
                return "Invalid computer task format"
            
            action = parts[1].lower()
            
            if action == "volume":
                computer.ComputerVolume(task)
                return f"Volume command executed: {' '.join(parts[2:])}"
            elif action == "run":
                computer.ComputerRun(task)
                return f"Run command executed: {' '.join(parts[2:])}"
            elif action == "media":
                computer.ComputerMedia(task)
                return f"Media command executed: {' '.join(parts[2:])}"
            elif action == "power":
                computer.ComputerPower(task)
                return f"Power command executed: {' '.join(parts[2:])}"
            else:
                return f"Unsupported computer action: {action}"
                
        except Exception as e:
            logging.error(f"Computer task error: {e}")
            return f"Computer task failed: {str(e)}"


class MessagingWorker(WorkerNodeBase):
    """Worker node for messaging/social media tasks"""
    
    def __init__(self, server_endpoint: str, worker_port: int = 6003):
        super().__init__(
            worker_type="messaging",
            capabilities=["discord", "telegram", "facebook"],
            server_endpoint=server_endpoint,
            worker_port=worker_port
        )
        
        # Initialize browser context for messaging
        self._init_browser_context()
    
    def _init_browser_context(self):
        """Initialize browser context for messaging integrations"""
        try:
            from playwright.sync_api import sync_playwright
            from utils import config
            
            self.playwright = sync_playwright().start()
            browser = self.playwright.firefox.launch(headless=True)
            
            state_file = os.path.join(config.config['cache_dir'], config.config['state_file'])
            self.context = browser.new_context(storage_state=state_file)
            
            logging.info("Initialized browser context for messaging")
        except Exception as e:
            logging.error(f"Failed to initialize browser context: {e}")
            self.context = None
    
    def register_task_handlers(self):
        """Register messaging task handlers"""
        self.register_handler("discord", self._handle_discord_task)
        self.register_handler("telegram", self._handle_telegram_task)
        self.register_handler("facebook", self._handle_facebook_task)
    
    def _handle_discord_task(self, task: str) -> str:
        """Handle Discord messaging tasks"""
        try:
            if not self.context:
                return "Browser context not available"
            
            from integrations import discord
            
            parts = task.split()
            if len(parts) < 3:
                return "Invalid Discord task format"
            
            recipient = parts[1]
            message = " ".join(parts[2:])
            
            page = self.context.new_page()
            discord.DiscordText(page, recipient, message)
            page.close()
            
            return f"Sent Discord message to {recipient}: {message}"
            
        except Exception as e:
            logging.error(f"Discord task error: {e}")
            return f"Discord task failed: {str(e)}"
    
    def _handle_telegram_task(self, task: str) -> str:
        """Handle Telegram messaging tasks"""
        try:
            if not self.context:
                return "Browser context not available"
            
            from integrations import telegram
            
            parts = task.split()
            if len(parts) < 3:
                return "Invalid Telegram task format"
            
            recipient = parts[1]
            message = " ".join(parts[2:])
            
            telegram.TelegramText(self.context, recipient, message)
            
            return f"Sent Telegram message to {recipient}: {message}"
            
        except Exception as e:
            logging.error(f"Telegram task error: {e}")
            return f"Telegram task failed: {str(e)}"
    
    def _handle_facebook_task(self, task: str) -> str:
        """Handle Facebook messaging tasks"""
        try:
            if not self.context:
                return "Browser context not available"
            
            from integrations import facebook
            
            parts = task.split()
            if len(parts) < 3:
                return "Invalid Facebook task format"
            
            recipient = parts[1]
            message = " ".join(parts[2:])
            
            page = self.context.new_page()
            facebook.FacebookText(page, recipient, message)
            page.close()
            
            return f"Sent Facebook message to {recipient}: {message}"
            
        except Exception as e:
            logging.error(f"Facebook task error: {e}")
            return f"Facebook task failed: {str(e)}"


class AIWorker(WorkerNodeBase):
    """Worker node for AI/OpenInterpreter tasks"""
    
    def __init__(self, server_endpoint: str, worker_port: int = 6004):
        super().__init__(
            worker_type="ai",
            capabilities=["openinterpreter"],
            server_endpoint=server_endpoint,
            worker_port=worker_port
        )
    
    def register_task_handlers(self):
        """Register AI task handlers"""
        self.register_handler("openinterpreter", self._handle_openinterpreter_task)
    
    def _handle_openinterpreter_task(self, task: str) -> str:
        """Handle OpenInterpreter tasks"""
        try:
            from integrations import open_interpreter
            
            parts = task.split()
            if len(parts) < 2:
                return "Invalid OpenInterpreter task format"
            
            message = " ".join(parts[1:])
            open_interpreter.openinterpretercall(message)
            
            return f"Executed OpenInterpreter task: {message}"
            
        except Exception as e:
            logging.error(f"OpenInterpreter task error: {e}")
            return f"OpenInterpreter task failed: {str(e)}"


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    if len(sys.argv) < 3:
        print("Usage: python worker_node.py <worker_type> <server_endpoint> [port]")
        print("Worker types: browser, computer, messaging, ai")
        sys.exit(1)
    
    worker_type = sys.argv[1]
    server_endpoint = sys.argv[2]
    port = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    if worker_type == "browser":
        worker = BrowserWorker(server_endpoint, port or 6001)
    elif worker_type == "computer":
        worker = ComputerWorker(server_endpoint, port or 6002)
    elif worker_type == "messaging":
        worker = MessagingWorker(server_endpoint, port or 6003)
    elif worker_type == "ai":
        worker = AIWorker(server_endpoint, port or 6004)
    else:
        print(f"Unknown worker type: {worker_type}")
        sys.exit(1)
    
    worker.run()
