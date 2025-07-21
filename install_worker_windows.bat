@echo off
REM LAMControl Worker Installation Script for Windows
REM This script installs and configures a LAMControl worker node

setlocal EnableDelayedExpansion

echo LAMControl Worker Installation Script
echo ====================================

REM Check if Python is installed
echo Checking Python installation...
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

REM Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python %PYTHON_VERSION% detected

REM Check if pip is installed
echo Checking pip installation...
python -m pip --version >nul 2>&1
if !errorlevel! neq 0 (
    echo ERROR: pip is not installed
    echo Please install pip or reinstall Python with pip included
    pause
    exit /b 1
)

echo pip detected - OK

REM Worker type selection
echo.
echo Available worker types:
echo 1) browser - Browser automation (requires Playwright)
echo 2) computer - Local computer actions
echo 3) messaging - Discord/Telegram messaging
echo 4) ai - AI model integration

:worker_choice
set /p "worker_choice=Select worker type (1-4): "
if "!worker_choice!"=="1" (
    set WORKER_TYPE=browser
    goto :config
)
if "!worker_choice!"=="2" (
    set WORKER_TYPE=computer
    goto :config
)
if "!worker_choice!"=="3" (
    set WORKER_TYPE=messaging
    goto :config
)
if "!worker_choice!"=="4" (
    set WORKER_TYPE=ai
    goto :config
)
echo Invalid choice. Please select 1-4.
goto :worker_choice

:config
REM Get server details
set /p "SERVER_HOST=Enter LAMControl server IP/hostname: "
if "!SERVER_HOST!"=="" (
    echo Server host cannot be empty
    goto :config
)

set /p "SERVER_PORT=Enter LAMControl server port [8080]: "
if "!SERVER_PORT!"=="" set SERVER_PORT=8080

REM Get worker details
set /p "WORKER_NAME=Enter worker name (optional): "
set /p "WORKER_LOCATION=Enter worker location (optional): "
set /p "WORKER_DESCRIPTION=Enter worker description (optional): "

REM Installation directory
set DEFAULT_INSTALL_DIR=%USERPROFILE%\lamcontrol-worker
set /p "INSTALL_DIR=Installation directory [!DEFAULT_INSTALL_DIR!]: "
if "!INSTALL_DIR!"=="" set INSTALL_DIR=!DEFAULT_INSTALL_DIR!

echo Creating installation directory...
if not exist "!INSTALL_DIR!" mkdir "!INSTALL_DIR!"
cd /d "!INSTALL_DIR!"

echo Downloading worker files...

