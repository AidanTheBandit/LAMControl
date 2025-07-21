import logging
import urllib.parse
import webbrowser
import subprocess
import platform
from typing import Dict, List, Callable
from integrations import Integration, IntegrationConfig

# Integration Metadata
INTEGRATION_METADATA = {
    "name": "browser",
    "version": "1.2.0",
    "author": "LAMControl Team",
    "description": "Browser automation and web search integration",
    "category": "web",
    "tags": ["browser", "web", "search", "automation"],
    "min_python_version": "3.8",
    "conflicts_with": [],
    "provides_capabilities": ["browsersite", "browsergoogle", "browseryoutube", "browsergmail", "browseramazon"]
}

# Feature Configurations
FEATURE_CONFIGS = {
    "site_browsing": {
        "name": "site_browsing",
        "enabled": True,
        "required": False,
        "description": "Open arbitrary websites in the default browser",
        "dependencies": [],
        "settings": {
            "default_browser": "system_default",
            "open_in_new_tab": True,
            "validate_urls": True
        }
    },
    "google_search": {
        "name": "google_search", 
        "enabled": True,
        "required": False,
        "description": "Search Google and open results in browser",
        "dependencies": [],
        "settings": {
            "search_domain": "google.com",
            "safe_search": "moderate",
            "result_limit": 10
        }
    },
    "youtube_search": {
        "name": "youtube_search",
        "enabled": True,
        "required": False,
        "description": "Search YouTube videos and open results",
        "dependencies": [],
        "settings": {
            "quality_preference": "auto",
            "restrict_mode": False,
            "search_type": "video"
        }
    },
    "gmail_integration": {
        "name": "gmail_integration",
        "enabled": True,
        "required": False,
        "description": "Search Gmail and open webmail interface",
        "dependencies": [],
        "settings": {
            "auto_login": False,
            "default_account": 0,
            "search_scope": "all"
        }
    },
    "amazon_search": {
        "name": "amazon_search",
        "enabled": True,
        "required": False,
        "description": "Search Amazon products and open results",
        "dependencies": [],
        "settings": {
            "preferred_domain": "amazon.com",
            "department_filter": "all",
            "price_range": "any"
        }
    }
}


