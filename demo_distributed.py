#!/usr/bin/env python3
"""
LAMControl Distributed System Demo

This script demonstrates how to:
1. Register worker nodes with custom names
2. Start worker processes 
3. Test the R1 interface

Usage:
    python demo_distributed.py --start-workers
    python demo_distributed.py --register-workers
    python demo_distributed.py --test-r1
"""

import argparse
import requests
import json
import subprocess
import time
import threading
from typing import List

class LAMControlDemo:
    def __init__(self, server_url="http://localhost:8080"):
        self.server_url = server_url
        
    def register_worker_via_api(self, worker_name: str, worker_type: str, 
                              endpoint: str, location: str = "", description: str = ""):
        """Register a worker via the API (simulates web interface registration)"""
        print(f"Registering worker: {worker_name} ({worker_type})")
        
        # Get capabilities for worker type
        capabilities_map = {
            'browser': ['browsersite', 'browsergoogle', 'browseryoutube', 'browsergmail', 'browseramazon'],
            'computer': ['computervolume', 'computerrun', 'computermedia', 'computerpower'],
            'messaging': ['discordtext', 'facebooktext', 'telegram'],
            'ai': ['openinterpreter', 'ai_automation']
        }
        
        capabilities = capabilities_map.get(worker_type, [])
        
        payload = {
            'worker_name': worker_name,
            'worker_type': worker_type,
            'endpoint': endpoint,
            'location': location,
            'description': description,
            'capabilities': capabilities
        }
        
        try:
            response = requests.post(f"{self.server_url}/api/worker/register", json=payload)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Worker registered successfully!")
                print(f"  Worker ID: {data['worker_id']}")
                print(f"  API Key: {data['api_key']}")
                return data
            else:
                print(f"✗ Registration failed: {response.status_code}")
                print(f"  Response: {response.text}")
        except Exception as e:
            print(f"✗ Registration error: {e}")
        
        return None
    
    def start_worker_process(self, worker_type: str, server_url: str, port: int):
        """Start a worker process"""
        script_map = {
            'browser': 'workers/browser_worker.py',
            'computer': 'workers/computer_worker.py', 
            'messaging': 'workers/messaging_worker.py',
            'ai': 'workers/ai_worker.py'
        }
        
        script = script_map.get(worker_type)
        if not script:
            print(f"Unknown worker type: {worker_type}")
            return None
        
        print(f"Starting {worker_type} worker on port {port}...")
        
        try:
            # Start worker process in background
            cmd = ['python', script, server_url, str(port)]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"✓ {worker_type} worker started (PID: {process.pid})")
            return process
        except Exception as e:
            print(f"✗ Failed to start {worker_type} worker: {e}")
            return None
    
    def register_demo_workers(self):
        """Register demonstration workers with custom names"""
        print("=== Registering Demo Workers ===")
        
        workers_to_register = [
            {
                'worker_name': 'living_room_pc',
                'worker_type': 'browser',
                'endpoint': 'http://192.168.1.100:6001',
                'location': 'Living Room',
                'description': 'Main computer for web browsing and media'
            },
            {
                'worker_name': 'bedroom_pc',
                'worker_type': 'computer',
                'endpoint': 'http://192.168.1.101:6002',
                'location': 'Bedroom',
                'description': 'Bedroom computer for volume and media control'
            },
            {
                'worker_name': 'home_server_pi',
                'worker_type': 'messaging',
                'endpoint': 'http://192.168.1.200:6003',
                'location': 'Server Closet',
                'description': 'Raspberry Pi for messaging and notifications'
            },
            {
                'worker_name': 'office_workstation',
                'worker_type': 'ai',
                'endpoint': 'http://192.168.1.102:6004',
                'location': 'Home Office',
                'description': 'Powerful workstation for AI and OpenInterpreter tasks'
            }
        ]
        
        registered_workers = []
        for worker_config in workers_to_register:
            result = self.register_worker_via_api(**worker_config)
            if result:
                registered_workers.append(result)
        
        print(f"\n✓ Registered {len(registered_workers)} workers successfully!")
        return registered_workers
    
    def start_demo_workers(self):
        """Start demo worker processes locally"""
        print("=== Starting Demo Workers ===")
        
        workers_to_start = [
            ('browser', 6001),
            ('computer', 6002),
            ('messaging', 6003),
            ('ai', 6004)
        ]
        
        processes = []
        for worker_type, port in workers_to_start:
            process = self.start_worker_process(worker_type, self.server_url, port)
            if process:
                processes.append((worker_type, process))
        
        if processes:
            print(f"\n✓ Started {len(processes)} worker processes!")
            print("Workers are now registering with the server...")
            
            # Wait a bit for workers to register
            time.sleep(3)
            
            # Check worker status
            self.check_worker_status()
        
        return processes
    
    def check_worker_status(self):
        """Check status of registered workers"""
        print("\n=== Worker Status ===")
        
        try:
            response = requests.get(f"{self.server_url}/api/workers")
            if response.status_code == 200:
                data = response.json()
                workers = data.get('workers', [])
                
                if workers:
                    print(f"Found {len(workers)} registered workers:")
                    for worker in workers:
                        status_icon = "🟢" if worker['status'] == 'online' else "🔴"
                        print(f"  {status_icon} {worker.get('custom_name', worker['worker_id'])}")
                        print(f"     Type: {worker['worker_type']}")
                        print(f"     Status: {worker['status']}")
                        print(f"     Capabilities: {', '.join(worker['capabilities'])}")
                        if worker.get('location'):
                            print(f"     Location: {worker['location']}")
                        print()
                else:
                    print("No workers registered yet.")
            else:
                print(f"Failed to get worker status: {response.status_code}")
        except Exception as e:
            print(f"Error checking worker status: {e}")
    
    def test_r1_interface(self):
        """Test the R1 interface by sending a sample command"""
        print("=== Testing R1 Interface ===")
        print(f"R1 Login Page: {self.server_url}/r1/login")
        print(f"Admin Dashboard: {self.server_url}")
        print()
        print("Login credentials:")
        print("  Username: admin")
        print("  Password: k0Hua97Nq1DchNLsYTJ31Q")
        print()
        print("To test the R1 interface:")
        print("1. Open the R1 login page in a browser")
        print("2. Login with the credentials above")
        print("3. Enter a test command like: 'Open YouTube and search for Weezer'")
        print("4. Watch the real-time status updates")
        
    def show_system_info(self):
        """Show information about the distributed system"""
        print("=== LAMControl Distributed System Information ===")
        print(f"Server URL: {self.server_url}")
        print()
        print("Available Interfaces:")
        print(f"  • Admin Dashboard: {self.server_url}")
        print(f"  • R1 Login Page: {self.server_url}/r1/login")
        print(f"  • Worker Registration API: {self.server_url}/api/worker/register")
        print(f"  • Worker Status API: {self.server_url}/api/workers")
        print()
        print("Supported Worker Types:")
        print("  • browser: Web browsing, Google, YouTube, Gmail, Amazon")
        print("  • computer: Volume control, app launching, media, power")
        print("  • messaging: Discord, Telegram, Facebook messaging")
        print("  • ai: OpenInterpreter, AI automation")
        print()
        print("Custom Worker Names Examples:")
        print("  • living_room_pc, bedroom_pc, office_workstation")
        print("  • home_server_pi, media_center_pc")
        print("  • room_pc, study_laptop, etc.")
        
def main():
    parser = argparse.ArgumentParser(description='LAMControl Distributed System Demo')
    parser.add_argument('--server', default='http://localhost:8080', 
                      help='Server URL (default: http://localhost:8080)')
    parser.add_argument('--register-workers', action='store_true',
                      help='Register demo workers via API')
    parser.add_argument('--start-workers', action='store_true',
                      help='Start demo worker processes')
    parser.add_argument('--check-status', action='store_true',
                      help='Check worker status')
    parser.add_argument('--test-r1', action='store_true',
                      help='Show R1 interface information')
    parser.add_argument('--info', action='store_true',
                      help='Show system information')
    
    args = parser.parse_args()
    
    demo = LAMControlDemo(args.server)
    
    if args.register_workers:
        demo.register_demo_workers()
    elif args.start_workers:
        demo.start_demo_workers()
    elif args.check_status:
        demo.check_worker_status()
    elif args.test_r1:
        demo.test_r1_interface()
    elif args.info:
        demo.show_system_info()
    else:
        # Show all information by default
        demo.show_system_info()
        print()
        demo.check_worker_status()
        print()
        demo.test_r1_interface()

if __name__ == "__main__":
    main()
