# outputmanager.py

import logging
import asyncio
from pythonosc.udp_client import SimpleUDPClient
import threading
import time
import os
import pygame
import queue
import tempfile
import boto3  # Import boto3 for Amazon Polly
from .notificationmanager import TypingIndicator  # Updated import path

POLLY_NEURAL_MAP = {
    "Joanna-Neural": "Joanna",
    "Amy-Neural": "Amy",
    "Brian-Neural": "Brian",
    "Justin-Neural": "Justin",
    "Emma-Neural": "Emma",
    "Arthur-Neural": "Arthur"  # Add 'Arthur' for Polly Neural
}

class OutputManager:
    def __init__(self):
        self.typing_indicator = TypingIndicator()
        self.chatbox_ip = "127.0.0.1"
        self.chatbox_port = 9000
        self.client = None
        self.polly_client = None
        self.voice_engine = "Polly Standard"  # Match ENGINES key from UIManager
        self.voice = "Joanna"  # Set default voice
        self.language = "en-US"  # Initialize language
        pygame.mixer.init()
        self.is_playing = False
        self.tts_queue = queue.Queue()
        self.initialize_client()
        self.initialize_tts_engine()
        
    def setup(self, config):
        """Configure output manager with settings from config."""
        try:
            settings = config['Settings']
            self.chatbox_ip = settings.get('chatbox_ip', self.chatbox_ip)
            self.chatbox_port = int(settings.get('chatbox_port', self.chatbox_port))
            self.voice_engine = settings.get('voice_engine', self.voice_engine)
            self.voice = settings.get('voice')
            self.language = settings.get('language', self.language)  # Set language from config
            
            # Initialize clients
            self.client = SimpleUDPClient(self.chatbox_ip, self.chatbox_port)
            
            # Initialize TTS engine
            if self.voice_engine.startswith("polly"):
                logging.info("Initializing Amazon Polly")
                self.polly_client = boto3.client('polly', region_name='us-east-1')
            
            logging.info(f"Output manager configured with engine: {self.voice_engine}, language: {self.language}")
            return True
        except Exception as e:
            logging.error(f"Error setting up output manager: {e}")
            return False

    def initialize_tts_engine(self):
        """
        Initialize Amazon Polly based on the selected polly engine type.
        """
        try:
            self.polly_client = boto3.client('polly')  # Initialize Amazon Polly client
        except Exception as e:
            logging.error(f"Error initializing Amazon Polly: {e}")

    def update_settings(self, chatbox_ip, chatbox_port, voice_engine, voice):
        self.chatbox_ip = chatbox_ip
        self.chatbox_port = int(chatbox_port)  # Ensure port is integer
        self.client = SimpleUDPClient(self.chatbox_ip, self.chatbox_port)
        self.voice_engine = voice_engine
        self.voice = voice
        self.initialize_tts_engine()

    def initialize_client(self):
        """Initialize UDP client with current settings"""
        try:
            self.client = SimpleUDPClient(self.chatbox_ip, self.chatbox_port)
        except Exception as e:
            logging.error(f"Failed to initialize UDP client: {e}")
            self.client = None

    def speak_text(self, text):
        if not self.voice or not isinstance(self.voice, str):
            logging.error("Voice must be a valid string.")
            return
        self.tts_queue.put(text)
        if not self.is_playing:
            threading.Thread(target=self.tts_playback_loop, daemon=True).start()

    def tts_playback_loop(self):
        while not self.tts_queue.empty():
            text = self.tts_queue.get()
            # Handle all Polly variants
            if self.voice_engine.lower().startswith("polly"):
                self.generate_and_play_audio_polly(text)
            else:
                logging.error(f"Unknown voice engine: {self.voice_engine}")

    async def generate_and_play_audio_edge(self, text):
        # Remove or comment out this edge-tts method and references
        pass

    def generate_and_play_audio_polly(self, text):
        logging.info("Generating speech with Amazon Polly...")
        self.stop_audio()
        self.is_playing = True
        output_file = None
        try:
            if "generative" in self.voice_engine.lower():
                engine = "neural"
            elif "neural" in self.voice_engine.lower():
                engine = "neural"
            else:
                engine = "standard"
            logging.info(f"Speaking '{text}' using engine: {engine}, language: {self.language}, voice: {self.voice}")
            
            # Ensure the voice is compatible with the engine
            if engine == "standard":
                voice_id = self.voice  # Use voice as is for standard
            elif engine == "neural":
                voice_id = POLLY_NEURAL_MAP.get(self.voice, self.voice)
            else:
                voice_id = self.voice  # Fallback
            
            response = self.polly_client.synthesize_speech(
                Text=text,
                VoiceId=voice_id,
                OutputFormat='mp3',
                Engine=engine
            )
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tmp_file.write(response['AudioStream'].read())
                output_file = tmp_file.name
            logging.info("Playing Amazon Polly audio...")
            pygame.mixer.music.load(output_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            logging.info("Amazon Polly audio playback finished.")
        except Exception as e:
            logging.error(f"Error during Amazon Polly playback: {e}")
        finally:
            pygame.mixer.music.unload()
            self.is_playing = False
            # Clean up the temporary file
            if output_file and os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except Exception as e:
                    logging.error(f"Error deleting temporary audio file: {e}")

    def stop_audio(self):
        """Stops audio playback and clears the queue."""
        if self.is_playing:
            if self.voice_engine == "polly":
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()  # Unload the music to release the file
            self.is_playing = False
        
        # Clear the queue
        while not self.tts_queue.empty():
            try:
                self.tts_queue.get_nowait()
            except queue.Empty:
                break

    def send_to_chatbox(self, text):
        """Send text to chatbox with error handling"""
        try:
            if self.client is None:
                self.initialize_client()
            if self.client:
                self.client.send_message("/chatbox/input", [text, True])
            else:
                logging.error("Chatbox client not initialized")
        except Exception as e:
            logging.error(f"Error sending to chatbox: {e}")
