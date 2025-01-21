# visvoice.py

import threading
import time
import logging
import sys

from managers.uimanager import UIManager
from managers.inputmanager import InputManager
from managers.outputmanager import OutputManager

class ApplicationController:
    def __init__(self):
        try:
            # Initialize logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
            
            # Initialize UIManager first to load settings
            self.ui_manager = UIManager(controller=self)

            # Initialize InputManager and OutputManager with settings from UIManager
            self.input_manager = InputManager()
            self.output_manager = OutputManager(
                chatbox_ip=self.ui_manager.chatbox_ip,
                chatbox_port=self.ui_manager.chatbox_port,
                voice_engine=self.ui_manager.voice_engine,
                voice=self.ui_manager.voice
            )

            self.running = True
            self.voice_capture_active = False
            self.is_typing = False

            # For handling long texts
            self.max_chatbox_length = 144

            # Start the voice input loop in a separate thread
            threading.Thread(target=self.voice_input_loop, daemon=True).start()
        
        except Exception as e:
            logging.critical(f"Failed to initialize application: {e}")
            sys.exit(1)

    def voice_input_loop(self):
        """Continuously listens for voice input if activated."""
        while self.running:
            if self.voice_capture_active and not self.is_typing:
                text = self.input_manager.get_voice_input()
                if text:
                    # Insert transcribed text into the textbox via UIManager
                    self.ui_manager.insert_text(text + ' ')
                    logging.info(f'Transcribed text inserted into textbox: {text}')
            else:
                # If voice capture is not active or user is typing, sleep briefly
                time.sleep(0.1)

    def process_text(self, text):
        """Processes the text: splits if necessary, outputs via TTS and chatbox."""
        # Split text into chunks
        chunks = self.split_text(text, self.max_chatbox_length)
        # Start processing chunks in a separate thread
        threading.Thread(target=self.output_chunks, args=(chunks,), daemon=True).start()

    def split_text(self, text, max_length):
        """Splits text into chunks not exceeding max_length characters."""
        import re

        sentence_endings = re.compile(r'(?<=[.!?])\s+')
        sentences = sentence_endings.split(text)

        chunks = []
        current_chunk = ''

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= max_length:
                current_chunk += (' ' + sentence) if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                if len(sentence) <= max_length:
                    current_chunk = sentence
                else:
                    # Split long sentence into smaller chunks
                    words = sentence.split()
                    current_sentence_chunk = ''
                    for word in words:
                        if len(current_sentence_chunk) + len(word) + 1 <= max_length:
                            current_sentence_chunk += (' ' + word) if current_sentence_chunk else word
                        else:
                            chunks.append(current_sentence_chunk.strip())
                            current_sentence_chunk = word
                    if current_sentence_chunk:
                        current_chunk = current_sentence_chunk
                    else:
                        current_chunk = ''
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

    def output_chunks(self, chunks):
        """Outputs text chunks via TTS and sends to chatbox."""
        for chunk in chunks:
            # Output via TTS if enabled
            if self.ui_manager.output_options.get('Voice Output', False):
                self.output_manager.speak_text(chunk)
            # Send to chatbox if enabled
            if self.ui_manager.output_options.get('Chatbox Output', False):
                self.output_manager.send_to_chatbox(chunk)
            # Wait before processing next chunk
            time.sleep(10)

    def toggle_voice_capture(self):
        """Toggles the voice capture on and off."""
        self.voice_capture_active = not self.voice_capture_active
        self.ui_manager.update_voice_capture_button(self.voice_capture_active)
        if self.voice_capture_active:
            logging.info('Voice capture started.')
        else:
            logging.info('Voice capture stopped.')

    def stop_audio(self):
        """Stops audio playback."""
        self.output_manager.stop_audio()

    def set_typing(self, is_typing):
        """Sets the typing status."""
        self.is_typing = is_typing

    def on_closing(self):
        """Handles actions when the window is closed."""
        try:
            self.running = False
            self.stop_audio()
            # Ensure all threads are stopped
            for thread in threading.enumerate():
                if thread != threading.main_thread():
                    thread.join(timeout=1.0)
            sys.exit(0)
        except Exception as e:
            logging.error(f"Error during shutdown: {e}")
            sys.exit(1)

    def run(self):
        """Runs the main application."""
        self.ui_manager.run()
        self.running = False
        self.output_manager.stop_audio()

def main():
    app_controller = ApplicationController()
    app_controller.run()

if __name__ == "__main__":
    main()
