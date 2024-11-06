# inputmanager.py

import warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import logging
import whisper
import sounddevice as sd
import numpy as np
import torch

class InputManager:
    def __init__(self):
        logging.info("Loading Whisper model...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = whisper.load_model("base", device=self.device)
        logging.info(f"Whisper model loaded on {self.device}.")

    def get_voice_input(self):
        logging.info("Listening for voice input...")
        duration = 5  # Duration in seconds for recording
        sample_rate = 16000
        try:
            recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="float32")
            sd.wait()  # Wait until recording is finished
            audio = np.squeeze(recording)

            logging.info("Transcribing voice input...")
            result = self.model.transcribe(audio, fp16=torch.cuda.is_available())
            text = result["text"].strip()
            logging.info(f"Transcribed text: {text}")
            return text
        except Exception as e:
            logging.error(f"Error during voice input transcription: {e}")
            return None
