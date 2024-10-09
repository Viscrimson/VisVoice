import logging
from pythonosc import udp_client
from managers.Settings_manager import SettingsManager

class TTCManager:
    def __init__(self):
        self.settings_manager = SettingsManager()
        # Get OSC settings
        self.ip = self.settings_manager.get_setting('OUTPUT', 'osc_ip')
        self.port = int(self.settings_manager.get_setting('OUTPUT', 'osc_port'))
        self.client = udp_client.SimpleUDPClient(self.ip, self.port)

        # Get text chunking settings
        self.characters_per_sync = int(self.settings_manager.get_setting('OUTPUT', 'characters_per_sync'))
        self.bytes_per_character = int(self.settings_manager.get_setting('OUTPUT', 'bytes_per_character'))

    def send_to_chatbox(self, text):
        """Sends text to the VRChat chatbox via OSC."""
        # Split text into chunks if necessary
        chunks = self.split_text(text)
        for chunk in chunks:
            # Send OSC message
            self.client.send_message('/chatbox/input', [chunk, True, False])
        print(f'Text sent to chatbox: {text}')

    def split_text(self, text):
        """Splits text into chunks based on characters per sync."""
        max_length = self.characters_per_sync
        return [text[i:i+max_length] for i in range(0, len(text), max_length)]

    def send_to_chatbox(self, text):
            """Sends text to the VRChat chatbox via OSC."""
            try:
                chunks = self.split_text(text)
                for chunk in chunks:
                    self.client.send_message('/chatbox/input', [chunk, True, False])
                print(f'Text sent to chatbox: {text}')
            except Exception as e:
                logging.error(f'Error sending text to chatbox: {e}')