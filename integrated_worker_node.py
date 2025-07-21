"""
LAMControl Worker Node with Pluggable Integrations

This is the new worker node framework that uses pluggable integrations
instead of fixed worker types.
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

# Import the integration system
from integrations import Integration, IntegrationConfig, IntegrationRegistry, auto_discover_integrations


class IntegratedWorkerNode:
    """Worker node that can dynamically load and use integrations"""
    
    def __init__(self, server_endpoint: str, worker_port: int = 6000, 
                 worker_name: str = None, location: str = "", description: str = ""):
        self.worker_id = f"worker_{secrets.token_hex(4)}"
        self.worker_name = worker_name or self.worker_id
        self.location = location
        self.description = description
        self.server_endpoint = server_endpoint
        self.worker_port = worker_port
        self.api_key = secrets.token_hex(16)
        
        # Flask app for receiving tasks
        self.app = Flask(f"LAMWorker_{self.worker_id}")
        self.setup_routes()
        
        # Worker state
        self.status = "starting"
        self.current_tasks = 0
        self.max_concurrent_tasks = 5
        self.task_history = []
        
        # Integration system
        self.registry = IntegrationRegistry()
        self.capabilities = []
        
        logging.info(f"Initialized integrated worker: {self.worker_id}")
    
    def load_integrations_from_config(self, integrations_config: Dict[str, Any]):
        """Load integrations based on configuration"""
        try:
            for integration_name, integration_config in integrations_config.items():
                if not integration_config.get('enabled', True):
                    self.logger.info(f"Integration {integration_name} is disabled")
                    continue
                
                # Create integration config
                config = IntegrationConfig(
                    name=integration_name,
                    enabled=integration_config.get('enabled', True),
                    settings=integration_config.get('settings', {}),
                    dependencies=integration_config.get('dependencies', [])
                )
                
                # Try to load the integration
                try:
                    module_name = f'integrations.{integration_name}'
                    module = __import__(module_name, fromlist=[integration_name])
                    
                    # Look for integration class
                    class_name = f"{integration_name.title()}Integration"
                    if hasattr(module, class_name):
                        integration_class = getattr(module, class_name)
                        integration = integration_class(config)
                        
                        if self.registry.register_integration(integration):
                            logging.info(f"Loaded integration: {integration_name}")
                        else:
                            logging.warning(f"Failed to register integration: {integration_name}")
                    else:
                        logging.warning(f"Integration class {class_name} not found in {module_name}")
                        
                except ImportError as e:
                    logging.error(f"Failed to import integration {integration_name}: {e}")
                except Exception as e:
                    logging.error(f"Error loading integration {integration_name}: {e}")
            
            # Update capabilities
            self.capabilities = self.registry.get_all_capabilities()
            logging.info(f"Worker loaded {len(self.registry.integrations)} integrations with {len(self.capabilities)} capabilities")
            
        except Exception as e:
            logging.error(f"Error loading integrations from config: {e}")
    
    def auto_discover_and_load_integrations(self, integrations_config: Dict[str, Any] = None):
        """Auto-discover and load all available integrations"""
        try:
            discovered = auto_discover_integrations()
            
            for integration in discovered:
                # Check if we have specific config for this integration
                if integrations_config and integration.name in integrations_config:
                    int_config = integrations_config[integration.name]
                    if not int_config.get('enabled', True):
                        logging.info(f"Integration {integration.name} is disabled in config")
                        continue
                    
                    # Update integration settings from config
                    integration.settings.update(int_config.get('settings', {}))
                
                if self.registry.register_integration(integration):
                    logging.info(f"Auto-loaded integration: {integration.name}")
                else:
                    logging.warning(f"Failed to auto-load integration: {integration.name}")
            
            # Update capabilities
            self.capabilities = self.registry.get_all_capabilities()
            logging.info(f"Worker auto-loaded {len(self.registry.integrations)} integrations with {len(self.capabilities)} capabilities")
            
        except Exception as e:
            logging.error(f"Error auto-discovering integrations: {e}")
    
    def setup_routes(self):
        """Setup Flask routes for the worker"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            return jsonify({
                'status': 'healthy',
                'worker_id': self.worker_id,
                'worker_name': self.worker_name,
                'capabilities': self.capabilities,
                'integrations': list(self.registry.integrations.keys()),
                'current_tasks': self.current_tasks,
                'location': self.location,
                'description': self.description,
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
                    return jsonify({'error': 'Worker at capacity'}), 503
                
                data = request.get_json()
                if not data or 'task' not in data:
                    return jsonify({'error': 'No task provided'}), 400
                
                task = data['task']
                task_id = secrets.token_hex(8)
                
                logging.info(f"Received task: {task}")
                
                # Execute task in background thread
                def execute_task_thread():
                    self.current_tasks += 1
                    try:
                        result = self._execute_task(task)
                        self.task_history.append({
                            'task_id': task_id,
                            'task': task,
                            'result': result,
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'status': 'completed'
                        })
                    except Exception as e:
                        logging.error(f"Task execution error: {e}")
                        self.task_history.append({
                            'task_id': task_id,
                            'task': task,
                            'result': f"Error: {str(e)}",
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'status': 'failed'
                        })
                    finally:
                        self.current_tasks -= 1
                
                thread = threading.Thread(target=execute_task_thread)
                thread.start()
                
                return jsonify({
                    'status': 'accepted',
                    'task_id': task_id,
                    'message': 'Task queued for execution'
                })
                
            except Exception as e:
                logging.error(f"Error in execute endpoint: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/status', methods=['GET'])
        def get_status():
            return jsonify({
                'worker_id': self.worker_id,
                'worker_name': self.worker_name,
                'status': self.status,
                'current_tasks': self.current_tasks,
                'max_concurrent_tasks': self.max_concurrent_tasks,
                'capabilities': self.capabilities,
                'integrations': list(self.registry.integrations.keys()),
                'task_history': self.task_history[-10:],  # Last 10 tasks
                'location': self.location,
                'description': self.description
            })
        
        @self.app.route('/integrations', methods=['GET'])
        def get_integrations():
            """Get information about loaded integrations"""
            integration_info = {}
            for name, integration in self.registry.integrations.items():
                integration_info[name] = {
                    'name': integration.name,
                    'enabled': integration.is_enabled(),
                    'capabilities': integration.get_capabilities(),
                    'dependencies': integration.get_dependencies()
                }
            return jsonify(integration_info)
    
    def _execute_task(self, task: str) -> str:
        """Execute a task using the appropriate integration"""
        try:
            # Parse the task to identify the capability
            parts = task.split()
            if len(parts) < 1:
                return "Empty task"
            
            capability = parts[0].lower()
            
            # Find the integration that handles this capability
            integration = self.registry.get_integration_for_capability(capability)
            if not integration:
                return f"No integration found for capability: {capability}"
            
            # Get the handler for this capability
            handlers = integration.get_handlers()
            handler = handlers.get(capability)
            if not handler:
                return f"No handler found for capability: {capability}"
            
            # Execute the task
            result = handler(task)
            return result
            
        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}"
            logging.error(error_msg)
            return error_msg
    
    def register_with_server(self) -> bool:
        """Register this worker with the central server"""
        try:
            payload = {
                'worker_id': self.worker_id,
                'worker_name': self.worker_name,
                'capabilities': self.capabilities,
                'integrations': list(self.registry.integrations.keys()),
                'endpoint': f"http://localhost:{self.worker_port}",
                'location': self.location,
                'description': self.description,
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
        def heartbeat_thread():
            while self.status != "stopped":
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
                    logging.warning(f"Heartbeat error: {e}")
                
                time.sleep(30)  # Send heartbeat every 30 seconds
        
        thread = threading.Thread(target=heartbeat_thread, daemon=True)
        thread.start()
    
    def run(self, debug=False):
        """Start the worker node"""
        try:
            logging.info(f"Starting worker {self.worker_id} on port {self.worker_port}")
            
            # Register with server
            if self.register_with_server():
                # Start heartbeat
                self.start_heartbeat()
                
                # Start Flask app
                self.app.run(host='0.0.0.0', port=self.worker_port, debug=debug)
            else:
                logging.error("Failed to register with server, not starting worker")
                
        except KeyboardInterrupt:
            logging.info("Worker stopped by user")
            self.status = "stopped"
        except Exception as e:
            logging.error(f"Worker error: {e}")
            self.status = "error"
        finally:
            # Cleanup integrations
            self.registry.cleanup_all()


def create_worker_from_config(config_file: str, server_endpoint: str, worker_port: int = 6000) -> IntegratedWorkerNode:
    """Create a worker node from a configuration file"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Extract worker configuration
        worker_config = config.get('worker', {})
        integrations_config = config.get('integrations', {})
        
        # Create worker
        worker = IntegratedWorkerNode(
            server_endpoint=server_endpoint,
            worker_port=worker_port,
            worker_name=worker_config.get('name'),
            location=worker_config.get('location', ''),
            description=worker_config.get('description', '')
        )
        
        # Load integrations
        if integrations_config:
            worker.load_integrations_from_config(integrations_config)
        else:
            # Auto-discover if no specific config
            worker.auto_discover_and_load_integrations()
        
        return worker
        
    except Exception as e:
        logging.error(f"Failed to create worker from config: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    if len(sys.argv) < 2:
        print("Usage: python integrated_worker_node.py <server_endpoint> [port] [config_file]")
        print("Example: python integrated_worker_node.py http://localhost:5000 6000 worker_config.json")
        sys.exit(1)
    
    server_endpoint = sys.argv[1]
    worker_port = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
    config_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        if config_file:
            worker = create_worker_from_config(config_file, server_endpoint, worker_port)
        else:
            # Create a default worker with auto-discovery
            worker = IntegratedWorkerNode(server_endpoint, worker_port)
            worker.auto_discover_and_load_integrations()
        
        worker.run()
        
    except Exception as e:
        logging.error(f"Failed to start worker: {e}")
        sys.exit(1)
