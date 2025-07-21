#!/usr/bin/env python3
"""
Messaging Worker for LAMControl Distributed System

Handles social media and messaging platform integrations including
Discord, Telegram, and Facebook messaging.

Usage:
    python messaging_worker.py <server_endpoint> [port]
    
Example:
    python messaging_worker.py http://your-server.com:5000 6003
"""

import sys
import os
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker_node import MessagingWorker


def main():
    if len(sys.argv) < 2:
        print("Usage: python messaging_worker.py <server_endpoint> [port]")
        print("Example: python messaging_worker.py http://localhost:5000 6003")
        sys.exit(1)
    
    server_endpoint = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 6003
    
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print(f"Starting Messaging Worker...")
    print(f"Server: {server_endpoint}")
    print(f"Port: {port}")
    print(f"Capabilities: Discord, Telegram, Facebook messaging")
    
    worker = MessagingWorker(server_endpoint, port)
    
    try:
        worker.run()
    except KeyboardInterrupt:
        print("\nShutting down Messaging Worker...")
        logging.info("Messaging Worker stopped")


if __name__ == "__main__":
    main()
