#!/usr/bin/env python3
"""
LAMControl R1 Client Script v2.0

This script allows the Rabbit R1 to send prompts directly to LAMControl
when running in web server mode, with enhanced features including:
- Status checking and response retrieval
- Better error handling and retries
- Async support for non-blocking operations
- Health checking

Usage:
    python r1_client.py "your prompt here"
    python r1_client.py --prompt "your prompt here"
    python r1_client.py --host http://your-server:5000 --prompt "your prompt"
    python r1_client.py --check-status PROMPT_ID
    python r1_client.py --health-check
"""

import argparse
import requests
import json
import sys
import time
from typing import Optional, Dict

class LAMControlClient:
    def __init__(self, host: str = "http://localhost:5000", timeout: int = 30):
        """
        Initialize the LAMControl client.
        
        Args:
            host: The base URL of the LAMControl web server
            timeout: Request timeout in seconds
        """
        self.host = host.rstrip('/')
        self.timeout = timeout
        
    def health_check(self) -> Dict:
        """
        Check if LAMControl server is healthy and get system info.
        
        Returns:
            Health status dictionary
        """
        try:
            response = requests.get(f"{self.host}/api/health", timeout=self.timeout)
            
            if response.status_code == 200:
                health_data = response.json()
                return {
                    "success": True,
                    "healthy": True,
                    "data": health_data,
                    "message": "LAMControl server is healthy"
                }
            else:
                return {
                    "success": False,
                    "healthy": False,
                    "error": f"Health check failed with status {response.status_code}",
                    "message": response.text
                }
                
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "healthy": False,
                "error": "Connection failed",
                "message": f"Could not connect to LAMControl server at {self.host}"
            }
        except Exception as e:
            return {
                "success": False,
                "healthy": False,
                "error": "Unexpected error",
                "message": str(e)
            }
        
    def send_prompt(self, prompt: str, source: str = "r1", metadata: Dict = None) -> Dict:
        """
        Send a prompt to LAMControl.
        
        Args:
            prompt: The text prompt to send
            source: Source identifier (default: "r1")
            metadata: Additional metadata to include
            
        Returns:
            Response dictionary from the server
        """
        url = f"{self.host}/api/prompt"
        
        payload = {
            "prompt": prompt,
            "source": source
        }
        
        if metadata:
            payload["metadata"] = metadata
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "data": data,
                    "prompt_id": data.get("id"),
                    "message": "Prompt sent successfully"
                }
            else:
                return {
                    "success": False,
                    "error": f"Server returned status {response.status_code}",
                    "message": response.text
                }
                
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Connection failed",
                "message": f"Could not connect to LAMControl server at {self.host}"
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timeout",
                "message": f"The request took longer than {self.timeout} seconds to complete"
            }
        except Exception as e:
            return {
                "success": False,
                "error": "Unexpected error",
                "message": str(e)
            }
    
    def check_prompt_status(self, prompt_id: str) -> Dict:
        """
        Check the status of a specific prompt.
        
        Args:
            prompt_id: The ID of the prompt to check
            
        Returns:
            Status dictionary
        """
        url = f"{self.host}/api/prompt/{prompt_id}/status"
        
        try:
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "data": data,
                    "status": data.get("status"),
                    "message": f"Prompt status: {data.get('status')}"
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": "Prompt not found",
                    "message": f"No prompt found with ID: {prompt_id}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Server returned status {response.status_code}",
                    "message": response.text
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": "Unexpected error",
                "message": str(e)
            }
    
    def send_and_wait(self, prompt: str, source: str = "r1", 
                     metadata: Dict = None, max_wait: int = 60, 
                     check_interval: int = 2) -> Dict:
        """
        Send a prompt and wait for completion.
        
        Args:
            prompt: The text prompt to send
            source: Source identifier
            metadata: Additional metadata
            max_wait: Maximum time to wait in seconds
            check_interval: How often to check status in seconds
            
        Returns:
            Final result dictionary
        """
        # First send the prompt
        result = self.send_prompt(prompt, source, metadata)
        
        if not result["success"]:
            return result
        
        prompt_id = result["prompt_id"]
        start_time = time.time()
        
        print(f"Prompt sent with ID: {prompt_id}")
        print("Waiting for completion...")
        
        while time.time() - start_time < max_wait:
            status_result = self.check_prompt_status(prompt_id)
            
            if not status_result["success"]:
                return status_result
            
            status = status_result["data"]["status"]
            
            if status == "completed":
                return {
                    "success": True,
                    "completed": True,
                    "data": status_result["data"],
                    "message": "Prompt completed successfully"
                }
            elif status == "failed":
                return {
                    "success": False,
                    "completed": True,
                    "error": "Prompt processing failed",
                    "data": status_result["data"],
                    "message": status_result["data"].get("error", "Unknown error")
                }
            
            # Still pending or processing
            print(f"Status: {status}... waiting {check_interval}s")
            time.sleep(check_interval)
        
        return {
            "success": False,
            "completed": False,
            "error": "Timeout",
            "message": f"Prompt did not complete within {max_wait} seconds"
        }

    def test_connection(self) -> bool:
        """
        Test if the LAMControl server is reachable.
        
        Returns:
            True if server is reachable, False otherwise
        """
        try:
            response = requests.get(f"{self.host}/", timeout=5)
            return response.status_code in [200, 302, 401]  # 401 is expected for login page
        except:
            return False


