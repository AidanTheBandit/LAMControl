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
- 📧 Contact: [Your Email]

## 🙏 Acknowledgments

- Rabbit Inc. for the amazing R1 device
- Open source community for the tools and libraries
- Contributors who make this project possible

---

<p align="center">
  <b>Transform your Rabbit R1 into the ultimate automation hub! 🚀</b>
</p>

# Or clone and run locally
git clone https://github.com/AidanTheBandit/LAMControl.git
cd LAMControl
python3 enhanced_worker_launcher.py --integrations browser,computer
```

📖 **[Complete Integration Guide](INTEGRATION_SYSTEM_GUIDE.md)**

---

## 🎯 Operating Modes:

LAMControl supports multiple operating modes to fit different use cases:

### 🌐 **Distributed Mode** (Recommended - NEW!)
- **Central server with pluggable worker nodes**
- Scale across multiple computers and locations
- Mix and match integrations per worker
- Enhanced performance and reliability
- Perfect for home automation setups

### 🖥️ **Web Mode**
- Direct HTTP API for R1 integration
- Admin dashboard for monitoring
- No Rabbit Hole tokens required
- Great for single-machine setups

### 🐰 **Rabbit Mode** (Legacy)
- Connects to hole.rabbit.tech
- Monitors journal entries  
- Requires Rabbit Hole access token

### 💻 **CLI Mode**
- Interactive command-line interface
- Perfect for testing and development

### Grabbing journal entries (Rabbit Mode):
By using your `hole.rabbit.tech` account token, we can directly fetch journal entries from the API. By doing this, we can efficiently grab your latest journal entry.

### Intention routing and command parsing:
By providing the user's utterance to `llama3-70b-8192` via the [Groq API](https://console.Groq.com) we can determine:

1. If the user is talking to r1, or if it is a command meant for LAMatHome
2. Which integration to call, and what parameters to give it

By doing this, we avoid the user having to learn every command for every integration, and enables natural language commands. It also enables creativity for the LLM to craft texts for you, if you're into automating social interaction.

**Examples:**

|User utterance in journal entry|LLM "rigid command" Output|
|-----------------------|----------|
|"Can you text my roommate Justin on telegram, yelling in all caps, that his music is too loud? Add a few extra exclamation points."|`Telegram Justin YOUR MUSIC IS TOO LOUD!!!`|
|"Can you turn the volume on my computer up to 100 to spite my roommate?"|`Computer Volume 100`|
|"What time does the moon come out today?"|`x`*|

*\*`x` is the output when the LLM decides your intention was to talk to r1, or, that it didn't have enough information. e.g. Name of recipient, platform to send on, etc.*

Then, `llm_parse.py` takes your neatly formatted command, and executes it based on which integration is called, and the parameters.

## Integrations
Below is a list of our current integrations. This list is kept up-to-date.

||Name|Category|Description|Example prompt|
|-|-|-|-|-|
||Site|Browser|Opens/Searches in any website.|`Open the _____ website`|
||[Google](https://google.com)|Browser|Searches Google.|`Search google on my computer for ______`|
||[YouTube](https://youtube.com)|Browser|Searches YouTube.|`Open a YouTube search for ______ on my computer`|
||[Gmail](https://gmail.com)|Browser|Searches Gmail.|`Search my emails on my computer for ______`|
||[Amazon](https://amazon.com)|Browser|Searches Amazon.|`Search amazon on computer: ______`|
|❕|Run|Local Actions|Presses Windows key, searches for an app, and runs.|`Open up the chat app for gamers on my computer`|
|❕|Volume|Local Actions|Sets volume, turns up/down, and mutes/unmutes.|`Change the volume on my pc to 50`|
||Media|Local Actions|Skips media next/back, pause/unpause.|`Pause on my pc`, `Skip twice backwards on my computer`|
|❕|Power|Local Actions|Power options (Lock/Sleep/Restart/Shutdown)|`Shutdown my PC`, `Please lock my computer`|
||[Google Home](https://home.google.com)|Local Actions|Activates Google Home automations.|`Turn on my desk lamp`, `Use google home to turn on my lamp, but I forgot what it's called`|
||Open Interpreter|Local Actions|Send commands to Open Interpreter|`Tell Open Interpreter to open the blender file on my desktop.`|
||LAMatHome|Local Actions|Only integration currently is "terminate", which closes LAH.|`That's enough from you. Close LAM at home.`|
|⚠️|[Discord](https://discord.com)|Messaging|Sends a message on Discord to a specified person/channel.|`Text poke on discord asking when he's going to be back online. Wait, no ask him on telegram. Actually no, discord is good.`|
|⚠️|[FB Messenger](https://messenger.com)|Messaging|Sends a message on FB Messenger to a specified person.|`Ask Justin what he thinks of my new sunglasses. Oh, send that on facebook.`|
|⚠️|[Telegram](https://web.telegram.org/)|Messaging|Sends a message on Telegram to a specified person.|`Message Kevin on telegram asking him when he's gonna PR his new feature`|

> [!NOTE]
>
> *Integrations marked with a* ❕ *may need to be saved as a note to work. r1 could interpret these as commands to itself, and not save the query to the rabbithole. This is a result of r1 update 20240603.15/0.8.99(134D8DE) that enabled voice settings.*
> 
> *Integrations marked with a ⚠️ are experimental and may send to the incorrect person/channel based on the way the user utterance is transcribed. This is a limitation of the r1, not LLM Parsing.*

## Quick start guide:

## 📦 Installation & Setup

### System Requirements:
- **Python 3.8+** (required)
- **Git** (for installation)
- **pip** (Python package manager)
- **Internet connection** (for dependency installation)

### 🚀 Quick Start (Distributed Mode - Recommended)

#### Option 1: Automated Installation
```bash
# Install server and worker with browser + computer integrations
curl -sSL https://raw.githubusercontent.com/AidanTheBandit/LAMControl/main/install_worker_enhanced.sh | bash -s -- \
  --integrations browser,computer \
  --server-host localhost \
  --worker-name "My-LAM-Worker"
```

#### Option 2: Manual Installation
```bash
# 1. Clone the repository
git clone https://github.com/AidanTheBandit/LAMControl.git
cd LAMControl

# 2. Install dependencies
pip3 install -r requirements_distributed.txt

# 3. Start the server
python3 distributed_server.py

# 4. In another terminal, start a worker with integrations
python3 enhanced_worker_launcher.py --integrations browser,computer
```

### 🌐 Web Mode Setup (Single Machine)
```bash
# 1. Clone repository
git clone https://github.com/AidanTheBandit/LAMControl.git
cd LAMControl

# 2. Install dependencies
pip3 install -r requirements.txt
playwright install

# 3. Configure for web mode
cp config.json config_backup.json
# Edit config.json: set "mode": "web"

# 4. Run LAMControl
python3 main.py
```

### 🐰 Rabbit Mode Setup (Legacy)
```bash
# 1. Follow Web Mode steps 1-2
# 2. Configure for rabbit mode
# Edit config.json: set "mode": "rabbit"
# 3. Get your Rabbit Hole token (see instructions below)
# 4. Run LAMControl
python3 main.py
```

---

## 🔧 Configuration

### Required API Keys:
1. **GROQ API Key** (required for all modes):
   - Go to [console.groq.com](https://console.groq.com)
   - Create account and generate API key
   - Add to `.env` file: `GROQ_API_KEY=your_key_here`

2. **Rabbit Hole Token** (only for Rabbit Mode):
   - Instructions below in Rabbit Mode section

### Integration-Specific Configuration:

#### Browser Integration:
```json
{
  "integrations": {
    "browser": {
      "enabled": true,
      "features": ["google_search", "youtube_search", "site_browsing"],
      "settings": {
        "default_browser": "system_default"
      }
    }
  }
}
```

#### Computer Integration:
```json
{
  "integrations": {
    "computer": {
      "enabled": true,
      "features": ["volume_control", "media_control", "system_control"],
      "settings": {
        "vol_step_value": 5
      }
    }
  }
}
```

#### Messaging Integration:
```json
{
  "integrations": {
    "messaging": {
      "enabled": true,
      "features": ["discord", "telegram"],
      "settings": {
        "auto_connect": false
      }
    }
  }
}
```

---

## 🎮 Usage Examples

### Distributed Mode Commands:
```bash
# List available integrations
python3 enhanced_worker_launcher.py --list-integrations

# Start worker with specific integrations and features
python3 enhanced_worker_launcher.py \
  --integrations browser:google_search,youtube_search,computer:volume_control \
  --server http://your-server:8080

# Create configuration template
python3 integration_manager.py --template my_config.json

# Test configuration without starting worker
python3 enhanced_worker_launcher.py --dry-run --integrations browser,computer
```

### R1 Voice Commands:
- *"Search Google for Python tutorials"* → Opens Google search
- *"Turn the volume up to 75"* → Sets system volume
- *"Open YouTube and search for cooking videos"* → YouTube search  
- *"Send a message on Discord to John"* → Discord integration
- *"Tell Open Interpreter to analyze this file"* → AI integration

---

## 🐰 Rabbit Mode Token Setup (Legacy)

**Obtaining your user token from [the rabbithole](https://hole.rabbit.tech/journal/details):**

- *Google Chrome*
   1. Log into the rabbit hole from the link above
   2. Press F12 to bring up the developer console. If this doesn't work, right-click the page, and click inspect. 
   3. Expand the developer console for better viewing
   4. Click the `Network` tab in the top navigation bar.
   5. Press Ctrl + R to reload the page.
   6. Near the bottom of the middle pane, find and select `fetchUserJournal`.
   7. In the new pane that opened, select `Payload` in the top navigation bar.
   8. Select everything inside the quotes after `accessToken`. This is your user token.

- *Firefox*
   1. Log into the rabbit hole from the link above
   2. Press F12 to bring up the developer console. If this doesn't work, right-click the page, and click inspect.
   3. Expand the developer console for better viewing
   4. Click the `Network` tab in the top navigation bar.
   5. Press Ctrl + R to reload the page.
   6. In the `Network` tab, in the `File` column, find and select `fetchUserJournal`.
   7. In the new sidebar that opened up, select `Request` in the top navigation bar.
   8. Select everything inside the quotes after `accessToken`. This is your user token.

   Note: Your token will expire 24 hours after you log in. This is out of our control but we are working on a better way.

---

## 🔥 Advanced Features

### Custom Integration Development:
```python
# Create custom integration in integrations/my_integration.py
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
        return {"my_capability": self._handle_my_capability}
    
    def _handle_my_capability(self, task):
        return "Handled my custom task"
```

### Multi-Worker Deployment:
```bash
# Deploy multiple specialized workers
./install_worker_enhanced.sh --integrations browser --worker-name "Browser-Worker" --location "Office"
./install_worker_enhanced.sh --integrations computer --worker-name "Computer-Worker" --location "Home"
./install_worker_enhanced.sh --integrations messaging --worker-name "Social-Worker" --location "Cloud"
```

### Production Deployment:
```bash
# Server (systemd service)
sudo systemctl enable lamcontrol-server
sudo systemctl start lamcontrol-server

# Workers (systemd services)
systemctl --user enable lamcontrol-worker
systemctl --user start lamcontrol-worker
```

---

## 🛠️ Development & Troubleshooting

### Development Setup:
```bash
git clone https://github.com/AidanTheBandit/LAMControl.git
cd LAMControl

# Install development dependencies
pip3 install -r requirements_distributed.txt

# Run tests
python3 demo_integrations.py
python3 test_distributed.py

# Start development server
python3 distributed_server.py --debug
```

### Common Issues:

| Error | Solution |
|-------|----------|
| `Integration not found` | Check integration name and ensure it's in the integrations/ directory |
| `Dependency installation failed` | Ensure pip is up to date: `pip3 install --upgrade pip` |
| `Worker connection failed` | Verify server endpoint and port are correct |
| `Permission denied` | Run with appropriate permissions or check file ownership |

### Logs and Debugging:
```bash
# View worker logs
tail -f worker.log

# View server logs  
tail -f server.log

# Debug mode
python3 enhanced_worker_launcher.py --verbose --dry-run
```

---

## 📚 Documentation

- 📖 **[Integration System Guide](INTEGRATION_SYSTEM_GUIDE.md)** - Complete integration documentation
- 🚀 **[Distributed Deployment Guide](DISTRIBUTED_DEPLOYMENT_GUIDE.md)** - Advanced deployment scenarios
- 🔧 **[Worker Installation Guide](WORKER_INSTALLATION_GUIDE.md)** - Detailed worker setup
- 🧩 **[Pluggable Integrations Guide](PLUGGABLE_INTEGRATIONS_GUIDE.md)** - Custom integration development

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines:
- Follow the existing integration pattern for new integrations
- Add tests for new functionality
- Update documentation for new features
- Ensure backwards compatibility

---

## 👥 Contributors & Acknowledgements

### Contributors:
[![LAMControl's Contributors](https://stats.deeptrain.net/contributor/AidanTheBandit/LAMControl/?theme=dark)](https://github.com/AidanTheBandit/LAMControl/contributors)

### Special Thanks:
- Original LAMatHome project inspiration
- Thanks to poke for the original idea [rabbitWrighter](https://github.com/glovergaytan-fs/rabbitWrighter)
- Community feedback and contributions
- Open source libraries that make this possible

---

## 📄 License

This project is licensed under the [MIT License](https://choosealicense.com/licenses/mit/) - see the LICENSE file for details.

---

## 🚀 What's Next?

- 🔌 More integrations (Home Assistant, MQTT, etc.)
- 🌍 Multi-language support
- 📱 Mobile app for management
- 🧠 Enhanced AI capabilities
- ☁️ Cloud deployment options

---

<p align="center">
  <strong>Ready to supercharge your rabbit r1? Get started with LAMControl today!</strong>
</p>

<p align="center">
  <a href="https://github.com/AidanTheBandit/LAMControl/issues">Report Bug</a> •
  <a href="https://github.com/AidanTheBandit/LAMControl/issues">Request Feature</a> •
  <a href="https://discord.gg/6aU9fjyk2g">Join Discord</a>
</p>
