import pyttsx3
from threading import Thread
from managers.Settings_manager import SettingsManager

class TTSManager:
    def __init__(self):
        self.settings_manager = SettingsManager()
        self.engine = pyttsx3.init()
        self.configure_engine()

    def configure_engine(self):
        """Configures the TTS engine based on settings."""
        # Voice selection
        tts_voice = self.settings_manager.get_setting('OUTPUT', 'tts_voice')
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if tts_voice.lower() in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break
        else:
            print(f"Voice '{tts_voice}' not found. Using default voice.")

        # Speech rate
        speech_rate = int(self.settings_manager.get_setting('OUTPUT', 'speech_rate'))
        self.engine.setProperty('rate', speech_rate)

        # Volume
        volume = float(self.settings_manager.get_setting('OUTPUT', 'volume'))
        self.engine.setProperty('volume', volume)

    def generate_speech(self, text):
        """Generates speech from text asynchronously."""
        Thread(target=self._speak, args=(text,)).start()

    def _speak(self, text):
        """Performs the speech synthesis."""
        self.engine.say(text)
        self.engine.runAndWait()
