import configparser
import os

class SettingsManager:
    def __init__(self, config_file='settings.ini'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_settings()

    def ensure_defaults(self):
        """Ensures that all sections and options have default values."""
        defaults = {
            'INPUT': {
                'stt_enabled': 'False',
                # Add other INPUT defaults...
            },
            'OUTPUT': {
                'output_type': 'TTC and TTS',
                # Add other OUTPUT defaults...
            },
            # Add other sections...
        }
        for section, options in defaults.items():
            if not self.config.has_section(section):
                self.config.add_section(section)
            for option, value in options.items():
                if not self.config.has_option(section, option):
                    self.config.set(section, option, value)
        self.save_settings()

    def load_settings(self):
        """Loads settings from the config file or sets defaults if the file doesn't exist."""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
            self.ensure_defaults()  # Add this line
        else:
            self.set_defaults()
            self.save_settings()

    def set_defaults(self):
        """Sets default configuration settings."""
        self.config['INPUT'] = {
            'stt_enabled': 'False',  # 'True' or 'False'
            'audio_input_device': 'Default',
            'voice_activation': 'False',  # 'True' or 'False'
            'stt_language': 'English',
            'transcription_model': 'Base',  # Placeholder for available models
        }

        self.config['OUTPUT'] = {
            'output_type': 'TTC and TTS',  # Options: 'TTC Only', 'TTS Only', 'TTC and TTS'
            'audio_output_device': 'Default',
            'automatic_approval': 'False',
            'auto_approve_delay': '2',  # In seconds
            'tts_language': 'English',
            'tts_voice': 'Default',
            'characters_per_sync': '70',
            'bytes_per_character': '1',  # '1' or '2'
        }

        self.config['HOTKEYS'] = {
            'ttt_hotkey': 'F1',
            'approve_hotkey': 'F2',
            'reject_hotkey': 'F3',
        }

        self.config['ADVANCED'] = {
            'process_priority': 'Normal',  # Options: 'Low', 'Below Normal', 'Normal', 'Above Normal', 'High'
            'gpu_index': '0',
            'minimum_silence': '500',  # In milliseconds
            'maximum_speech_duration': '30',  # In seconds
            'use_cpu': 'False',
            'use_flash_attention': 'False',
            'profanity_filter': 'True',
        }

        self.config['UI'] = {
            'text_box_rows': '3',
            'text_box_columns': '50',
            'opacity': '80',  # Default to 80%
        }

        self.config['GENERAL'] = {
            'visvoice_enabled': 'True',
        }

    def save_settings(self):
        """Saves the current settings to the config file."""
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def get_setting(self, section, option):
        """Retrieves a specific setting."""
        return self.config.get(section, option)

    def set_setting(self, section, option, value):
        """Updates a specific setting and saves it."""
        self.config.set(section, option, value)
        self.save_settings()

    def set_defaults(self):
        """Sets default configuration settings."""
        self.config['OUTPUT'] = {
            'output_type': 'TTC and TTS',
            'audio_output_device': 'Default',
            'automatic_approval': 'False',
            'auto_approve_delay': '2',
            'tts_language': 'English',
            'tts_voice': 'Default',
            'characters_per_sync': '70',
            'bytes_per_character': '1',
            'osc_ip': '127.0.0.1',     
            'osc_port': '9000',      
        }

