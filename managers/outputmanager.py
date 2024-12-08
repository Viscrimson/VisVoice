# outputmanager.py

import logging
import asyncio
from pythonosc.udp_client import SimpleUDPClient
import edge_tts
import threading
import time
import os
import pygame
import queue
import tempfile
import boto3  # Import boto3 for Amazon Polly

class OutputManager:
    def __init__(self, chatbox_ip="127.0.0.1", chatbox_port=9000, voice_engine="edge-tts", voice=None):
        self.chatbox_ip = chatbox_ip
        self.chatbox_port = chatbox_port
        self.client = SimpleUDPClient(self.chatbox_ip, self.chatbox_port)
        self.polly_client = None
        self.voice_engine = voice_engine
        self.voice = voice
        pygame.mixer.init()
        self.is_playing = False
        self.tts_queue = queue.Queue()
        self.initialize_tts_engine()

    def initialize_tts_engine(self):
        if self.voice_engine == "edge-tts":
            pass  # Edge TTS doesn't require initialization here
        elif self.voice_engine == "polly":
            self.polly_client = boto3.client('polly')  # Initialize Amazon Polly client

    def update_settings(self, chatbox_ip, chatbox_port, voice_engine, voice):
        self.chatbox_ip = chatbox_ip
        self.chatbox_port = int(chatbox_port)  # Ensure port is integer
        self.client = SimpleUDPClient(self.chatbox_ip, self.chatbox_port)
        self.voice_engine = voice_engine
        self.voice = voice
        self.initialize_tts_engine()

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
            if self.voice_engine == "edge-tts":
                asyncio.run(self.generate_and_play_audio_edge(text))
            elif self.voice_engine == "polly":
                self.generate_and_play_audio_polly(text)
            else:
                logging.error(f"Unknown voice engine: {self.voice_engine}")

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

    def generate_and_play_audio_polly(self, text):
        logging.info("Generating speech with Amazon Polly...")
        self.stop_audio()
        self.is_playing = True
        try:
            response = self.polly_client.synthesize_speech(
                Text=text,
                VoiceId=self.voice,
                OutputFormat='mp3'
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
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except Exception as e:
                    logging.error(f"Error deleting temporary audio file: {e}")

    def stop_audio(self):
        """Stops audio playback."""
        if self.is_playing:
            if self.voice_engine == "edge-tts":
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()  # Unload the music to release the file
                self.is_playing = False
            elif self.voice_engine == "polly":
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()  # Unload the music to release the file
                self.is_playing = False

    def send_to_chatbox(self, text):
        logging.info(f"Sending to chatbox: {text}")
        self.client.send_message("/chatbox/input", [text, True])
