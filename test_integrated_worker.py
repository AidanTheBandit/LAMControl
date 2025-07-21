#!/usr/bin/env python3
"""
Test script for the new integrated worker node system

This script demonstrates how to create and run a worker with pluggable integrations.
"""

import logging
import time
from integrated_worker_node import IntegratedWorkerNode

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_integrated_worker():
    """Test the integrated worker node"""
    
    print("🚀 Testing LAMControl Integrated Worker Node")
    print("=" * 50)
    
    # Create a worker with auto-discovery
    worker = IntegratedWorkerNode(
        server_endpoint="http://localhost:8080",
        worker_port=6001,
        worker_name="test-integrated-worker",
        location="Development Environment",
        description="Test worker with auto-discovered integrations"
    )
    
    print("Auto-discovering and loading integrations...")
    worker.auto_discover_and_load_integrations()
    
    print(f"\n✅ Worker created with {len(worker.capabilities)} capabilities:")
    for capability in worker.capabilities:
        print(f"  • {capability}")
    
    print(f"\n📦 Loaded integrations:")
    for name, integration in worker.registry.integrations.items():
        print(f"  • {name}: {integration.get_capabilities()}")
    
    # Test some capabilities
    print(f"\n🧪 Testing task execution:")
    
    test_tasks = [
        "browsergoogle test search",
        "computervolume up",
        "discordtext testuser hello world"
    ]
    
    for task in test_tasks:
        print(f"\nExecuting: {task}")
        try:
            result = worker._execute_task(task)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")
    
    print(f"\n✅ Integration test completed!")
    print(f"Worker ready to start on port {worker.worker_port}")

def test_config_based_worker():
    """Test worker creation from configuration file"""
    
    print("\n🔧 Testing Configuration-Based Worker")
    print("=" * 50)
    
    from integrated_worker_node import create_worker_from_config
    
    try:
        worker = create_worker_from_config(
            "worker_config_integrated.json",
            "http://localhost:8080",
            6002
        )
        
        print(f"✅ Worker created from config with {len(worker.capabilities)} capabilities:")
        for capability in worker.capabilities:
            print(f"  • {capability}")
        
        print(f"\n📦 Configured integrations:")
        for name, integration in worker.registry.integrations.items():
            print(f"  • {name}: enabled={integration.is_enabled()}")
        
    except Exception as e:
        print(f"❌ Failed to create worker from config: {e}")

if __name__ == "__main__":
    try:
        test_integrated_worker()
        test_config_based_worker()
        
        print("\n🎉 All tests completed!")
        print("\nTo run a worker:")
        print("  python integrated_worker_node.py http://localhost:8080 6001")
        print("  python integrated_worker_node.py http://localhost:8080 6001 worker_config_integrated.json")
        
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
