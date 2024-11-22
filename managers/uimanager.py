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
import os

# Import keyboard for global hotkey functionality
import keyboard
import boto3  # Add AWS SDK for Python

class UIManager:
    def __init__(self, controller):
        self.controller = controller
        self.root = tk.Tk()
        self.root.title("Vis Voice")

        # Initialize settings
        self.input_device = None
        self.output_device = None
        self.chatbox_ip = '127.0.0.1'
        self.chatbox_port = 9000
        self.voice_engine = 'edge-tts'
        self.voice = None
        self.language = 'en-US'  # Default language
        self.hotkey = '`'  # Default hotkey
        # Output options
        self.output_options = {'Voice Output': True, 'Chatbox Output': True}

        # Initialize StringVar variables for settings
        self.voice_engine_var = tk.StringVar(value=self.voice_engine)
        self.language_var = tk.StringVar(value=self.language)
        self.voice_var = tk.StringVar(value=self.voice)

        # Initialize StringVar variables for chatbox settings
        self.chatbox_ip_var = tk.StringVar(value=self.chatbox_ip)
        self.chatbox_port_var = tk.StringVar(value=str(self.chatbox_port))

        # Initialize voice dictionaries
        self.edge_voice_dict = {}
        self.aws_polly_voice_dict = {}

        # Flags
        self.is_typing = False  # Flag to detect typing

        self.load_settings()
        self.create_widgets()
        self.spellchecker = SpellChecker()

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
            self.voice_engine = settings.get('voice_engine', 'edge-tts')
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
        """Returns a string representing the current settings in the correct order."""
        output_methods = ', '.join([key for key, value in self.output_options.items() if value])
        settings_text = (
            f"Input Device: {self.input_device}\n"
            f"Output Device: {self.output_device}\n"
            f"Engine: {self.voice_engine}\n"
            f"Language: {self.language}\n"
            f"Voice: {self.voice}\n"
            f"Hotkey: {self.hotkey}\n"
            f"Output Methods: {output_methods}\n"
            f"IP: {self.chatbox_ip}, Port: {self.chatbox_port}"
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
            self.controller.process_text(text)
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
        self.controller.toggle_voice_capture()

    def update_voice_capture_button(self, active):
        """Updates the voice capture button's text."""
        if active:
            self.toggle_voice_button.config(text='Stop Voice Capture')
        else:
            self.toggle_voice_button.config(text='Start Voice Capture')

    def setup_hotkey_listener(self):
        """Sets up the hotkey listener for toggling voice capture."""
        try:
            keyboard.add_hotkey(self.hotkey, self.toggle_voice_capture)
            logging.info(f'Hotkey "{self.hotkey}" registered for toggling voice capture.')
        except Exception as e:
            logging.error(f'Error setting up hotkey: {e}')

    def on_key_press(self, event):
        self.controller.set_typing(True)

    def on_key_release(self, event):
        self.controller.set_typing(False)

    def insert_text(self, text):
        """Inserts text into the textbox."""
        self.textbox.insert(tk.END, text)

    def show_settings(self):
        """Displays the settings window in the correct order."""
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Settings")
        row = 0

        # Create all BooleanVar variables at initialization
        self.voice_output_var = tk.BooleanVar(value=self.output_options['Voice Output'])
        self.chatbox_output_var = tk.BooleanVar(value=self.output_options['Chatbox Output'])

        # Input Device
        ttk.Label(self.settings_window, text='Input Device:').grid(row=row, column=0, padx=5, pady=5, sticky='E')
        input_devices = self.get_audio_devices(input=True)
        self.input_device_var = tk.StringVar(value=self.input_device)
        ttk.Combobox(self.settings_window, textvariable=self.input_device_var, values=input_devices, width=50).grid(
            row=row, column=1, padx=5, pady=5, sticky='W')
        row += 1

        # Output Device
        ttk.Label(self.settings_window, text='Output Device:').grid(row=row, column=0, padx=5, pady=5, sticky='E')
        output_devices = self.get_audio_devices(output=True)
        self.output_device_var = tk.StringVar(value=self.output_device)
        ttk.Combobox(self.settings_window, textvariable=self.output_device_var, values=output_devices, width=50).grid(
            row=row, column=1, padx=5, pady=5, sticky='W')
        row += 1

        # Engine
        ttk.Label(self.settings_window, text='Engine:').grid(row=row, column=0, padx=5, pady=5, sticky='E')
        voice_engines = ['edge-tts', 'aws-polly']
        ttk.Combobox(self.settings_window, textvariable=self.voice_engine_var, values=voice_engines, state='readonly', width=50).grid(
            row=row, column=1, padx=5, pady=5, sticky='W')
        self.voice_engine_var.trace('w', self.update_voice_options)
        row += 1

        # Language
        ttk.Label(self.settings_window, text='Language:').grid(row=row, column=0, padx=5, pady=5, sticky='E')
        languages = self.get_available_languages()
        language_combobox = ttk.Combobox(self.settings_window, textvariable=self.language_var, values=languages, state='readonly', width=50)
        language_combobox.grid(row=row, column=1, padx=5, pady=5, sticky='W')
        self.language_var.trace('w', self.update_voice_options)  # Add this trace
        row += 1

        # Voice
        ttk.Label(self.settings_window, text='Voice:').grid(row=row, column=0, padx=5, pady=5, sticky='E')
        self.voice_combobox = ttk.Combobox(self.settings_window, textvariable=self.voice_var, state='readonly', width=50)
        self.voice_combobox.grid(row=row, column=1, padx=5, pady=5, sticky='W')
        self.update_voice_options()
        row += 1

        # Hotkey
        ttk.Label(self.settings_window, text='Hotkey:').grid(row=row, column=0, padx=5, pady=5, sticky='E')
        self.hotkey_var = tk.StringVar(value=self.hotkey)
        hotkey_entry = ttk.Entry(self.settings_window, textvariable=self.hotkey_var, width=50)
        hotkey_entry.grid(row=row, column=1, padx=5, pady=5, sticky='W')
        row += 1

        # Output Methods Frame
        ttk.Label(self.settings_window, text='Output Methods:').grid(row=row, column=0, padx=5, pady=5, sticky='E')
        methods_frame = ttk.Frame(self.settings_window)
        methods_frame.grid(row=row, column=1, padx=5, pady=5, sticky='W')
        ttk.Checkbutton(methods_frame, text='Voice Output', variable=self.voice_output_var).pack(side='left', padx=5)
        ttk.Checkbutton(methods_frame, text='Chatbox Output', variable=self.chatbox_output_var).pack(side='left', padx=5)
        row += 1

        # IP and Port
        ttk.Label(self.settings_window, text='IP and Port:').grid(row=row, column=0, padx=5, pady=5, sticky='E')
        ip_port_frame = ttk.Frame(self.settings_window)
        ip_port_frame.grid(row=row, column=1, padx=5, pady=5, sticky='W')
        ttk.Entry(ip_port_frame, textvariable=self.chatbox_ip_var, width=20).pack(side='left')
        ttk.Label(ip_port_frame, text=':').pack(side='left', padx=2)
        ttk.Entry(ip_port_frame, textvariable=self.chatbox_port_var, width=10).pack(side='left')
        row += 1

        # Save and Cancel buttons
        button_frame = ttk.Frame(self.settings_window)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text='Save', command=self.save_settings).pack(side='left', padx=5)
        ttk.Button(button_frame, text='Cancel', command=self.settings_window.destroy).pack(side='left', padx=5)

    def save_settings(self):
        """Saves the settings from the settings window."""
        try:
            # Extract device indices from the selected device names
            self.input_device = self.input_device_var.get()
            self.output_device = self.output_device_var.get()

            input_device_index = int(self.input_device.split('(')[-1].strip(')'))
            output_device_index = int(self.output_device.split('(')[-1].strip(')'))

            # Update sounddevice settings
            sd.default.device = (input_device_index, output_device_index)
            
            # Force sounddevice to use new settings
            sd.stop()
            
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
            elif self.voice_engine == 'aws-polly':
                self.voice = self.aws_polly_voice_dict.get(self.voice, self.voice)

            # Update the OutputManager via the controller
            self.controller.output_manager.update_settings(
                chatbox_ip=self.chatbox_ip,
                chatbox_port=self.chatbox_port,
                voice_engine=self.voice_engine,
                voice=self.voice,
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
        except Exception as e:
            logging.error(f"Error saving settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

    def update_voice_options(self, *args):
        """Updates the voice options based on the selected engine and language."""
        try:
            selected_engine = self.voice_engine_var.get()
            selected_language = self.language_var.get()
            
            if selected_engine == 'edge-tts':
                voices = self.get_edge_tts_voices(selected_language)
            elif selected_engine == 'aws-polly':
                voices = self.get_aws_polly_voices(selected_language)
            else:
                voices = []
                
            self.voice_combobox['values'] = voices
            # Only set to first voice if current selection is invalid
            if not self.voice_var.get() or self.voice_var.get() not in voices:
                self.voice_var.set(voices[0] if voices else '')
                
        except Exception as e:
            logging.error(f"Error updating voice options: {e}")

    def get_available_languages(self):
        """Returns a list of available languages for the selected voice engine."""
        selected_engine = self.voice_engine_var.get()
        if (selected_engine == 'edge-tts'):
            voices = self.get_all_edge_tts_voices()
            languages = set()
            for voice in voices:
                # Only include English languages
                if voice['Locale'].startswith('en-'):
                    languages.add(voice['Locale'])
            return sorted(languages)
        elif selected_engine == 'aws-polly':
            return ['en-US', 'en-GB', 'en-AU', 'en-IN']  # Restrict to English variants
        else:
            return []

    def get_all_edge_tts_voices(self):
        """Retrieves all voices from edge-tts."""
        import edge_tts
        voices = asyncio.run(edge_tts.list_voices())
        return voices

    def get_edge_tts_voices(self, selected_language):
        """Returns a list of available voices for Edge TTS given a language."""
        voices = self.get_all_edge_tts_voices()
        voice_names = []
        self.edge_voice_dict = {}
        for voice in voices:
            if voice['Locale'] == selected_language:
                voice_names.append(voice['FriendlyName'])
                self.edge_voice_dict[voice['FriendlyName']] = voice['ShortName']
        return voice_names

    def get_aws_polly_voices(self, selected_language):
        """Returns a list of available voices for AWS Polly given a language."""
        # ...existing code to retrieve AWS Polly voices...
        pass

    def get_audio_devices(self, input=False, output=False):
        """Returns a list of available audio devices."""
        devices = sd.query_devices()
        device_names = set()
        for idx, device in enumerate(devices):
            # Skip MME devices and focus on Windows DirectSound/WASAPI
            if 'MME' in device['name']:
                continue
            # Skip disabled and unwanted devices
            if any(x in device['name'] for x in ['(Disabled)', '(Hidden)', 'Microsoft Sound Mapper']):
                continue
            name = f"{device['name']} ({idx})"
            if input and device['max_input_channels'] > 0:
                device_names.add(name)
            if output and device['max_output_channels'] > 0:
                device_names.add(name)
        return sorted(device_names)

    def stop_audio(self):
        """Stops audio playback."""
        self.controller.stop_audio()

    def on_closing(self):
        """Handles actions when the window is closed."""
        self.root.destroy()
        sys.exit(0)

    def run(self):
        """Runs the main loop of the UI."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
