import logging
from typing import Dict, List, Callable
from integrations import Integration, IntegrationConfig
from utils import config, get_env


class AiIntegration(Integration):
    """AI integration for OpenInterpreter and other AI tools"""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        
        # Individual capability settings from config
        self.openinterpreter_enabled = self.settings.get('openinterpreter_enabled', True)
        self.ai_automation_enabled = self.settings.get('ai_automation_enabled', True)
        
        # OpenInterpreter configuration
        self.interpreter = None
        if self.openinterpreter_enabled:
            self._setup_openinterpreter()
    
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities this integration provides"""
        capabilities = []
        if self.openinterpreter_enabled:
            capabilities.append('openinterpreter')
        if self.ai_automation_enabled:
            capabilities.append('ai_automation')
        return capabilities
    
    def get_handlers(self) -> Dict[str, Callable]:
        """Return dictionary of capability -> handler function mappings"""
        handlers = {}
        if self.openinterpreter_enabled:
            handlers['openinterpreter'] = self._handle_openinterpreter
        if self.ai_automation_enabled:
            handlers['ai_automation'] = self._handle_ai_automation
        return handlers
    
    def get_dependencies(self) -> List[str]:
        """Get list of Python package dependencies"""
        deps = []
        if self.openinterpreter_enabled:
            deps.append('open-interpreter')
        return deps
    
    def initialize(self) -> bool:
        """Initialize the integration"""
        try:
            if self.openinterpreter_enabled and not self.interpreter:
                self._setup_openinterpreter()
            
            self.logger.info("AI integration initialized")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize AI integration: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources"""
        self.logger.info("AI integration cleaned up")
    
    def _setup_openinterpreter(self):
        """Setup OpenInterpreter with configuration"""
        try:
            from interpreter import interpreter
            self.interpreter = interpreter
            
            # Configure API base
            api_base = self.settings.get('openinterpreter_llm_api_base', 
                                       config.config.get("openinterpreter_llm_api_base"))
            
            if api_base in ["groq", "openai"]:
                if api_base == "groq":
                    self.interpreter.llm.api_base = "https://api.groq.com/openai/v1"
                elif api_base == "openai":
                    self.interpreter.llm.api_base = "https://api.openai.com/v1/models"
            elif api_base:
                self.interpreter.llm.api_base = api_base
            
            # Configure verbose mode
            verbose_mode = self.settings.get('openinterpreter_verbose_mode_isenabled',
                                           config.config.get("openinterpreter_verbose_mode_isenabled", "true"))
            if verbose_mode == "true":
                self.interpreter.verbose = True
            elif verbose_mode == "false":
                self.interpreter.verbose = False
            else:
                self.logger.warning("Invalid verbose mode setting, defaulting to true")
                self.interpreter.verbose = True
            
            # Set other configuration
            self.interpreter.auto_run = self.settings.get('openinterpreter_auto_run_isenabled',
                                                        config.config.get("openinterpreter_auto_run_isenabled", False))
            self.interpreter.llm.api_key = self.settings.get('openinterpreter_llm_api_key',
                                                           config.config.get("openinterpreter_llm_api_key"))
            self.interpreter.llm.model = self.settings.get('openinterpreter_llm_model',
                                                         config.config.get("openinterpreter_llm_model"))
            self.interpreter.llm.temperature = self.settings.get('openinterpreter_llm_temperature',
                                                               config.config.get("openinterpreter_llm_temperature"))
            
            self.logger.info("OpenInterpreter configured successfully")
            
        except ImportError:
            self.logger.error("OpenInterpreter not installed. Install with: pip install open-interpreter")
            self.interpreter = None
        except Exception as e:
            self.logger.error(f"Failed to setup OpenInterpreter: {e}")
            self.interpreter = None
    
    def _handle_openinterpreter(self, task: str) -> str:
        """Handle OpenInterpreter tasks"""
        try:
            if not self.interpreter:
                return "OpenInterpreter not available. Please check configuration and dependencies."
            
            # Extract the actual task from the command
            parts = task.split(maxsplit=1)
            if len(parts) < 2:
                return "Invalid OpenInterpreter task format. Usage: openinterpreter <task>"
            
            ai_task = parts[1]
            
            # Execute the task
            self.logger.info(f"Executing OpenInterpreter task: {ai_task}")
            result = self.interpreter.chat(ai_task)
            
            # Format the result
            if isinstance(result, list):
                # Extract text responses from the result
                response_parts = []
                for item in result:
                    if isinstance(item, dict) and 'content' in item:
                        response_parts.append(str(item['content']))
                    else:
                        response_parts.append(str(item))
                response = "\n".join(response_parts)
            else:
                response = str(result)
            
            self.logger.info("OpenInterpreter task completed")
            return f"OpenInterpreter result: {response}"
            
        except Exception as e:
            self.logger.error(f"OpenInterpreter task error: {e}")
            return f"OpenInterpreter task failed: {str(e)}"
    
    def _handle_ai_automation(self, task: str) -> str:
        """Handle general AI automation tasks"""
        try:
            parts = task.split(maxsplit=1)
            if len(parts) < 2:
                return "Invalid AI automation task format. Usage: ai_automation <task>"
            
            automation_task = parts[1]
            
            # For now, delegate to OpenInterpreter if available
            if self.interpreter:
                return self._handle_openinterpreter(f"openinterpreter {automation_task}")
            else:
                # Could integrate with other AI services here
                return "AI automation not available. OpenInterpreter not configured."
            
        except Exception as e:
            self.logger.error(f"AI automation task error: {e}")
            return f"AI automation task failed: {str(e)}"


# Legacy function wrapper for backward compatibility
def openinterpretercall(task):
    """Legacy OpenInterpreter function"""
    try:
        from interpreter import interpreter
        
        # Configure interpreter (basic setup)
        if config.config.get("openinterpreter_llm_api_base") in ["groq", "openai"]:
            if config.config.get("openinterpreter_llm_api_base") == "groq":
                interpreter.llm.api_base = "https://api.groq.com/openai/v1"
            elif config.config.get("openinterpreter_llm_api_base") == "openai":
                interpreter.llm.api_base = "https://api.openai.com/v1/models"
        else:
            interpreter.llm.api_base = config.config.get("openinterpreter_llm_api_base")

        if config.config.get("openinterpreter_verbose_mode_isenabled") == "true":
            interpreter.verbose = True
        elif config.config.get("openinterpreter_verbose_mode_isenabled") == "false":
            interpreter.verbose = False
        else:
            logging.error("Invalid value for openinterpreter_verbose_mode_isenabled in config. Defaulting to true")
            interpreter.verbose = True

        # Set the rest of the OI values
        interpreter.auto_run = config.config.get("openinterpreter_auto_run_isenabled")
        interpreter.llm.api_key = config.config.get("openinterpreter_llm_api_key")
        interpreter.llm.model = config.config.get("openinterpreter_llm_model")
        interpreter.llm.temperature = config.config.get("openinterpreter_llm_temperature")

        # Run openinterpreter based on task from llm_parse.py
        interpreter.chat(task)
        
    except Exception as e:
        logging.error(f"OpenInterpreter error: {e}")
