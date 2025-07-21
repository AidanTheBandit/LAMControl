#!/usr/bin/env python3
"""
Browser Worker for LAMControl Distributed System

Handles browser automation tasks including web searches,
site navigation, and browser-based integrations.

Usage:
    python browser_worker.py <server_endpoint> [port]
    
Example:
    python browser_worker.py http://your-server.com:5000 6001
"""

import sys
import os
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker_node import BrowserWorker


def main():
    if len(sys.argv) < 2:
        print("Usage: python browser_worker.py <server_endpoint> [port]")
        print("Example: python browser_worker.py http://localhost:5000 6001")
        sys.exit(1)
    
    server_endpoint = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 6001
    
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print(f"Starting Browser Worker...")
    print(f"Server: {server_endpoint}")
    print(f"Port: {port}")
    print(f"Capabilities: Web browsing, Google/YouTube/Gmail/Amazon searches")
    
    worker = BrowserWorker(server_endpoint, port)
    
    try:
        worker.run()
    except KeyboardInterrupt:
        print("\nShutting down Browser Worker...")
        logging.info("Browser Worker stopped")


if __name__ == "__main__":
    main()
