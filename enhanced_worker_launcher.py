#!/usr/bin/env python3
"""
Enhanced LAMControl Worker Launcher

Launches workers with pluggable integrations using the enhanced integration manager.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from integration_manager import EnhancedIntegrationManager
from integrated_worker_node import IntegratedWorkerNode


def load_config(config_path: str) -> dict:
    """Load configuration from file"""
    if not os.path.exists(config_path):
        return {}
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load config from {config_path}: {e}")
        return {}


def create_default_config(config_path: str):
    """Create a default configuration file"""
    default_config = {
        "worker": {
            "name": "LAMControl-Worker",
            "location": "localhost",
            "description": "Auto-configured LAMControl worker",
            "port": 6000,
            "max_concurrent_tasks": 5
        },
        "server": {
            "endpoint": "http://localhost:8080"
        },
        "integrations": {
            "browser": {
                "enabled": True,
                "features": ["site_browsing", "google_search", "youtube_search"],
                "settings": {
                    "default_browser": "system_default"
                }
            },
            "computer": {
                "enabled": True,
                "features": ["volume_control", "media_control", "system_control"],
                "settings": {
                    "vol_step_value": 5
                }
            },
            "messaging": {
                "enabled": False,
                "features": ["discord", "telegram"],
                "settings": {
                    "auto_connect": False
                }
            },
            "ai": {
                "enabled": False,
                "features": ["openinterpreter", "automation"],
                "settings": {
                    "llm_model": "llama-3.3-70b-versatile",
                    "auto_run": False
                }
            }
        }
    }
    
    # Ensure directory exists
    config_dir = os.path.dirname(config_path)
    if config_dir:  # Only create directory if there is one
        os.makedirs(config_dir, exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(default_config, f, indent=2)
    
    print(f"Created default configuration: {config_path}")
    return default_config


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('worker.log')
        ]
    )


def main():
    parser = argparse.ArgumentParser(description="Enhanced LAMControl Worker Launcher")
    parser.add_argument("--config", "-c", default="worker_config.json", 
                       help="Configuration file path")
    parser.add_argument("--create-config", action="store_true",
                       help="Create default configuration file")
    parser.add_argument("--integrations", "-i", nargs='+',
                       help="List of integrations to load (overrides config)")
    parser.add_argument("--server", "-s", 
                       help="Server endpoint (overrides config)")
    parser.add_argument("--port", "-p", type=int,
                       help="Worker port (overrides config)")
    parser.add_argument("--name", "-n",
                       help="Worker name (overrides config)")
    parser.add_argument("--location", "-l",
                       help="Worker location (overrides config)")
    parser.add_argument("--description", "-d",
                       help="Worker description (overrides config)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be loaded without starting worker")
    parser.add_argument("--list-integrations", action="store_true",
                       help="List available integrations and exit")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger("WorkerLauncher")
    
    # Handle special actions
    if args.create_config:
        config = create_default_config(args.config)
        return
    
    if args.list_integrations:
        print("Discovering available integrations...")
        manager = EnhancedIntegrationManager()
        discovered = manager.discover_integrations()
        
        print(f"\\nFound {len(discovered)} integrations:\\n")
        for name, info in discovered.items():
            metadata = info['metadata']
            features = info['features']
            print(f"📦 {name} (v{metadata['version']})")
            print(f"   Description: {metadata['description']}")
            print(f"   Category: {metadata['category']}")
            print(f"   Capabilities: {', '.join(info['capabilities'])}")
            if features:
                print(f"   Features: {', '.join(features.keys())}")
            print()
        return
    
    # Load configuration
    config = load_config(args.config)
    if not config and not args.create_config:
        logger.warning(f"Configuration file not found: {args.config}")
        logger.info("Creating default configuration...")
        config = create_default_config(args.config)
    
    # Apply command line overrides
    if args.server:
        config.setdefault('server', {})['endpoint'] = args.server
    if args.port:
        config.setdefault('worker', {})['port'] = args.port
    if args.name:
        config.setdefault('worker', {})['name'] = args.name
    if args.location:
        config.setdefault('worker', {})['location'] = args.location
    if args.description:
        config.setdefault('worker', {})['description'] = args.description
    
    # Get configuration values
    worker_config = config.get('worker', {})
    server_config = config.get('server', {})
    integrations_config = config.get('integrations', {})
    
    worker_name = worker_config.get('name', 'LAMControl-Worker')
    worker_port = worker_config.get('port', 6000)
    worker_location = worker_config.get('location', 'localhost')
    worker_description = worker_config.get('description', 'LAMControl worker with pluggable integrations')
    server_endpoint = server_config.get('endpoint', 'http://localhost:8080')
    max_concurrent_tasks = worker_config.get('max_concurrent_tasks', 5)
    
    logger.info(f"Starting LAMControl Worker: {worker_name}")
    logger.info(f"Server endpoint: {server_endpoint}")
    logger.info(f"Worker port: {worker_port}")
    
    # Initialize integration manager
    manager = EnhancedIntegrationManager()
    
    # Determine which integrations to load
    if args.integrations:
        # Use command line specified integrations
        integrations_to_load = args.integrations
        logger.info(f"Loading integrations from command line: {integrations_to_load}")
    else:
        # Use integrations from config
        integrations_to_load = []
        for name, int_config in integrations_config.items():
            if int_config.get('enabled', True):
                features = int_config.get('features', [])
                if features:
                    integrations_to_load.append(f"{name}:{','.join(features)}")
                else:
                    integrations_to_load.append(name)
        
        logger.info(f"Loading integrations from config: {integrations_to_load}")
    
    if not integrations_to_load:
        logger.warning("No integrations specified to load!")
        logger.info("Use --integrations to specify integrations or check your config file")
        return
    
    # Load integrations
    logger.info("Loading integrations...")
    results = manager.load_integrations_from_list(integrations_to_load, integrations_config)
    
    loaded_count = sum(1 for success in results.values() if success)
    failed_count = len(results) - loaded_count
    
    logger.info(f"Integration loading results: {loaded_count} loaded, {failed_count} failed")
    
    for name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"  {name}: {status}")
    
    if loaded_count == 0:
        logger.error("No integrations loaded successfully! Cannot start worker.")
        return
    
    # Show what would be loaded in dry-run mode
    if args.dry_run:
        print("\\n=== DRY RUN MODE ===")
        print(f"Worker would be started with:")
        print(f"  Name: {worker_name}")
        print(f"  Port: {worker_port}")
        print(f"  Server: {server_endpoint}")
        print(f"  Location: {worker_location}")
        print(f"  Description: {worker_description}")
        print(f"  Max concurrent tasks: {max_concurrent_tasks}")
        print(f"  Loaded integrations: {loaded_count}")
        
        registry = manager.get_registry()
        print(f"  Total capabilities: {len(registry.get_all_capabilities())}")
        print(f"  Capabilities: {', '.join(registry.get_all_capabilities())}")
        print("\\nDry run complete - no worker started.")
        return
    
    # Create and configure worker
    worker = IntegratedWorkerNode(
        server_endpoint=server_endpoint,
        worker_port=worker_port,
        worker_name=worker_name,
        location=worker_location,
        description=worker_description
    )
    
    # Set the integration registry
    worker.registry = manager.get_registry()
    worker.capabilities = worker.registry.get_all_capabilities()
    worker.max_concurrent_tasks = max_concurrent_tasks
    
    logger.info(f"Worker configured with {len(worker.capabilities)} capabilities")
    logger.info(f"Capabilities: {', '.join(worker.capabilities)}")
    
    try:
        # Register with server
        logger.info("Registering with server...")
        if worker.register_with_server():
            logger.info("Successfully registered with server")
        else:
            logger.warning("Failed to register with server - continuing anyway")
        
        # Start heartbeat
        worker.start_heartbeat()
        
        # Start worker
        logger.info(f"Starting worker on port {worker_port}...")
        worker.app.run(host='0.0.0.0', port=worker_port, debug=False)
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Worker error: {e}")
    finally:
        # Cleanup
        logger.info("Shutting down worker...")
        worker.registry.cleanup_all()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    main()
