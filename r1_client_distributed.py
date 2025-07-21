#!/usr/bin/env python3
"""
Enhanced R1 Client for LAMControl Distributed System

This script allows the Rabbit R1 to send prompts to LAMControl servers
(both traditional and distributed) with enhanced features including:
- Automatic server discovery
- Load balancing across multiple servers
- Enhanced error handling and retries
- Real-time status monitoring

Usage:
    python r1_client_distributed.py "your prompt here"
    python r1_client_distributed.py --prompt "your prompt here"
    python r1_client_distributed.py --discover-servers
    python r1_client_distributed.py --server http://your-server:5000 --prompt "your prompt"
"""

import argparse
import json
import logging
import random
import time
from typing import Optional, Dict, List
import requests
from datetime import datetime, timezone


class DistributedLAMClient:
    """Enhanced client for LAMControl distributed system"""
    
    def __init__(self, servers: List[str] = None, timeout: int = 30):
        self.servers = servers or ["http://localhost:5000"]
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'LAMControl-R1-Client-Distributed/3.0',
            'Content-Type': 'application/json'
        })
        
        # Server health cache
        self.server_health = {}
        self.last_health_check = {}
    
    def discover_servers(self, base_ports: List[int] = [5000, 5001, 5002]) -> List[str]:
        """Discover available LAMControl servers on the network"""
        discovered = []
        
        # Check localhost ports
        for port in base_ports:
            server = f"http://localhost:{port}"
            if self._check_server_health(server):
                discovered.append(server)
        
        # Check common network addresses (basic discovery)
        common_ips = ['127.0.0.1', '192.168.1.100', '192.168.1.101']
        for ip in common_ips:
            for port in base_ports:
                server = f"http://{ip}:{port}"
                if self._check_server_health(server):
                    discovered.append(server)
        
        if discovered:
            self.servers = discovered
            logging.info(f"Discovered {len(discovered)} servers: {discovered}")
        
        return discovered
    
    def _check_server_health(self, server: str) -> bool:
        """Check if a server is healthy"""
        try:
            response = self.session.get(
                f"{server}/api/health",
                timeout=5
            )
            
            if response.status_code == 200:
                health_data = response.json()
                self.server_health[server] = {
                    'status': 'healthy',
                    'last_check': datetime.now(timezone.utc),
                    'workers': health_data.get('workers', 0),
                    'online_workers': health_data.get('online_workers', 0),
                    'version': health_data.get('version', 'unknown')
                }
                return True
            else:
                self.server_health[server] = {
                    'status': 'unhealthy',
                    'last_check': datetime.now(timezone.utc),
                    'error': f"HTTP {response.status_code}"
                }
                return False
                
        except Exception as e:
            self.server_health[server] = {
                'status': 'unreachable',
                'last_check': datetime.now(timezone.utc),
                'error': str(e)
            }
            return False
    
    def get_best_server(self) -> Optional[str]:
        """Get the best available server based on health and load"""
        healthy_servers = []
        
        for server in self.servers:
            # Check health if not checked recently
            last_check = self.last_health_check.get(server)
            if (not last_check or 
                (datetime.now(timezone.utc) - last_check).seconds > 60):
                self._check_server_health(server)
                self.last_health_check[server] = datetime.now(timezone.utc)
            
            # Add to healthy servers if available
            health = self.server_health.get(server, {})
            if health.get('status') == 'healthy':
                healthy_servers.append((server, health))
        
        if not healthy_servers:
            return None
        
        # Sort by online workers (more workers = better)
        healthy_servers.sort(key=lambda x: x[1].get('online_workers', 0), reverse=True)
        
        # Return the best server (or random among top 3)
        top_servers = healthy_servers[:3]
        return random.choice(top_servers)[0]
    
    def send_prompt(self, prompt: str, source: str = "r1", 
                   metadata: Dict = None, max_retries: int = 3) -> Dict:
        """Send a prompt with automatic server selection and retries"""
        
        for attempt in range(max_retries):
            server = self.get_best_server()
            if not server:
                if attempt == 0:
                    # Try discovering servers
                    discovered = self.discover_servers()
                    if discovered:
                        server = self.get_best_server()
                
                if not server:
                    return {
                        'success': False,
                        'error': 'No healthy servers available',
                        'attempt': attempt + 1
                    }
            
            try:
                payload = {
                    'prompt': prompt,
                    'source': source,
                    'metadata': metadata or {}
                }
                
                response = self.session.post(
                    f"{server}/api/prompt",
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        'success': True,
                        'server': server,
                        'response': result.get('response', ''),
                        'id': result.get('id'),
                        'attempt': attempt + 1
                    }
                else:
                    logging.warning(f"Server {server} returned {response.status_code}")
                    # Mark server as unhealthy and try next
                    self.server_health[server] = {
                        'status': 'unhealthy',
                        'last_check': datetime.now(timezone.utc),
                        'error': f"HTTP {response.status_code}"
                    }
                    
            except Exception as e:
                logging.error(f"Error sending to {server}: {e}")
                # Mark server as unreachable
                self.server_health[server] = {
                    'status': 'unreachable',
                    'last_check': datetime.now(timezone.utc),
                    'error': str(e)
                }
            
            # Wait before retry
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return {
            'success': False,
            'error': f'Failed after {max_retries} attempts',
            'attempts': max_retries
        }
    
    def get_server_status(self) -> Dict:
        """Get status of all known servers"""
        status = {
            'servers': [],
            'total_servers': len(self.servers),
            'healthy_servers': 0,
            'total_workers': 0,
            'online_workers': 0
        }
        
        for server in self.servers:
            self._check_server_health(server)
            health = self.server_health.get(server, {})
            
            server_info = {
                'url': server,
                'status': health.get('status', 'unknown'),
                'workers': health.get('workers', 0),
                'online_workers': health.get('online_workers', 0),
                'version': health.get('version', 'unknown'),
                'last_check': health.get('last_check', '').isoformat() if health.get('last_check') else '',
                'error': health.get('error', '')
            }
            
            status['servers'].append(server_info)
            
            if health.get('status') == 'healthy':
                status['healthy_servers'] += 1
                status['total_workers'] += health.get('workers', 0)
                status['online_workers'] += health.get('online_workers', 0)
        
        return status
    
    def monitor_servers(self, interval: int = 30):
        """Monitor server health continuously"""
        print("Starting server monitoring (Ctrl+C to stop)...")
        
        try:
            while True:
                status = self.get_server_status()
                
                print(f"\n=== Server Status at {datetime.now().strftime('%H:%M:%S')} ===")
                print(f"Healthy servers: {status['healthy_servers']}/{status['total_servers']}")
                print(f"Total workers: {status['online_workers']}/{status['total_workers']} online")
                
                for server_info in status['servers']:
                    status_icon = "✓" if server_info['status'] == 'healthy' else "✗"
                    print(f"{status_icon} {server_info['url']} - {server_info['status']}")
                    if server_info['status'] == 'healthy':
                        print(f"   Workers: {server_info['online_workers']}/{server_info['workers']}")
                    elif server_info['error']:
                        print(f"   Error: {server_info['error']}")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")


