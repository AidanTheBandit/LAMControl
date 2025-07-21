#!/usr/bin/env python3
"""
LAMControl Worker Setup Utility

This script helps generate worker installation commands and manage worker deployments
with the new integration-based architecture.
"""

import os
import json
import argparse
from pathlib import Path


def generate_install_command(integrations, server_host, server_port=8080, worker_name="", location="", description=""):
    """Generate installation command for a worker with specific integrations"""
    
    integrations_str = ",".join(integrations) if isinstance(integrations, list) else integrations    
    linux_cmd = f"""curl -sSL https://raw.githubusercontent.com/AidanTheBandit/LAMControl/main/install_worker_enhanced.sh | bash -s -- \\
    --integrations {integrations_str} \\
    --server-host {server_host} \\
    --server-port {server_port}"""
    
    if worker_name:
        linux_cmd += f" \\\n    --worker-name '{worker_name}'"
    if location:
        linux_cmd += f" \\\n    --location '{location}'"
    if description:
        linux_cmd += f" \\\n    --description '{description}'"
    
    windows_cmd = f"""powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/AidanTheBandit/LAMControl/main/install_worker_enhanced.sh' -OutFile 'install_worker.bat'; bash install_worker.bat --integrations {integrations_str} --server-host {server_host} --server-port {server_port}"
    if worker_name:
        windows_cmd += f" --worker-name '{worker_name}'"
    if location:
        windows_cmd += f" --location '{location}'"
    if description:
        windows_cmd += f" --description '{description}'"
    windows_cmd += '"'"""
    
    return linux_cmd, windows_cmd


def create_worker_config(workers_config):
    """Create a configuration file for multiple workers with integrations"""
    
    config = {
        "server": {
            "host": workers_config.get("server_host", "localhost"),
            "port": workers_config.get("server_port", 8080)
        },
        "workers": []
    }
    
    for worker in workers_config.get("workers", []):
        worker_config = {
            "name": worker.get("name", ""),
            "location": worker.get("location", ""),
            "description": worker.get("description", ""),
            "integrations": worker.get("integrations", {})
        }
        config["workers"].append(worker_config)
    
    return config


def create_integration_config(integration_name, settings=None):
    """Create configuration for a specific integration"""
    if settings is None:
        settings = {}
    
    # Default configurations for each integration
    default_configs = {
        "browser": {
            "enabled": True,
            "settings": {
                "site_enabled": True,
                "google_enabled": True,
                "youtube_enabled": True,
                "gmail_enabled": True,
                "amazon_enabled": True
            },
            "dependencies": []
        },
        "computer": {
            "enabled": True,
            "settings": {
                "volume_enabled": True,
                "run_enabled": True,
                "media_enabled": True,
                "power_enabled": True,
                "vol_up_step_value": 5,
                "vol_down_step_value": 5
            },
            "dependencies": []
        },
        "messaging": {
            "enabled": True,
            "settings": {
                "discord_enabled": True,
                "telegram_enabled": True,
                "facebook_enabled": True
            },
            "dependencies": ["playwright", "python-telegram-bot"]
        },
        "ai": {
            "enabled": True,
            "settings": {
                "openinterpreter_enabled": True,
                "ai_automation_enabled": True,
                "openinterpreter_llm_api_base": "groq",
                "openinterpreter_verbose_mode_isenabled": "true",
                "openinterpreter_auto_run_isenabled": False,
                "openinterpreter_llm_api_key": "${GROQ_API_KEY}",
                "openinterpreter_llm_model": "llama-3.3-70b-versatile",
                "openinterpreter_llm_temperature": 0.7
            },
            "dependencies": ["open-interpreter"]
        }
    }
    
    config = default_configs.get(integration_name, {"enabled": True, "settings": {}, "dependencies": []})
    config["settings"].update(settings)
    
    return config


def get_available_integrations():
    """Get list of available integrations"""
    return ["browser", "computer", "messaging", "ai"]