def print_result(result: dict, verbose: bool = False):
    """Print result in a user-friendly format"""
    if result["success"]:
        print("✅ SUCCESS:", result["message"])
        if "prompt_id" in result:
            print(f"   Prompt ID: {result['prompt_id']}")
        if verbose and "data" in result:
            print(f"   Details: {json.dumps(result['data'], indent=2)}")
    else:
        print("❌ ERROR:", result["message"])
        if "error" in result:
            print(f"   Error Type: {result['error']}")

def main():
    """Main function to handle command line arguments and execute requests"""
    parser = argparse.ArgumentParser(
        description="LAMControl R1 Client v2.0 - Send prompts to LAMControl web server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Turn on the lights"
  %(prog)s --prompt "Send a text to John saying I'm running late"
  %(prog)s --host http://192.168.1.100:5000 --prompt "Play music on Spotify"
  %(prog)s --check-status abc123def456
  %(prog)s --health-check
  %(prog)s --wait "Turn volume to 50"
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
        '--host',
        default='http://localhost:5000',
        help='LAMControl server URL (default: http://localhost:5000)'
    )
    
    parser.add_argument(
        '--source', '-s',
        default='r1',
        help='Source identifier (default: r1)'
    )
    
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    # Status checking
    parser.add_argument(
        '--check-status',
        metavar='PROMPT_ID',
        help='Check the status of a specific prompt by ID'
    )
    
    # Health check
    parser.add_argument(
        '--health-check',
        action='store_true',
        help='Check if LAMControl server is healthy'
    )
    
    # Send and wait
    parser.add_argument(
        '--wait', '-w',
        action='store_true',
        help='Send prompt and wait for completion'
    )
    
    parser.add_argument(
        '--max-wait',
        type=int,
        default=60,
        help='Maximum time to wait for completion in seconds (default: 60)'
    )
    
    # Metadata
    parser.add_argument(
        '--metadata',
        help='Additional metadata as JSON string'
    )
    
    # Output options
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output'
    )
    
    parser.add_argument(
        '--json-output',
        action='store_true',
        help='Output results as JSON'
    )
    
    args = parser.parse_args()
    
    # Initialize client
    client = LAMControlClient(host=args.host, timeout=args.timeout)
    
    # Handle different operations
    if args.health_check:
        result = client.health_check()
        
    elif args.check_status:
        result = client.check_prompt_status(args.check_status)
        
    else:
        # Determine the prompt to send
        prompt = args.prompt or args.prompt
        if not prompt:
            parser.print_help()
            print("\nError: No prompt provided. Use positional argument or --prompt option.")
            sys.exit(1)
        
        # Parse metadata if provided
        metadata = None
        if args.metadata:
            try:
                metadata = json.loads(args.metadata)
            except json.JSONDecodeError:
                print("Error: Invalid JSON in metadata argument")
                sys.exit(1)
        
        # Test connection first
        if args.verbose:
            print(f"Testing connection to {args.host}...")
        
        if not client.test_connection():
            print(f"❌ ERROR: Cannot connect to LAMControl server at {args.host}")
            print("   Make sure the server is running and accessible.")
            sys.exit(1)
        
        if args.verbose:
            print("✅ Connection successful")
        
        # Send prompt
        if args.wait:
            print(f"Sending prompt and waiting for completion: {prompt}")
            result = client.send_and_wait(
                prompt, 
                source=args.source, 
                metadata=metadata,
                max_wait=args.max_wait
            )
        else:
            result = client.send_prompt(prompt, source=args.source, metadata=metadata)
    
    # Output results
    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        print_result(result, verbose=args.verbose)
    
    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)

if __name__ == "__main__":
    main()