def print_result(result: dict, verbose: bool = False):
    """Print result in a user-friendly format"""
    if result["success"]:
        print("✓ SUCCESS")
        print(f"Response: {result.get('response', 'Task completed')}")
        
        if verbose:
            print(f"Server: {result.get('server', 'unknown')}")
            print(f"ID: {result.get('id', 'unknown')}")
            print(f"Attempts: {result.get('attempt', 1)}")
    else:
        print("✗ FAILED")
        print(f"Error: {result.get('error', 'Unknown error')}")
        
        if verbose and 'attempts' in result:
            print(f"Failed after {result['attempts']} attempts")


def main():
    """Main function to handle command line arguments and execute requests"""
    parser = argparse.ArgumentParser(
        description="Enhanced R1 Client for LAMControl Distributed System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Turn on the lights"
  %(prog)s --prompt "Send a text to John saying I'm running late"
  %(prog)s --servers http://server1:5000,http://server2:5000 --prompt "Play music"
  %(prog)s --discover-servers
  %(prog)s --status
  %(prog)s --monitor
        """
    )
    
    # Main arguments
    parser.add_argument(
        'prompt', 
        nargs='?', 
        help='The prompt to send to LAMControl'
    )
    
    parser.add_argument(
        '--prompt', '-p',
        help='The prompt to send to LAMControl (alternative to positional argument)'
    )
    
    parser.add_argument(
        '--servers', '-s',
        help='Comma-separated list of server URLs (default: http://localhost:5000)'
    )
    
    parser.add_argument(
        '--discover-servers', '-d',
        action='store_true',
        help='Discover available LAMControl servers'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show status of all servers'
    )
    
    parser.add_argument(
        '--monitor',
        action='store_true',
        help='Monitor server health continuously'
    )
    
    parser.add_argument(
        '--source',
        default='r1',
        help='Source identifier (default: r1)'
    )
    
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum retry attempts (default: 3)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Parse servers
    if args.servers:
        servers = [s.strip() for s in args.servers.split(',')]
    else:
        servers = ["http://localhost:5000"]
    
    # Initialize client
    client = DistributedLAMClient(servers=servers, timeout=args.timeout)
    
    # Handle different modes
    if args.discover_servers:
        print("Discovering LAMControl servers...")
        discovered = client.discover_servers()
        if discovered:
            print(f"Found {len(discovered)} servers:")
            for server in discovered:
                print(f"  {server}")
        else:
            print("No servers found.")
        return
    
    if args.status:
        status = client.get_server_status()
        print(f"=== LAMControl Server Status ===")
        print(f"Servers: {status['healthy_servers']}/{status['total_servers']} healthy")
        print(f"Workers: {status['online_workers']}/{status['total_workers']} online")
        print()
        
        for server_info in status['servers']:
            status_icon = "✓" if server_info['status'] == 'healthy' else "✗"
            print(f"{status_icon} {server_info['url']}")
            print(f"   Status: {server_info['status']}")
            if server_info['status'] == 'healthy':
                print(f"   Workers: {server_info['online_workers']}/{server_info['workers']}")
                print(f"   Version: {server_info['version']}")
            elif server_info['error']:
                print(f"   Error: {server_info['error']}")
            print()
        return
    
    if args.monitor:
        client.monitor_servers()
        return
    
    # Get prompt
    prompt = args.prompt or args.prompt
    if not prompt:
        print("Error: No prompt provided")
        print("Use --help for usage information")
        return
    
    # Send prompt
    print(f"Sending prompt to LAMControl: {prompt}")
    result = client.send_prompt(
        prompt=prompt,
        source=args.source,
        max_retries=args.max_retries
    )
    
    print_result(result, args.verbose)


if __name__ == "__main__":
    main()