class BrowserIntegration(Integration):
    """Browser automation integration"""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        
        # Individual capability settings from config
        self.site_enabled = self.settings.get('site_enabled', True)
        self.google_enabled = self.settings.get('google_enabled', True)
        self.youtube_enabled = self.settings.get('youtube_enabled', True)
        self.gmail_enabled = self.settings.get('gmail_enabled', True)
        self.amazon_enabled = self.settings.get('amazon_enabled', True)
    
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities this integration provides"""
        capabilities = []
        if self.site_enabled:
            capabilities.append('browsersite')
        if self.google_enabled:
            capabilities.append('browsergoogle')
        if self.youtube_enabled:
            capabilities.append('browseryoutube')
        if self.gmail_enabled:
            capabilities.append('browsergmail')
        if self.amazon_enabled:
            capabilities.append('browseramazon')
        return capabilities
    
    def get_handlers(self) -> Dict[str, Callable]:
        """Return dictionary of capability -> handler function mappings"""
        handlers = {}
        if self.site_enabled:
            handlers['browsersite'] = self._handle_site
        if self.google_enabled:
            handlers['browsergoogle'] = self._handle_google
        if self.youtube_enabled:
            handlers['browseryoutube'] = self._handle_youtube
        if self.gmail_enabled:
            handlers['browsergmail'] = self._handle_gmail
        if self.amazon_enabled:
            handlers['browseramazon'] = self._handle_amazon
        return handlers
    
    def initialize(self) -> bool:
        """Initialize the integration"""
        self.logger.info("Browser integration initialized")
        return True
    
    def cleanup(self):
        """Clean up resources"""
        self.logger.info("Browser integration cleaned up")
    
    def _open_url(self, url: str, description: str = ""):
        """Helper method to open URLs across platforms"""
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', '-a', 'Safari', url])
            else:  # Windows or other OS
                webbrowser.open(url)
            self.logger.info(f"Opened {description or url}")
        except Exception as e:
            self.logger.error(f"Failed to open {description or url}: {e}")
            raise
    
    def _handle_site(self, task: str) -> str:
        """Handle opening websites directly"""
        parts = task.split()
        if len(parts) < 3:
            return "Invalid site command format. Usage: browser site <url>"
        
        url = " ".join(parts[2:])
        self._open_url(url, f"website: {url}")
        return f"Opened website: {url}"
    
    def _handle_google(self, task: str) -> str:
        """Handle Google searches"""
        parts = task.split()
        if len(parts) < 3:
            return "Invalid Google search format. Usage: browser google <search terms>"
        
        query = " ".join(parts[2:])
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded_query}"
        self._open_url(url, f"Google search for: {query}")
        return f"Searched Google for: {query}"
    
    def _handle_youtube(self, task: str) -> str:
        """Handle YouTube searches"""
        parts = task.split()
        if len(parts) < 3:
            return "Invalid YouTube search format. Usage: browser youtube <search terms>"
        
        query = " ".join(parts[2:])
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        self._open_url(url, f"YouTube search for: {query}")
        return f"Searched YouTube for: {query}"
    
    def _handle_gmail(self, task: str) -> str:
        """Handle Gmail searches"""
        parts = task.split()
        if len(parts) < 3:
            return "Invalid Gmail search format. Usage: browser gmail <search terms>"
        
        query = " ".join(parts[2:])
        encoded_query = urllib.parse.quote(query)
        url = f"https://mail.google.com/mail/u/0/#search/{encoded_query}"
        self._open_url(url, f"Gmail search for: {query}")
        return f"Searched Gmail for: {query}"
    
    def _handle_amazon(self, task: str) -> str:
        """Handle Amazon searches"""
        parts = task.split()
        if len(parts) < 3:
            return "Invalid Amazon search format. Usage: browser amazon <search terms>"
        
        query = " ".join(parts[2:])
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.amazon.com/s?k={encoded_query}"
        self._open_url(url, f"Amazon search for: {query}")
        return f"Searched Amazon for: {query}"


# Legacy function wrappers for backward compatibility
def BrowserSite(title):
    """Legacy wrapper for browser site functionality"""
    try:
        if platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', '-a', 'Safari', title])
        else:  # Windows or other OS
            webbrowser.open(title)
        logging.info(f"Opened website: {title}")
    except Exception as e:
        logging.error(f"Failed to open website: {e}")

def BrowserGoogle(title):
    """Legacy wrapper for browser google functionality"""
    encoded_query = urllib.parse.quote(title)
    url = f"https://www.google.com/search?q={encoded_query}"
    try:
        if platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', '-a', 'Safari', url])
        else:  # Windows or other OS
            webbrowser.open(url)
        logging.info(f"Opened Google search for query: {title}")
    except Exception as e:
        logging.error(f"Failed to open Google search: {e}")

def BrowserYoutube(title):
    """Legacy wrapper for browser youtube functionality"""
    encoded_query = urllib.parse.quote(title)
    url = f"https://www.youtube.com/results?search_query={encoded_query}"
    try:
        if platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', '-a', 'Safari', url])
        else:  # Windows or other OS
            webbrowser.open(url)
        logging.info(f"Opened YouTube search for query: {title}")
    except Exception as e:
        logging.error(f"Failed to open YouTube search: {e}")

def BrowserGmail(title):
    """Legacy wrapper for browser gmail functionality"""
    encoded_query = urllib.parse.quote(title)
    url = f"https://mail.google.com/mail/u/0/#search/{encoded_query}"
    try:
        if platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', '-a', 'Safari', url])
        else:  # Windows or other OS
            webbrowser.open(url)
        logging.info(f"Opened Gmail search for query: {title}")
    except Exception as e:
        logging.error(f"Failed to open Gmail search: {e}")

def BrowserAmazon(title):
    """Legacy wrapper for browser amazon functionality"""
    encoded_query = urllib.parse.quote(title)
    url = f"https://www.amazon.com/s?k={encoded_query}"
    try:
        if platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', '-a', 'Safari', url])
        else:  # Windows or other OS
            webbrowser.open(url)
        logging.info(f"Opened Amazon search for query: {title}")
    except Exception as e:
        logging.error(f"Failed to open Amazon search: {e}")
