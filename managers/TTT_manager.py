import os
import time

class TTTManager:
    def __init__(self, queue_manager):
        self.queue_manager = queue_manager
        self.temp_dir = 'temp'
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    def submit_text(self, text):
        """Handles the submission of typed text and saves it temporarily."""
        if text.strip():
            # Save text to a temporary file
            timestamp = int(time.time() * 1000)
            temp_file_path = os.path.join(self.temp_dir, f'typed_{timestamp}.txt')
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write(text)

            # Send text and temp file path to QueueManager
            self.queue_manager.add_to_queue((text, temp_file_path))
            print(f'Text submitted: {text}')
        else:
            print('No text entered.')
