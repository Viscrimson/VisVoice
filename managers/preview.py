# uimanager.py

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import logging
import re
from spellchecker import SpellChecker
import threading
import time
import sounddevice as sd
import pyttsx3

class UIManager:
    def __init__(self, queue, ttt_manager, stt_manager, approval_manager, tts_manager, ttc_manager, font_manager):
        self.queue = queue
        self.ttt_manager = ttt_manager
        self.stt_manager = stt_manager
        self.approval_manager = approval_manager
        self.tts_manager = tts_manager
        self.ttc_manager = ttc_manager
        self.font_manager = font_manager

        self.root = tk.Tk()
        self.root.title('Vis Voice')
        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Initialize settings
        self.input_device = None
        self.output_device = None
        self.chatbox_ip = '127.0.0.1'
        self.chatbox_port = 9000
        self.voice_engine = 'pyttsx3'
        self.voice = None
        self.engine = None

        self.load_default_settings()

    def load_default_settings(self):
        """Loads default settings."""
        # Initialize pyttsx3 engine
        self.engine = pyttsx3.init()
        voices = self.engine.getProperty('voices')
        self.voice = voices[0].id  # Default to the first voice
        self.engine.setProperty('voice', self.voice)
        # Set default input and output devices
        self.input_device = sd.default.device[0]
        self.output_device = sd.default.device[1]

    def create_widgets(self):
        """Initializes the main UI."""
        self.create_main_ui()

    def create_main_ui(self):
        """Creates the main UI with the specified layout."""
        # Display Section at the Top
        display_frame = ttk.Frame(self.root)
        display_frame.pack(side='top', fill='x', padx=10, pady=5)

        # Current Settings Label
        self.current_settings_label = ttk.Label(display_frame, text=self.get_current_settings_text())
        self.current_settings_label.pack(side='left')

        # Settings Button on the Right
        settings_button = ttk.Button(display_frame, text='Settings', command=self.show_settings)
        settings_button.pack(side='right')

        # Textbox in the Middle
        text_frame = ttk.Frame(self.root)
        text_frame.pack(expand=True, fill='both', padx=10, pady=5)

        self.textbox = tk.Text(text_frame, wrap='word', height=10, width=80)
        self.textbox.pack(side='left', expand=True, fill='both')
        self.textbox.bind('<KeyRelease>', self.check_spelling)
        self.textbox.bind('<Button-3>', self.show_suggestions)
        self.textbox.bind('<Return>', self.submit_text)

        scrollbar = ttk.Scrollbar(text_frame, command=self.textbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.textbox.config(yscrollcommand=scrollbar.set)

        # Buttons at the Bottom
        button_frame = ttk.Frame(self.root)
        button_frame.pack(side='bottom', fill='x', pady=10)

        # Center the buttons
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)

        cancel_button = ttk.Button(button_frame, text='Cancel', command=self.cancel_text)
        cancel_button.grid(row=0, column=0, sticky='e')

        send_button = ttk.Button(button_frame, text='Send', command=self.submit_text)
        send_button.grid(row=0, column=1)

        # Start a thread to process the queue
        threading.Thread(target=self.process_queue, daemon=True).start()

        # Initialize spellchecker
        self.spellchecker = SpellChecker()

    def get_current_settings_text(self):
        """Returns a string representing the current important settings."""
        return f"Input Device: {self.input_device}, Output Device: {self.output_device}, Voice Engine: {self.voice_engine}"

    def update_current_settings_label(self):
        """Updates the current settings label."""
        self.current_settings_label.config(text=self.get_current_settings_text())

    def submit_text(self, event=None):
        """Submits the text from the textbox."""
        text = self.textbox.get("1.0", tk.END).strip()
        if text:
            self.ttt_manager.submit_text(text)
            self.textbox.delete("1.0", tk.END)
            logging.info(f'Text submitted: {text}')
        return 'break'  # Prevents the default newline behavior

    def cancel_text(self):
        """Clears the text in the textbox."""
        self.textbox.delete("1.0", tk.END)
        logging.info('Text input canceled.')

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
            word_start = self.textbox.search(r'\b', index, backwards=True, regexp=True)
            word_end = self.textbox.search(r'\b', index, forwards=True, regexp=True)
            word = self.textbox.get(word_start, word_end).strip()
            if word.lower() in self.spellchecker:
                return
            suggestions = self.spellchecker.candidates(word.lower())
            if suggestions:
                menu = tk.Menu(self.root, tearoff=0)
                for suggestion in suggestions:
                    menu.add_command(
                        label=suggestion,
                        command=lambda s=suggestion: self.replace_word(word_start, word_end, s)
                    )
                menu.post(event.x_root, event.y_root)
        except Exception as e:
            logging.error(f"Error showing suggestions: {e}")

    def replace_word(self, start, end, replacement):
        """Replaces the misspelled word with the selected suggestion."""
        self.textbox.delete(start, end)
        self.textbox.insert(start, replacement)

    def process_queue(self):
        """Processes items in the queue."""
        while True:
            if self.queue:
                item = self.queue.pop(0)
                text, input_type = item
                # Implement approval logic if needed
                approved = True  # Assuming auto-approval for simplicity
                if approved:
                    logging.info(f'Item approved: {text}')
                    # Handle text longer than 144 characters
                    text_chunks = self.split_text(text, 144)
                    # Synchronize outputs
                    threading.Thread(target=self.speak_and_send, args=(text_chunks,)).start()
                else:
                    logging.info(f'Item rejected: {text}')
            else:
                # No items in the queue, sleep briefly to prevent tight loop
                time.sleep(0.1)

    def split_text(self, text, max_length):
        """Splits text into chunks of a specified maximum length."""
        words = text.split()
        chunks = []
        current_chunk = ''
        for word in words:
            if len(current_chunk) + len(word) + 1 <= max_length:
                current_chunk += ' ' + word if current_chunk else word
            else:
                chunks.append(current_chunk)
                current_chunk = word
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

    def speak_and_send(self, text_chunks):
        """Speaks the text and sends it to VRChat in chunks."""
        for chunk in text_chunks:
            # Speak the chunk
            self.tts_manager.process_text(chunk)
            # Send the chunk to VRChat
            self.ttc_manager.process_text(chunk)
            # Wait for a specified duration before sending the next chunk
            time.sleep(1)  # Adjust the sleep duration as needed

    def show_settings(self):
        """Displays the settings window."""
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title('Settings')

        # Input Audio Device
        ttk.Label(self.settings_window, text='Input Audio Device:').grid(row=0, column=0, padx=5, pady=5, sticky='E')
        input_devices = self.get_audio_devices(input=True)
        self.input_device_var = tk.StringVar(value=self.input_device)
        ttk.Combobox(self.settings_window, textvariable=self.input_device_var, values=input_devices).grid(row=0, column=1, padx=5, pady=5, sticky='W')

        # Output Audio Device
        ttk.Label(self.settings_window, text='Output Audio Device:').grid(row=1, column=0, padx=5, pady=5, sticky='E')
        output_devices = self.get_audio_devices(output=True)
        self.output_device_var = tk.StringVar(value=self.output_device)
        ttk.Combobox(self.settings_window, textvariable=self.output_device_var, values=output_devices).grid(row=1, column=1, padx=5, pady=5, sticky='W')

        # Chatbox IP
        ttk.Label(self.settings_window, text='Chatbox IP:').grid(row=2, column=0, padx=5, pady=5, sticky='E')
        self.chatbox_ip_var = tk.StringVar(value=self.chatbox_ip)
        ttk.Entry(self.settings_window, textvariable=self.chatbox_ip_var).grid(row=2, column=1, padx=5, pady=5, sticky='W')

        # Chatbox Port
        ttk.Label(self.settings_window, text='Chatbox Port:').grid(row=3, column=0, padx=5, pady=5, sticky='E')
        self.chatbox_port_var = tk.IntVar(value=self.chatbox_port)
        ttk.Entry(self.settings_window, textvariable=self.chatbox_port_var).grid(row=3, column=1, padx=5, pady=5, sticky='W')

        # Voice Engine
        ttk.Label(self.settings_window, text='Voice Engine:').grid(row=4, column=0, padx=5, pady=5, sticky='E')
        voice_engines = ['pyttsx3']
        self.voice_engine_var = tk.StringVar(value=self.voice_engine)
        ttk.Combobox(self.settings_window, textvariable=self.voice_engine_var, values=voice_engines, state='readonly').grid(row=4, column=1, padx=5, pady=5, sticky='W')
        self.voice_engine_var.trace('w', self.update_voice_options)

        # Voice Options
        ttk.Label(self.settings_window, text='Voice:').grid(row=5, column=0, padx=5, pady=5, sticky='E')
        voices = self.get_pyttsx3_voices()
        self.voice_var = tk.StringVar(value=self.voice)
        self.voice_combobox = ttk.Combobox(self.settings_window, textvariable=self.voice_var, values=voices)
        self.voice_combobox.grid(row=5, column=1, padx=5, pady=5, sticky='W')

        # Save and Cancel Buttons
        save_button = ttk.Button(self.settings_window, text='Save', command=self.save_settings)
        save_button.grid(row=6, column=0, padx=5, pady=10)
        cancel_button = ttk.Button(self.settings_window, text='Cancel', command=self.settings_window.destroy)
        cancel_button.grid(row=6, column=1, padx=5, pady=10)

    def get_audio_devices(self, input=False, output=False):
        """Returns a list of available audio devices."""
        devices = sd.query_devices()
        device_names = set()
        for device in devices:
            if input and device['max_input_channels'] > 0:
                device_names.add(device['name'])
            if output and device['max_output_channels'] > 0:
                device_names.add(device['name'])
        # Filter out duplicates and limit to important devices (e.g., WDM devices)
        device_names = [name for name in device_names if 'WDM' in name]
        return sorted(device_names)

    def get_pyttsx3_voices(self):
        """Returns a list of available voices for pyttsx3."""
        voices = self.engine.getProperty('voices')
        voice_names = [voice.id for voice in voices]
        return voice_names

    def update_voice_options(self, *args):
        """Updates the voice options based on the selected voice engine."""
        selected_engine = self.voice_engine_var.get()
        if selected_engine == 'pyttsx3':
            voices = self.get_pyttsx3_voices()
            self.voice_combobox.config(values=voices)
            if self.voice not in voices:
                self.voice_var.set(voices[0] if voices else '')
        else:
            # Handle other voice engines if implemented
            pass

    def save_settings(self):
        """Saves the settings from the settings window."""
        self.input_device = self.input_device_var.get()
        self.output_device = self.output_device_var.get()
        self.chatbox_ip = self.chatbox_ip_var.get()
        self.chatbox_port = self.chatbox_port_var.get()
        self.voice_engine = self.voice_engine_var.get()
        self.voice = self.voice_var.get()

        # Apply the settings
        sd.default.device = (self.input_device, self.output_device)
        self.ttc_manager.client.address = (self.chatbox_ip, self.chatbox_port)
        self.engine.setProperty('voice', self.voice)

        # Update the current settings label
        self.update_current_settings_label()

        logging.info('Settings have been saved.')
        self.settings_window.destroy()

    def on_closing(self):
        """Handles actions when the window is closed."""
        self.root.destroy()

    def run(self):
        """Runs the main loop of the UI."""
        self.root.mainloop()
