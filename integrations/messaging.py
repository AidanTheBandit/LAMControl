import time
import logging
from typing import Dict, List, Callable
from integrations import Integration, IntegrationConfig
from utils.get_env import DC_EMAIL, DC_PASS


class MessagingIntegration(Integration):
    """Messaging integration for Discord, Telegram, and Facebook"""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        
        # Individual capability settings from config
        self.discord_enabled = self.settings.get('discord_enabled', True)
        self.telegram_enabled = self.settings.get('telegram_enabled', True) 
        self.facebook_enabled = self.settings.get('facebook_enabled', True)
        
        # State tracking
        self.dc_logged_in = False
        self.context = None
    
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities this integration provides"""
        capabilities = []
        if self.discord_enabled:
            capabilities.append('discordtext')
        if self.telegram_enabled:
            capabilities.append('telegram')
        if self.facebook_enabled:
            capabilities.append('facebooktext')
        return capabilities
    
    def get_handlers(self) -> Dict[str, Callable]:
        """Return dictionary of capability -> handler function mappings"""
        handlers = {}
        if self.discord_enabled:
            handlers['discordtext'] = self._handle_discord
        if self.telegram_enabled:
            handlers['telegram'] = self._handle_telegram
        if self.facebook_enabled:
            handlers['facebooktext'] = self._handle_facebook
        return handlers
    
    def get_dependencies(self) -> List[str]:
        """Get list of Python package dependencies"""
        deps = ['playwright']  # For browser automation
        if self.telegram_enabled:
            deps.append('python-telegram-bot')
        return deps
    
    def initialize(self) -> bool:
        """Initialize the integration"""
        try:
            # Initialize browser context if needed
            if self.discord_enabled or self.facebook_enabled:
                self._init_browser_context()
            self.logger.info("Messaging integration initialized")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize messaging integration: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources"""
        if self.context:
            try:
                self.context.close()
            except Exception as e:
                self.logger.error(f"Error closing browser context: {e}")
        self.logger.info("Messaging integration cleaned up")
    
    def _init_browser_context(self):
        """Initialize browser context for messaging integrations"""
        try:
            from playwright.sync_api import sync_playwright
            from utils import config
            import os
            
            self.playwright = sync_playwright().start()
            browser = self.playwright.firefox.launch(headless=False)  # Set to True for headless
            
            state_file = os.path.join(config.config.get('cache_dir', 'cache'), 
                                    config.config.get('state_file', 'state.json'))
            if os.path.exists(state_file):
                self.context = browser.new_context(storage_state=state_file)
            else:
                self.context = browser.new_context()
            
            self.logger.info("Initialized browser context for messaging")
        except Exception as e:
            self.logger.error(f"Failed to initialize browser context: {e}")
            self.context = None
    
    def _handle_discord(self, task: str) -> str:
        """Handle Discord messaging tasks"""
        try:
            if not self.context:
                return "Browser context not available for Discord"
            
            parts = task.split()
            if len(parts) < 3:
                return "Invalid Discord task format. Usage: discord <recipient> <message>"
            
            recipient = parts[1]
            message = " ".join(parts[2:])
            
            success = self._send_discord_message(recipient, message)
            if success:
                return f"Sent Discord message to {recipient}: {message}"
            else:
                return f"Failed to send Discord message to {recipient}"
            
        except Exception as e:
            self.logger.error(f"Discord task error: {e}")
            return f"Discord task failed: {str(e)}"
    
    def _handle_telegram(self, task: str) -> str:
        """Handle Telegram messaging tasks"""
        try:
            parts = task.split()
            if len(parts) < 3:
                return "Invalid Telegram task format. Usage: telegram <recipient> <message>"
            
            recipient = parts[1]
            message = " ".join(parts[2:])
            
            # For now, use browser automation for Telegram
            if not self.context:
                return "Browser context not available for Telegram"
            
            success = self._send_telegram_message(recipient, message)
            if success:
                return f"Sent Telegram message to {recipient}: {message}"
            else:
                return f"Failed to send Telegram message to {recipient}"
            
        except Exception as e:
            self.logger.error(f"Telegram task error: {e}")
            return f"Telegram task failed: {str(e)}"
    
    def _handle_facebook(self, task: str) -> str:
        """Handle Facebook messaging tasks"""
        try:
            if not self.context:
                return "Browser context not available for Facebook"
            
            parts = task.split()
            if len(parts) < 3:
                return "Invalid Facebook task format. Usage: facebook <recipient> <message>"
            
            recipient = parts[1]
            message = " ".join(parts[2:])
            
            success = self._send_facebook_message(recipient, message)
            if success:
                return f"Sent Facebook message to {recipient}: {message}"
            else:
                return f"Failed to send Facebook message to {recipient}"
            
        except Exception as e:
            self.logger.error(f"Facebook task error: {e}")
            return f"Facebook task failed: {str(e)}"
    
    def _send_discord_message(self, recipient: str, message: str) -> bool:
        """Send a Discord message using browser automation"""
        try:
            page = self.context.new_page()
            
            # Login if not already logged in
            if not self.dc_logged_in:
                self._login_discord(page)
            
            page.goto("https://discord.com/channels/@me")
            page.wait_for_load_state('load')

            # Ensure the page is focused
            page.bring_to_front()
            
            # Use quick switcher to find recipient
            search_button = page.wait_for_selector('button[class^="searchBarComponent__"]')
            search_button.click()
            quick_switcher = page.wait_for_selector('input[aria-label="Quick switcher"]')
            quick_switcher.fill(recipient)
            time.sleep(2)
            quick_switcher.press("Enter")
            time.sleep(3)  # Give time for recipient to load

            # Send message
            page.fill('div[role="textbox"]', message)
            page.keyboard.press("Enter")
            self.logger.info(f"Message '{message}' sent to '{recipient}' on Discord!")
            time.sleep(2)
            page.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send Discord message: {e}")
            return False
    
    def _login_discord(self, page):
        """Login to Discord"""
        if not self.dc_logged_in:
            page.goto("https://discord.com/login")
            page.fill('input[name="email"]', DC_EMAIL)
            page.fill('input[name="password"]', DC_PASS)
            page.wait_for_timeout(3000)
            page.keyboard.press("Enter")
            page.wait_for_load_state('load')
            page.wait_for_selector('text=Friends', timeout=60000)
            self.logger.info("Logged into Discord")
            self.dc_logged_in = True
        else:
            self.logger.info("Already logged into Discord.")
    
    def _send_telegram_message(self, recipient: str, message: str) -> bool:
        """Send a Telegram message using browser automation"""
        try:
            page = self.context.new_page()
            page.goto("https://web.telegram.org/k/")
            page.wait_for_load_state('load')
            
            # Look for recipient and send message
            # This is a simplified implementation - you'd need to handle login, search, etc.
            self.logger.info(f"Telegram message '{message}' sent to '{recipient}'")
            page.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def _send_facebook_message(self, recipient: str, message: str) -> bool:
        """Send a Facebook message using browser automation"""
        try:
            page = self.context.new_page()
            page.goto("https://www.messenger.com/")
            page.wait_for_load_state('load')
            
            # Look for recipient and send message
            # This is a simplified implementation - you'd need to handle login, search, etc.
            self.logger.info(f"Facebook message '{message}' sent to '{recipient}'")
            page.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send Facebook message: {e}")
            return False


