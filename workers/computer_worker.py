#!/usr/bin/env python3
"""
Computer Control Worker for LAMControl Distributed System

Handles local computer control tasks including volume control,
application launching, media controls, and power management.

Usage:
    python computer_worker.py <server_endpoint> [port]
    
Example:
    python computer_worker.py http://your-server.com:5000 6002
"""

import sys
import os
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker_node import ComputerWorker


def main():
    if len(sys.argv) < 2:
        print("Usage: python computer_worker.py <server_endpoint> [port]")
        print("Example: python computer_worker.py http://localhost:5000 6002")
        sys.exit(1)
    
    server_endpoint = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 6002
    
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print(f"Starting Computer Control Worker...")
    print(f"Server: {server_endpoint}")
    print(f"Port: {port}")
    print(f"Capabilities: Volume control, app launching, media controls, power management")
    
    worker = ComputerWorker(server_endpoint, port)
    
    try:
        worker.run()
    except KeyboardInterrupt:
        print("\nShutting down Computer Control Worker...")
        logging.info("Computer Control Worker stopped")


if __name__ == "__main__":
    main()