REM Create worker_node.py
(
echo """
echo LAMControl Worker Node Base Classes
echo.
echo This module contains the base classes for all worker node types.
echo """
echo.
echo import os
echo import sys
echo import json
echo import time
echo import logging
echo import requests
echo import threading
echo from abc import ABC, abstractmethod
echo from datetime import datetime, timezone
echo.
echo class WorkerNodeBase^(ABC^):
echo     """Base class for all worker nodes"""
echo.    
echo     def __init__^(self, worker_type: str, capabilities: list, server_url: str, worker_name: str = None^):
echo         self.worker_type = worker_type
echo         self.capabilities = capabilities
echo         self.server_url = server_url.rstrip^('^/'^ )
echo         self.worker_name = worker_name
echo         self.worker_id = None
echo         self.api_key = None
echo         self.running = False
echo         self.heartbeat_interval = 30  # seconds
echo.        
echo         # Setup logging
echo         logging.basicConfig^(
echo             level=logging.INFO,
echo             format='%%^(asctime^)s - %%^(name^)s - %%^(levelname^)s - %%^(message^)s'
echo         ^)
echo         self.logger = logging.getLogger^(f'Worker-{worker_type}'^)
echo.    
echo     def register_with_server^(self, location: str = "", description: str = ""^):
echo         """Register this worker with the central server"""
echo         try:
echo             # Determine local endpoint
echo             import socket
echo             hostname = socket.gethostname^(^)
echo             local_ip = socket.gethostbyname^(hostname^)
echo             endpoint = f"http://{local_ip}:5000"  # Workers run on port 5000
echo.            
echo             registration_data = {
echo                 'worker_type': self.worker_type,
echo                 'capabilities': self.capabilities,
echo                 'endpoint': endpoint,
echo                 'location': location,
echo                 'description': description
echo             }
echo.            
echo             if self.worker_name:
echo                 registration_data['worker_name'] = self.worker_name
echo.            
echo             response = requests.post^(
echo                 f"{self.server_url}/api/register-worker",
echo                 json=registration_data,
echo                 timeout=10
echo             ^)
echo.            
echo             if response.status_code == 200:
echo                 result = response.json^(^)
echo                 self.worker_id = result['worker_id']
echo                 self.api_key = result['api_key']
echo                 self.logger.info^(f"Successfully registered as {self.worker_id}"^)
echo                 return True
echo             else:
echo                 self.logger.error^(f"Registration failed: {response.text}"^)
echo                 return False
echo.                
echo         except Exception as e:
echo             self.logger.error^(f"Registration error: {e}"^)
echo             return False
echo.    
echo     def send_heartbeat^(self^):
echo         """Send heartbeat to server"""
echo         if not self.worker_id:
echo             return
echo.        
echo         try:
echo             response = requests.post^(
echo                 f"{self.server_url}/api/worker/{self.worker_id}/heartbeat",
echo                 headers={'Authorization': f'Bearer {self.api_key}'},
echo                 timeout=5
echo             ^)
echo             if response.status_code != 200:
echo                 self.logger.warning^(f"Heartbeat failed: {response.text}"^)
echo         except Exception as e:
echo             self.logger.error^(f"Heartbeat error: {e}"^)
echo.    
echo     def heartbeat_loop^(self^):
echo         """Background heartbeat thread"""
echo         while self.running:
echo             self.send_heartbeat^(^)
echo             time.sleep^(self.heartbeat_interval^)
echo.    
echo     def execute_task^(self, task_data: dict^) -^> dict:
echo         """Execute a task assigned to this worker"""
echo         pass
echo.    
echo     def start^(self, location: str = "", description: str = ""^):
echo         """Start the worker node"""
echo         self.logger.info^(f"Starting {self.worker_type} worker..."^)
echo.        
echo         # Register with server
echo         if not self.register_with_server^(location, description^):
echo             self.logger.error^("Failed to register with server"^)
echo             return False
echo.        
echo         self.running = True
echo.        
echo         # Start heartbeat thread
echo         heartbeat_thread = threading.Thread^(target=self.heartbeat_loop, daemon=True^)
echo         heartbeat_thread.start^(^)
echo.        
echo         self.logger.info^(f"Worker {self.worker_id} started successfully"^)
echo         return True
echo.    
echo     def stop^(self^):
echo         """Stop the worker node"""
echo         self.running = False
echo         self.logger.info^(f"Worker {self.worker_id} stopped"^)
echo.
echo class BrowserWorker^(WorkerNodeBase^):
echo     """Worker for browser automation tasks"""
echo.    
echo     def __init__^(self, server_url: str, worker_name: str = None^):
echo         capabilities = ['web_navigation', 'form_filling', 'web_scraping', 'browser_automation']
echo         super^(^).__init__^('browser', capabilities, server_url, worker_name^)
echo.    
echo     def execute_task^(self, task_data: dict^) -^> dict:
echo         """Execute browser automation task"""
echo         try:
echo             # Placeholder for browser automation
echo             self.logger.info^(f"Executing browser task: {task_data}"^)
echo             return {'status': 'success', 'message': 'Browser task completed'}
echo         except Exception as e:
echo             self.logger.error^(f"Browser task failed: {e}"^)
echo             return {'status': 'error', 'message': str^(e^)}
echo.
echo class ComputerWorker^(WorkerNodeBase^):
echo     """Worker for local computer actions"""
echo.    
echo     def __init__^(self, server_url: str, worker_name: str = None^):
echo         capabilities = ['file_operations', 'system_commands', 'local_automation']
echo         super^(^).__init__^('computer', capabilities, server_url, worker_name^)
echo.    
echo     def execute_task^(self, task_data: dict^) -^> dict:
echo         """Execute computer automation task"""
echo         try:
echo             # Placeholder for computer automation
echo             self.logger.info^(f"Executing computer task: {task_data}"^)
echo             return {'status': 'success', 'message': 'Computer task completed'}
echo         except Exception as e:
echo             self.logger.error^(f"Computer task failed: {e}"^)
echo             return {'status': 'error', 'message': str^(e^)}
echo.
echo class MessagingWorker^(WorkerNodeBase^):
echo     """Worker for messaging platform integration"""
echo.    
echo     def __init__^(self, server_url: str, worker_name: str = None^):
echo         capabilities = ['discord_messaging', 'telegram_messaging', 'social_media']
echo         super^(^).__init__^('messaging', capabilities, server_url, worker_name^)
echo.    
echo     def execute_task^(self, task_data: dict^) -^> dict:
echo         """Execute messaging task"""
echo         try:
echo             # Placeholder for messaging automation
echo             self.logger.info^(f"Executing messaging task: {task_data}"^)
echo             return {'status': 'success', 'message': 'Messaging task completed'}
echo         except Exception as e:
echo             self.logger.error^(f"Messaging task failed: {e}"^)
echo             return {'status': 'error', 'message': str^(e^)}
echo.
echo class AIWorker^(WorkerNodeBase^):
echo     """Worker for AI model integration"""
echo.    
echo     def __init__^(self, server_url: str, worker_name: str = None^):
echo         capabilities = ['llm_processing', 'ai_analysis', 'model_inference']
echo         super^(^).__init__^('ai', capabilities, server_url, worker_name^)
echo.    
echo     def execute_task^(self, task_data: dict^) -^> dict:
echo         """Execute AI task"""
echo         try:
echo             # Placeholder for AI processing
echo             self.logger.info^(f"Executing AI task: {task_data}"^)
echo             return {'status': 'success', 'message': 'AI task completed'}
echo         except Exception as e:
echo             self.logger.error^(f"AI task failed: {e}"^)
echo             return {'status': 'error', 'message': str^(e^)}
) > worker_node.py

