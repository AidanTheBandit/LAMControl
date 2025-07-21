#!/usr/bin/env python3
"""
AI Worker for LAMControl Distributed System

Handles AI-powered integrations including OpenInterpreter
and other AI-based automation tasks.

Usage:
    python ai_worker.py <server_endpoint> [port]
    
Example:
    python ai_worker.py http://your-server.com:5000 6004
"""

import sys
import os
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker_node import AIWorker


def main():
    if len(sys.argv) < 2:
        print("Usage: python ai_worker.py <server_endpoint> [port]")
        print("Example: python ai_worker.py http://localhost:5000 6004")
        sys.exit(1)
    
    server_endpoint = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 6004
    
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print(f"Starting AI Worker...")
    print(f"Server: {server_endpoint}")
    print(f"Port: {port}")
    print(f"Capabilities: OpenInterpreter, AI automation")
    
    worker = AIWorker(server_endpoint, port)
    
    try:
        worker.run()
    except KeyboardInterrupt:
        print("\nShutting down AI Worker...")
        logging.info("AI Worker stopped")


if __name__ == "__main__":
    main()
