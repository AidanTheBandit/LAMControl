#!/usr/bin/env python3
"""
LAMControl Pluggable Integrations Demo

This script demonstrates the new pluggable integrations system for LAMControl workers.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from integration_manager import EnhancedIntegrationManager
from integrated_worker_node import IntegratedWorkerNode


def setup_demo_logging():
    """Setup logging for the demo"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def demo_integration_discovery():
    """Demonstrate integration discovery"""
    print("🔍 Discovering Available Integrations")
    print("=" * 50)
    
    manager = EnhancedIntegrationManager()
    discovered = manager.discover_integrations()
    
    print(f"Found {len(discovered)} integrations:\\n")
    
    for name, info in discovered.items():
        metadata = info['metadata']
        features = info['features']
        capabilities = info['capabilities']
        
        print(f"📦 {name.upper()} Integration (v{metadata['version']})")
        print(f"   Author: {metadata['author']}")
        print(f"   Description: {metadata['description']}")
        print(f"   Category: {metadata['category']}")
        print(f"   Tags: {', '.join(metadata['tags'])}")
        print(f"   Capabilities: {', '.join(capabilities)}")
        
        if features:
            print(f"   Features:")
            for feature_name, feature_info in features.items():
                enabled = "✅" if feature_info['enabled'] else "❌"
                required = "🔒" if feature_info['required'] else "🔓"
                print(f"     {enabled} {required} {feature_name}: {feature_info['description']}")
        
        print()
    
    return discovered


