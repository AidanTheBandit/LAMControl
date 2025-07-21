# LAMControl Enhanced Web Mode Setup Guide

## Overview

LAMControl now features a **completely revamped Web Mode** that provides a modern, real-time dashboard with authentication, replacing the need for hole.rabbit.tech entirely. This allows your Rabbit R1 to communicate directly with LAMControl through a secure HTTP API.

## 🆕 New Features in v2.0

### Enhanced Web Dashboard
- **Real-time Updates**: Live prompt monitoring using WebSockets
- **Modern UI**: Beautiful, responsive dashboard with dark theme
- **System Statistics**: Live uptime, success rates, and performance metrics
- **Prompt History**: View both pending and processed prompts with detailed status
- **Interactive Charts**: Visual representation of prompt statistics
- **Test Interface**: Send test prompts directly from the dashboard

### Advanced R1 Client
- **Status Checking**: Check prompt completion status by ID
- **Wait for Completion**: Send prompts and wait for results
- **Health Monitoring**: Verify server health and connectivity
- **Enhanced Error Handling**: Better error messages and retry logic
- **Metadata Support**: Include additional data with prompts

### Improved API
- **RESTful Design**: Clean API endpoints for all operations
- **Response Tracking**: Monitor prompt processing with detailed responses
- **Error Reporting**: Comprehensive error tracking and reporting
- **Health Checks**: Built-in health monitoring endpoints

## Quick Setup

### 1. Install Enhanced Dependencies

```bash
pip install flask-socketio
```

### 2. Configure Web Mode

Your `config.json` should already be set to web mode:

```json
{
    "mode": "web",
    "web_server_host": "0.0.0.0",
    "web_server_port": 5000,
    "groq_model": "llama-3.3-70b-versatile"
}
```

### 3. Run LAMControl

```bash
python main.py
```

On first run, you'll see admin credentials displayed in the console. **Save these securely!**

### 4. Access the Enhanced Dashboard

Open your browser and navigate to:
- **Local**: `http://localhost:5000`
- **Network**: `http://YOUR_IP:5000`

## Using the Enhanced R1 Client

### Basic Usage

```bash
# Send a simple prompt
python r1_client.py "Turn on the lights"

# Send prompt with source identifier
python r1_client.py --source "my-r1" "Play music on Spotify"

# Send to remote server
python r1_client.py --host http://192.168.1.100:5000 "Set volume to 50"
```

### Advanced Features

```bash
# Send prompt and wait for completion
python r1_client.py --wait "Send a text to John saying I'm running late"

# Check server health
python r1_client.py --health-check

# Check prompt status
python r1_client.py --check-status abc123def456

# Send with metadata
python r1_client.py --metadata '{"priority": "high", "room": "living_room"}' "Turn off all lights"

# Verbose output with JSON response
python r1_client.py --verbose --json-output "What's the weather?"
```

## Dashboard Features

### System Statistics Panel
- **Uptime**: How long LAMControl has been running
- **Total Prompts**: Total number of prompts received
- **Pending Queue**: Current prompts waiting for processing
- **Success Rate**: Percentage of successfully processed prompts

### Prompt Management
- **Pending Tab**: View prompts currently in the queue
- **Recent History**: See the last 20 processed prompts with results
- **Real-time Updates**: Automatic updates without page refresh

### Test Interface
- Send test prompts directly from the web interface
- Visual feedback for successful/failed submissions
- Interactive prompt statistics chart

## API Endpoints

### For R1 Integration

- **POST** `/api/prompt` - Send a new prompt
- **GET** `/api/prompt/{id}/status` - Check prompt status
- **GET** `/api/health` - Health check

### For Dashboard (Authenticated)

- **GET** `/api/prompts` - Get all prompts and statistics
- **POST** `/api/test` - Send test prompt
- **GET** `/api/stats` - Get system statistics

## Setting Up R1 Integration

### Option 1: Direct Integration
Configure your R1 to make HTTP POST requests to `/api/prompt` with JSON payload:

```json
{
    "prompt": "Your command here",
    "source": "r1",
    "metadata": {
        "optional": "data"
    }
}
```

### Option 2: Using the R1 Client Script
Copy `r1_client.py` to your R1 and use it to send commands:

```bash
python r1_client.py "Your command here"
```

### Option 3: Custom Integration
Use the LAMControlClient class in your own scripts:

```python
from r1_client import LAMControlClient

client = LAMControlClient("http://your-server:5000")
result = client.send_prompt("Turn on the lights")
print(result)
```

## Security Features

- **Session-based Authentication**: Secure admin access
- **Password Hashing**: SHA-256 hashed passwords
- **Session Management**: Automatic session expiration
- **Network Isolation**: Configurable host binding

## Troubleshooting

### Common Issues

1. **"Connection failed"**
   - Ensure LAMControl is running
   - Check firewall settings
   - Verify host/port configuration

2. **"Real-time updates not working"**
   - Install flask-socketio: `pip install flask-socketio`
   - Check browser console for errors

3. **"Authentication failed"**
   - Check admin credentials in console output
   - Clear browser cookies and try again

### Health Check
```bash
python r1_client.py --health-check
```

This will verify:
- Server connectivity
- API availability
- System status

## Performance Tips

- **Local Network**: Host on local network for fastest response
- **Resource Monitoring**: Use dashboard statistics to monitor performance
- **Prompt Batching**: Group related commands when possible

## Migration from hole.rabbit.tech

This enhanced web mode completely replaces the need for:
- ❌ Rabbit Hole tokens
- ❌ External API dependencies
- ❌ Manual journal reading
- ❌ Browser automation for login

✅ **Direct R1 → LAMControl communication**
✅ **No external dependencies**
✅ **Real-time monitoring**
✅ **Enhanced security**

## What's Different from Original Web Mode

### Original Web Mode
- Basic authentication
- Simple prompt queue
- Manual refresh required
- Limited error handling

### Enhanced Web Mode v2.0
- Real-time WebSocket updates
- Advanced dashboard with statistics
- Comprehensive error tracking
- Modern UI with responsive design
- Detailed prompt history
- Health monitoring
- Enhanced R1 client with status checking

## Technical Architecture

```
R1 Device → HTTP POST → LAMControl Web Server → Task Processor → Browser/Integrations
                                ↓
                        Real-time Dashboard ← WebSocket Updates
```

The enhanced system provides a complete replacement for hole.rabbit.tech with superior features, security, and monitoring capabilities.
