from pythonosc import udp_client
import time
import logging
import threading

class TypingIndicator:
    def __init__(self, ip="127.0.0.1", port=9000):
        self.client = udp_client.SimpleUDPClient(ip, port)
        self.is_typing = False
        self.typing_thread = None

    def _animate_typing(self):
        """Animates typing indicator dots while is_typing is True"""
        try:
            while self.is_typing:
                # Send typing indicator message in correct format
                self.client.send_message("/chatbox/input", ["", True, True])
                self.client.send_message("/chatbox/typing", [True])
                time.sleep(0.1)
            # Clear typing indicator when done
            self.client.send_message("/chatbox/typing", [False])
            self.client.send_message("/chatbox/input", ["", True, False])
        except Exception as e:
            logging.error(f"Error in typing animation: {e}")
            self.stop_typing()

    def start_typing(self):
        """Starts the typing indicator animation"""
        if not self.is_typing:
            self.is_typing = True
            # Send immediate typing state with correct format
            self.client.send_message("/chatbox/typing", [True])
            self.client.send_message("/chatbox/input", ["", True, True])
            logging.debug("Starting typing indicator")
            self.typing_thread = threading.Thread(target=self._animate_typing, daemon=True)
            self.typing_thread.start()

    def stop_typing(self):
        """Stops the typing indicator animation"""
        self.is_typing = False
        if self.typing_thread and self.typing_thread.is_alive():
            self.typing_thread.join(timeout=1.0)
        # Clear typing indicator with correct format
        self.client.send_message("/chatbox/typing", [False])
        self.client.send_message("/chatbox/input", ["", True, False])
        logging.debug("Stopped typing indicator")

    def update_client(self, ip, port):
        """Updates the OSC client with new IP and port"""
        try:
            self.client = udp_client.SimpleUDPClient(ip, port)
            logging.info(f"Typing indicator client updated to {ip}:{port}")
            return True
        except Exception as e:
            logging.error(f"Error updating typing indicator client: {e}")
            return False
