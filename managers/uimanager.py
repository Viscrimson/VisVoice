# uimanager.py

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import logging
import re
from spellchecker import SpellChecker
from .inputmanager import InputManager
from .outputmanager import OutputManager
import sounddevice as sd
import asyncio
import sys
import configparser

# Import keyboard for global hotkey functionality
import keyboard

class UIManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Vis Voice")

        self.input_manager = InputManager()
        self.output_manager = OutputManager()

        # Initialize settings
        self.input_device = None
        self.output_device = None
        self.chatbox_ip = '127.0.0.1'
        self.chatbox_port = 9000
        self.voice_engine = 'pyttsx3'
        self.voice = None
        self.engine = None
        self.language = 'en-US'  # Default language
        self.hotkey = '`'  # Default hotkey

        # Output options
        self.output_options = {'Voice Output': True, 'Chatbox Output': True}

        # Flag to control the main loop
        self.running = True  # Ensure this is initialized before starting threads
        self.voice_capture_active = False  # To control voice capture
        self.is_typing = False  # Flag to detect typing

        self.load_settings()
        self.create_widgets()
        self.spellchecker = SpellChecker()

        # For handling long texts
        self.max_chatbox_length = 144

        # Start the voice input loop thread
        threading.Thread(target=self.voice_input_loop, daemon=True).start()

        # Set up hotkey listener
        self.setup_hotkey_listener()

        # Bind events to detect typing
        self.root.bind_all('<KeyPress>', self.on_key_press)
        self.root.bind_all('<KeyRelease>', self.on_key_release)

    def load_settings(self):
        """Loads settings from settings.ini or sets defaults."""
        config = configparser.ConfigParser()
        config.read('settings.ini')

        if 'Settings' in config:
            settings = config['Settings']
            self.input_device = settings.get('input_device', self.get_default_input_device())
            self.output_device = settings.get('output_device', self.get_default_output_device())
            self.chatbox_ip = settings.get('chatbox_ip', '127.0.0.1')
            self.chatbox_port = settings.getint('chatbox_port', 9000)
            self.voice_engine = settings.get('voice_engine', 'pyttsx3')
            self.voice = settings.get('voice', None)
            self.language = settings.get('language', 'en-US')
            self.hotkey = settings.get('hotkey', '`')

            # Output options
            self.output_options['Voice Output'] = settings.getboolean('voice_output', True)
            self.output_options['Chatbox Output'] = settings.getboolean('chatbox_output', True)
        else:
            # Set defaults
            self.input_device = self.get_default_input_device()
            self.output_device = self.get_default_output_device()

    def save_settings_to_file(self):
        """Saves settings to settings.ini."""
        config = configparser.ConfigParser()
        config['Settings'] = {
            'input_device': self.input_device,
            'output_device': self.output_device,
            'chatbox_ip': self.chatbox_ip,
            'chatbox_port': str(self.chatbox_port),
            'voice_engine': self.voice_engine,
            'voice': self.voice or '',
            'language': self.language,
            'hotkey': self.hotkey,
            'voice_output': str(self.output_options['Voice Output']),
            'chatbox_output': str(self.output_options['Chatbox Output']),
        }
        with open('settings.ini', 'w') as configfile:
            config.write(configfile)

    def get_default_input_device(self):
        """Gets the default input device."""
        sd.default.device = sd.default.device
        index = sd.default.device[0]
        device_info = sd.query_devices(index)
        return f"{device_info['name']} ({index})"

    def get_default_output_device(self):
        """Gets the default output device."""
        sd.default.device = sd.default.device
        index = sd.default.device[1]
        device_info = sd.query_devices(index)
        return f"{device_info['name']} ({index})"

    def create_widgets(self):
        """Creates the main UI."""
        # Display section at the top
        display_frame = ttk.Frame(self.root)
        display_frame.pack(side='top', fill='x', padx=10, pady=5)

        # Use labels to display settings in a structured way
        settings_label = ttk.Label(display_frame, text="Current Settings:", font=('Arial', 10, 'bold'))
        settings_label.pack(side='top', anchor='w')

        self.current_settings_label = ttk.Label(display_frame, text=self.get_current_settings_text(), justify='left')
        self.current_settings_label.pack(side='left', anchor='w')

        settings_button = ttk.Button(display_frame, text='Settings', command=self.show_settings)
        settings_button.pack(side='right')

        # Separator
        separator = ttk.Separator(self.root, orient='horizontal')
        separator.pack(fill='x', padx=10, pady=5)

        # Textbox for typing and STT output
        text_frame = ttk.Frame(self.root)
        text_frame.pack(expand=True, fill='both', padx=10, pady=5)

        self.textbox = tk.Text(text_frame, wrap='word', height=10, width=80)
        self.textbox.pack(side='left', expand=True, fill='both')
        self.textbox.bind('<KeyRelease>', self.check_spelling)
        self.textbox.bind('<Button-3>', self.show_suggestions)
        self.textbox.bind('<Return>', self.submit_text)
        # Add vertical scrollbar
        scrollbar = ttk.Scrollbar(text_frame, command=self.textbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.textbox.config(yscrollcommand=scrollbar.set)

        # Buttons at the bottom
        button_frame = ttk.Frame(self.root)
        button_frame.pack(side='bottom', fill='x', pady=10)
        # Center the buttons
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        button_frame.columnconfigure(3, weight=1)

        cancel_button = ttk.Button(button_frame, text='Cancel', command=self.cancel_text)
        cancel_button.grid(row=0, column=0, sticky='e')

        send_button = ttk.Button(button_frame, text='Send', command=self.submit_text)
        send_button.grid(row=0, column=1)

        # Toggle Voice Capture Button
        self.toggle_voice_button = ttk.Button(button_frame, text='Start Voice Capture', command=self.toggle_voice_capture)
        self.toggle_voice_button.grid(row=0, column=2, sticky='w')

        # Stop Audio Button
        stop_audio_button = ttk.Button(button_frame, text='Stop Audio', command=self.stop_audio)
        stop_audio_button.grid(row=0, column=3, sticky='w')

    def get_current_settings_text(self):
        """Returns a string representing the current important settings."""
        output_methods = ', '.join([key for key, value in self.output_options.items() if value])
        settings_text = (
            f"Input Device: {self.input_device}\n"
            f"Output Device: {self.output_device}\n"
            f"Voice Engine: {self.voice_engine}\n"
            f"Voice: {self.voice}\n"  # Added voice name
            f"Language: {self.language}\n"
            f"Hotkey: {self.hotkey}\n"
            f"Output Methods: {output_methods}\n"
            f"Chatbox IP: {self.chatbox_ip}, Port: {self.chatbox_port}"
        )
        return settings_text

    def update_current_settings_label(self):
        """Updates the current settings label."""
        self.current_settings_label.config(text=self.get_current_settings_text())

    def check_spelling(self, event=None):
        """Checks the spelling of the text in the textbox."""
        self.textbox.tag_remove("misspelled", "1.0", tk.END)
        text = self.textbox.get("1.0", tk.END)
        words = re.finditer(r'\b\w+\b', text)
        for word_match in words:
            word = word_match.group()
            if word.lower() in self.spellchecker:
                continue
            start_idx = f"1.0+{word_match.start()}c"
            end_idx = f"1.0+{word_match.end()}c"
            self.textbox.tag_add("misspelled", start_idx, end_idx)
        self.textbox.tag_config("misspelled", foreground="red")

    def show_suggestions(self, event):
        """Shows spelling suggestions for the misspelled word."""
        try:
            index = self.textbox.index(f"@{event.x},{event.y}")
            # Get the start and end indices of the word
            word_start = self.textbox.index(f"{index} wordstart")
            word_end = self.textbox.index(f"{index} wordend")
            word = self.textbox.get(word_start, word_end).strip()
            if not word:
                return
            if word.lower() in self.spellchecker:
                return
            suggestions = self.spellchecker.suggest(word.lower())
            if suggestions:
                menu = tk.Menu(self.root, tearoff=0)
                for suggestion in suggestions[:10]:  # Limit to first 10 suggestions
                    menu.add_command(
                        label=suggestion,
                        command=lambda s=suggestion, start=word_start, end=word_end: self.replace_word(start, end, s)
                    )
                menu.post(event.x_root, event.y_root)
            else:
                messagebox.showinfo("No Suggestions", "No spelling suggestions available.")
        except Exception as e:
            logging.error(f"Error showing suggestions: {e}")

    def replace_word(self, start, end, replacement):
        """Replaces the misspelled word with the selected suggestion."""
        self.textbox.delete(start, end)
        self.textbox.insert(start, replacement)
        # Recheck the spelling
        self.check_spelling()

    def submit_text(self, event=None):
        """Handles the 'Send' button click or Enter key press."""
        text = self.textbox.get("1.0", tk.END).strip()
        if text:
            self.process_text(text)
            self.textbox.delete("1.0", tk.END)
            logging.info(f'Text submitted: {text}')
        else:
            logging.warning('No text entered.')
        return 'break'  # Prevent default behavior of adding a newline

    def cancel_text(self):
        """Handles the 'Cancel' button click."""
        self.textbox.delete("1.0", tk.END)
        logging.info('Text input canceled.')

    def toggle_voice_capture(self):
        """Toggles the voice capture on and off."""
        self.voice_capture_active = not self.voice_capture_active
        if self.voice_capture_active:
            self.toggle_voice_button.config(text='Stop Voice Capture')
            logging.info('Voice capture started.')
        else:
            self.toggle_voice_button.config(text='Start Voice Capture')
            logging.info('Voice capture stopped.')

    def setup_hotkey_listener(self):
        """Sets up the hotkey listener for toggling voice capture."""
        try:
            keyboard.add_hotkey(self.hotkey, self.toggle_voice_capture)
            logging.info(f'Hotkey "{self.hotkey}" registered for toggling voice capture.')
        except Exception as e:
            logging.error(f'Error setting up hotkey: {e}')

    def on_key_press(self, event):
        self.is_typing = True

    def on_key_release(self, event):
        self.is_typing = False

    def voice_input_loop(self):
        """Continuously listens for voice input if activated."""
        while self.running:
            if self.voice_capture_active and not self.is_typing:
                text = self.input_manager.get_voice_input()
                if text:
                    # Insert transcribed text into the textbox
                    self.textbox.insert(tk.END, text + ' ')
                    logging.info(f'Transcribed text inserted into textbox: {text}')
            else:
                # If voice capture is not active or user is typing, sleep briefly
                time.sleep(0.1)

    def process_text(self, text):
        """Processes the text: splits if necessary, outputs via TTS and chatbox."""
        # Split text into chunks of up to max_chatbox_length
        chunks = self.split_text(text, self.max_chatbox_length)
        # Start processing chunks in a separate thread
        threading.Thread(target=self.output_chunks, args=(chunks,), daemon=True).start()

    def split_text(self, text, max_length):
        """Splits text into chunks not exceeding max_length characters, ending on a full sentence or word."""
        import re

        # Use regular expressions to split text into sentences
        sentence_endings = re.compile(r'(?<=[.!?])\s+')
        sentences = sentence_endings.split(text)

        chunks = []
        current_chunk = ''

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= max_length:
                current_chunk += (' ' + sentence) if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                if len(sentence) <= max_length:
                    current_chunk = sentence
                else:
                    # Split long sentence into smaller chunks
                    words = sentence.split()
                    current_sentence_chunk = ''
                    for word in words:
                        if len(current_sentence_chunk) + len(word) + 1 <= max_length:
                            current_sentence_chunk += (' ' + word) if current_sentence_chunk else word
                        else:
                            chunks.append(current_sentence_chunk.strip())
                            current_sentence_chunk = word
                    if current_sentence_chunk:
                        current_chunk = current_sentence_chunk
                    else:
                        current_chunk = ''
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

    def output_chunks(self, chunks):
        """Outputs text chunks via TTS and sends to chatbox."""
        for chunk in chunks:
            # Output via TTS if enabled
            if self.output_options.get('Voice Output', False):
                self.output_manager.speak_text(chunk)
            # Send to chatbox if enabled
            if self.output_options.get('Chatbox Output', False):
                self.output_manager.send_to_chatbox(chunk)
            # Wait for 10 seconds before processing next chunk
            time.sleep(10)

    def show_settings(self):
        """Displays the settings window."""
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Settings")

        row = 0

        # Output Options
        ttk.Label(self.settings_window, text='Output Options:', font=('Arial', 10, 'bold')).grid(row=row, column=0, padx=5, pady=5, sticky='W')
        row += 1

        self.voice_output_var = tk.BooleanVar(value=self.output_options.get('Voice Output', True))
        voice_output_cb = ttk.Checkbutton(self.settings_window, text='Voice Output', variable=self.voice_output_var)
        voice_output_cb.grid(row=row, column=0, padx=5, pady=2, sticky='W')

        self.chatbox_output_var = tk.BooleanVar(value=self.output_options.get('Chatbox Output', True))
        chatbox_output_cb = ttk.Checkbutton(self.settings_window, text='Chatbox Output', variable=self.chatbox_output_var)
        chatbox_output_cb.grid(row=row, column=1, padx=5, pady=2, sticky='W')
        row += 1

        # Input Audio Device
        ttk.Label(self.settings_window, text='Input Audio Device:').grid(row=row, column=0, padx=5, pady=5, sticky='E')
        input_devices = self.get_audio_devices(input=True)
        self.input_device_var = tk.StringVar(value=self.input_device)
        ttk.Combobox(self.settings_window, textvariable=self.input_device_var, values=input_devices, width=50).grid(row=row, column=1, padx=5, pady=5, sticky='W')
        row += 1

        # Output Audio Device
        ttk.Label(self.settings_window, text='Output Audio Device:').grid(row=row, column=0, padx=5, pady=5, sticky='E')
        output_devices = self.get_audio_devices(output=True)
        self.output_device_var = tk.StringVar(value=self.output_device)
        ttk.Combobox(self.settings_window, textvariable=self.output_device_var, values=output_devices, width=50).grid(row=row, column=1, padx=5, pady=5, sticky='W')
        row += 1

        # Chatbox IP
        ttk.Label(self.settings_window, text='Chatbox IP:').grid(row=row, column=0, padx=5, pady=5, sticky='E')
        self.chatbox_ip_var = tk.StringVar(value=self.chatbox_ip)
        ttk.Entry(self.settings_window, textvariable=self.chatbox_ip_var, width=50).grid(row=row, column=1, padx=5, pady=5, sticky='W')
        row += 1

        # Chatbox Port
        ttk.Label(self.settings_window, text='Chatbox Port:').grid(row=row, column=0, padx=5, pady=5, sticky='E')
        self.chatbox_port_var = tk.IntVar(value=self.chatbox_port)
        ttk.Entry(self.settings_window, textvariable=self.chatbox_port_var, width=50).grid(row=row, column=1, padx=5, pady=5, sticky='W')
        row += 1

        # Voice Engine
        ttk.Label(self.settings_window, text='Voice Engine:').grid(row=row, column=0, padx=5, pady=5, sticky='E')
        voice_engines = ['pyttsx3', 'edge-tts']
        self.voice_engine_var = tk.StringVar(value=self.voice_engine)
        voice_engine_combobox = ttk.Combobox(self.settings_window, textvariable=self.voice_engine_var, values=voice_engines, state='readonly', width=50)
        voice_engine_combobox.grid(row=row, column=1, padx=5, pady=5, sticky='W')
        self.voice_engine_var.trace('w', self.update_voice_options)
        row += 1

        # Language Selection
        ttk.Label(self.settings_window, text='Language:').grid(row=row, column=0, padx=5, pady=5, sticky='E')
        languages = self.get_available_languages()
        self.language_var = tk.StringVar(value=self.language)
        language_combobox = ttk.Combobox(self.settings_window, textvariable=self.language_var, values=languages, state='readonly', width=50)
        language_combobox.grid(row=row, column=1, padx=5, pady=5, sticky='W')
        self.language_var.trace('w', self.update_voice_options)
        row += 1

        # Voice Options
        ttk.Label(self.settings_window, text='Voice:').grid(row=row, column=0, padx=5, pady=5, sticky='E')
        self.voice_var = tk.StringVar(value=self.voice)
        self.voice_combobox = ttk.Combobox(self.settings_window, textvariable=self.voice_var, width=50)
        self.voice_combobox.grid(row=row, column=1, padx=5, pady=5, sticky='W')
        self.update_voice_options()
        row += 1

        # Hotkey Setting
        ttk.Label(self.settings_window, text='Hotkey:').grid(row=row, column=0, padx=5, pady=5, sticky='E')
        self.hotkey_var = tk.StringVar(value=self.hotkey)
        ttk.Entry(self.settings_window, textvariable=self.hotkey_var, width=50).grid(row=row, column=1, padx=5, pady=5, sticky='W')
        row += 1

        # Save and Cancel Buttons
        save_button = ttk.Button(self.settings_window, text='Save', command=self.save_settings)
        save_button.grid(row=row, column=0, padx=5, pady=10)
        cancel_button = ttk.Button(self.settings_window, text='Cancel', command=self.settings_window.destroy)
        cancel_button.grid(row=row, column=1, padx=5, pady=10)

    def get_audio_devices(self, input=False, output=False):
        """Returns a list of available audio devices."""
        devices = sd.query_devices()
        device_names = []
        for idx, device in enumerate(devices):
            # Skip devices with '(Disabled)' or '(Hidden)' in their names
            if '(Disabled)' in device['name'] or '(Hidden)' in device['name']:
                continue
            # Skip "Primary Sound Driver"
            if 'Primary Sound Driver' in device['name']:
                continue
            if input and device['max_input_channels'] > 0:
                device_name = f"{device['name']} ({idx})"
                device_names.append(device_name)
            if output and device['max_output_channels'] > 0:
                device_name = f"{device['name']} ({idx})"
                device_names.append(device_name)
        return device_names

    def update_voice_options(self, *args):
        """Updates the voice options based on the selected voice engine and language."""
        selected_engine = self.voice_engine_var.get()
        if selected_engine == 'pyttsx3':
            voices = self.get_pyttsx3_voices()
        elif selected_engine == 'edge-tts':
            voices = self.get_edge_tts_voices()
        else:
            voices = []
        self.voice_combobox.config(values=voices)
        if self.voice not in voices:
            self.voice_var.set(voices[0] if voices else '')

    def get_available_languages(self):
        """Returns a list of available languages for the selected voice engine."""
        selected_engine = self.voice_engine_var.get()
        if selected_engine == 'edge-tts':
            voices = self.get_all_edge_tts_voices()
            languages = set()
            for voice in voices:
                languages.add(voice['Locale'])
            return sorted(languages)
        elif selected_engine == 'pyttsx3':
            # pyttsx3 does not provide language info
            return ['en-US']
        else:
            return []

    def get_pyttsx3_voices(self):
        """Returns a list of available voices for pyttsx3."""
        import pyttsx3
        self.engine = pyttsx3.init()
        voices = self.engine.getProperty('voices')
        voice_names = [f"{voice.id} - {voice.name}" for voice in voices]
        self.pyttsx3_voice_dict = {f"{voice.id} - {voice.name}": voice.id for voice in voices}
        return voice_names

    def get_edge_tts_voices(self):
        """Retrieves edge-tts voices filtered by the selected language."""
        voices = []
        self.edge_voice_dict = {}
        try:
            all_voices = self.get_all_edge_tts_voices()
            selected_language = self.language_var.get()
            # Filter voices by selected language
            filtered_voices = [voice for voice in all_voices if voice['Locale'] == selected_language]
            if not filtered_voices:
                logging.warning(f"No voices found for language: {selected_language}")
                return []
            voice_names = []
            for voice in filtered_voices:
                # Safely access 'LocalName' or fall back to other names
                local_name = voice.get('LocalName') or voice.get('FriendlyName') or voice.get('ShortName')
                display_name = f"{voice['ShortName']} - {local_name} ({voice['Locale']})"
                voice_names.append(display_name)
                self.edge_voice_dict[display_name] = voice['ShortName']
            voices = voice_names
        except Exception as e:
            logging.error(f"Error retrieving edge-tts voices: {e}")
        return voices

    def get_all_edge_tts_voices(self):
        """Returns a list of all available voices for edge-tts."""
        if hasattr(self, 'edge_voices') and self.edge_voices:
            return self.edge_voices
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.edge_voices = loop.run_until_complete(self.get_all_edge_tts_voices_async())
            loop.close()
        except Exception as e:
            logging.error(f"Error retrieving edge-tts voices: {e}")
            self.edge_voices = []
        return self.edge_voices

    async def get_all_edge_tts_voices_async(self):
        """Asynchronously retrieves all available voices for edge-tts."""
        from edge_tts import VoicesManager
        voices = []
        try:
            voices_manager = await VoicesManager.create()
            voices = voices_manager.voices
        except Exception as e:
            logging.error(f"Error retrieving edge-tts voices: {e}")
        return voices

    def save_settings(self):
        """Saves the settings from the settings window."""
        # Extract device indices from the selected device names
        self.input_device = self.input_device_var.get()
        self.output_device = self.output_device_var.get()

        input_device_index = int(self.input_device.split('(')[-1].strip(')'))
        output_device_index = int(self.output_device.split('(')[-1].strip(')'))

        self.chatbox_ip = self.chatbox_ip_var.get()
        self.chatbox_port = self.chatbox_port_var.get()
        self.voice_engine = self.voice_engine_var.get()
        self.voice = self.voice_var.get()
        self.language = self.language_var.get()
        self.hotkey = self.hotkey_var.get()

        # Output options
        self.output_options['Voice Output'] = self.voice_output_var.get()
        self.output_options['Chatbox Output'] = self.chatbox_output_var.get()

        # Apply the settings
        sd.default.device = (input_device_index, output_device_index)
        if self.voice_engine == 'edge-tts':
            self.voice = self.edge_voice_dict.get(self.voice, self.voice)
        elif self.voice_engine == 'pyttsx3':
            self.voice = self.pyttsx3_voice_dict.get(self.voice, self.voice)
        self.output_manager.update_settings(
            chatbox_ip=self.chatbox_ip,
            chatbox_port=self.chatbox_port,
            voice_engine=self.voice_engine,
            voice=self.voice
        )
        # Update the current settings label
        self.update_current_settings_label()

        # Update hotkey
        keyboard.unhook_all_hotkeys()
        self.setup_hotkey_listener()

        # Save settings to file
        self.save_settings_to_file()

        logging.info('Settings have been saved.')
        self.settings_window.destroy()

    def stop_audio(self):
        """Stops audio playback."""
        self.output_manager.stop_audio()

    def on_closing(self):
        """Handles actions when the window is closed."""
        self.running = False
        self.output_manager.stop_audio()  # Ensure audio is stopped
        keyboard.unhook_all()
        self.root.destroy()
        sys.exit(0)

    def run(self):
        """Runs the main loop of the UI."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