REM Create launch_worker.py
(
echo import sys
echo import signal
echo from worker_node import BrowserWorker, ComputerWorker, MessagingWorker, AIWorker
echo.
echo def signal_handler^(sig, frame^):
echo     print^('\nShutting down worker...'^)
echo     if 'worker' in globals^(^):
echo         worker.stop^(^)
echo     sys.exit^(0^)
echo.
echo def main^(^):
echo     # Worker configuration
echo     WORKER_TYPE = "!WORKER_TYPE!"
echo     SERVER_URL = "http://!SERVER_HOST!:!SERVER_PORT!"
echo     WORKER_NAME = "!WORKER_NAME!"
echo     WORKER_LOCATION = "!WORKER_LOCATION!"
echo     WORKER_DESCRIPTION = "!WORKER_DESCRIPTION!"
echo.    
echo     # Create worker based on type
echo     if WORKER_TYPE == "browser":
echo         worker = BrowserWorker^(SERVER_URL, WORKER_NAME if WORKER_NAME else None^)
echo     elif WORKER_TYPE == "computer":
echo         worker = ComputerWorker^(SERVER_URL, WORKER_NAME if WORKER_NAME else None^)
echo     elif WORKER_TYPE == "messaging":
echo         worker = MessagingWorker^(SERVER_URL, WORKER_NAME if WORKER_NAME else None^)
echo     elif WORKER_TYPE == "ai":
echo         worker = AIWorker^(SERVER_URL, WORKER_NAME if WORKER_NAME else None^)
echo     else:
echo         print^(f"Unknown worker type: {WORKER_TYPE}"^)
echo         sys.exit^(1^)
echo.    
echo     # Set up signal handlers
echo     signal.signal^(signal.SIGINT, signal_handler^)
echo     signal.signal^(signal.SIGTERM, signal_handler^)
echo.    
echo     # Start worker
echo     if worker.start^(WORKER_LOCATION, WORKER_DESCRIPTION^):
echo         print^(f"Worker started successfully. Press Ctrl+C to stop."^)
echo.        
echo         # Keep running
echo         try:
echo             while worker.running:
echo                 import time
echo                 time.sleep^(1^)
echo         except KeyboardInterrupt:
echo             pass
echo     else:
echo         print^("Failed to start worker"^)
echo         sys.exit^(1^)
echo.
echo if __name__ == "__main__":
echo     main^(^)
) > launch_worker.py

REM Install Python dependencies
echo Installing Python dependencies...
python -m pip install --user requests

REM Install worker-specific dependencies
if "!WORKER_TYPE!"=="browser" (
    echo Installing browser automation dependencies...
    python -m pip install --user playwright
    python -m playwright install
)
if "!WORKER_TYPE!"=="messaging" (
    echo Installing messaging dependencies...
    python -m pip install --user discord.py python-telegram-bot
)

REM Create startup script
echo Creating startup script...
(
echo @echo off
echo cd /d "!INSTALL_DIR!"
echo python launch_worker.py
echo pause
) > start_worker.bat

REM Create Windows service script (optional)
echo Creating service installation script...
(
echo @echo off
echo REM Install LAMControl Worker as Windows Service
echo REM Requires nssm ^(Non-Sucking Service Manager^)
echo.
echo set NSSM_URL=https://nssm.cc/release/nssm-2.24.zip
echo set SERVICE_NAME=LAMControlWorker
echo.
echo echo Installing LAMControl Worker as Windows Service...
echo echo This requires nssm ^(Non-Sucking Service Manager^)
echo echo.
echo echo Download nssm from: %%NSSM_URL%%
echo echo Extract nssm.exe and place it in your PATH
echo echo.
echo echo Then run:
echo echo nssm install %%SERVICE_NAME%% "python" "!INSTALL_DIR!\launch_worker.py"
echo echo nssm set %%SERVICE_NAME%% AppDirectory "!INSTALL_DIR!"
echo echo nssm start %%SERVICE_NAME%%
echo.
echo pause
) > install_service.bat

echo.
echo Installation Complete!
echo =====================
echo Worker installed in: !INSTALL_DIR!
echo Worker type: !WORKER_TYPE!
echo Server: !SERVER_HOST!:!SERVER_PORT!
echo.
echo To start the worker:
echo   Double-click: start_worker.bat
echo   Command line: cd "!INSTALL_DIR!" ^&^& python launch_worker.py
echo.
echo To install as Windows service:
echo   Run: install_service.bat
echo.
echo Installation completed successfully!
pause
