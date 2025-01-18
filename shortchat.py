# shortchat.py
import time
import keyboard
import webbrowser
import pyperclip
import json
from urllib.parse import quote
import os
import sys
import subprocess
from pathlib import Path
import logging
import tempfile
from mistralai import Mistral

# Set up logging
def setup_logging():
    log_dir = os.path.expanduser('~/Library/Logs/ShortChat')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'ShortChat.log')
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )
    return log_path

def check_accessibility_permissions():
    """Check if the app has accessibility permissions on macOS"""
    if sys.platform != "darwin":
        return True
        
    try:
        # Try to simulate a key press
        keyboard.send('shift')
        return True
    except Exception as e:
        logging.error(f"Accessibility permissions error: {e}")
        return False

def prompt_accessibility_permissions():
    """Show dialog to prompt for accessibility permissions"""
    script = '''
    tell application "System Preferences"
        activate
        set current pane to pane "com.apple.preference.security"
        reveal anchor "Privacy_Accessibility" of pane "com.apple.preference.security"
    end tell
    '''
    subprocess.run(['osascript', '-e', script])

class ShortChat:
    def __init__(self):
        self.shortcuts = self.load_shortcuts()
        self.last_key_time = 0
        # Read Mistral configuration
        mistral_config_path = os.path.expanduser('~/.mistral_key')
        if os.path.exists(mistral_config_path):
            with open(mistral_config_path, 'r') as f:
                mistral_key = f.read().strip()  # Added strip() to remove any whitespace
            logging.info(f"Loaded Mistral config from: {mistral_config_path}")
            logging.info(f"Mistral key: {mistral_key}")
        else:
            mistral_key = None
            logging.warning(f"Mistral config not found at: {mistral_config_path}")

        self.mistral_client = Mistral(api_key=mistral_key)
        self.model_id="mistral-large-latest"
        logging.info("ShortChat initialized")
        
    def load_shortcuts(self):
        """Load shortcuts from configuration file"""
        config_path = os.path.expanduser('~/Library/Application Support/ShortChat/config.json')
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        logging.info(f"Loading config from: {config_path}")
        
        if not os.path.exists(config_path):
            # Using function keys as default shortcuts
            default_shortcuts = {
                "f1": "Make this text more diplomatic:\n{selection}",
                "f2": "Debug this code:\n{selection}",
                "f3": "Correct the spelling mistakes:\n{selection}",
            }

            with open(config_path, 'w') as f:
                json.dump(default_shortcuts, f, indent=4)
            logging.info("Created default config file with function keys")
            shortcuts = default_shortcuts
            
        try:
            with open(config_path, 'r') as f:
                shortcuts = json.load(f)
            logging.info("Loaded existing config file")
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            return {}
        
        complement = "\Do not add any other word than the strict minimum asked, so it can be pasted as is."
        for key,value in default_shortcuts.items():
            shortcuts[key] = value + complement
        
        return shortcuts

    def get_selected_text(self):
        """Get text currently selected in the active application"""
        try:
            old_clipboard = pyperclip.paste()
            
            keyboard.send('command+c' if sys.platform == "darwin" else 'ctrl+c')
            time.sleep(0.2)
            
            selection = pyperclip.paste()
            pyperclip.copy(old_clipboard)
            
            if selection:
                logging.debug("Successfully got selected text")
            else:
                logging.debug("No text selected")
                
            return selection.strip()
        except Exception as e:
            logging.error(f"Error getting selected text: {e}")
            return ""

    def paste_text_at_cursor(self, text):
        """Paste text at the current cursor position"""
        try:
            # Save current clipboard content
            old_clipboard = pyperclip.paste()
            
            # Copy new text to clipboard
            pyperclip.copy(text)
            time.sleep(0.1)  # Small delay to ensure clipboard is updated
            
            # Paste at cursor position
            keyboard.send('command+v' if sys.platform == "darwin" else 'ctrl+v')
            time.sleep(0.1)  # Small delay to ensure paste is completed
            
            # Restore original clipboard content
            pyperclip.copy(old_clipboard)
            
            logging.debug("Successfully pasted text at cursor")
        except Exception as e:
            logging.error(f"Error pasting text at cursor: {e}")
            # Attempt to restore clipboard even if paste failed
            pyperclip.copy(old_clipboard)

    def open_chatgpt_with_prompt(self, prompt_template):
        """Get LLM response and paste it at cursor position"""
        # Debounce to prevent double triggers
        current_time = time.time()
        if current_time - self.last_key_time < 0.5:  # 500ms debounce
            return
        self.last_key_time = current_time
        
        selection = self.get_selected_text()
        if not selection:
            logging.warning("No text selected!")
            return
            
        prompt = prompt_template.format(selection=selection)
        
        try:
            chat_response = self.mistral_client.chat.complete(
                model=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            text_answer = chat_response.choices[0].message.content
            logging.info("Received response from Mistral API")
            
            # Paste the response at cursor position
            self.paste_text_at_cursor(text_answer)
            
        except Exception as e:
            logging.error(f"Error getting or pasting Mistral response: {e}")
            error_message = "Error: Failed to get AI response. Check logs for details."
            self.paste_text_at_cursor(error_message)

    def handle_shortcut(self, event):
        """Handle keyboard event"""
        key_name = event.name.lower()
        logging.debug(f"Key pressed: {key_name}")
        
        if key_name in self.shortcuts:
            logging.info(f"Shortcut triggered: {key_name}")
            self.open_chatgpt_with_prompt(self.shortcuts[key_name])

    def register_shortcuts(self):
        """Register all keyboard shortcuts"""
        try:
            # Remove any existing hooks
            keyboard.unhook_all()
            
            # Register for raw key events
            keyboard.on_press(self.handle_shortcut)
            
            for shortcut in self.shortcuts.keys():
                logging.info(f"Monitoring for shortcut: {shortcut}")
            
        except Exception as e:
            logging.error(f"Error registering shortcuts: {e}")
            raise

    def run(self):
        """Start the application"""
        try:
            print("ShortChat is running...")
            logging.info("Application started")
            
            if sys.platform == "darwin" and not check_accessibility_permissions():
                print("\nAccessibility permissions required!")
                print("Please grant accessibility permissions to ShortChat in System Preferences.")
                prompt_accessibility_permissions()
                print("\nAfter granting permissions, please restart the application.")
                return
            
            print("\nRegistered shortcuts:")
            for shortcut, prompt in self.shortcuts.items():
                print(f"  {shortcut}: {prompt}")
            print("\nPress Ctrl+C to exit")
            
            self.register_shortcuts()
            keyboard.wait()
            
        except KeyboardInterrupt:
            logging.info("Application shutdown requested")
            print("\nShutting down ShortChat...")
        except Exception as e:
            logging.error(f"Error running application: {e}")
            raise

def main():
    log_path = setup_logging()
    
    try:
        logging.info("Starting ShortChat application")
        app = ShortChat()
        app.run()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        print(f"\nAn error occurred. Check the logs at: {log_path}")
        print(f"Error: {e}")
        
        if sys.platform == "darwin":
            print("\nIf you're seeing permission errors, please:")
            print("1. Open System Preferences")
            print("2. Go to Security & Privacy -> Privacy -> Accessibility")
            print("3. Click the lock to make changes")
            print("4. Add ShortChat to the allowed applications")
        
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()