#!/usr/bin/env python3
"""
LAMControl Integration Manager

Enhanced integration management system with auto-registration, dependency management,
and feature configuration for pluggable worker integrations.
"""

import os
import sys
import json
import logging
import importlib
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, asdict
from integrations import Integration, IntegrationConfig, IntegrationRegistry


@dataclass
class IntegrationMetadata:
    """Metadata for an integration"""
    name: str
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    category: str = "general"
    tags: List[str] = None
    min_python_version: str = "3.8"
    conflicts_with: List[str] = None
    provides_capabilities: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.conflicts_with is None:
            self.conflicts_with = []
        if self.provides_capabilities is None:
            self.provides_capabilities = []


@dataclass
class FeatureConfig:
    """Configuration for a specific feature within an integration"""
    name: str
    enabled: bool = True
    required: bool = False
    description: str = ""
    dependencies: List[str] = None
    settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.settings is None:
            self.settings = {}


class EnhancedIntegrationManager:
    """Enhanced manager for integrations with auto-registration and feature configs"""
    
    def __init__(self, integrations_dir: str = None):
        self.integrations_dir = integrations_dir or os.path.join(os.path.dirname(__file__), "integrations")
        self.registry = IntegrationRegistry()
        self.logger = logging.getLogger("IntegrationManager")
        
        # Metadata and feature tracking
        self.integration_metadata: Dict[str, IntegrationMetadata] = {}
        self.feature_configs: Dict[str, Dict[str, FeatureConfig]] = {}
        self.installed_packages: Set[str] = set()
        
        # Configuration cache
        self.config_cache: Dict[str, Any] = {}
        
        self.logger.info("Initialized Enhanced Integration Manager")
    
    def discover_integrations(self) -> Dict[str, Any]:
        """Discover all available integrations and their metadata"""
        discovered = {}
        
        if not os.path.exists(self.integrations_dir):
            self.logger.warning(f"Integrations directory not found: {self.integrations_dir}")
            return discovered
        
        for file in os.listdir(self.integrations_dir):
            if file.endswith('.py') and not file.startswith('_') and file != '__init__.py':
                integration_name = file[:-3]
                
                try:
                    integration_info = self._analyze_integration_file(integration_name)
                    if integration_info:
                        discovered[integration_name] = integration_info
                        self.logger.info(f"Discovered integration: {integration_name}")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to analyze integration {integration_name}: {e}")
        
        return discovered
    
    def _analyze_integration_file(self, integration_name: str) -> Optional[Dict[str, Any]]:
        """Analyze an integration file to extract metadata and features"""
        try:
            # Import the module
            module = importlib.import_module(f'integrations.{integration_name}')
            
            # Look for integration class
            integration_class = None
            possible_names = [
                f"{integration_name.title()}Integration",
                f"{integration_name.capitalize()}Integration",
                f"{integration_name.upper()}Integration",
                f"{integration_name}Integration"
            ]
            
            for class_name in possible_names:
                if hasattr(module, class_name):
                    attr = getattr(module, class_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, Integration) and 
                        attr != Integration):
                        integration_class = attr
                        break
            
            if not integration_class:
                return None
            
            # Extract metadata if available
            metadata = getattr(module, 'INTEGRATION_METADATA', None)
            if metadata and isinstance(metadata, dict):
                metadata_obj = IntegrationMetadata(**metadata)
            else:
                metadata_obj = IntegrationMetadata(name=integration_name)
            
            # Extract feature configurations if available
            feature_configs = getattr(module, 'FEATURE_CONFIGS', None)
            if feature_configs and isinstance(feature_configs, dict):
                features = {name: FeatureConfig(**config) for name, config in feature_configs.items()}
            else:
                features = {}
            
            # Create temporary instance to get capabilities
            temp_config = IntegrationConfig(name=integration_name)
            temp_instance = integration_class(temp_config)
            capabilities = temp_instance.get_capabilities() if hasattr(temp_instance, 'get_capabilities') else []
            
            # Store metadata and features
            self.integration_metadata[integration_name] = metadata_obj
            self.feature_configs[integration_name] = features
            
            return {
                'name': integration_name,
                'class': integration_class,
                'metadata': asdict(metadata_obj),
                'features': {name: asdict(config) for name, config in features.items()},
                'capabilities': capabilities,
                'dependencies': getattr(temp_instance, 'get_dependencies', lambda: [])()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing integration {integration_name}: {e}")
            return None
    
    def install_dependencies(self, integration_name: str, features: List[str] = None) -> bool:
        """Install dependencies for an integration and its features"""
        try:
            integration_info = self.integration_metadata.get(integration_name)
            if not integration_info:
                self.logger.error(f"Integration metadata not found: {integration_name}")
                return False
            
            # Collect all dependencies
            all_deps = set()
            
            # Add integration-level dependencies
            if hasattr(integration_info, 'dependencies'):
                all_deps.update(integration_info.dependencies)
            
            # Add feature-specific dependencies
            if features and integration_name in self.feature_configs:
                for feature_name in features:
                    feature_config = self.feature_configs[integration_name].get(feature_name)
                    if feature_config:
                        all_deps.update(feature_config.dependencies)
            
            # Install dependencies
            for dep in all_deps:
                if dep not in self.installed_packages:
                    if self._install_package(dep):
                        self.installed_packages.add(dep)
                    else:
                        self.logger.error(f"Failed to install dependency: {dep}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error installing dependencies for {integration_name}: {e}")
            return False
    
    def _install_package(self, package: str) -> bool:
        """Install a Python package using pip"""
        try:
            self.logger.info(f"Installing package: {package}")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                self.logger.info(f"Successfully installed: {package}")
                return True
            else:
                self.logger.error(f"Failed to install {package}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout installing package: {package}")
            return False
        except Exception as e:
            self.logger.error(f"Error installing package {package}: {e}")
            return False
    
    def load_integration_with_features(self, integration_name: str, 
                                     integration_config: Dict[str, Any] = None,
                                     enabled_features: List[str] = None) -> bool:
        """Load an integration with specific feature configuration"""
        try:
            # Get integration info
            discovered = self.discover_integrations()
            if integration_name not in discovered:
                self.logger.error(f"Integration not found: {integration_name}")
                return False
            
            integration_info = discovered[integration_name]
            
            # Install dependencies for enabled features
            if not self.install_dependencies(integration_name, enabled_features):
                self.logger.error(f"Failed to install dependencies for {integration_name}")
                return False
            
            # Prepare configuration
            config_data = integration_config or {}
            
            # Configure features
            if enabled_features and integration_name in self.feature_configs:
                feature_settings = {}
                for feature_name in enabled_features:
                    if feature_name in self.feature_configs[integration_name]:
                        feature_config = self.feature_configs[integration_name][feature_name]
                        feature_settings.update(feature_config.settings)
                        # Add feature enable flags
                        feature_settings[f"{feature_name}_enabled"] = True
                
                # Merge feature settings into config
                config_data.setdefault('settings', {}).update(feature_settings)
            
            # Create integration config
            config = IntegrationConfig(
                name=integration_name,
                enabled=config_data.get('enabled', True),
                settings=config_data.get('settings', {}),
                dependencies=integration_info['dependencies']
            )
            
            # Create integration instance
            integration_class = integration_info['class']
            integration = integration_class(config)
            
            # Register with registry
            if self.registry.register_integration(integration):
                self.logger.info(f"Successfully loaded integration: {integration_name}")
                return True
            else:
                self.logger.error(f"Failed to register integration: {integration_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error loading integration {integration_name}: {e}")
            return False
    
    def load_integrations_from_list(self, integrations_list: List[str],
                                  global_config: Dict[str, Any] = None) -> Dict[str, bool]:
        """Load multiple integrations from a list"""
        results = {}
        global_config = global_config or {}
        
        for integration_spec in integrations_list:
            # Parse integration specification (name:feature1,feature2)
            if ':' in integration_spec:
                integration_name, features_str = integration_spec.split(':', 1)
                enabled_features = [f.strip() for f in features_str.split(',')]
            else:
                integration_name = integration_spec
                enabled_features = None
            
            # Get integration-specific config
            integration_config = global_config.get(integration_name, {})
            
            # Load the integration
            success = self.load_integration_with_features(
                integration_name, integration_config, enabled_features
            )
            results[integration_name] = success
        
        return results
    
    def get_integration_info(self, integration_name: str = None) -> Dict[str, Any]:
        """Get detailed information about integrations"""
        if integration_name:
            # Return info for specific integration
            if integration_name in self.integration_metadata:
                return {
                    'metadata': asdict(self.integration_metadata[integration_name]),
                    'features': {name: asdict(config) for name, config in 
                               self.feature_configs.get(integration_name, {}).items()},
                    'loaded': integration_name in self.registry.integrations
                }
            return {}
        else:
            # Return info for all integrations
            info = {}
            for name in self.integration_metadata:
                info[name] = self.get_integration_info(name)
            return info
    
    def get_registry(self) -> IntegrationRegistry:
        """Get the integration registry"""
        return self.registry
    
    def save_config_template(self, filepath: str, include_all_features: bool = False):
        """Save a configuration template with all discovered integrations"""
        discovered = self.discover_integrations()
        
        config_template = {
            "integrations": {}
        }
        
        for name, info in discovered.items():
            integration_config = {
                "enabled": True,
                "settings": {},
                "features": {}
            }
            
            # Add feature configurations
            if include_all_features and name in self.feature_configs:
                for feature_name, feature_config in self.feature_configs[name].items():
                    integration_config["features"][feature_name] = {
                        "enabled": feature_config.enabled,
                        "settings": feature_config.settings.copy()
                    }
            
            config_template["integrations"][name] = integration_config
        
        with open(filepath, 'w') as f:
            json.dump(config_template, f, indent=2)
        
        self.logger.info(f"Saved configuration template to: {filepath}")


def main():
    """CLI interface for the integration manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LAMControl Integration Manager")
    parser.add_argument("--discover", action="store_true", help="Discover available integrations")
    parser.add_argument("--load", nargs='+', help="Load specific integrations (name:feature1,feature2)")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--template", help="Generate configuration template")
    parser.add_argument("--info", help="Get info about specific integration")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    manager = EnhancedIntegrationManager()
    
    if args.discover:
        print("Discovering integrations...")
        discovered = manager.discover_integrations()
        print(f"Found {len(discovered)} integrations:")
        for name, info in discovered.items():
            print(f"  - {name}: {len(info['capabilities'])} capabilities")
    
    elif args.load:
        config = {}
        if args.config and os.path.exists(args.config):
            with open(args.config) as f:
                config = json.load(f)
        
        results = manager.load_integrations_from_list(args.load, config.get('integrations', {}))
        print("Loading results:")
        for name, success in results.items():
            status = "SUCCESS" if success else "FAILED"
            print(f"  - {name}: {status}")
    
    elif args.template:
        manager.save_config_template(args.template, include_all_features=True)
        print(f"Configuration template saved to: {args.template}")
    
    elif args.info:
        info = manager.get_integration_info(args.info)
        if info:
            print(json.dumps(info, indent=2))
        else:
            print(f"Integration not found: {args.info}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