def main():
    parser = argparse.ArgumentParser(description="LAMControl Worker Setup Utility (Integration-based)")
    parser.add_argument("--generate-commands", action="store_true", help="Generate installation commands")
    parser.add_argument("--create-config", action="store_true", help="Create worker configuration file")
    parser.add_argument("--integrations", nargs='+', choices=get_available_integrations(), 
                       help="List of integrations to include")
    parser.add_argument("--server-host", default="localhost", help="Server hostname/IP")
    parser.add_argument("--server-port", type=int, default=8080, help="Server port")
    parser.add_argument("--worker-name", default="", help="Worker name")
    parser.add_argument("--location", default="", help="Worker location")
    parser.add_argument("--description", default="", help="Worker description")
    parser.add_argument("--config-file", default="worker_config.json", help="Configuration file path")
    
    args = parser.parse_args()
    
    if args.generate_commands:
        if not args.integrations:
            print("Error: --integrations is required when generating commands")
            print(f"Available integrations: {', '.join(get_available_integrations())}")
            return
        
        linux_cmd, windows_cmd = generate_install_command(
            args.integrations, args.server_host, args.server_port,
            args.worker_name, args.location, args.description
        )
        
        print("Linux Installation Command:")
        print("=" * 50)
        print(linux_cmd)
        print("\n")
        
        print("Windows Installation Command:")
        print("=" * 50)
        print(windows_cmd)
        print("\n")
    
    elif args.create_config:
        # Interactive configuration creation
        print("Creating worker configuration with integrations...")
        
        config = {
            "worker": {
                "name": input(f"Worker name [{args.worker_name}]: ").strip() or args.worker_name,
                "location": input(f"Worker location [{args.location}]: ").strip() or args.location,
                "description": input(f"Worker description [{args.description}]: ").strip() or args.description
            },
            "integrations": {}
        }
        
        print(f"\nAvailable integrations: {', '.join(get_available_integrations())}")
        print("Select integrations to enable (press Enter with empty input to finish):")
        
        while True:
            integration = input("Integration name: ").strip().lower()
            if not integration:
                break
            
            if integration not in get_available_integrations():
                print(f"Invalid integration: {integration}")
                continue
            
            print(f"\nConfiguring {integration} integration:")
            enable = input(f"Enable {integration}? [Y/n]: ").strip().lower()
            
            if enable in ['n', 'no']:
                config["integrations"][integration] = {"enabled": False}
                continue
            
            # Get integration-specific settings
            integration_config = create_integration_config(integration)
            
            print(f"Configure {integration} settings? [y/N]: ", end="")
            configure_settings = input().strip().lower() == 'y'
            
            if configure_settings:
                settings = {}
                print(f"Available settings for {integration}:")
                for key, value in integration_config["settings"].items():
                    new_value = input(f"  {key} [{value}]: ").strip()
                    if new_value:
                        # Try to preserve type
                        if isinstance(value, bool):
                            settings[key] = new_value.lower() in ['true', 'yes', '1', 'on']
                        elif isinstance(value, int):
                            try:
                                settings[key] = int(new_value)
                            except ValueError:
                                settings[key] = new_value
                        elif isinstance(value, float):
                            try:
                                settings[key] = float(new_value)
                            except ValueError:
                                settings[key] = new_value
                        else:
                            settings[key] = new_value
                
                integration_config["settings"].update(settings)
            
            config["integrations"][integration] = integration_config
        
        # Save configuration
        with open(args.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\nConfiguration saved to {args.config_file}")
        
        # Generate commands for the worker
        print("\nGenerated installation command:")
        print("=" * 50)
        
        integrations = list(config["integrations"].keys())
        if integrations:
            linux_cmd, windows_cmd = generate_install_command(
                integrations, args.server_host, args.server_port,
                config["worker"]["name"], config["worker"]["location"], 
                config["worker"]["description"]
            )
            print(f"Linux: {linux_cmd}")
            print(f"Windows: {windows_cmd}")
        else:
            print("No integrations selected - worker would have no capabilities")
    
    else:
        print("LAMControl Worker Setup Utility (Integration-based)")
        print("=" * 50)
        print("Usage:")
        print("  --generate-commands   Generate installation commands for a worker")
        print("  --create-config      Create a worker configuration file interactively")
        print()
        print("Examples:")
        print("  # Generate commands for a worker with browser and computer integrations")
        print(f"  python {__file__} --generate-commands --integrations browser computer --server-host 192.168.1.100")
        print()
        print("  # Create a configuration file interactively")
        print(f"  python {__file__} --create-config --config-file my_worker.json")
        print()
        print(f"Available integrations: {', '.join(get_available_integrations())}")


if __name__ == "__main__":
    main()
