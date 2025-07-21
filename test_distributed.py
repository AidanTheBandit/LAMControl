#!/usr/bin/env python3
"""
Test Script for LAMControl Distributed System

This script tests the distributed architecture by:
1. Starting a test server
2. Starting test workers
3. Sending test prompts
4. Verifying responses

Usage:
    python test_distributed.py [--port 5000]
"""

import os
import sys
import time
import subprocess
import threading
import requests
import json
import argparse
from typing import List

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class DistributedSystemTester:
    """Test suite for distributed LAMControl system"""
    
    def __init__(self, server_port: int = 5000):
        self.server_port = server_port
        self.server_url = f"http://localhost:{server_port}"
        self.worker_ports = [6001, 6002, 6003, 6004]
        self.processes = []
        
    def start_test_server(self):
        """Start a test server instance"""
        print("Starting test server...")
        
        # Create test config
        config = {
            "mode": "distributed_server",
            "distributed": {
                "server_host": "127.0.0.1",
                "server_port": self.server_port
            },
            "groq_model": "llama-3.3-70b-versatile",
            "debug": True
        }
        
        with open('test_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        # Start server process
        cmd = [sys.executable, 'main_distributed.py', '--config', 'test_config.json']
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.processes.append(process)
        
        # Wait for server to start
        self._wait_for_server()
        print(f"✓ Test server started on {self.server_url}")
        
    def start_test_workers(self):
        """Start test worker instances"""
        worker_types = ['browser', 'computer', 'messaging', 'ai']
        
        for i, worker_type in enumerate(worker_types):
            port = self.worker_ports[i]
            print(f"Starting {worker_type} worker on port {port}...")
            
            cmd = [
                sys.executable, 
                f'workers/{worker_type}_worker.py',
                self.server_url,
                str(port)
            ]
            
            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.processes.append(process)
                time.sleep(2)  # Give worker time to start
                print(f"✓ {worker_type.title()} worker started")
            except Exception as e:
                print(f"✗ Failed to start {worker_type} worker: {e}")
    
    def _wait_for_server(self, timeout: int = 30):
        """Wait for server to become available"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.server_url}/api/health", timeout=5)
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(1)
        
        raise Exception(f"Server did not start within {timeout} seconds")
    
    def test_server_health(self):
        """Test server health endpoint"""
        print("\nTesting server health...")
        
        try:
            response = requests.get(f"{self.server_url}/api/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Server health: {data['status']}")
                print(f"  Workers: {data.get('workers', 0)}")
                print(f"  Online workers: {data.get('online_workers', 0)}")
                return True
            else:
                print(f"✗ Server health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Server health check error: {e}")
            return False
    
    def test_worker_registration(self):
        """Test worker registration"""
        print("\nTesting worker registration...")
        
        try:
            response = requests.get(f"{self.server_url}/api/workers", timeout=10)
            if response.status_code == 200:
                data = response.json()
                workers = data.get('workers', [])
                print(f"✓ {len(workers)} workers registered")
                
                for worker in workers:
                    status_icon = "✓" if worker['status'] == 'online' else "✗"
                    print(f"  {status_icon} {worker['worker_type']} worker: {worker['status']}")
                
                return len(workers) > 0
            else:
                print(f"✗ Worker registration check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Worker registration check error: {e}")
            return False
    
    def test_prompt_processing(self):
        """Test prompt processing"""
        print("\nTesting prompt processing...")
        
        test_prompts = [
            "browser google search for cats",
            "computer volume 50",
            "openinterpreter say hello"
        ]
        
        success_count = 0
        
        for prompt in test_prompts:
            try:
                print(f"  Testing: {prompt}")
                
                payload = {
                    'prompt': prompt,
                    'source': 'test'
                }
                
                response = requests.post(
                    f"{self.server_url}/api/prompt",
                    json=payload,
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'success':
                        print(f"    ✓ Success: {data.get('response', 'No response')}")
                        success_count += 1
                    else:
                        print(f"    ✗ Failed: {data.get('error', 'Unknown error')}")
                else:
                    print(f"    ✗ HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"    ✗ Error: {e}")
        
        print(f"\n✓ {success_count}/{len(test_prompts)} prompts processed successfully")
        return success_count > 0
    
    def test_distributed_client(self):
        """Test distributed client"""
        print("\nTesting distributed client...")
        
        try:
            # Import the distributed client
            from r1_client_distributed import DistributedLAMClient
            
            client = DistributedLAMClient(servers=[self.server_url])
            
            # Test server discovery
            servers = client.discover_servers([self.server_port])
            print(f"✓ Discovered {len(servers)} servers")
            
            # Test prompt sending
            result = client.send_prompt("test prompt from distributed client")
            if result['success']:
                print(f"✓ Client prompt successful: {result.get('response', 'No response')}")
                return True
            else:
                print(f"✗ Client prompt failed: {result.get('error')}")
                return False
                
        except Exception as e:
            print(f"✗ Distributed client test error: {e}")
            return False
    
    def cleanup(self):
        """Clean up test processes and files"""
        print("\nCleaning up...")
        
        # Terminate all processes
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
        
        # Remove test config file
        try:
            os.remove('test_config.json')
        except:
            pass
        
        print("✓ Cleanup completed")
    
    def run_full_test(self):
        """Run the complete test suite"""
        print("=== LAMControl Distributed System Test ===\n")
        
        try:
            # Start server
            self.start_test_server()
            
            # Start workers
            self.start_test_workers()
            
            # Wait for workers to register
            time.sleep(5)
            
            # Run tests
            tests = [
                self.test_server_health,
                self.test_worker_registration,
                self.test_prompt_processing,
                self.test_distributed_client
            ]
            
            passed = 0
            for test in tests:
                if test():
                    passed += 1
            
            print(f"\n=== Test Results ===")
            print(f"Passed: {passed}/{len(tests)} tests")
            
            if passed == len(tests):
                print("🎉 All tests passed! Distributed system is working correctly.")
                return True
            else:
                print("⚠️  Some tests failed. Check the output above for details.")
                return False
                
        except KeyboardInterrupt:
            print("\nTest interrupted by user")
            return False
        except Exception as e:
            print(f"\nTest suite error: {e}")
            return False
        finally:
            self.cleanup()


def main():
    parser = argparse.ArgumentParser(description='Test LAMControl Distributed System')
    parser.add_argument('--port', '-p', type=int, default=5000,
                       help='Server port to use for testing (default: 5000)')
    
    args = parser.parse_args()
    
    # Check if required files exist
    required_files = [
        'main_distributed.py',
        'distributed_server.py',
        'worker_node.py',
        'r1_client_distributed.py'
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        print(f"Error: Missing required files: {missing_files}")
        sys.exit(1)
    
    # Run tests
    tester = DistributedSystemTester(args.port)
    success = tester.run_full_test()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
