# LAMControl Worker Installation Guide

This guide explains how to install and configure LAMControl worker nodes on remote computers.

## Overview

LAMControl uses a distributed architecture where:
- **Central Server**: Receives R1 prompts and coordinates tasks
- **Worker Nodes**: Execute specific tasks on remote computers

## Worker Types

1. **Browser Worker**: Web automation, form filling, scraping
2. **Computer Worker**: Local file operations, system commands
3. **Messaging Worker**: Discord, Telegram, social media integration  
4. **AI Worker**: LLM processing, AI model inference

## Quick Installation

### Linux/macOS

```bash
# Download and run the installation script
curl -sSL https://raw.githubusercontent.com/your-repo/LAMControl/main/install_worker_linux.sh | bash
```

### Windows

```batch
# Download and run the installation script
powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/your-repo/LAMControl/main/install_worker_windows.bat' -OutFile 'install_worker.bat'; .\install_worker.bat"
```

## Manual Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Network access to the LAMControl server

### Step 1: Download Installation Scripts

Download the appropriate script for your operating system:
- Linux: `install_worker_linux.sh`
- Windows: `install_worker_windows.bat`

### Step 2: Run Installation

#### Linux/macOS
```bash
chmod +x install_worker_linux.sh
./install_worker_linux.sh
```

#### Windows
```batch
install_worker_windows.bat
```

### Step 3: Configure Worker

The installation script will prompt for:
1. **Worker Type**: Choose from browser, computer, messaging, or ai
2. **Server Details**: IP/hostname and port of LAMControl server
3. **Worker Identity**: Name, location, and description (optional)
4. **Installation Directory**: Where to install the worker

## Configuration Options

### Worker Types and Capabilities

#### Browser Worker
- **Capabilities**: web_navigation, form_filling, web_scraping, browser_automation
- **Dependencies**: Playwright (automatically installed)
- **Use Cases**: Website automation, data extraction, form submission

#### Computer Worker  
- **Capabilities**: file_operations, system_commands, local_automation
- **Dependencies**: None (uses built-in Python modules)
- **Use Cases**: File management, system administration, local scripting

#### Messaging Worker
- **Capabilities**: discord_messaging, telegram_messaging, social_media
- **Dependencies**: discord.py, python-telegram-bot
- **Use Cases**: Social media posting, chat bot responses, notifications

#### AI Worker
- **Capabilities**: llm_processing, ai_analysis, model_inference  
- **Dependencies**: Varies by AI framework
- **Use Cases**: Local AI processing, model inference, data analysis

## Starting Workers

### Manual Start
```bash
cd ~/lamcontrol-worker
python3 launch_worker.py
```

### As System Service

#### Linux (systemd)
```bash
# Start service
systemctl --user start lamcontrol-worker.service

# Enable auto-start on boot
systemctl --user enable lamcontrol-worker.service

# Check status
systemctl --user status lamcontrol-worker.service

# View logs
journalctl --user -u lamcontrol-worker.service -f
```

#### Windows (requires NSSM)
```batch
# Download NSSM from https://nssm.cc/
# Install as service
nssm install LAMControlWorker "python" "C:\Users\YourUser\lamcontrol-worker\launch_worker.py"
nssm set LAMControlWorker AppDirectory "C:\Users\YourUser\lamcontrol-worker"
nssm start LAMControlWorker
```

## Configuration Management

### Worker Setup Utility

Use the `setup_workers.py` utility to generate installation commands:

```bash
# Generate installation command for a browser worker
python3 setup_workers.py --generate-commands --worker-type browser --server-host 192.168.1.100 --worker-name "Office-Browser"

# Create configuration file for multiple workers
python3 setup_workers.py --create-config --config-file my_workers.json
```

### Configuration File Format

Create a `workers_config.json` file to define multiple workers:

```json
{
  "server": {
    "host": "192.168.1.100", 
    "port": 8080
  },
  "workers": [
    {
      "type": "browser",
      "name": "office-browser", 
      "location": "Office Desktop",
      "description": "Browser automation for office tasks"
    },
    {
      "type": "computer",
      "name": "home-computer",
      "location": "Home PC", 
      "description": "File operations and system commands"
    }
  ]
}
```

## Monitoring and Management

### Worker Status

Workers automatically send heartbeats to the server every 30 seconds. Check worker status in the LAMControl web interface at `http://server:8080/admin`.

### Logs

#### Linux
```bash
# Service logs
journalctl --user -u lamcontrol-worker.service -f

# Manual run logs
tail -f ~/lamcontrol-worker/worker.log
```

#### Windows  
```batch
# Service logs (if using NSSM)
nssm rotate LAMControlWorker

# Manual run logs
type %USERPROFILE%\lamcontrol-worker\worker.log
```

### Troubleshooting

#### Worker Not Registering
1. Check network connectivity to server
2. Verify server hostname/IP and port
3. Check firewall settings
4. Review worker logs for error messages

#### Dependencies Issues
1. Ensure Python 3.8+ is installed
2. Check pip installation and permissions
3. For browser workers, verify Playwright installation:
   ```bash
   python3 -m playwright install
   ```

#### Service Not Starting
1. Check systemd user service permissions (Linux)
2. Verify NSSM installation and service configuration (Windows)
3. Ensure working directory and Python paths are correct

## Security Considerations

### API Keys
- Workers receive unique API keys during registration
- Keys are used for authentication with the central server
- Store keys securely and rotate them regularly

### Network Security
- Use HTTPS for production deployments
- Consider VPN or secure tunnels for remote workers
- Implement firewall rules to restrict access

### Permissions
- Run workers with minimal required permissions
- Avoid running as administrator/root unless necessary
- Use dedicated user accounts for worker services

## Advanced Configuration

### Custom Capabilities
Add custom capabilities to workers by extending the base classes:

```python
class CustomBrowserWorker(BrowserWorker):
    def __init__(self, server_url, worker_name=None):
        super().__init__(server_url, worker_name)
        self.capabilities.extend(['custom_automation', 'special_scraping'])
```

### Environment Variables
Set environment variables for worker configuration:

```bash
export LAM_SERVER_URL="http://server:8080"
export LAM_WORKER_TYPE="browser"
export LAM_WORKER_NAME="my-worker"
```

### Load Balancing
Deploy multiple workers of the same type for load balancing:
- Use different worker names but same type
- Server automatically distributes tasks among available workers
- Workers can be on same or different machines

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review worker and server logs
3. Verify network connectivity and configuration
4. Check the main LAMControl documentation

## Example Deployments

### Small Office Setup
- 1 Central server (always-on computer)
- 2 Browser workers (office desktops)
- 1 Computer worker (file server)

### Home Automation
- 1 Central server (Raspberry Pi)
- 1 Browser worker (home computer)
- 1 Messaging worker (notification hub)

### Development Environment  
- 1 Central server (localhost)
- Multiple workers on same machine for testing
- Different worker types for comprehensive testing
