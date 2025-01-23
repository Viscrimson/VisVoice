# inputmanager.py

import warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import logging
import whisper  # This imports the correct 'whisper' module from 'openai-whisper'
import sounddevice as sd
import numpy as np
import torch
import webrtcvad
import collections
import sys
import os
from tqdm.utils import DisableOnWindows
from tqdm import tqdm

class InputManager:
    def __init__(self):
        self.logger = logging.getLogger('VisVoice.InputManager')
        self.logger.info("Initializing InputManager...")
        
        # Set device first
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.logger.info(f"Using device: {self.device}")
        
        try:
            # Initialize VAD first as it's simpler
            self.vad = webrtcvad.Vad(2)
            self.logger.info("VAD initialized")
            
            # Create cache directory in appdata
            cache_dir = os.path.join(os.getenv('APPDATA'), 'VisVoice', 'cache')
            os.makedirs(cache_dir, exist_ok=True)
            self.logger.info(f"Cache directory: {cache_dir}")
            
            # Disable progress bar and load model
            os.environ["PYTHONIOENCODING"] = "utf-8"
            tqdm._instances.clear()
            
            self.logger.info("Loading Whisper model (this may take a while)...")
            with DisableOnWindows():
                self.model = whisper.load_model(
                    "base",
                    device=self.device,
                    in_memory=True  # Try to keep model in memory
                )
            self.logger.info("Whisper model loaded successfully")
            
        except Exception as e:
            self.logger.error("Failed to initialize", exc_info=True)
            raise

        self.stream = None

    def get_voice_input(self):
        logging.debug("Starting voice input capture...")
        logging.info("Listening for voice input with VAD...")
        sample_rate = 16000
        frame_duration = 30  # ms
        num_padding_frames = 10
        threshold = 0.9  # Ratio of voiced frames needed

        ring_buffer = collections.deque(maxlen=num_padding_frames)
        triggered = False
        voiced_frames = []

        try:
            # Log audio device info
            device_info = sd.query_devices(sd.default.device[0])
            logging.debug("Using input device: %s", device_info)
            
            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype='int16',
                device=sd.default.device[0],  # Explicitly use default input device
                latency='low'
            ) as stream:
                while True:
                    data, overflowed = stream.read(int(sample_rate * frame_duration / 1000))
                    if overflowed:
                        logging.warning("Audio buffer overflowed")
                    
                    is_speech = self.vad.is_speech(data.tobytes(), sample_rate)
                    logging.debug("VAD result: %s", is_speech)
                    if not triggered:
                        ring_buffer.append((data.tobytes(), is_speech))
                        num_voiced = len([f for f, speech in ring_buffer if speech])
                        logging.debug("Number of voiced frames: %d", num_voiced)
                        if num_voiced > threshold * num_padding_frames:
                            triggered = True
                            voiced_frames.extend([f for f, s in ring_buffer])
                            ring_buffer.clear()
                            logging.debug("Voice activity detected, starting recording")
                    else:
                        voiced_frames.append(data.tobytes())
                        ring_buffer.append((data.tobytes(), is_speech))
                        num_unvoiced = len([f for f, speech in ring_buffer if not speech])
                        logging.debug("Number of unvoiced frames: %d", num_unvoiced)
                        if num_unvoiced > threshold * num_padding_frames:
                            logging.debug("End of speech detected")
                            break  # End of speech
                    if len(voiced_frames) > sample_rate * 10:  # Limit recording to 10 seconds
                        logging.info("Max recording duration reached.")
                        break

        except Exception as e:
            logging.error("Error during voice input: %s", e, exc_info=True)
            return None

        if not voiced_frames:
            logging.info("No speech detected.")
            return None

        audio_data = b''.join(voiced_frames)
        audio_array = np.frombuffer(audio_data, dtype='int16').astype(np.float32) / 32768.0

        logging.info("Transcribing voice input...")
        try:
            result = self.model.transcribe(audio_array, fp16=torch.cuda.is_available())
            text = result["text"].strip()
            logging.info(f"Transcribed text: {text}")
            return text
        except Exception as e:
            logging.error(f"Error during transcription: {e}")
            return None
