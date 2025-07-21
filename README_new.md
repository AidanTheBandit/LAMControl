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

## ✨ Key Features

- 🧩 **Pluggable Integrations**: Install only what you need
- 🌐 **Distributed Architecture**: Scale across multiple devices
- ⚙️ **Feature-Based Configuration**: Fine-grained control
- 🔄 **Auto-Discovery**: Automatic integration detection
- 📦 **Dependency Management**: Automatic package installation
- 🎯 **Dynamic Loading**: No restart required for changes

## 🛠️ Available Integrations

| Integration | Features | Capabilities |
|-------------|----------|--------------|
| **🌐 Browser** | Site browsing, Google/YouTube/Gmail/Amazon search | Web automation and search |
| **💻 Computer** | Volume/media/system/power control | Local system automation |
| **💬 Messaging** | Discord, Telegram, Facebook | Social platform integrations |
| **🤖 AI** | OpenInterpreter, automation, LLM integration | AI-powered tasks |

## 🚀 Quick Start

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
