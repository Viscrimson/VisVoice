# outputmanager.py

import logging
import asyncio
from pythonosc.udp_client import SimpleUDPClient
import edge_tts
import pygame
import queue
import tempfile
import threading
import os
import boto3  # Add AWS SDK for Python (Boto3)

class OutputManager:
    def __init__(self, chatbox_ip="127.0.0.1", chatbox_port=9000, voice_engine="edge-tts", voice=None):
        self.chatbox_ip = chatbox_ip
        self.chatbox_port = chatbox_port
        self.client = SimpleUDPClient(self.chatbox_ip, self.chatbox_port)
        self.voice_engine = voice_engine
        self.voice = voice
        self.tts_queue = queue.Queue()
        pygame.mixer.init()
        self.is_playing = False
        self.initialize_tts_engine()

    def initialize_tts_engine(self):
        if self.voice_engine == "edge-tts":
            # Edge TTS initialization if needed
            pass
        elif self.voice_engine == "aws-polly":
            try:
                # Initialize AWS Polly client
                self.polly_client = boto3.client('polly')
                # Test the connection
                self.polly_client.describe_voices()
            except Exception as e:
                logging.error(f"Failed to initialize AWS Polly: {e}")
                # Fallback to edge-tts
                self.voice_engine = "edge-tts"
                logging.info("Falling back to edge-tts")
        else:
            logging.error(f"Unknown voice engine: {self.voice_engine}")

    def update_settings(self, chatbox_ip, chatbox_port, voice_engine, voice):
        old_engine = self.voice_engine
        self.chatbox_ip = chatbox_ip
        self.chatbox_port = int(chatbox_port)
        self.client = SimpleUDPClient(self.chatbox_ip, self.chatbox_port)
        self.voice_engine = voice_engine
        self.voice = voice
        
        # Re-initialize pygame mixer with new device
        pygame.mixer.quit()
        pygame.mixer.init()
        
        if old_engine != self.voice_engine:
            self.initialize_tts_engine()

    def speak_text(self, text):
        self.tts_queue.put(text)
        if not self.is_playing:
            threading.Thread(target=self.tts_playback_loop, daemon=True).start()

    def tts_playback_loop(self):
        while not self.tts_queue.empty():
            text = self.tts_queue.get()
            if self.voice_engine == "edge-tts":
                asyncio.run(self.generate_and_play_audio_edge(text))
            elif self.voice_engine == "aws-polly":
                self.generate_and_play_audio_polly(text)
            else:
                logging.error(f"Unknown voice engine: {self.voice_engine}")

    def generate_and_play_audio_polly(self, text):
        """Generates and plays audio using AWS Polly."""
        logging.info("Generating speech with AWS Polly...")
        output_file = None
        try:
            response = self.polly_client.synthesize_speech(
                Text=text,
                OutputFormat='mp3',
                VoiceId=self.voice
            )
            # Save the audio stream to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                output_file = tmp_file.name
                tmp_file.write(response['AudioStream'].read())
            # Play the audio
            self.play_audio_file(output_file)
        except Exception as e:
            logging.error(f"Error during AWS Polly playback: {e}")
        finally:
            # Clean up temporary file
            if output_file and os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except Exception as e:
                    logging.error(f"Error deleting temporary audio file: {e}")

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

    def play_audio_file(self, filepath):
        """Plays an audio file using pygame."""
        try:
            self.stop_audio()
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play()
            self.is_playing = True
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
            self.is_playing = False
        except Exception as e:
            logging.error(f"Error playing audio file: {e}")

    def stop_audio(self):
        """Stops audio playback."""
        if self.is_playing:
            pygame.mixer.music.stop()
            self.is_playing = False

    def send_to_chatbox(self, text):
        logging.info(f"Sending to chatbox: {text}")
        self.client.send_message("/chatbox/input", [text, True])
