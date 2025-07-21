# LAMControl Pluggable Integrations System

## Overview

LAMControl now uses a pluggable integrations system instead of fixed worker types. Workers can dynamically load and configure integrations based on their needs, providing maximum flexibility and modularity.

## Key Features

- **Auto-Discovery**: Integrations are automatically discovered and registered
- **Feature-Based Configuration**: Each integration can have multiple configurable features
- **Dependency Management**: Automatic installation of integration dependencies
- **Dynamic Loading**: Integrations can be loaded and unloaded at runtime
- **Metadata System**: Rich metadata for integration discovery and management

## Architecture

### Integration Base Class

All integrations inherit from the `Integration` base class and must implement:

```python
class MyIntegration(Integration):
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities this integration provides"""
        pass
    
    def get_handlers(self) -> Dict[str, Callable]:
        """Return dictionary of capability -> handler function mappings"""
        pass
    
    def initialize(self) -> bool:
        """Initialize the integration. Return True if successful."""
        pass
    
    def cleanup(self):
        """Clean up any resources used by the integration"""
        pass
```

### Integration Metadata

Integrations can define metadata for discovery and management:

```python
INTEGRATION_METADATA = {
    "name": "my_integration",
    "version": "1.0.0",
    "author": "Your Name",
    "description": "Description of what this integration does",
    "category": "automation",
    "tags": ["automation", "control"],
    "min_python_version": "3.8",
    "conflicts_with": ["other_integration"],
    "provides_capabilities": ["capability1", "capability2"]
}
```

### Feature Configuration

Features within integrations can be configured:

```python
FEATURE_CONFIGS = {
    "feature_name": {
        "name": "feature_name",
        "enabled": True,
        "required": False,
        "description": "What this feature does",
        "dependencies": ["package1", "package2"],
        "settings": {
            "setting1": "default_value",
            "setting2": True
        }
    }
}
```

## Available Integrations

### Browser Integration
- **Capabilities**: Web browsing, search engines, webmail
- **Features**:
  - `site_browsing`: Open arbitrary websites
  - `google_search`: Google search functionality
  - `youtube_search`: YouTube search and video opening
  - `gmail_integration`: Gmail web interface access
  - `amazon_search`: Amazon product search

### Computer Integration
- **Capabilities**: System control, media management
- **Features**:
  - `volume_control`: Audio volume management
  - `media_control`: Media playback control
  - `system_control`: System commands and utilities
  - `power_management`: System power operations

### Messaging Integration
- **Capabilities**: Messaging platform integrations
- **Features**:
  - `discord`: Discord bot integration
  - `telegram`: Telegram bot integration
  - `facebook`: Facebook Messenger integration

### AI Integration
- **Capabilities**: AI automation and language models
- **Features**:
  - `openinterpreter`: Open Interpreter integration
  - `automation`: AI-powered automation
  - `llm_integration`: Language model integration

## Usage

### Installing a Worker with Integrations

Use the enhanced installation script:

```bash
# Basic installation with browser and computer integrations
./install_worker_enhanced.sh --integrations browser,computer --server-host 192.168.1.100

# Installation with specific features
./install_worker_enhanced.sh --integrations browser:google_search,youtube_search,computer:volume_control

# Full installation with custom worker details
./install_worker_enhanced.sh \\
  --integrations browser,computer,ai \\
  --worker-name "Home-Assistant" \\
  --worker-location "Living Room" \\
  --server-host 192.168.1.50
```

### Starting a Worker

Use the enhanced launcher:

```bash
# Start with default configuration
python3 enhanced_worker_launcher.py

# Start with specific integrations
python3 enhanced_worker_launcher.py --integrations browser,computer

# Start with custom configuration
python3 enhanced_worker_launcher.py --config my_worker_config.json
```

### Configuration File Format

```json
{
  "worker": {
    "name": "My-Worker",
    "location": "Office",
    "description": "Office automation worker",
    "port": 6000,
    "max_concurrent_tasks": 5
  },
  "server": {
    "endpoint": "http://localhost:8080"
  },
  "integrations": {
    "browser": {
      "enabled": true,
      "features": ["site_browsing", "google_search"],
      "settings": {
        "default_browser": "firefox"
      }
    },
    "computer": {
      "enabled": true,
      "features": ["volume_control", "media_control"],
      "settings": {
        "vol_step_value": 10
      }
    }
  }
}
```

## Integration Management

### Discovering Available Integrations

```bash
# List all available integrations
python3 enhanced_worker_launcher.py --list-integrations

# Use integration manager directly
python3 integration_manager.py --discover
```

### Creating Configuration Templates

```bash
# Generate a configuration template with all features
python3 integration_manager.py --template worker_template.json
```

### Testing Integration Loading

```bash
# Dry run to see what would be loaded
python3 enhanced_worker_launcher.py --dry-run --integrations browser,computer
```

## Development

### Creating a New Integration

1. Create a new Python file in the `integrations/` directory
2. Define your integration class inheriting from `Integration`
3. Add metadata and feature configurations
4. Implement required methods

Example:

```python
# integrations/my_integration.py
from integrations import Integration, IntegrationConfig

INTEGRATION_METADATA = {
    "name": "my_integration",
    "version": "1.0.0",
    "description": "My custom integration",
    "category": "custom"
}

FEATURE_CONFIGS = {
    "my_feature": {
        "name": "my_feature",
        "enabled": True,
        "description": "My custom feature"
    }
}

class MyIntegration(Integration):
    def get_capabilities(self):
        return ["my_capability"]
    
    def get_handlers(self):
        return {"my_capability": self._handle_my_capability}
    
    def initialize(self):
        return True
    
    def cleanup(self):
        pass
    
    def _handle_my_capability(self, task):
        return "Handled my capability"
```

### Integration Guidelines

1. **Keep integrations focused**: Each integration should have a clear, single purpose
2. **Use feature flags**: Break functionality into configurable features
3. **Handle dependencies**: Gracefully handle missing dependencies
4. **Provide good metadata**: Include comprehensive metadata for discovery
5. **Test thoroughly**: Ensure integrations work in isolation and together

## Migration from Worker Types

The old worker type system has been replaced with pluggable integrations:

| Old Worker Type | New Integration(s) |
|----------------|-------------------|
| `browser_worker` | `browser` integration |
| `computer_worker` | `computer` integration |
| `messaging_worker` | `messaging` integration |
| `ai_worker` | `ai` integration |

To migrate existing workers:

1. Identify which old worker type you were using
2. Map to the corresponding integration(s)
3. Update your installation commands to use integrations
4. Update configuration files to use the new format

## Benefits

- **Modularity**: Only install what you need
- **Flexibility**: Mix and match capabilities
- **Extensibility**: Easy to add new integrations
- **Maintainability**: Isolated integration code
- **Configuration**: Fine-grained feature control
- **Dependencies**: Automatic dependency management
- **Discovery**: Automatic integration discovery and registration

## Troubleshooting

### Integration Not Loading

1. Check integration is in the `integrations/` directory
2. Verify the integration class follows naming conventions
3. Check dependencies are installed
4. Review worker logs for error messages

### Feature Not Working

1. Verify feature is enabled in configuration
2. Check feature dependencies are installed
3. Review integration-specific logs
4. Test feature in isolation

### Dependency Issues

1. Use `--verbose` flag for detailed dependency installation logs
2. Check Python version compatibility
3. Verify pip can install packages
4. Check for conflicting package versions

For more help, check the worker logs and use the `--verbose` flag for detailed output.