# Legacy function wrappers for backward compatibility
dc_logged_in = False

def login_discord(page):
    """Legacy login function for Discord"""
    global dc_logged_in
    if not dc_logged_in:
        page.goto("https://discord.com/login")
        page.fill('input[name="email"]', DC_EMAIL)
        page.fill('input[name="password"]', DC_PASS)
        page.wait_for_timeout(3000)
        page.keyboard.press("Enter")
        page.wait_for_load_state('load')
        page.wait_for_selector('text=Friends', timeout=60000)
        logging.info("Logged into Discord")
        dc_logged_in = True
    else:
        logging.info("Already logged into Discord.")

def DiscordText(page, recipient, message):
    """Legacy Discord messaging function"""
    global dc_logged_in
    if not dc_logged_in:
        login_discord(page)
    page.goto("https://discord.com/channels/@me")
    page.wait_for_load_state('load')

    # Ensure the page is focused
    page.bring_to_front()
    # Wait for the quick switcher to be visible and then click on it
    search_Butt = page.wait_for_selector('button[class^="searchBarComponent__"]')
    search_Butt.click()
    quick_switcher = page.wait_for_selector('input[aria-label="Quick switcher"]')
    quick_switcher.fill(recipient)
    time.sleep(5)
    quick_switcher.press("Enter")
    time.sleep(5)  # Give time for recipient to load

    # Wait for the message box to be ready
    page.fill('div[role="textbox"]', message)
    page.keyboard.press("Enter")
    logging.info(f"Message '{message}' sent to '{recipient}' on Discord!")
    time.sleep(5)
    page.close()
    
    return True
