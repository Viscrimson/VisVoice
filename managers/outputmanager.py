# outputmanager.py

import logging
import asyncio
from pythonosc.udp_client import SimpleUDPClient
import pyttsx3
import edge_tts
import threading
import time
import os
import pygame
import queue
import tempfile

class OutputManager:
    def __init__(self, chatbox_ip="127.0.0.1", chatbox_port=9000, voice_engine="pyttsx3", voice=None):
        self.chatbox_ip = chatbox_ip
        self.chatbox_port = chatbox_port
        self.client = SimpleUDPClient(self.chatbox_ip, self.chatbox_port)
        self.voice_engine = voice_engine
        self.voice = voice
        self.tts_engine = None
        self.edge_voice = voice
        pygame.mixer.init()
        self.is_playing = False
        self.tts_queue = queue.Queue()
        self.initialize_tts_engine()

    def initialize_tts_engine(self):
        if self.voice_engine == "pyttsx3":
            self.tts_engine = pyttsx3.init()
            if self.voice:
                self.tts_engine.setProperty('voice', self.voice)
            else:
                # Set default voice
                voices = self.tts_engine.getProperty('voices')
                if voices:
                    self.tts_engine.setProperty('voice', voices[0].id)
        elif self.voice_engine == "edge-tts":
            # Edge TTS doesn't require initialization here
            pass

    def update_settings(self, chatbox_ip, chatbox_port, voice_engine, voice):
        self.chatbox_ip = chatbox_ip
        self.chatbox_port = int(chatbox_port)
        self.client = SimpleUDPClient(self.chatbox_ip, self.chatbox_port)
        self.voice_engine = voice_engine
        self.voice = voice
        self.initialize_tts_engine()

    def speak_text(self, text):
        self.tts_queue.put(text)
        if not self.is_playing:
            threading.Thread(target=self.tts_playback_loop, daemon=True).start()

    def tts_playback_loop(self):
        while not self.tts_queue.empty():
            text = self.tts_queue.get()
            if self.voice_engine == "pyttsx3":
                self.generate_and_play_audio_pyttsx3(text)
            elif self.voice_engine == "edge-tts":
                asyncio.run(self.generate_and_play_audio_edge(text))
            else:
                logging.error(f"Unknown voice engine: {self.voice_engine}")

    def generate_and_play_audio_pyttsx3(self, text):
        logging.info("Generating speech with pyttsx3...")
        self.stop_audio()
        self.is_playing = True
        self.tts_engine.connect('finished-utterance', self.on_tts_finished)
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()
        logging.info("pyttsx3 TTS audio playback finished.")

    def on_tts_finished(self, name, completed):
        self.is_playing = False
        self.tts_engine.disconnect('finished-utterance', self.on_tts_finished)

    async def generate_and_play_audio_edge(self, text):
        logging.info("Generating speech with Edge TTS...")
        # Generate a unique temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            output_file = tmp_file.name

        try:
            communicate = edge_tts.Communicate(text, voice=self.voice)
            await communicate.save(output_file)
            logging.info("Playing Edge TTS audio...")
            self.stop_audio()  # Stop any existing playback
            pygame.mixer.music.load(output_file)
            pygame.mixer.music.play()
            self.is_playing = True
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
            logging.info("Edge TTS audio playback finished.")
        except Exception as e:
            logging.error(f"Error during Edge TTS playback: {e}")
        finally:
            # Ensure the audio file is unloaded before deletion
            pygame.mixer.music.unload()
            self.is_playing = False
            # Clean up the temporary file
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except Exception as e:
                    logging.error(f"Error deleting temporary audio file: {e}")

    def stop_audio(self):
        """Stops audio playback."""
        if self.is_playing:
            if self.voice_engine == "pyttsx3":
                self.tts_engine.stop()
                self.is_playing = False
            elif self.voice_engine == "edge-tts":
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()  # Unload the music to release the file
                self.is_playing = False

    def send_to_chatbox(self, text):
        logging.info(f"Sending to chatbox: {text}")
        self.client.send_message("/chatbox/input", [text, True])