def demo_feature_configuration():
    """Demonstrate feature-based configuration"""
    print("⚙️  Feature-Based Configuration Demo")
    print("=" * 50)
    
    # Create a sample configuration
    config = {
        "worker": {
            "name": "Demo-Worker",
            "location": "Demo Environment",
            "description": "Demonstration of pluggable integrations",
            "port": 6000
        },
        "server": {
            "endpoint": "http://localhost:8080"
        },
        "integrations": {
            "browser": {
                "enabled": True,
                "features": ["site_browsing", "google_search", "youtube_search"],
                "settings": {
                    "default_browser": "system_default",
                    "search_domain": "google.com"
                }
            },
            "computer": {
                "enabled": True,
                "features": ["volume_control", "media_control"],
                "settings": {
                    "vol_step_value": 5,
                    "max_volume": 100
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
                "features": ["openinterpreter"],
                "settings": {
                    "llm_model": "llama-3.3-70b-versatile",
                    "auto_run": False
                }
            }
        }
    }
    
    # Save demo configuration
    config_file = "demo_worker_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"📄 Created demo configuration: {config_file}")
    print("\\nConfiguration includes:")
    
    for integration_name, int_config in config["integrations"].items():
        status = "✅ ENABLED" if int_config["enabled"] else "❌ DISABLED"
        features = int_config.get("features", [])
        print(f"  {status} {integration_name}: {len(features)} features")
        if features:
            print(f"    Features: {', '.join(features)}")
    
    print()
    return config_file


def demo_integration_loading():
    """Demonstrate loading integrations with features"""
    print("🔄 Integration Loading Demo")
    print("=" * 50)
    
    manager = EnhancedIntegrationManager()
    
    # Define integrations to load with specific features
    integrations_to_load = [
        "browser:site_browsing,google_search",
        "computer:volume_control"
    ]
    
    print(f"Loading integrations: {integrations_to_load}")
    print()
    
    # Load integrations
    results = manager.load_integrations_from_list(integrations_to_load)
    
    print("Loading Results:")
    for name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {name}: {status}")
    
    # Show loaded capabilities
    registry = manager.get_registry()
    capabilities = registry.get_all_capabilities()
    
    print(f"\\n🎯 Total Capabilities Loaded: {len(capabilities)}")
    if capabilities:
        print("Capabilities:")
        for cap in capabilities:
            print(f"  - {cap}")
    
    print()
    return manager


def demo_worker_with_integrations():
    """Demonstrate creating a worker with loaded integrations"""
    print("🤖 Worker with Integrations Demo")
    print("=" * 50)
    
    # Load integrations
    manager = EnhancedIntegrationManager()
    integrations_to_load = ["browser:google_search,youtube_search"]
    results = manager.load_integrations_from_list(integrations_to_load)
    
    # Create worker (don't actually start it)
    worker = IntegratedWorkerNode(
        server_endpoint="http://localhost:8080",
        worker_port=6000,
        worker_name="Demo-Worker",
        location="Demo Environment",
        description="Demo worker with pluggable integrations"
    )
    
    # Set the integration registry
    worker.registry = manager.get_registry()
    worker.capabilities = worker.registry.get_all_capabilities()
    
    print(f"👷 Created worker: {worker.worker_name}")
    print(f"📍 Location: {worker.location}")
    print(f"🔧 Worker ID: {worker.worker_id}")
    print(f"🌐 Server endpoint: {worker.server_endpoint}")
    print(f"🔌 Worker port: {worker.worker_port}")
    print(f"🎯 Capabilities: {len(worker.capabilities)}")
    
    if worker.capabilities:
        print("\\nAvailable capabilities:")
        for cap in worker.capabilities:
            integration = worker.registry.get_integration_for_capability(cap)
            integration_name = integration.name if integration else "unknown"
            print(f"  - {cap} (from {integration_name} integration)")
    
    print("\\n💡 This worker can now handle tasks for the loaded capabilities!")
    print()


def demo_task_execution():
    """Demonstrate task execution through integrations"""
    print("🎮 Task Execution Demo")
    print("=" * 50)
    
    # Load browser integration
    manager = EnhancedIntegrationManager()
    results = manager.load_integrations_from_list(["browser:google_search"])
    
    if not results.get("browser", False):
        print("❌ Failed to load browser integration for demo")
        return
    
    # Get the registry and simulate task execution
    registry = manager.get_registry()
    
    # Test capability lookup
    capability = "browsergoogle"
    integration = registry.get_integration_for_capability(capability)
    
    if integration:
        print(f"✅ Found integration for '{capability}': {integration.name}")
        
        # Get handler
        handlers = integration.get_handlers()
        handler = handlers.get(capability)
        
        if handler:
            print(f"✅ Found handler for '{capability}'")
            
            # Simulate task execution (don't actually open browser in demo)
            print(f"🎯 Simulating task execution: 'browsergoogle Python programming'")
            print(f"📋 Handler would process this task and open Google search")
            print(f"🔗 Would open: https://www.google.com/search?q=Python+programming")
        else:
            print(f"❌ No handler found for '{capability}'")
    else:
        print(f"❌ No integration found for '{capability}'")
    
    print()


def create_demo_scripts():
    """Create example scripts for different use cases"""
    print("📝 Creating Demo Scripts")
    print("=" * 50)
    
    # Home automation worker script
    home_worker_script = """#!/usr/bin/env python3
# Home Automation Worker - Browser and Computer control
import sys
import os
sys.path.append(os.path.dirname(__file__))
from enhanced_worker_launcher import main
import sys

# Override sys.argv for this demo
sys.argv = [
    'enhanced_worker_launcher.py',
    '--integrations', 'browser:google_search,youtube_search', 'computer:volume_control,media_control',
    '--worker-name', 'Home-Automation-Worker',
    '--location', 'Living Room',
    '--server', 'http://192.168.1.100:8080'
]

if __name__ == "__main__":
    main()
"""
    
    with open("demo_home_worker.py", "w") as f:
        f.write(home_worker_script)
    
    # Office worker script
    office_worker_script = """#!/usr/bin/env python3
# Office Worker - Browser, Computer, and AI capabilities
import sys
import os
sys.path.append(os.path.dirname(__file__))
from enhanced_worker_launcher import main
import sys

# Override sys.argv for this demo
sys.argv = [
    'enhanced_worker_launcher.py',
    '--integrations', 'browser', 'computer', 'ai:openinterpreter',
    '--worker-name', 'Office-Assistant',
    '--location', 'Home Office',
    '--server', 'http://localhost:8080'
]

if __name__ == "__main__":
    main()
"""
    
    with open("demo_office_worker.py", "w") as f:
        f.write(office_worker_script)
    
    # Minimal worker script
    minimal_worker_script = """#!/usr/bin/env python3
# Minimal Worker - Just browser capabilities
import sys
import os
sys.path.append(os.path.dirname(__file__))
from enhanced_worker_launcher import main
import sys

# Override sys.argv for this demo
sys.argv = [
    'enhanced_worker_launcher.py',
    '--integrations', 'browser:google_search',
    '--worker-name', 'Minimal-Worker',
    '--dry-run'  # Don't actually start, just show what would be loaded
]

if __name__ == "__main__":
    main()
"""
    
    with open("demo_minimal_worker.py", "w") as f:
        f.write(minimal_worker_script)
    
    print("Created demo scripts:")
    print("  📱 demo_home_worker.py - Home automation worker")
    print("  💼 demo_office_worker.py - Office assistant worker")
    print("  🎯 demo_minimal_worker.py - Minimal worker (dry-run)")
    print()


def main():
    """Run the complete demo"""
    print("🚀 LAMControl Pluggable Integrations System Demo")
    print("=" * 60)
    print()
    
    setup_demo_logging()
    
    try:
        # Run all demo sections
        discovered = demo_integration_discovery()
        config_file = demo_feature_configuration()
        manager = demo_integration_loading()
        demo_worker_with_integrations()
        demo_task_execution()
        create_demo_scripts()
        
        # Summary
        print("✨ Demo Complete!")
        print("=" * 50)
        print("Key features demonstrated:")
        print("  🔍 Auto-discovery of integrations")
        print("  ⚙️  Feature-based configuration")
        print("  🔄 Dynamic integration loading")
        print("  🤖 Worker creation with integrations")
        print("  🎮 Task execution through integrations")
        print("  📝 Example scripts for different use cases")
        print()
        print("Next steps:")
        print("  1. Run 'python3 demo_minimal_worker.py' to see a minimal worker")
        print("  2. Edit demo_worker_config.json to customize integrations")
        print("  3. Use './install_worker_enhanced.sh' to install on other systems")
        print("  4. Check INTEGRATION_SYSTEM_GUIDE.md for detailed documentation")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the LAMControl directory")
    except Exception as e:
        print(f"❌ Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
