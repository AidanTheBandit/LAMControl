# LAMControl Web Mode Setup Guide

## Overview

LAMControl now supports a **Web Mode** that hosts a simple web server with authentication instead of connecting to hole.rabbit.tech. This allows the Rabbit R1 to send prompts directly to LAMControl via HTTP requests.

## Features

- **Simple Authentication**: Admin dashboard with username/password login
- **Direct R1 Integration**: R1 can send prompts via HTTP API calls
- **Real-time Dashboard**: Web interface to monitor received prompts
- **Test Interface**: Send test prompts through the web dashboard
- **No External Dependencies**: No need for Rabbit Hole tokens

## Quick Setup

### 1. Configure Web Mode

Edit `config.json` and set the mode to "web":

```json
{
    "mode": "web",
    "web_server_host": "0.0.0.0",
    "web_server_port": 5000,
    ...
}
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run LAMControl

```bash
python main.py
```

On first run:
- Only GROQ API Key is required (other credentials are optional)
- Admin credentials will be automatically generated and displayed in the console
- Save these credentials securely!

### 4. Access the Dashboard

Open your browser and go to:
- Local: `http://localhost:5000`
- Network: `http://YOUR_IP:5000`

Login with the generated admin credentials.

## R1 Integration

### Using the R1 Client Script

Use the provided `r1_client.py` script to send prompts from your R1:

```bash
# Basic usage
python r1_client.py "Turn on my desk lamp"

# With custom server
python r1_client.py --host http://192.168.1.100:5000 --prompt "Search Google for rabbit care"

# Test connection
python r1_client.py --test-connection --host http://192.168.1.100:5000
```

### Direct HTTP API

Send POST requests to `/api/prompt`:

```bash
curl -X POST http://localhost:5000/api/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Turn on my desk lamp", "source": "r1"}'
```

### R1 Integration Example

Create a simple script on your R1 device or any device that can make HTTP requests:

```python
import requests

def send_to_lamcontrol(prompt, server_ip="192.168.1.100", port=5000):
    url = f"http://{server_ip}:{port}/api/prompt"
    data = {"prompt": prompt, "source": "r1"}
    
    try:
        response = requests.post(url, json=data, timeout=5)
        if response.status_code == 200:
            print("✓ Prompt sent successfully")
        else:
            print(f"✗ Error: {response.status_code}")
    except Exception as e:
        print(f"✗ Failed to send: {e}")

# Usage
send_to_lamcontrol("Turn on my desk lamp")
```

## Configuration Options

### Web Server Settings

In `config.json`:

```json
{
    "mode": "web",
    "web_server_host": "0.0.0.0",     // "0.0.0.0" for all interfaces, "127.0.0.1" for local only
    "web_server_port": 5000,          // Port number for the web server
    "debug": false                    // Enable debug mode for development
}
```

### Security Notes

- **Admin Credentials**: Automatically generated on first run
- **Session Security**: Uses secure Flask sessions
- **Network Access**: Configure `web_server_host` appropriately:
  - `127.0.0.1` or `localhost`: Local access only
  - `0.0.0.0`: Access from any device on your network
  - Specific IP: Access from that IP address only

## API Reference

### POST /api/prompt

Send a prompt to LAMControl.

**Request:**
```json
{
    "prompt": "Turn on my desk lamp",
    "source": "r1"  // Optional, defaults to "r1"
}
```

**Response (Success):**
```json
{
    "status": "success",
    "message": "Prompt received",
    "id": "abc123def456"
}
```

**Response (Error):**
```json
{
    "error": "No prompt provided"
}
```

### GET /api/prompts

Get all received prompts (requires authentication).

**Response:**
```json
[
    {
        "id": "abc123def456",
        "prompt": "Turn on my desk lamp",
        "timestamp": "2025-01-20T10:30:00Z",
        "source": "r1",
        "processed": false
    }
]
```

## Dashboard Features

### Admin Dashboard

- **Real-time Prompt Monitoring**: See prompts as they arrive
- **Processing Status**: Track which prompts have been processed
- **Test Interface**: Send test prompts directly from the web interface
- **Auto-refresh**: Dashboard updates every 5 seconds

### Test Prompts

Use the dashboard to send test prompts:
1. Log into the admin dashboard
2. Use the "Test Prompt" section
3. Enter a prompt and click "Send Test Prompt"

## Troubleshooting

### Connection Issues

1. **Check if server is running:**
   ```bash
   python r1_client.py --test-connection
   ```

2. **Verify network connectivity:**
   ```bash
   curl http://YOUR_IP:5000/
   ```

3. **Check firewall settings:**
   - Ensure port 5000 (or your configured port) is open
   - Check both host and R1 device firewalls

### Common Errors

| Error | Solution |
|-------|----------|
| "Connection failed" | Check server IP and port, ensure LAMControl is running |
| "Invalid credentials" | Use the admin credentials generated on first run |
| "No prompt provided" | Ensure the prompt field is not empty |
| "Server returned status 500" | Check LAMControl logs for detailed error information |

### Debug Mode

Enable debug mode in `config.json`:
```json
{
    "debug": true
}
```

This provides:
- Detailed logging
- Flask debug mode
- Verbose error messages

## Migration from Rabbit Mode

If migrating from rabbit mode to web mode:

1. **Backup your configuration:**
   ```bash
   cp config.json config.json.backup
   ```

2. **Update mode in config.json:**
   ```json
   {
       "mode": "web"
   }
   ```

3. **Keep existing integrations:**
   All existing integrations (Discord, Telegram, etc.) continue to work

4. **Update R1 prompting method:**
   Replace Rabbit Hole journal entries with HTTP API calls

## Advanced Usage

### Custom Client Implementation

Implement your own client for any device:

```python
import requests

class LAMControlClient:
    def __init__(self, host="http://localhost:5000"):
        self.host = host
    
    def send_prompt(self, prompt, source="custom"):
        response = requests.post(
            f"{self.host}/api/prompt",
            json={"prompt": prompt, "source": source}
        )
        return response.json()

# Usage
client = LAMControlClient("http://192.168.1.100:5000")
result = client.send_prompt("Turn on my lights")
```

### Integration with Other Systems

The HTTP API makes it easy to integrate with:
- Smart home systems
- Voice assistants
- Mobile apps
- IoT devices
- Home automation platforms

### Multiple R1 Devices

Support multiple R1 devices by using different `source` identifiers:

```python
# R1 Device 1
send_prompt("Turn on lights", source="r1_living_room")

# R1 Device 2  
send_prompt("Play music", source="r1_bedroom")
```

## Security Considerations

1. **Network Security**: Run on a secure local network
2. **Admin Credentials**: Store admin credentials securely
3. **HTTPS**: For production use, consider adding HTTPS support
4. **Rate Limiting**: Monitor for unusual prompt activity
5. **Access Control**: Use firewall rules to restrict access

## Support

For issues, questions, or feature requests:
1. Check the troubleshooting section above
2. Review LAMControl logs for detailed error information
3. Open an issue on the project repository
