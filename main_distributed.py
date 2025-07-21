"""
LAMControl Distributed Main Entry Point

Supports both traditional modes (web, rabbit, cli) and new distributed modes:
- distributed_server: Run as central server
- distributed_worker: Run as worker node

Usage:
    python main_distributed.py [--config config_file.json]
    
The mode is determined by the "mode" field in the configuration file.
"""

import os
import sys
import json
import logging
import coloredlogs
import argparse
from datetime import datetime, timezone

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import config as config_module, get_env, splash_screen
from distributed_server import DistributedLAMServer
from worker_node import BrowserWorker, ComputerWorker, MessagingWorker, AIWorker


def load_distributed_config(config_file="config_distributed.json"):
    """Load configuration file for distributed mode"""
    if not os.path.exists(config_file):
        # Fall back to regular config
        config_file = "config.json"
    
    with open(config_file, 'r') as f:
        return json.load(f)


def run_distributed_server(config):
    """Run LAMControl as distributed server"""
    print(splash_screen.colored_splash)
    print("Starting LAMControl Distributed Server...")
    
    # Get server configuration
    server_config = config.get('distributed', {})
    host = server_config.get('server_host', '0.0.0.0')
    port = server_config.get('server_port', 5000)
    
    # Initialize and start server
    server = DistributedLAMServer(host=host, port=port)
    
    logging.info(f"LAMControl Distributed Server starting on {host}:{port}")
    print(f"\n=== LAMControl Distributed Server ===")
    print(f"Server URL: http://{host}:{port}")
    print(f"Admin Dashboard: http://{host}:{port}")
    print(f"Worker Registration: http://{host}:{port}/api/worker/register")
    print(f"R1 API Endpoint: http://{host}:{port}/api/prompt")
    print(f"=====================================\n")
    
    try:
        server.run(debug=config.get('debug', False))
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"Server error: {e}")
        raise


def run_distributed_worker(config):
    """Run LAMControl as distributed worker"""
    print(splash_screen.colored_splash)
    
    # Get worker configuration
    worker_config = config.get('worker', {})
    worker_type = worker_config.get('type', 'browser')
    server_endpoint = worker_config.get('server_endpoint', 'http://localhost:5000')
    worker_port = worker_config.get('worker_port', 6001)
    
    print(f"Starting LAMControl {worker_type.title()} Worker...")
    print(f"Server: {server_endpoint}")
    print(f"Port: {worker_port}")
    
    # Create appropriate worker
    if worker_type == 'browser':
        worker = BrowserWorker(server_endpoint, worker_port)
        print("Capabilities: Web browsing, Google/YouTube/Gmail/Amazon searches")
    elif worker_type == 'computer':
        worker = ComputerWorker(server_endpoint, worker_port)
        print("Capabilities: Volume control, app launching, media controls, power management")
    elif worker_type == 'messaging':
        worker = MessagingWorker(server_endpoint, worker_port)
        print("Capabilities: Discord, Telegram, Facebook messaging")
    elif worker_type == 'ai':
        worker = AIWorker(server_endpoint, worker_port)
        print("Capabilities: OpenInterpreter, AI automation")
    else:
        logging.error(f"Unknown worker type: {worker_type}")
        print(f"Error: Unknown worker type '{worker_type}'")
        print("Valid types: browser, computer, messaging, ai")
        sys.exit(1)
    
    try:
        worker.run(debug=config.get('debug', False))
    except KeyboardInterrupt:
        logging.info(f"{worker_type.title()} Worker stopped by user")
    except Exception as e:
        logging.error(f"Worker error: {e}")
        raise


def run_traditional_mode(config):
    """Run LAMControl in traditional mode (web, rabbit, cli)"""
    # Import the original main module
    from main import main as original_main
    
    # Set the config for the traditional mode
    config_module.config = config
    
    # Run the original main function
    original_main()


def main():
    """Main entry point for distributed LAMControl"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='LAMControl Distributed System')
    parser.add_argument('--config', '-c', default='config_distributed.json',
                       help='Configuration file to use (default: config_distributed.json)')
    parser.add_argument('--worker-type', '-w', 
                       choices=['browser', 'computer', 'messaging', 'ai'],
                       help='Worker type (overrides config file)')
    parser.add_argument('--server-endpoint', '-s',
                       help='Server endpoint for worker mode (overrides config file)')
    parser.add_argument('--port', '-p', type=int,
                       help='Port to run on (overrides config file)')
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_distributed_config(args.config)
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {args.config}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in configuration file: {e}")
        sys.exit(1)
    
    # Override config with command line arguments
    if args.worker_type:
        config.setdefault('worker', {})['type'] = args.worker_type
    if args.server_endpoint:
        config.setdefault('worker', {})['server_endpoint'] = args.server_endpoint
    if args.port:
        if config.get('mode') == 'distributed_server':
            config.setdefault('distributed', {})['server_port'] = args.port
        else:
            config.setdefault('worker', {})['worker_port'] = args.port
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if config.get('debug', False) else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    coloredlogs.install(
        level='DEBUG' if config.get('debug', False) else 'INFO',
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        field_styles={'asctime': {'color': 'white'}}
    )
    
    # Get mode from config
    mode = config.get('mode', 'web')
    
    logging.info(f"Starting LAMControl in {mode} mode")
    
    try:
        if mode == 'distributed_server':
            run_distributed_server(config)
        elif mode == 'distributed_worker':
            run_distributed_worker(config)
        elif mode in ['web', 'rabbit', 'cli']:
            # Set the global config for traditional mode
            config_module.config = config
            run_traditional_mode(config)
        else:
            logging.error(f"Unknown mode: {mode}")
            print(f"Error: Unknown mode '{mode}'")
            print("Valid modes: web, rabbit, cli, distributed_server, distributed_worker")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logging.info("LAMControl stopped by user")
    except Exception as e:
        logging.error(f"LAMControl error: {e}")
        if config.get('debug', False):
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()
