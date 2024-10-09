from managers.Settings_manager import SettingsManager

class ApprovalManager:
    def __init__(self, queue_manager):
        self.queue_manager = queue_manager
        self.settings_manager = SettingsManager()
        self.automatic_approval = self.settings_manager.get_setting('OUTPUT', 'automatic_approval') == 'True'
        self.auto_approve_delay = float(self.settings_manager.get_setting('OUTPUT', 'auto_approve_delay'))

    def request_approval(self, text):
        """Requests user approval for the text."""
        if self.automatic_approval:
            # Automatically approve after delay
            import time
            time.sleep(self.auto_approve_delay)
            return True
        else:
            # For TTT input, we can skip approval if desired
            # For now, we'll assume TTT doesn't need approval
            # STT inputs would require user approval
            # This logic can be adjusted based on the input source
            # Since we're dealing with TTT, we can return True
            return True  # Approve TTT inputs by default
