"""
LAMControl Integrations Package

This package contains all the integrations that can be loaded and registered
with worker nodes dynamically.
"""

import os
import sys
import importlib
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass


@dataclass
class IntegrationConfig:
    """Configuration for an integration"""
    name: str
    enabled: bool = True
    settings: Dict[str, Any] = None
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.settings is None:
            self.settings = {}
        if self.dependencies is None:
            self.dependencies = []


class Integration(ABC):
    """Base class for all integrations"""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.name = config.name
        self.enabled = config.enabled
        self.settings = config.settings
        self.logger = logging.getLogger(f"Integration.{self.name}")
        
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities this integration provides"""
        pass
    
    @abstractmethod
    def get_handlers(self) -> Dict[str, Callable]:
        """Return dictionary of capability -> handler function mappings"""
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the integration. Return True if successful."""
        pass
    
    @abstractmethod
    def cleanup(self):
        """Clean up any resources used by the integration"""
        pass
    
    def is_enabled(self) -> bool:
        """Check if integration is enabled"""
        return self.enabled
    
    def get_dependencies(self) -> List[str]:
        """Get list of Python package dependencies"""
        return self.config.dependencies
    
    def validate_dependencies(self) -> bool:
        """Check if all required dependencies are available"""
        for dep in self.get_dependencies():
            try:
                importlib.import_module(dep)
            except ImportError:
                self.logger.error(f"Missing dependency: {dep}")
                return False
        return True


class IntegrationRegistry:
    """Registry for managing integrations"""
    
    def __init__(self):
        self.integrations: Dict[str, Integration] = {}
        self.capability_map: Dict[str, str] = {}  # capability -> integration_name
        self.logger = logging.getLogger("IntegrationRegistry")
        
    def register_integration(self, integration: Integration) -> bool:
        """Register an integration"""
        try:
            if not integration.is_enabled():
                self.logger.info(f"Integration {integration.name} is disabled, skipping")
                return False
                
            if not integration.validate_dependencies():
                self.logger.error(f"Integration {integration.name} failed dependency check")
                return False
                
            if not integration.initialize():
                self.logger.error(f"Integration {integration.name} failed to initialize")
                return False
                
            self.integrations[integration.name] = integration
            
            # Map capabilities to integration
            for capability in integration.get_capabilities():
                if capability in self.capability_map:
                    self.logger.warning(f"Capability {capability} already registered by {self.capability_map[capability]}")
                self.capability_map[capability] = integration.name
                
            self.logger.info(f"Registered integration: {integration.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register integration {integration.name}: {e}")
            return False
    
    def get_integration(self, name: str) -> Optional[Integration]:
        """Get integration by name"""
        return self.integrations.get(name)
    
    def get_integration_for_capability(self, capability: str) -> Optional[Integration]:
        """Get integration that handles a specific capability"""
        integration_name = self.capability_map.get(capability)
        if integration_name:
            return self.integrations.get(integration_name)
        return None
    
    def get_all_capabilities(self) -> List[str]:
        """Get all available capabilities"""
        return list(self.capability_map.keys())
    
    def get_enabled_integrations(self) -> List[Integration]:
        """Get all enabled integrations"""
        return [integration for integration in self.integrations.values() if integration.is_enabled()]
    
    def unregister_integration(self, name: str):
        """Unregister an integration"""
        if name in self.integrations:
            integration = self.integrations[name]
            integration.cleanup()
            
            # Remove capability mappings
            capabilities_to_remove = [cap for cap, int_name in self.capability_map.items() if int_name == name]
            for cap in capabilities_to_remove:
                del self.capability_map[cap]
                
            del self.integrations[name]
            self.logger.info(f"Unregistered integration: {name}")
    
    def cleanup_all(self):
        """Cleanup all integrations"""
        for integration in self.integrations.values():
            try:
                integration.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up {integration.name}: {e}")
        
        self.integrations.clear()
        self.capability_map.clear()


def auto_discover_integrations(integrations_dir: str = None) -> List[Integration]:
    """Auto-discover integrations in the integrations directory"""
    if integrations_dir is None:
        integrations_dir = os.path.dirname(__file__)
    
    discovered = []
    logger = logging.getLogger("IntegrationDiscovery")
    
    # Look for integration modules
    for file in os.listdir(integrations_dir):
        if file.endswith('.py') and not file.startswith('_') and file != '__init__.py':
            module_name = file[:-3]  # Remove .py extension
            
            try:
                # Import the module
                module = importlib.import_module(f'integrations.{module_name}')
                
                # Look for integration classes - try multiple naming patterns
                integration_class = None
                possible_names = [
                    f"{module_name.title()}Integration",
                    f"{module_name.capitalize()}Integration", 
                    f"{module_name.upper()}Integration",
                    f"{module_name}Integration"
                ]
                
                for class_name in possible_names:
                    if hasattr(module, class_name):
                        attr = getattr(module, class_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, Integration) and 
                            attr != Integration):
                            integration_class = attr
                            break
                
                if integration_class:
                    # Create default config
                    config = IntegrationConfig(name=module_name)
                    integration = integration_class(config)
                    discovered.append(integration)
                    logger.info(f"Discovered integration: {module_name}")
                else:
                    logger.warning(f"No integration class found in {module_name}")
                        
            except Exception as e:
                logger.warning(f"Failed to load integration from {module_name}: {e}")
    
    return discovered


# Global registry instance
registry = IntegrationRegistry()
