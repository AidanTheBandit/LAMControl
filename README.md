# LAMControl

<p align="center">
  <img src="assets/LAMAtHome.png" alt="LAMControl" width="400"/>
</p>

<div align="center">
  <a href="https://discord.gg/6aU9fjyk2g" style="text-decoration: none;">
    <img src="https://dcbadge.limes.pink/api/server/6aU9fjyk2g?style=flat&theme=default-inverted" alt="Discord Badge" width="auto" height="20px">
  </a>
  <a href="https://github.com/AidanTheBandit/LAMControl/commits/main" style="text-decoration: none;">
    <img src="https://img.shields.io/github/commit-activity/m/AidanTheBandit/LAMControl" alt="Commit Activity">
  </a>
  <a href="https://github.com/AidanTheBandit/LAMControl/commits/main" style="text-decoration: none;">
    <img src="https://img.shields.io/github/last-commit/AidanTheBandit/LAMControl" alt="Last Commit">
  </a>
  <a href="https://github.com/AidanTheBandit/LAMControl/issues" style="text-decoration: none;">
    <img src="https://img.shields.io/github/issues/AidanTheBandit/LAMControl" alt="Issues">
  </a>
</div>

<p align="center">
  <i>Advanced distributed control system for your Rabbit R1 with pluggable integrations</i>
</p>

---

## 🚀 What is LAMControl?

LAMControl is a **distributed automation system** that turns your Rabbit R1 into a powerful control hub for your digital life. Use natural language to control browsers, computers, messaging platforms, and AI tools across multiple devices.

**Example:** Say "Open YouTube and search for cooking videos" on your R1, and LAMControl will execute it on your computer!

## ✨ Key Features

- 🧩 **Pluggable Integrations**: Mix and match browser, computer, messaging, and AI capabilities
- 🌐 **Distributed Architecture**: Central server + multiple worker nodes
- ⚙️ **Natural Language**: Speak to your R1, LAMControl understands
- 🔄 **Real-time**: Instant command execution and status updates
- � **Web Interface**: Manage workers and send commands via browser
- 🛡️ **Secure**: API key authentication and admin protection

## 🛠️ Available Integrations

| Integration | Capabilities | Example Commands |
|-------------|-------------|------------------|
| **🌐 Browser** | Web browsing, search engines, email | "Open YouTube", "Search Google for Python tutorials", "Check Gmail" |
| **💻 Computer** | Volume, media, system control | "Volume up", "Play music", "Restart computer" |
| **💬 Messaging** | Discord, Telegram, Facebook | "Message John on Discord saying hello" |
| **🤖 AI** | OpenInterpreter automation | "Use Open Interpreter to organize my desktop files" |

## 📋 Prerequisites

