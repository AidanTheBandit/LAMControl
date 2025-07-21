#!/usr/bin/env python3
"""
LAMControl Worker Registration Demo

This script demonstrates how to register workers with the distributed server.
"""

import requests
import json
import sys

# Server configuration
SERVER_URL = "http://localhost:8080"

def register_demo_workers():
    """Register some demo workers to show the system working"""
    
    print("🚀 LAMControl Distributed System Demo")
    print("=" * 50)
    
    # Demo workers to register
    demo_workers = [
        {
            "worker_name": "living_room_pc",
            "worker_type": "browser",
            "endpoint": "http://192.168.1.100:6001",
            "location": "Living Room",
            "description": "Main computer for web browsing and media",
            "capabilities": ["browsersite", "browsergoogle", "browseryoutube", "browsergmail", "browseramazon"]
        },
        {
            "worker_name": "home_office_computer",
            "worker_type": "computer",
            "endpoint": "http://192.168.1.101:6002", 
            "location": "Home Office",
            "description": "Work computer for system control",
            "capabilities": ["computervolume", "computerrun", "computermedia", "computerpower"]
        },
        {
            "worker_name": "raspberry_pi_messenger",
            "worker_type": "messaging",
            "endpoint": "http://192.168.1.102:6003",
            "location": "Home Network",
            "description": "Raspberry Pi for messaging services",
            "capabilities": ["discordtext", "facebooktext", "telegram"]
        },
        {
            "worker_name": "ai_server",
            "worker_type": "ai",
            "endpoint": "http://192.168.1.103:6004",
            "location": "Server Rack",
            "description": "High-performance AI processing server",
            "capabilities": ["openinterpreter", "ai_automation"]
        }
    ]
    
    print(f"Registering {len(demo_workers)} demo workers with server: {SERVER_URL}")
    print()
    
    registered_workers = []
    
    for worker in demo_workers:
        print(f"📡 Registering: {worker['worker_name']} ({worker['worker_type']})")
        
        try:
            response = requests.post(
                f"{SERVER_URL}/api/worker/register",
                json=worker,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    print(f"   ✅ Success! Worker ID: {result['worker_id']}")
                    print(f"   🔑 API Key: {result['api_key']}")
                    registered_workers.append({
                        **worker,
                        'worker_id': result['worker_id'],
                        'api_key': result['api_key']
                    })
                else:
                    print(f"   ❌ Registration failed: {result.get('error', 'Unknown error')}")
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Cannot connect to server at {SERVER_URL}")
            print("   Make sure the LAMControl distributed server is running!")
            return
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        print()
    
    print("=" * 50)
    print(f"✅ Registration complete! {len(registered_workers)} workers registered")
    
    if registered_workers:
        print("\n📋 Worker Summary:")
        for worker in registered_workers:
            print(f"  • {worker['worker_name']} ({worker['worker_type']}) - {worker['location']}")
        
        print(f"\n🌐 View workers in admin dashboard: {SERVER_URL}")
        print(f"🤖 R1 interface: {SERVER_URL}/r1/login")
        print()
        print("R1 Login Credentials:")
        print("  Username: admin")
        print("  Password: k0Hua97Nq1DchNLsYTJ31Q")
        print()
        print("Example R1 commands to test:")
        print("  • 'Play Weezer on YouTube'")
        print("  • 'Set volume to 50'")
        print("  • 'Send a text to John saying I'm running late'")
        print("  • 'Open Google and search for pizza near me'")


def show_system_info():
    """Show information about the LAMControl distributed system"""
    
    print("📊 LAMControl Distributed System Information")
    print("=" * 50)
    
    try:
        # Check server health
        response = requests.get(f"{SERVER_URL}/api/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Server Status: {health['status']}")
            print(f"⏱️  Uptime: {health.get('uptime', 0):.1f} seconds")
            print(f"👥 Connected Workers: {health.get('workers', 0)}")
        else:
            print("❌ Server health check failed")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to server at {SERVER_URL}")
        print("Make sure the LAMControl distributed server is running!")
        return
    
    print()
    print("🏗️ Architecture Overview:")
    print("  1. Central Server: Receives R1 prompts, processes with LLM")
    print("  2. Worker Nodes: Execute tasks on different devices")
    print("  3. R1 Interface: Web-based command interface for Rabbit R1")
    print()
    print("🔧 Worker Types:")
    print("  • browser: Web automation (YouTube, Google, etc.)")
    print("  • computer: System control (volume, media, power)")
    print("  • messaging: Communication (Discord, Telegram, Facebook)")
    print("  • ai: AI processing (OpenInterpreter, automation)")
    print()
    print("📱 R1 Workflow:")
    print("  1. R1 navigates to login page and logs in (one time)")
    print("  2. R1 enters command in web interface")
    print("  3. Server processes command with LLM")
    print("  4. Server routes task to appropriate worker")
    print("  5. Worker executes task and returns result")
    print("  6. R1 sees real-time status and output")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "info":
        show_system_info()
    else:
        register_demo_workers()
