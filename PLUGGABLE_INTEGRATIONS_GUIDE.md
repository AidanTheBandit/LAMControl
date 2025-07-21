# LAMControl Pluggable Integrations Architecture

## Overview

LAMControl has been refactored to use a **pluggable integrations architecture** instead of fixed worker types. This new system allows workers to dynamically load and use specific integrations based on configuration, making the system more flexible and extensible.

## Key Changes

### Before (Worker Types)
- Workers had fixed types: `browser`, `computer`, `messaging`, `ai`
- Each worker type had hardcoded capabilities
- Adding new functionality required creating new worker types
- Limited flexibility in deployment scenarios

### After (Pluggable Integrations)
- Workers can load any combination of integrations
- Integrations are auto-discovered and configurable
- Each integration provides specific capabilities
- Easy to add new integrations without changing core worker code
- Workers can be customized per deployment

## Architecture Components

### 1. Integration Base Class (`integrations/__init__.py`)

```python
class Integration(ABC):
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities this integration provides"""
        
    @abstractmethod
    def get_handlers(self) -> Dict[str, Callable]:
        """Return capability -> handler function mappings"""
        
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the integration"""
        
    @abstractmethod
    def cleanup(self):
        """Clean up resources"""
```

### 2. Integration Registry
- Manages loaded integrations
- Maps capabilities to integrations
- Handles integration lifecycle
- Provides capability discovery

### 3. Integrated Worker Node
- Dynamically loads integrations
- Routes tasks to appropriate integration handlers
- Supports configuration-based setup
- Auto-discovery of available integrations

## Available Integrations

### Browser Integration (`integrations/browser.py`)
**Capabilities:** `browsersite`, `browsergoogle`, `browseryoutube`, `browsergmail`, `browseramazon`

**Configuration:**
```json
{
  "browser": {
    "enabled": true,
    "settings": {
      "site_enabled": true,
      "google_enabled": true,
      "youtube_enabled": true,
      "gmail_enabled": true,
      "amazon_enabled": true
    }
  }
}
```

### Computer Integration (`integrations/computer.py`)
**Capabilities:** `computervolume`, `computerrun`, `computermedia`, `computerpower`

**Configuration:**
```json
{
  "computer": {
    "enabled": true,
    "settings": {
      "volume_enabled": true,
      "run_enabled": true,
      "media_enabled": true,
      "power_enabled": true,
      "vol_up_step_value": 5,
      "vol_down_step_value": 5
    }
  }
}
```

### Messaging Integration (`integrations/messaging.py`)
**Capabilities:** `discordtext`, `telegram`, `facebooktext`

**Configuration:**
```json
{
  "messaging": {
    "enabled": true,
    "settings": {
      "discord_enabled": true,
      "telegram_enabled": true,
      "facebook_enabled": true
    },
    "dependencies": ["playwright", "python-telegram-bot"]
  }
}
```

### AI Integration (`integrations/ai.py`)
**Capabilities:** `openinterpreter`, `ai_automation`

**Configuration:**
```json
{
  "ai": {
    "enabled": true,
    "settings": {
      "openinterpreter_enabled": true,
      "ai_automation_enabled": true,
      "openinterpreter_llm_api_base": "groq",
      "openinterpreter_llm_model": "llama-3.3-70b-versatile"
    },
    "dependencies": ["open-interpreter"]
  }
}
```

## Usage

### 1. Auto-Discovery Mode
The worker automatically discovers and loads all available integrations:

```bash
python integrated_worker_node.py http://localhost:8080 6001
```

### 2. Configuration-Based Mode
Create a configuration file and specify which integrations to load:

```bash
python integrated_worker_node.py http://localhost:8080 6001 worker_config.json
```

**Sample Configuration File:**
```json
{
  "worker": {
    "name": "my-custom-worker",
    "location": "Home Office",
    "description": "Custom worker with selected integrations"
  },
  "integrations": {
    "browser": {
      "enabled": true,
      "settings": {
        "youtube_enabled": true,
        "gmail_enabled": false
      }
    },
    "computer": {
      "enabled": true,
      "settings": {
        "power_enabled": false
      }
    }
  }
}
```

### 3. Setup Utility
Use the updated setup utility to generate configurations:

```bash
# Generate installation commands for specific integrations
python setup_workers.py --generate-commands --integrations browser computer --server-host 192.168.1.100

# Create configuration file interactively
python setup_workers.py --create-config --config-file my_worker.json
```

## Creating New Integrations

### 1. Create Integration Class
Create a new file in `integrations/` directory:

```python
# integrations/my_integration.py
from integrations import Integration, IntegrationConfig
from typing import Dict, List, Callable

class MyIntegration(Integration):
    def get_capabilities(self) -> List[str]:
        return ['mycapability1', 'mycapability2']
    
    def get_handlers(self) -> Dict[str, Callable]:
        return {
            'mycapability1': self._handle_capability1,
            'mycapability2': self._handle_capability2
        }
    
    def initialize(self) -> bool:
        self.logger.info("My integration initialized")
        return True
    
    def cleanup(self):
        self.logger.info("My integration cleaned up")
    
    def _handle_capability1(self, task: str) -> str:
        # Implementation here
        return "Capability 1 executed"
    
    def _handle_capability2(self, task: str) -> str:
        # Implementation here
        return "Capability 2 executed"
```

### 2. Add Configuration Support
Update the setup utility to include your new integration:

```python
# In setup_workers.py, add to get_available_integrations()
def get_available_integrations():
    return ["browser", "computer", "messaging", "ai", "my_integration"]
```

### 3. Auto-Discovery
The new integration will be automatically discovered and loaded by workers using auto-discovery mode.

## Benefits

### 🚀 **Flexibility**
- Workers can be customized for specific use cases
- Mix and match integrations as needed
- Enable/disable specific capabilities per deployment

### 🔧 **Maintainability**
- Each integration is self-contained
- Easy to add new integrations
- Clear separation of concerns
- Simplified testing and debugging

### 📦 **Modularity**
- Integrations can be developed independently
- Optional dependencies per integration
- Graceful degradation when dependencies are missing

### ⚡ **Performance**
- Only load needed integrations
- Reduced memory footprint
- Faster startup times

### 🛠️ **Developer Experience**
- Simple integration API
- Auto-discovery of integrations
- Configuration-driven setup
- Interactive setup utility

## Migration from Worker Types

### Old System (Worker Types)
```bash
# Browser worker
python workers/browser_worker.py http://server:8080 6001

# Computer worker  
python workers/computer_worker.py http://server:8080 6002
```

### New System (Integrated Workers)
```bash
# Worker with browser integration
python integrated_worker_node.py http://server:8080 6001 browser_config.json

# Worker with computer integration
python integrated_worker_node.py http://server:8080 6002 computer_config.json

# Worker with both integrations
python integrated_worker_node.py http://server:8080 6003 combined_config.json
```

### Backward Compatibility
The old worker types are still supported through legacy wrapper functions in each integration module.

## Testing

Run the test script to verify the integration system:

```bash
python test_integrated_worker.py
```

This will:
- Test auto-discovery of integrations
- Test configuration-based worker creation
- Verify capability mapping
- Test task execution

## Future Enhancements

1. **Plugin System**: Support for external integration plugins
2. **Hot Reloading**: Reload integrations without restarting workers
3. **Integration Marketplace**: Repository of community integrations
4. **Dependency Management**: Automatic installation of integration dependencies
5. **Integration Templates**: Scaffolding for new integrations
6. **Performance Monitoring**: Per-integration metrics and monitoring