- **Python 3.8+** with pip
- **Git** for installation
- **Groq API Key** for LLM processing ([Get one free here](https://groq.com/))
- **Multiple devices** for distributed setup (optional)

## 🚀 Installation

### 1. 📥 Download LAMControl

```bash
git clone https://github.com/AidanTheBandit/LAMControl.git
cd LAMControl
```

### 2. 🔧 Install Dependencies

```bash
pip install -r requirements_distributed.txt
```

### 3. ⚙️ Configure Environment

Create a `.env` file with your API keys:

```bash
echo "GROQ_API_KEY=your_groq_api_key_here" > .env
```

### 4. 🖥️ Start the Server

```bash
python distributed_server.py --host 0.0.0.0 --port 8080
```

The server will start and show you:
- **Admin credentials** (save these!)
- **Web interface URL**: `http://localhost:8080`
- **R1 interface URL**: `http://localhost:8080/r1/login`

### 5. 🤖 Start a Worker

In a new terminal (or on another computer):

```bash
python integrated_worker_node.py
```

This will start a worker with browser and computer integrations.

### 6. 🐰 Connect Your R1

Configure your R1 to send requests to:
```
http://your-server-ip:8080/api/prompt
```

Or use the web interface at: `http://your-server-ip:8080/r1/login`

## 🎯 Usage Examples

### Via R1 Device
Just speak naturally to your R1:
- "Open Google and search for news"
- "Turn the volume up to 50"
- "Send a Discord message to Sarah saying I'll be late"

### Via Web Interface
1. Go to `http://your-server:8080/r1/login`
2. Login with admin credentials
3. Type commands in the interface

### Via API
```bash
curl -X POST http://your-server:8080/api/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Open YouTube and search for music"}'
```

## 🔧 Worker Configuration

### Custom Worker Setup

```bash
# Start worker with specific integrations
python integrated_worker_node.py --integrations browser,computer,ai

# Start worker with custom name and location
python integrated_worker_node.py --name "Living-Room-PC" --location "Living Room"
```

### Available Integration Options

- **browser**: Web browsing and search capabilities
- **computer**: System control (volume, media, power)
- **messaging**: Discord, Telegram, Facebook messaging
- **ai**: OpenInterpreter and AI automation

## 🌐 Distributed Setup

### Multiple Workers Example

**Server (Main computer):**
```bash
python distributed_server.py --host 0.0.0.0 --port 8080
```

**Worker 1 (Living room PC):**
```bash
python integrated_worker_node.py --name "Living-Room" --integrations browser,computer
```

**Worker 2 (Office computer):**
```bash
python integrated_worker_node.py --name "Office" --integrations browser,computer,ai
```

**Worker 3 (Media server):**
```bash
python integrated_worker_node.py --name "Media-Server" --integrations computer
```

### Network Configuration

1. **Find server IP**: `ip addr show` (Linux) or `ipconfig` (Windows)
2. **Configure workers**: Set `--server-host` to server IP
3. **Open firewall**: Allow port 8080 on server
### Network Configuration

1. **Find server IP**: `ip addr show` (Linux) or `ipconfig` (Windows)
2. **Configure workers**: Set `--server-host` to server IP
3. **Open firewall**: Allow port 8080 on server
4. **Test connection**: Visit `http://server-ip:8080` from another device

## 🔍 Monitoring & Management

### Admin Dashboard
Visit `http://server-ip:8080` to access:
- **Worker Status**: View all connected workers
- **Task History**: Monitor command execution
- **System Stats**: Server health and performance
- **Worker Registration**: Add new workers manually

### Worker Management
- **View Workers**: See all connected devices and their capabilities
- **Remove Workers**: Disconnect or remove problematic workers
- **Health Monitoring**: Automatic heartbeat checking
- **Load Balancing**: Commands distributed across available workers

## 🛠️ Troubleshooting

### Common Issues

**Workers not connecting:**
```bash
# Check if server is running
curl http://server-ip:8080/api/health

# Check worker logs
python integrated_worker_node.py --verbose
```

**Commands not executing:**
- Verify Groq API key is set correctly
- Check worker has required integration capabilities
- Review server logs for error messages

**R1 not responding:**
- Ensure R1 is configured with correct server URL
- Test with web interface first: `http://server-ip:8080/r1/login`
- Check network connectivity between R1 and server

### Logs

Server logs show:
- Worker connections/disconnections
- Command processing and routing
- LLM parsing results
- Task execution status

Worker logs show:
- Integration loading status
- Task execution details
- Connection status with server

## 🤝 Contributing

We welcome contributions! Here's how to help:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/new-integration`
3. **Add your integration** following the existing patterns
4. **Test thoroughly** with multiple workers
5. **Submit a pull request** with detailed description

### Creating Custom Integrations

See the existing integrations in `integrations/` for examples:
- Inherit from `Integration` base class
- Implement required methods: `get_capabilities()`, `get_handlers()`, `initialize()`, `cleanup()`
- Add metadata and feature configuration
- Test with distributed setup

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙋 Support

- **Discord**: [Join our community](https://discord.gg/6aU9fjyk2g)
- **Issues**: [GitHub Issues](https://github.com/AidanTheBandit/LAMControl/issues)
- **Discussions**: [GitHub Discussions](https://github.com/AidanTheBandit/LAMControl/discussions)

---

<p align="center">
  <i>Built with ❤️ for the Rabbit R1 community</i>
</p>

### Server Installation (Cloud/VPS)

```bash
# Clone repository
git clone https://github.com/AidanTheBandit/LAMControl.git
cd LAMControl

# Install dependencies
pip install -r requirements_distributed.txt

# Start server
python3 distributed_server.py
```

### Worker Installation (Local Computer)

```bash
# Enhanced installation with specific integrations
curl -sSL https://raw.githubusercontent.com/AidanTheBandit/LAMControl/main/install_worker_enhanced.sh | bash -s -- \
  --integrations browser:google_search,youtube_search,computer:volume_control \
  --server-host your-server-ip \
  --worker-name "Home-Assistant"
```

### Manual Worker Setup

```bash
# Clone repository
git clone https://github.com/AidanTheBandit/LAMControl.git
cd LAMControl

# Install dependencies
pip install -r requirements_distributed.txt

# Start worker with specific integrations
python3 enhanced_worker_launcher.py --integrations browser,computer --server http://your-server:5000
```

## 📖 Documentation

- **[Integration System Guide](INTEGRATION_SYSTEM_GUIDE.md)** - Complete integration documentation
- **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)** - Technical implementation details

## 🎮 Usage Examples

### Basic Commands
```
"Search YouTube for Python tutorials"
"Turn volume to 50"
"Open Google and search for weather"
"Send Discord message to John: Meeting at 3pm"
```

### Worker Management
```bash
# List available integrations
python3 enhanced_worker_launcher.py --list-integrations

# Test configuration without starting
python3 enhanced_worker_launcher.py --dry-run --integrations browser:google_search

# Create configuration template
python3 integration_manager.py --template worker_template.json
```

## 🏗️ Architecture

```
Rabbit R1 ──► Central Server ──► Worker Nodes
                   │                 ├─ Browser Worker (PC 1)
                   │                 ├─ Computer Worker (PC 2)
                   └─ Dashboard      └─ AI Worker (PC 3)
```

### Components

- **Central Server**: Receives R1 prompts, processes with LLM, routes tasks
- **Worker Nodes**: Execute tasks using pluggable integrations
- **Admin Dashboard**: Monitor system health and manage workers
- **Enhanced R1 Client**: Improved communication with error handling

## ⚙️ Configuration

### Worker Configuration Example
```json
{
  "worker": {
    "name": "Home-Assistant",
    "location": "Living Room"
  },
  "server": {
    "endpoint": "http://localhost:5000"
  },
  "integrations": {
    "browser": {
      "enabled": true,
      "features": ["google_search", "youtube_search"],
      "settings": {"default_browser": "firefox"}
    },
    "computer": {
      "enabled": true,
      "features": ["volume_control"],
      "settings": {"vol_step_value": 10}
    }
  }
}
```

## 🔧 Development

### Adding New Integrations

1. Create integration file in `integrations/` directory
2. Inherit from `Integration` base class
3. Define metadata and features
4. Implement required methods

```python
# integrations/my_integration.py
from integrations import Integration, IntegrationConfig

INTEGRATION_METADATA = {
    "name": "my_integration",
    "version": "1.0.0",
    "description": "My custom integration"
}

class MyIntegration(Integration):
    def get_capabilities(self):
        return ["my_capability"]
    
    def get_handlers(self):
        return {"my_capability": self._handle_task}
    
    def initialize(self):
        return True
    
    def cleanup(self):
        pass
```

### Testing
```bash
# Run integration demo
python3 demo_integrations.py

# Test minimal worker
python3 demo_minimal_worker.py

# Test specific integration
python3 integration_manager.py --load browser:google_search
```

## 📋 Requirements

- **Python 3.8+**
- **Flask** for web server
- **Requests** for HTTP communication
- **Groq API Key** for LLM processing
- **Playwright** (for browser integration)
- **Additional packages** installed automatically per integration

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 💬 [Discord Community](https://discord.gg/6aU9fjyk2g)
- 🐛 [Report Issues](https://github.com/AidanTheBandit/LAMControl/issues)
- 📧 Contact: [Support Email]

## 🙏 Acknowledgments

- Rabbit Inc. for the amazing R1 device
- Open source community for the tools and libraries
- Contributors who make this project possible

---

<p align="center">
  <b>Transform your Rabbit R1 into the ultimate automation hub! 🚀</b>
</p>
