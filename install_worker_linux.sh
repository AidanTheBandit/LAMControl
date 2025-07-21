#!/bin/bash

# LAMControl Worker Installation Script for Linux
# This script installs and configures a LAMControl worker node

set -e

echo "LAMControl Worker Installation Script"
echo "===================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root. Please run as a regular user."
   exit 1
fi

# Check if Python 3.8+ is installed
print_header "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    print_error "Python $required_version or higher is required. Found: $python_version"
    exit 1
fi

print_status "Python $python_version detected - OK"

# Check if pip is installed
print_header "Checking pip installation..."
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed. Please install pip3."
    exit 1
fi

print_status "pip3 detected - OK"

# Get configuration from user
print_header "Worker Configuration"

# Worker type selection
echo "Available worker types:"
echo "1) browser - Browser automation (requires Playwright)"
echo "2) computer - Local computer actions"
echo "3) messaging - Discord/Telegram messaging"
echo "4) ai - AI model integration"

while true; do
    read -p "Select worker type (1-4): " worker_choice
    case $worker_choice in
        1) WORKER_TYPE="browser"; break;;
        2) WORKER_TYPE="computer"; break;;
        3) WORKER_TYPE="messaging"; break;;
        4) WORKER_TYPE="ai"; break;;
        *) print_error "Invalid choice. Please select 1-4.";;
    esac
done

# Get server details
read -p "Enter LAMControl server IP/hostname: " SERVER_HOST
while [[ -z "$SERVER_HOST" ]]; do
    print_error "Server host cannot be empty"
    read -p "Enter LAMControl server IP/hostname: " SERVER_HOST
done

read -p "Enter LAMControl server port [8080]: " SERVER_PORT
SERVER_PORT=${SERVER_PORT:-8080}

# Get worker details
read -p "Enter worker name (optional): " WORKER_NAME
read -p "Enter worker location (optional): " WORKER_LOCATION
read -p "Enter worker description (optional): " WORKER_DESCRIPTION

# Installation directory
INSTALL_DIR="$HOME/lamcontrol-worker"
read -p "Installation directory [$INSTALL_DIR]: " custom_dir
INSTALL_DIR=${custom_dir:-$INSTALL_DIR}

print_header "Creating installation directory..."
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Download worker files
print_header "Downloading worker files..."

# Create a minimal worker file structure
cat > worker_node.py << 'EOF'
"""
LAMControl Worker Node Base Classes

This module contains the base classes for all worker node types.
"""

import os
import sys
import json
import time
import logging
import requests
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone

