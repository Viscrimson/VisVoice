# visvoice.py

import logging
import configparser
from managers.uimanager import UIManager
from managers.inputmanager import InputManager
from managers.outputmanager import OutputManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class VisVoice:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        try:
            # Load configuration
            self.config = configparser.ConfigParser()
            if not self.config.read('config.ini'):
                self.logger.warning("Config file not found, using defaults")
                self.config['Settings'] = {
                    'voice_engine': 'Polly Standard',
                    'language': 'en-US',
                    'voice': 'Joanna',
                    'chatbox_ip': '127.0.0.1',
                    'chatbox_port': '9000'
                }
            
            # Initialize managers
            self.input_manager = InputManager()
            self.output_manager = OutputManager()
            
            # Setup output manager with correct engine
            voice_engine = self.config['Settings'].get('voice_engine', 'Polly Standard')
            voice = self.config['Settings'].get('voice', 'Joanna')
            chatbox_ip = self.config['Settings'].get('chatbox_ip', '127.0.0.1')
            chatbox_port = self.config['Settings'].get('chatbox_port', '9000')
            
            self.output_manager.update_settings(chatbox_ip, chatbox_port, voice_engine, voice)
            
            if not self.output_manager.setup(self.config):
                raise RuntimeError("Failed to setup output manager")
            
            # Setup UI
            self.ui_manager = UIManager()
            self.ui_manager.run()
            
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            raise

def main():
    try:
        app = VisVoice()
    except Exception as e:
        logging.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    main()
