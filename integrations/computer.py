import re
import time
import ctypes
import logging
import subprocess
import platform
from typing import Dict, List, Callable
from utils.helpers import log_disabled_integration
from utils.config import config
from integrations import Integration, IntegrationConfig


class ComputerIntegration(Integration):
    """Computer control integration for system operations"""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        
        # Individual capability settings from config
        self.volume_enabled = self.settings.get('volume_enabled', True)
        self.run_enabled = self.settings.get('run_enabled', True)
        self.media_enabled = self.settings.get('media_enabled', True)
        self.power_enabled = self.settings.get('power_enabled', True)
        
        # Platform detection
        self.is_mac = platform.system() == "Darwin"
        self.is_windows = platform.system() == "Windows"
        
        # Volume settings from config
        self.vol_up_step = self.settings.get('vol_up_step_value', 5)
        self.vol_down_step = self.settings.get('vol_down_step_value', 5)
    
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities this integration provides"""
        capabilities = []
        if self.volume_enabled:
            capabilities.append('computervolume')
        if self.run_enabled:
            capabilities.append('computerrun')
        if self.media_enabled:
            capabilities.append('computermedia')
        if self.power_enabled:
            capabilities.append('computerpower')
        return capabilities
    
    def get_handlers(self) -> Dict[str, Callable]:
        """Return dictionary of capability -> handler function mappings"""
        handlers = {}
        if self.volume_enabled:
            handlers['computervolume'] = self._handle_volume
        if self.run_enabled:
            handlers['computerrun'] = self._handle_run
        if self.media_enabled:
            handlers['computermedia'] = self._handle_media
        if self.power_enabled:
            handlers['computerpower'] = self._handle_power
        return handlers
    
    def initialize(self) -> bool:
        """Initialize the integration"""
        self.logger.info(f"Computer integration initialized on {platform.system()}")
        return True
    
    def cleanup(self):
        """Clean up resources"""
        self.logger.info("Computer integration cleaned up")
    
    def _handle_volume(self, task: str) -> str:
        """Handle volume control commands"""
        title_cleaned = re.sub(r'[^\w\s]', '', task).lower()
        words = title_cleaned.split()
        if len(words) < 3:
            return "Invalid volume command format. Usage: computer volume <mute|unmute|up|down|0-100>"

        volume_word = words[2]

        if self.is_mac:
            return self._handle_volume_mac(volume_word)
        elif self.is_windows:
            return self._handle_volume_windows(volume_word)
        else:
            return "Volume control not supported on this platform"
    
    def _handle_volume_mac(self, volume_word: str) -> str:
        """Handle volume control on macOS"""
        try:
            if volume_word == "mute":
                subprocess.run(["osascript", "-e", "set volume with output muted"])
                self.logger.info("Muted the volume")
                return "Volume muted"
            elif volume_word == "unmute":
                subprocess.run(["osascript", "-e", "set volume without output muted"])
                self.logger.info("Unmuted the volume")
                return "Volume unmuted"
            elif volume_word == "up":
                subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) + 10) --100%"])
                self.logger.info("Increased volume")
                return "Volume increased"
            elif volume_word == "down":
                subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) - 10) --100%"])
                self.logger.info("Decreased volume")
                return "Volume decreased"
            else:
                volume_value = int(volume_word)
                if volume_value < 0 or volume_value > 100:
                    raise ValueError("Volume must be between 0 and 100")
                subprocess.run(["osascript", "-e", f"set volume output volume {volume_value} --100%"])
                self.logger.info(f"Set volume to {volume_value}%")
                return f"Volume set to {volume_value}%"
        except ValueError as e:
            error_msg = f"Invalid volume value: {volume_word}. {str(e)}"
            self.logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Failed to control volume: {e}"
            self.logger.error(error_msg)
            return error_msg
    
    def _handle_volume_windows(self, volume_word: str) -> str:
        """Handle volume control on Windows"""
        try:
            if volume_word == "mute":
                ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
                self.logger.info("Muted the volume")
                return "Volume muted"
            elif volume_word == "unmute":
                ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
                self.logger.info("Unmuted the volume")
                return "Volume unmuted"
            elif volume_word == "up":
                for _ in range(self.vol_up_step):
                    ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)
                self.logger.info(f"Increased volume by {self.vol_up_step} steps")
                return f"Volume increased by {self.vol_up_step} steps"
            elif volume_word == "down":
                for _ in range(self.vol_down_step):
                    ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)
                self.logger.info(f"Decreased volume by {self.vol_down_step} steps")
                return f"Volume decreased by {self.vol_down_step} steps"
            else:
                volume_value = int(volume_word)
                if volume_value < 0 or volume_value > 100:
                    raise ValueError("Volume must be between 0 and 100")
                
                # Reset volume to 0 then set to desired level
                for _ in range(50):
                    ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)
                for _ in range(volume_value // 2):
                    ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)
                self.logger.info(f"Set volume to {volume_value}%")
                return f"Volume set to {volume_value}%"
        except ValueError as e:
            error_msg = f"Invalid volume value: {volume_word}. {str(e)}"
            self.logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Failed to control volume: {e}"
            self.logger.error(error_msg)
            return error_msg
    
    def _handle_run(self, task: str) -> str:
        """Handle application launch commands"""
        title_cleaned = re.sub(r'[^\w\s]', '', task).lower()
        words = title_cleaned.split()
        if len(words) < 3:
            return "Invalid run command format. Usage: computer run <application>"

        command = " ".join(words[2:])
        
        try:
            if self.is_mac:
                subprocess.run(['open', '-a', f'{command}'])
                subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke return'])
                self.logger.info(f"Executed command: {command}")
                return f"Launched application: {command}"
            else:
                # Press Windows key
                ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)
                time.sleep(0.1)
                ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)
                time.sleep(0.1)

                # Type the command
                for char in command:
                    vk = ctypes.windll.user32.VkKeyScanW(ord(char))
                    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
                    time.sleep(0.05)

                # Press Enter
                ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0)
                self.logger.info(f"Executed command: {command}")
                return f"Executed command: {command}"
        except Exception as e:
            error_msg = f"Failed to execute command: {e}"
            self.logger.error(error_msg)
            return error_msg
    
    def _handle_media(self, task: str) -> str:
        """Handle media control commands"""
        words = task.split()
        if len(words) < 3:
            return "Invalid media command format. Usage: computer media <next|back|play|pause>"

        action = words[2].lower()
        
        try:
            if self.is_mac:
                if action == "next":
                    subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 124 using {command down}'])
                    self.logger.info("Skipped to the next song")
                    return "Skipped to next track"
                elif action == "back":
                    subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 123 using {command down}'])
                    self.logger.info("Skipped to the previous song")
                    return "Skipped to previous track"
                elif action in ["play", "pause"]:
                    subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 49'])
                    self.logger.info("Play/Pause the current song")
                    return "Toggled play/pause"
                else:
                    return f"Invalid media action: {action}. Use next, back, play, or pause"
            else:
                if action == "next":
                    ctypes.windll.user32.keybd_event(0xB0, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0xB0, 0, 2, 0)
                    self.logger.info("Skipped to the next song")
                    return "Skipped to next track"
                elif action == "back":
                    ctypes.windll.user32.keybd_event(0xB1, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0xB1, 0, 2, 0)
                    self.logger.info("Skipped to the previous song")
                    return "Skipped to previous track"
                elif action in ["play", "pause"]:
                    ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0xB3, 0, 2, 0)
                    self.logger.info("Play/Pause the current song")
                    return "Toggled play/pause"
                else:
                    return f"Invalid media action: {action}. Use next, back, play, or pause"
        except Exception as e:
            error_msg = f"Failed to execute media command: {e}"
            self.logger.error(error_msg)
            return error_msg
    
    def _handle_power(self, task: str) -> str:
        """Handle power management commands"""
        words = task.split()
        if len(words) < 3:
            return "Invalid power command format. Usage: computer power <lock|sleep|restart|shutdown>"
        
        action = words[2].lower()
        self.logger.info(f"Power action identified: {action}")

        try:
            if self.is_mac:
                if action == "lock":
                    self.logger.info("Locking Mac...")
                    subprocess.run(['osascript', '-e', 'tell application "System Events" to keystroke "q" using {control down, command down}'])
                    return "Computer locked"
                elif action == "sleep":
                    self.logger.info("Putting Mac to sleep...")
                    subprocess.run(['osascript', '-e', 'tell application "System Events" to sleep'])
                    return "Computer put to sleep"
                elif action == "restart":
                    self.logger.info("Restarting Mac...")
                    subprocess.run(['osascript', '-e', 'tell application "System Events" to restart'])
                    return "Computer restarting"
                elif action == "shutdown":
                    self.logger.info("Shutting down Mac...")
                    subprocess.run(['osascript', '-e', 'tell application "System Events" to shut down'])
                    return "Computer shutting down"
                else:
                    return f"Invalid power action: {action}. Use lock, sleep, restart, or shutdown"
            else:
                if action == "lock":
                    self.logger.info("Locking computer...")
                    ctypes.windll.user32.LockWorkStation()
                    return "Computer locked"
                elif action == "sleep":
                    self.logger.info("Putting computer to sleep...")
                    self._windows_power_shortcut("u", "s")
                    return "Computer put to sleep"
                elif action == "restart":
                    self.logger.info("Restarting computer...")
                    self._windows_power_shortcut("u", "r")
                    return "Computer restarting"
                elif action == "shutdown":
                    self.logger.info("Shutting down computer...")
                    self._windows_power_shortcut("u", "u")
                    return "Computer shutting down"
                else:
                    return f"Invalid power action: {action}. Use lock, sleep, restart, or shutdown"
        except Exception as e:
            error_msg = f"Failed to execute power command: {e}"
            self.logger.error(error_msg)
            return error_msg
    
    def _windows_power_shortcut(self, first_key: str, second_key: str):
        """Helper method for Windows power shortcuts"""
        # Win+X menu
        ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)  # win key down
        ctypes.windll.user32.keybd_event(0x58, 0, 0, 0)  # x key down
        ctypes.windll.user32.keybd_event(0x58, 0, 2, 0)  # x key up
        ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)  # win key up
        time.sleep(0.3)
        
        # First key (u for shutdown options)
        key_code = ord(first_key.upper())
        ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(key_code, 0, 2, 0)
        time.sleep(0.3)
        
        # Second key (specific action)
        key_code = ord(second_key.upper())
        ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(key_code, 0, 2, 0)


# Legacy function wrappers for backward compatibility
def is_mac():
    return platform.system() == "Darwin"

def ComputerVolume(title):
    title_cleaned = re.sub(r'[^\w\s]', '', title).lower()
    words = title_cleaned.split()
    if len(words) < 3:
        logging.error(f"Invalid prompt format '{title_cleaned}' for Computer Volume command.")
        return

    volume_word = words[2]

    if is_mac():
        if volume_word == "mute":
            subprocess.run(["osascript", "-e", "set volume with output muted"])
            logging.info("Muted the volume")
        elif volume_word == "unmute":
            subprocess.run(["osascript", "-e", "set volume without output muted"])
            logging.info("Unmuted the volume")
        elif volume_word == "up":
            subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) + 10) --100%"])
            logging.info("Increased volume")
        elif volume_word == "down":
            subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) - 10) --100%"])
            logging.info("Decreased volume")
        else:
            try:
                volume_value = int(volume_word)
                if volume_value < 0 or volume_value > 100:
                    raise ValueError
                subprocess.run(["osascript", "-e", f"set volume output volume {volume_value} --100%"])
                logging.info(f"Set volume to {volume_value}%")
            except ValueError:
                logging.error(f"Invalid volume value: {volume_word}. Must be an integer between 0 and 100.")
    else:
        if volume_word == "mute":
            try:
                ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
                logging.info("Muted the volume")
            except Exception as e:
                logging.error(f"Failed to mute volume: {e}")
            return

        if volume_word == "unmute":
            try:
                ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
                logging.info("Unmuted the volume")
            except Exception as e:
                logging.error(f"Failed to unmute volume: {e}")
            return

        if volume_word == "up":
            try:
                for _ in range(config.config.get('vol_up_step_value', 5)):
                    ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)
                logging.info(f"Increased volume by {config.config.get('vol_up_step_value', 5)} steps")
            except Exception as e:
                logging.error(f"Failed to increase volume: {e}")
            return

        if volume_word == "down":
            try:
                for _ in range(config.config.get('vol_down_step_value', 5)):
                    ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)
                logging.info(f"Decreased volume by {config.config.get('vol_down_step_value', 5)} steps")
            except Exception as e:
                logging.error(f"Failed to decrease volume: {e}")
            return

        try:
            volume_value = int(volume_word)
            if volume_value < 0 or volume_value > 100:
                raise ValueError
        except ValueError:
            logging.error(f"Invalid volume value: {volume_word}. Must be an integer between 0 and 100.")
            return

        try:
            for _ in range(50):
                ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)
            for _ in range(volume_value // 2):
                ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)
            logging.info(f"Set volume to {volume_value}%")
        except Exception as e:
            logging.error(f"Failed to set volume: {e}")

computerrun_isenabled = True

def ComputerRun(title):
    title_cleaned = re.sub(r'[^\w\s]', '', title).lower()
    words = title_cleaned.split()
    if len(words) < 3:
        logging.error("Invalid prompt format for Computer Run command.")
        return

    command = " ".join(words[2:])
    if is_mac():
        try:
            subprocess.run(['open', '-a', f'{command}'])
            subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke return'])
            logging.info(f"Executed command: {command}")
        except Exception as e:
            logging.error(f"Failed to execute command: {e}")
    else:
        try:
            # Press Windows key
            ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)
            time.sleep(0.1)
            ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)
            time.sleep(0.1)

            # Type the command
            for char in command:
                vk = ctypes.windll.user32.VkKeyScanW(ord(char))
                ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
                ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
                time.sleep(0.05)

            # Press Enter
            ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0)
            logging.info(f"Executed command: {command}")
        except Exception as e:
            logging.error(f"Failed to execute command: {e}")

computermedia_isenabled = True

def ComputerMedia(title):
    words = title.split()
    if len(words) < 3:
        logging.error("Invalid prompt format for Computer Media command.")
        return

    action = words[2]

    if is_mac():
        try:
            if action == "next":
                subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 124 using {command down}'])
                logging.info("Skipped to the next song")
            elif action == "back":
                subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 123 using {command down}'])
                logging.info("Skipped to the previous song")
            elif action == "play" or action == "pause":
                subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 49'])
                logging.info("Play/Pause the current song")
            else:
                logging.error("Invalid prompt format for Computer Media command.")
        except Exception as e:
            logging.error(f"Failed to execute media command: {e}")
    else:
        try:
            if action == "next":
                ctypes.windll.user32.keybd_event(0xB0, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0xB0, 0, 2, 0)  # key up event
                logging.info("Skipped to the next song")
            elif action == "back":
                ctypes.windll.user32.keybd_event(0xB1, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0xB1, 0, 2, 0)  # key up event
                logging.info("Skipped to the previous song")
            elif action == "play" or action == "pause":
                ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0xB3, 0, 2, 0)  # key up event
                logging.info("Play/Pause the current song")
            else:
                logging.error("Invalid prompt format for Computer Media command.")
        except Exception as e:
            logging.error(f"Failed to execute media command: {e}")

def ComputerPower(title):
    words = title.split()
    if len(words) < 3:
        logging.error("Invalid prompt format for Computer Power command.")
        return
    
    action = words[2].lower()
    logging.info(f"Action identified: {action}")

    if is_mac():
        try:
            if action == "lock":
                logging.info("Locking Mac...")
                subprocess.run(['osascript', '-e', 'tell application "System Events" to keystroke "q" using {control down, command down}'])

            elif action == "sleep":
                logging.info("Putting Mac to sleep...")
                subprocess.run(['osascript', '-e', 'tell application "System Events" to sleep'])

            elif action == "restart":
                logging.info("Restarting Mac...")
                subprocess.run(['osascript', '-e', 'tell application "System Events" to restart'])

            elif action == "shutdown":
                logging.info("Shutting down Mac...")
                subprocess.run(['osascript', '-e', 'tell application "System Events" to shut down'])
            else:
                logging.error(f"Unknown action: {action}")
        except Exception as e:
            logging.error(f"Failed to execute Mac command: {e}")

    else:
        try:
            if action == "lock":
                logging.info("Locking computer...")
                ctypes.windll.user32.LockWorkStation()

            elif action == "sleep":
                logging.info("Putting computer to sleep...")
                ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)  # win key down
                ctypes.windll.user32.keybd_event(0x58, 0, 0, 0)  # x key down
                ctypes.windll.user32.keybd_event(0x58, 0, 2, 0)  # x key up
                ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)  # win key up
                time.sleep(0.3)
                ctypes.windll.user32.keybd_event(0x55, 0, 0, 0)  # u key down
                ctypes.windll.user32.keybd_event(0x55, 0, 2, 0)  # u key up
                time.sleep(0.3)
                ctypes.windll.user32.keybd_event(0x53, 0, 0, 0)  # s key down
                ctypes.windll.user32.keybd_event(0x53, 0, 2, 0)  # s key up

            elif action == "restart":
                logging.info("Restarting computer...")
                ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)  # win key down
                ctypes.windll.user32.keybd_event(0x58, 0, 0, 0)  # x key down
                ctypes.windll.user32.keybd_event(0x58, 0, 2, 0)  # x key up
                ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)  # win key up
                ctypes.windll.user32.keybd_event(0x55, 0, 0, 0)  # u key down
                ctypes.windll.user32.keybd_event(0x55, 0, 2, 0)  # u key up
                ctypes.windll.user32.keybd_event(0x52, 0, 0, 0)  # r key down
                ctypes.windll.user32.keybd_event(0x52, 0, 2, 0)  # r key up

            elif action == "shutdown":
                logging.info("Shutting down computer...")
                ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)  # win key down
                ctypes.windll.user32.keybd_event(0x58, 0, 0, 0)  # x key down
                ctypes.windll.user32.keybd_event(0x58, 0, 2, 0)  # x key up
                ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)  # win key up
                ctypes.windll.user32.keybd_event(0x55, 0, 0, 0)  # u key down
                ctypes.windll.user32.keybd_event(0x55, 0, 2, 0)  # u key up
                ctypes.windll.user32.keybd_event(0x55, 0, 0, 0)  # u key down
                ctypes.windll.user32.keybd_event(0x55, 0, 2, 0)  # u key up

            else:
                logging.error(f"Unknown action: {action}")

        except Exception as e:
            logging.error(f"Failed to execute Windows command: {e}")