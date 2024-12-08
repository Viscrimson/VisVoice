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
        self.voice_engine = 'polly'
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
        self.spellcheck_delay = 1000  # Delay in milliseconds
        self.spellcheck_job = None

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
            self.voice_engine = settings.get('voice_engine', 'polly')
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

        if 'Presets' in config:
            # Convert all preset names to lowercase for consistency
            self.presets = {k.lower(): v for k, v in config['Presets'].items()}
        else:
            # Default presets with lowercase keys
            self.presets = {
                'preset 1': 'ja-JP-NanamiNeural',
                'preset 2': 'en-US-JennyNeural',
                'preset 3': 'zh-CN-XiaoyiNeural',
                'preset 4': 'ko-KR-SunHiNeural',
                'preset 5': 'fr-FR-DeniseNeural',
                'preset 6': 'de-DE-KatjaNeural',
                'preset 7': 'es-ES-ElviraNeural',
                'preset 8': 'it-IT-ElsaNeural',
            }

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
        # Save presets with consistent case
        config['Presets'] = {k: v for k, v in self.presets.items()}
        
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

        # Action Buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill='x', pady=5)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        button_frame.columnconfigure(3, weight=1)

        cancel_button = ttk.Button(button_frame, text='Cancel', command=self.cancel_text)
        cancel_button.grid(row=0, column=0, sticky='e')

        send_button = ttk.Button(button_frame, text='Send', command=self.submit_text)
        send_button.grid(row=0, column=1)

        self.toggle_voice_button = ttk.Button(button_frame, text='Start Voice Capture', 
                                            command=self.toggle_voice_capture)
        self.toggle_voice_button.grid(row=0, column=2, sticky='w')

        stop_audio_button = ttk.Button(button_frame, text='Stop Audio', command=self.stop_audio)
        stop_audio_button.grid(row=0, column=3, sticky='w')

        # Preset buttons section
        preset_frame = ttk.Frame(self.root)
        preset_frame.pack(fill='x', padx=10, pady=5)
        
        # Create preset grid (2 rows of 4 buttons)
        self.preset_buttons = {}  # Store buttons for later reference
        for i in range(8):
            preset_name = f"Preset {i+1}"
            voice = self.presets.get(preset_name.lower(), '')  # Use lowercase for consistency
            btn = ttk.Button(preset_frame, text=preset_name, 
                           command=lambda v=voice, b=preset_name: self.apply_preset(v, b))
            row = i // 4
            col = i % 4
            btn.grid(row=row, column=col, padx=2, pady=2, sticky='ew')
            btn.bind('<Button-3>', lambda e, b=btn: self.configure_preset(e, b))
            self.preset_buttons[preset_name.lower()] = btn  # Store button reference
        
        # Configure grid columns to be equal width
        for i in range(4):
            preset_frame.columnconfigure(i, weight=1)

        # Settings Accordion
        settings_frame = ttk.Frame(self.root)
        settings_frame.pack(fill='x', padx=10, pady=5)

        def toggle_settings():
            if settings_content.winfo_viewable():
                settings_content.pack_forget()
                toggle_btn.configure(text='▼ Settings')
            else:
                settings_content.pack(fill='x', padx=5, pady=5)
                toggle_btn.configure(text='▲ Settings')

        toggle_btn = ttk.Button(settings_frame, text='▼ Settings', command=toggle_settings)
        toggle_btn.pack(fill='x')

        # Settings Content (initially hidden)
        settings_content = ttk.Frame(settings_frame)
        
        # Create two columns for settings
        col1_frame = ttk.Frame(settings_content)
        col1_frame.pack(side='left', fill='both', expand=True)

        col2_frame = ttk.Frame(settings_content)
        col2_frame.pack(side='right', fill='both', expand=True)

        # Column 1 Settings
        ttk.Label(col1_frame, text='Output Options:', font=('Arial', 10, 'bold')).pack(anchor='w')
        self.voice_output_var = tk.BooleanVar(value=self.output_options.get('Voice Output', True))
        ttk.Checkbutton(col1_frame, text='Voice Output', variable=self.voice_output_var).pack(anchor='w')

        self.chatbox_output_var = tk.BooleanVar(value=self.output_options.get('Chatbox Output', True))
        ttk.Checkbutton(col1_frame, text='Chatbox Output', variable=self.chatbox_output_var).pack(anchor='w')

        ttk.Label(col1_frame, text='Input Audio Device:').pack(anchor='w')
        input_devices = self.get_audio_devices(input=True)
        self.input_device_var = tk.StringVar(value=self.input_device)
        ttk.Combobox(col1_frame, textvariable=self.input_device_var, values=input_devices, width=50).pack(anchor='w')

        ttk.Label(col1_frame, text='Output Audio Device:').pack(anchor='w')
        output_devices = self.get_audio_devices(output=True)
        self.output_device_var = tk.StringVar(value=self.output_device)
        ttk.Combobox(col1_frame, textvariable=self.output_device_var, values=output_devices, width=50).pack(anchor='w')

        ttk.Label(col1_frame, text='Hotkey:').pack(anchor='w')
        self.hotkey_var = tk.StringVar(value=self.hotkey)
        ttk.Entry(col1_frame, textvariable=self.hotkey_var, width=50).pack(anchor='w')

        # Column 2 Settings
        ttk.Label(col2_frame, text='Voice Engine:').pack(anchor='w')
        voice_engines = ['edge-tts', 'polly']
        self.voice_engine_var = tk.StringVar(value=self.voice_engine)
        ttk.Combobox(col2_frame, textvariable=self.voice_engine_var, values=voice_engines, state='readonly', width=50).pack(anchor='w')

        ttk.Label(col2_frame, text='Language:').pack(anchor='w')
        languages = self.get_available_languages()
        self.language_var = tk.StringVar(value=self.language)
        self.language_combobox = ttk.Combobox(col2_frame, textvariable=self.language_var, values=languages, state='readonly', width=50)
        self.language_combobox.pack(anchor='w')

        ttk.Label(col2_frame, text='Voice:').pack(anchor='w')
        self.voice_var = tk.StringVar(value=self.voice)
        self.voice_combobox = ttk.Combobox(col2_frame, textvariable=self.voice_var, width=50)
        self.voice_combobox.pack(anchor='w')

        ttk.Label(col2_frame, text='Chatbox IP:').pack(anchor='w')
        self.chatbox_ip_var = tk.StringVar(value=self.chatbox_ip)
        ttk.Entry(col2_frame, textvariable=self.chatbox_ip_var, width=50).pack(anchor='w')

        ttk.Label(col2_frame, text='Chatbox Port:').pack(anchor='w')
        self.chatbox_port_var = tk.IntVar(value=self.chatbox_port)
        ttk.Entry(col2_frame, textvariable=self.chatbox_port_var, width=50).pack(anchor='w')

        # Now add the trace callbacks
        self.voice_engine_var.trace('w', self.update_voice_options)
        self.voice_engine_var.trace('w', self.save_settings)
        self.language_var.trace('w', self.update_voice_options)
        self.language_var.trace('w', self.save_settings)
        self.voice_var.trace('w', self.save_settings)
        self.voice_output_var.trace('w', self.save_settings)
        self.chatbox_output_var.trace('w', self.save_settings)
        self.input_device_var.trace('w', self.save_settings)
        self.output_device_var.trace('w', self.save_settings)
        self.hotkey_var.trace('w', self.save_settings)
        self.chatbox_ip_var.trace('w', self.save_settings)
        self.chatbox_port_var.trace('w', self.save_settings)

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
        """Checks the spelling of the text in the textbox and auto-corrects obvious errors."""
        if self.spellcheck_job:
            self.root.after_cancel(self.spellcheck_job)
        self.spellcheck_job = self.root.after(self.spellcheck_delay, self.perform_spellcheck)

    def perform_spellcheck(self):
        """Performs the actual spell checking and correction."""
        self.textbox.tag_remove("misspelled", "1.0", tk.END)
        text = self.textbox.get("1.0", tk.END)
        words = re.finditer(r'\b\w+\b', text)
        for word_match in words:
            word = word_match.group()
            if word.lower() in self.spellchecker:
                continue
            best_suggestion = self.spellchecker.correction(word.lower())
            if best_suggestion:
                start_idx = f"1.0+{word_match.start()}c"
                end_idx = f"1.0+{word_match.end()}c"
                self.textbox.delete(start_idx, end_idx)
                self.textbox.insert(start_idx, best_suggestion)
                self.textbox.tag_add("corrected", start_idx, f"{start_idx}+{len(best_suggestion)}c")
        self.textbox.tag_config("corrected", foreground="blue")

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
            suggestions = self.spellchecker.candidates(word.lower())
            if suggestions:
                menu = tk.Menu(self.root, tearoff=0)
                for suggestion in sorted(suggestions)[:10]:  # Limit to first 10 suggestions
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
        self.perform_spellcheck()

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

    def save_settings(self, *args):
        """Saves the settings when any setting is changed."""
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
            # Ensure edge_voice_dict is initialized
            if not hasattr(self, 'edge_voice_dict') or not self.edge_voice_dict:
                self.update_voice_options()
            self.voice = self.edge_voice_dict.get(self.voice_var.get(), self.voice_var.get())
        elif self.voice_engine == 'polly':
            # Ensure polly_voice_dict is initialized
            if not hasattr(self, 'polly_voice_dict') or not self.polly_voice_dict:
                self.update_voice_options()
            self.voice = self.polly_voice_dict.get(self.voice_var.get(), self.voice_var.get())
        self.output_manager.update_settings(
            chatbox_ip=self.chatbox_ip,
            chatbox_port=self.chatbox_port,
            voice_engine=self.voice_engine,
            voice=self.voice
        )
        # Update hotkey
        keyboard.unhook_all_hotkeys()
        self.setup_hotkey_listener()

        # Save settings to file
        self.save_settings_to_file()

        logging.info('Settings have been saved.')

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
        """Updates voice options based on selected engine and language."""
        selected_engine = self.voice_engine_var.get()
        if (selected_engine == 'edge-tts'):
            voices = self.get_all_edge_tts_voices()
            # Filter voices by selected language
            selected_language = self.language_var.get()
            if selected_language:
                voices = [voice for voice in voices if voice['Locale'] == selected_language]
            # Build display names and populate edge_voice_dict
            self.edge_voice_dict = {}
            display_names = []
            for voice in voices:
                # Store ShortName as both key and value
                shortname = voice['ShortName']
                display_name = f"{shortname} ({voice['Locale']})"
                display_names.append(display_name)
                self.edge_voice_dict[display_name] = shortname
            self.voice_combobox.config(values=display_names)
            if self.voice_var.get() not in display_names:
                self.voice_var.set(display_names[0] if display_names else '')
        elif selected_engine == 'polly':
            # Add the code to handle Polly voice options
            voices = self.get_polly_voices()
            self.voice_combobox.config(values=voices)
            if self.voice_var.get() not in voices:
                self.voice_var.set(voices[0] if voices else '')
        else:
            logging.error(f"Unknown voice engine: {selected_engine}")

    def get_available_languages(self):
        """Returns a list of available languages for the selected voice engine."""
        selected_engine = self.voice_engine_var.get()
        if selected_engine == 'edge-tts':
            try:
                voices = self.get_all_edge_tts_voices()
                languages = set()
                for voice in voices:
                    if 'Locale' in voice:  # Ensure the key exists
                        languages.add(voice['Locale'])
                return sorted(languages)
            except Exception as e:
                logging.error(f"Error getting languages: {e}")
                return []
        elif selected_engine == 'polly':
            return self.get_polly_languages()
        else:
            return []

    def get_polly_languages(self):
        """Returns a list of available languages for Amazon Polly."""
        import boto3
        polly_client = boto3.client('polly')
        response = polly_client.describe_voices()
        languages = {voice['LanguageCode'] for voice in response['Voices']}
        return sorted(languages)

    def get_polly_voices(self):
        """Returns a list of available voices for Amazon Polly."""
        import boto3
        polly_client = boto3.client('polly')
        response = polly_client.describe_voices(LanguageCode=self.language_var.get())
        voices = []
        self.polly_voice_dict = {}
        for voice in response['Voices']:
            display_name = f"{voice['Name']} ({voice['Id']})"
            voices.append(display_name)
            self.polly_voice_dict[display_name] = voice['Id']
        return voices

    def get_all_edge_tts_voices(self):
        """Returns a list of all available voice dictionaries for edge-tts."""
        if hasattr(self, 'edge_voices') and self.edge_voices:
            return self.edge_voices
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            voices = loop.run_until_complete(self.get_all_edge_tts_voices_async())
            # Log the first voice to debug structure
            if voices:
                logging.debug(f"First voice structure: {voices[0]}")
            self.edge_voices = voices
            return self.edge_voices
        except Exception as e:
            logging.error(f"Error retrieving edge-tts voices: {e}")
            self.edge_voices = []
            return []

    async def get_all_edge_tts_voices_async(self):
        """Asynchronously retrieves all available voices for edge-tts."""
        from edge_tts import VoicesManager
        try:
            voices_manager = await VoicesManager.create()
            voices = voices_manager.voices
            # Ensure each voice has required keys
            processed_voices = []
            for voice in voices:
                if all(key in voice for key in ['ShortName', 'Name', 'Locale']):
                    processed_voices.append(voice)
            return processed_voices
        except Exception as e:
            logging.error(f"Error retrieving edge-tts voices: {e}")
            return []

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

    def apply_preset(self, voice, preset_name):
        """Applies the selected voice preset."""
        if not voice:
            logging.warning(f"No voice assigned to preset: {preset_name}")
            return
            
        # Update voice engine first
        self.voice_engine_var.set('edge-tts')
        self.voice_engine = 'edge-tts'
        
        # Extract language from voice ID (e.g., 'ja-JP' from 'ja-JP-NanamiNeural')
        language = '-'.join(voice.split('-')[:2])
        self.language_var.set(language)
        
        # Update voice settings
        self.update_voice_options()
        
        # Set the voice after options are updated
        def set_voice_delayed():
            voices = self.voice_combobox['values']
            for v in voices:
                if voice in v:  # Match if the voice ID is in the display name
                    self.voice_var.set(v)
                    self.save_settings()  # Save the changes
                    break
        
        # Wait for language change to update voices
        self.root.after(200, set_voice_delayed)

    def configure_preset(self, event, button):
        """Shows configuration menu for preset button."""
        menu = tk.Menu(self.root, tearoff=0)
        
        # Get current voice selection
        current_voice = self.edge_voice_dict.get(self.voice_var.get(), '')
        
        # Add option to set current voice as preset
        menu.add_command(
            label=f"Set as current voice ({current_voice})",
            command=lambda: self.update_preset(button, current_voice)
        )
        
        # Add option to rename preset
        menu.add_command(
            label="Rename preset",
            command=lambda: self.rename_preset(button)
        )
        
        menu.post(event.x_root, event.y_root)

    def update_preset(self, button, voice):
        """Updates the preset with the new voice."""
        preset_name = button['text'].lower()  # Convert to lowercase
        if voice:
            self.presets[preset_name] = voice
            self.save_settings_to_file()
            logging.info(f"Updated preset '{preset_name}' to voice: {voice}")
        else:
            logging.warning(f"Cannot update preset '{preset_name}': No voice selected")

    def rename_preset(self, button):
        """Shows dialog to rename preset."""
        old_name = button['text']
        old_name_lower = old_name.lower()
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Rename Preset")
        dialog.grab_set()
        
        ttk.Label(dialog, text="Enter new name:").pack(padx=5, pady=5)
        entry = ttk.Entry(dialog)
        entry.insert(0, old_name)
        entry.pack(padx=5, pady=5)
        
        def save_rename():
            new_name = entry.get()
            new_name_lower = new_name.lower()
            if new_name and new_name_lower != old_name_lower:
                # Update presets dictionary
                voice = self.presets.pop(old_name_lower, None)
                if voice:
                    self.presets[new_name_lower] = voice
                    # Update button text
                    button.config(text=new_name)
                    self.save_settings_to_file()
            dialog.destroy()
        
        ttk.Button(dialog, text="Save", command=save_rename).pack(pady=5)