class WorkerNodeBase(ABC):
    """Base class for all worker nodes"""
    
    def __init__(self, worker_type: str, capabilities: list, server_url: str, worker_name: str = None):
        self.worker_type = worker_type
        self.capabilities = capabilities
        self.server_url = server_url.rstrip('/')
        self.worker_name = worker_name
        self.worker_id = None
        self.api_key = None
        self.running = False
        self.heartbeat_interval = 30  # seconds
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(f'Worker-{worker_type}')
    
    def register_with_server(self, location: str = "", description: str = ""):
        """Register this worker with the central server"""
        try:
            # Determine local endpoint
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            endpoint = f"http://{local_ip}:5000"  # Workers run on port 5000
            
            registration_data = {
                'worker_type': self.worker_type,
                'capabilities': self.capabilities,
                'endpoint': endpoint,
                'location': location,
                'description': description
            }
            
            if self.worker_name:
                registration_data['worker_name'] = self.worker_name
            
            response = requests.post(
                f"{self.server_url}/api/register-worker",
                json=registration_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                self.worker_id = result['worker_id']
                self.api_key = result['api_key']
                self.logger.info(f"Successfully registered as {self.worker_id}")
                return True
            else:
                self.logger.error(f"Registration failed: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return False
    
    def send_heartbeat(self):
        """Send heartbeat to server"""
        if not self.worker_id:
            return
        
        try:
            response = requests.post(
                f"{self.server_url}/api/worker/{self.worker_id}/heartbeat",
                headers={'Authorization': f'Bearer {self.api_key}'},
                timeout=5
            )
            if response.status_code != 200:
                self.logger.warning(f"Heartbeat failed: {response.text}")
        except Exception as e:
            self.logger.error(f"Heartbeat error: {e}")
    
    def heartbeat_loop(self):
        """Background heartbeat thread"""
        while self.running:
            self.send_heartbeat()
            time.sleep(self.heartbeat_interval)
    
    @abstractmethod
    def execute_task(self, task_data: dict) -> dict:
        """Execute a task assigned to this worker"""
        pass
    
    def start(self, location: str = "", description: str = ""):
        """Start the worker node"""
        self.logger.info(f"Starting {self.worker_type} worker...")
        
        # Register with server
        if not self.register_with_server(location, description):
            self.logger.error("Failed to register with server")
            return False
        
        self.running = True
        
        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        
        self.logger.info(f"Worker {self.worker_id} started successfully")
        return True
    
    def stop(self):
        """Stop the worker node"""
        self.running = False
        self.logger.info(f"Worker {self.worker_id} stopped")

class BrowserWorker(WorkerNodeBase):
    """Worker for browser automation tasks"""
    
    def __init__(self, server_url: str, worker_name: str = None):
        capabilities = ['web_navigation', 'form_filling', 'web_scraping', 'browser_automation']
        super().__init__('browser', capabilities, server_url, worker_name)
    
    def execute_task(self, task_data: dict) -> dict:
        """Execute browser automation task"""
        try:
            # Placeholder for browser automation
            self.logger.info(f"Executing browser task: {task_data}")
            return {'status': 'success', 'message': 'Browser task completed'}
        except Exception as e:
            self.logger.error(f"Browser task failed: {e}")
            return {'status': 'error', 'message': str(e)}

class ComputerWorker(WorkerNodeBase):
    """Worker for local computer actions"""
    
    def __init__(self, server_url: str, worker_name: str = None):
        capabilities = ['file_operations', 'system_commands', 'local_automation']
        super().__init__('computer', capabilities, server_url, worker_name)
    
    def execute_task(self, task_data: dict) -> dict:
        """Execute computer automation task"""
        try:
            # Placeholder for computer automation
            self.logger.info(f"Executing computer task: {task_data}")
            return {'status': 'success', 'message': 'Computer task completed'}
        except Exception as e:
            self.logger.error(f"Computer task failed: {e}")
            return {'status': 'error', 'message': str(e)}

class MessagingWorker(WorkerNodeBase):
    """Worker for messaging platform integration"""
    
    def __init__(self, server_url: str, worker_name: str = None):
        capabilities = ['discord_messaging', 'telegram_messaging', 'social_media']
        super().__init__('messaging', capabilities, server_url, worker_name)
    
    def execute_task(self, task_data: dict) -> dict:
        """Execute messaging task"""
        try:
            # Placeholder for messaging automation
            self.logger.info(f"Executing messaging task: {task_data}")
            return {'status': 'success', 'message': 'Messaging task completed'}
        except Exception as e:
            self.logger.error(f"Messaging task failed: {e}")
            return {'status': 'error', 'message': str(e)}

class AIWorker(WorkerNodeBase):
    """Worker for AI model integration"""
    
    def __init__(self, server_url: str, worker_name: str = None):
        capabilities = ['llm_processing', 'ai_analysis', 'model_inference']
        super().__init__('ai', capabilities, server_url, worker_name)
    
    def execute_task(self, task_data: dict) -> dict:
        """Execute AI task"""
        try:
            # Placeholder for AI processing
            self.logger.info(f"Executing AI task: {task_data}")
            return {'status': 'success', 'message': 'AI task completed'}
        except Exception as e:
            self.logger.error(f"AI task failed: {e}")
            return {'status': 'error', 'message': str(e)}
EOF

# Create worker launcher script
cat > launch_worker.py << EOF
#!/usr/bin/env python3

import sys
import signal
from worker_node import BrowserWorker, ComputerWorker, MessagingWorker, AIWorker

def signal_handler(sig, frame):
    print('\nShutting down worker...')
    if 'worker' in globals():
        worker.stop()
    sys.exit(0)

def main():
    # Worker configuration
    WORKER_TYPE = "${WORKER_TYPE}"
    SERVER_URL = "http://${SERVER_HOST}:${SERVER_PORT}"
    WORKER_NAME = "${WORKER_NAME}"
    WORKER_LOCATION = "${WORKER_LOCATION}"
    WORKER_DESCRIPTION = "${WORKER_DESCRIPTION}"
    
    # Create worker based on type
    if WORKER_TYPE == "browser":
        worker = BrowserWorker(SERVER_URL, WORKER_NAME if WORKER_NAME else None)
    elif WORKER_TYPE == "computer":
        worker = ComputerWorker(SERVER_URL, WORKER_NAME if WORKER_NAME else None)
    elif WORKER_TYPE == "messaging":
        worker = MessagingWorker(SERVER_URL, WORKER_NAME if WORKER_NAME else None)
    elif WORKER_TYPE == "ai":
        worker = AIWorker(SERVER_URL, WORKER_NAME if WORKER_NAME else None)
    else:
        print(f"Unknown worker type: {WORKER_TYPE}")
        sys.exit(1)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start worker
    if worker.start(WORKER_LOCATION, WORKER_DESCRIPTION):
        print(f"Worker started successfully. Press Ctrl+C to stop.")
        
        # Keep running
        try:
            while worker.running:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        print("Failed to start worker")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

chmod +x launch_worker.py

# Install Python dependencies
print_header "Installing Python dependencies..."
pip3 install --user requests

# Install worker-specific dependencies
if [ "$WORKER_TYPE" = "browser" ]; then
    print_status "Installing browser automation dependencies..."
    pip3 install --user playwright
    python3 -m playwright install
elif [ "$WORKER_TYPE" = "messaging" ]; then
    print_status "Installing messaging dependencies..."
    pip3 install --user discord.py python-telegram-bot
fi

# Create systemd service (optional)
print_header "Creating systemd service..."
SERVICE_FILE="$HOME/.config/systemd/user/lamcontrol-worker.service"

mkdir -p "$HOME/.config/systemd/user"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=LAMControl Worker Node
After=network.target

[Service]
Type=simple
User=%i
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/launch_worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

# Enable systemd service for current user
systemctl --user daemon-reload
systemctl --user enable lamcontrol-worker.service

print_header "Installation Complete!"
print_status "Worker installed in: $INSTALL_DIR"
print_status "Worker type: $WORKER_TYPE"
print_status "Server: $SERVER_HOST:$SERVER_PORT"

echo ""
echo "To start the worker:"
echo "  Manually: cd $INSTALL_DIR && python3 launch_worker.py"
echo "  As service: systemctl --user start lamcontrol-worker.service"
echo ""
echo "To check service status:"
echo "  systemctl --user status lamcontrol-worker.service"
echo ""
echo "To view logs:"
echo "  journalctl --user -u lamcontrol-worker.service -f"

print_status "Installation completed successfully!"
