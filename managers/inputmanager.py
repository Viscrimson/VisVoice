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
import time  # Add missing import
from typing import Optional

class InputManager:
    def __init__(self):
        try:
            logging.info("Loading Whisper model...")
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            # Use a smaller model to reduce memory usage
            self.model = whisper.load_model("tiny", device=self.device)
            logging.info(f"Whisper model loaded on {self.device}.")
            
            # Fix VAD initialization with proper frame duration
            self.vad = webrtcvad.Vad(2)  # Aggressiveness level 2
            self.sample_rate = 16000
            self.frame_duration = 30  # milliseconds
            self.frame_size = int(self.sample_rate * self.frame_duration / 1000)
            self.is_listening = False
            self.language = "en-US"  # Initialize language

            # Remove attempt to set sd.default.hostapi
            hostapis = sd.query_hostapis()
            wasapi_index = None
            for i, h in enumerate(hostapis):
                if "WASAPI" in h["name"].upper():
                    wasapi_index = i
                    break

            if wasapi_index is not None:
                devices = sd.query_devices()
                wasapi_input_devices = [
                    idx for idx, dev in enumerate(devices)
                    if dev["hostapi"] == wasapi_index and dev["max_input_channels"] > 0
                ]
                wasapi_output_devices = [
                    idx for idx, dev in enumerate(devices)
                    if dev["hostapi"] == wasapi_index and dev["max_output_channels"] > 0
                ]
                if wasapi_input_devices and wasapi_output_devices:
                    sd.default.device = (wasapi_input_devices[0], wasapi_output_devices[0])
        except Exception as e:
            logging.error(f"Failed to initialize InputManager: {e}")
            raise

    def test_components(self) -> dict:
        """Test each component and return status"""
        status = {
            "whisper_model": False,
            "vad": False,
            "audio_input": False
        }
        
        # Test Whisper
        try:
            test_audio = np.zeros((16000,), dtype=np.float32)
            self.model.transcribe(test_audio)
            status["whisper_model"] = True
        except Exception as e:
            logging.error(f"Whisper test failed: {e}")

        # Test VAD with proper frame size
        try:
            test_frame = b'\x00' * self.frame_size * 2  # 16-bit audio
            self.vad.is_speech(test_frame, self.sample_rate)
            status["vad"] = True
        except Exception as e:
            logging.error(f"VAD test failed: {e}")

        # Test audio input
        try:
            devices = sd.query_devices()
            if sd.default.device[0] is not None:
                status["audio_input"] = True
        except Exception as e:
            logging.error(f"Audio input test failed: {e}")

        return status

    def transcribe_audio(self, audio_data: np.ndarray) -> Optional[str]:
        """
        Transcribe a short audio segment using Whisper model.
        Returns the recognized text or None if empty.
        """
        try:
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            # Convert region-specific English to plain 'en'
            actual_lang = "en" if self.language.lower().startswith("en-") else self.language
            result = self.model.transcribe(audio_data, language=actual_lang, fp16=torch.cuda.is_available())
            text = result.get("text", "").strip()
            return text if text else None
        except Exception as e:
            logging.error(f"Error in transcription: {e}")
            return None

    def get_voice_input(self) -> Optional[str]:
        """
        Capture audio from the default input device in short chunks, 
        transcribe them, and return recognized text if any.
        """
        if self.is_listening:
            return None
        self.is_listening = True
        audio_buffer = []
        is_recording = False
        recognized_text = None

        def audio_callback(indata, frames, time_info, status):
            nonlocal audio_buffer, is_recording, recognized_text
            if status:
                logging.warning(f"Audio status: {status}")
                return

            try:
                # Simple VAD decision on each chunk
                chunk_bytes = indata.flatten().tobytes()
                speech_detected = self.vad.is_speech(chunk_bytes[:self.frame_size * 2], self.sample_rate)
                if speech_detected:
                    is_recording = True
                    audio_buffer.append(indata.copy())

                # If we accumulate ~1 second of audio, transcribe
                if is_recording and len(audio_buffer) >= int(1000 / self.frame_duration):
                    audio_data = np.concatenate(audio_buffer)
                    recognized_text = self.transcribe_audio(audio_data)
                    audio_buffer.clear()
                    is_recording = False
                    self.is_listening = False
            except Exception as e:
                logging.error(f"Error in audio callback: {e}")

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='int16',
            blocksize=self.frame_size,
            callback=audio_callback
        ):
            while self.is_listening:
                time.sleep(0.1)

        return recognized_text

input_manager = InputManager()
status = input_manager.test_components()
print("Component Status:", status)

# Add to debug voice input
test_audio = np.zeros((16000,), dtype=np.float32)  # 1 second of silence
result = input_manager.transcribe_audio(test_audio)
print("Test transcription result:", result)

# Add to UIManager where voice input is processed
def on_voice_input_received(self, text):
    print("Voice input received:", text)  # Debug print
    if text:
        self.text_var.set(text)  # Verify this updates UI
