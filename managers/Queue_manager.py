import queue
import threading
import os
from managers.Approval_manager import ApprovalManager
from managers.TTC_manager import TTCManager

class QueueManager:
    def __init__(self):
        self.input_queue = queue.Queue()
        self.processing = False
        self.approval_manager = ApprovalManager(self)
        self.ttc_manager = TTCManager()

    def add_to_queue(self, item_data):
        """Adds a new item to the input queue."""
        self.input_queue.put(item_data)
        if not self.processing:
            self.process_next_item()

    def process_next_item(self):
        """Processes the next item in the queue."""
        if not self.input_queue.empty():
            self.processing = True
            item_data = self.input_queue.get()
            threading.Thread(target=self.handle_item, args=(item_data,)).start()
        else:
            self.processing = False

    def handle_item(self, item_data):
        """Handles the processing of an item."""
        text, temp_file_path = item_data
        # Approval process
        approved = self.approval_manager.request_approval(text)
        if approved:
            print(f'Approved item: {text}')
            self.ttc_manager.send_to_chatbox(text)
            # If using TTS, call TTSManager here
        else:
            print(f'Rejected item: {text}')
        # Cleanup and proceed to next item
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        self.process_next_item()
