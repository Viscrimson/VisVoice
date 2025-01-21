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

# Engine Names and Types
ENGINES = {
    'Polly Standard': 'Amazon Polly (Standard)',
    'Polly Neural': 'Amazon Polly (Neural)',
    'Polly Generative': 'Amazon Polly (Generative)'
}

# English Language Codes
ENGLISH_VARIANTS = {
    'Polly Standard': ['en-AU', 'en-GB', 'en-IN', 'en-US'],
    'Polly Neural': ['en-AU', 'en-GB', 'en-IN', 'en-IE', 'en-NZ', 'en-ZA', 'en-US'],
    'Polly Generative': ['en-AU', 'en-GB', 'en-IN', 'en-ZA', 'en-US']
}

# Voice Mappings
EDGE_VOICES = {
    'en-US': ['Jenny', 'Guy', 'Ana', 'Christopher', 'Eric', 'Michelle', 'Roger', 'Steffan'],
    'en-GB': ['Ryan', 'Sonia', 'Nancy', 'LibbyNeural'],
    'en-AU': ['Natasha', 'William'],
    'en-CA': ['Clara', 'Liam'],
    'en-IN': ['Neerja', 'Prabhat']
}

POLLY_STANDARD_VOICES = {
    'en-AU': ['Nicole', 'Russell'],
    'en-GB': ['Amy', 'Emma', 'Brian'],  # Removed 'Arthur'
    'en-IN': ['Aditi', 'Raveena'],      # Added 'Raveena'
    'en-US': ['Ivy', 'Joanna', 'Kendra']  # Removed 'Gregory', 'Kevin', 'Ruth', 'Stephen', 'Patrick'
}

POLLY_NEURAL_VOICES = {
    'en-AU': ['Olivia'],
    'en-GB': ['Amy', 'Emma', 'Brian', 'Arthur'],  # Added 'Arthur'
    'en-IN': ['Kajal'],                           # Removed 'Aditi', 'Raveena'
    'en-IE': ['Niamh'],
    'en-NZ': ['Aria'],
    'en-ZA': ['Ayanda'],
    'en-US': [
        'Danielle', 'Ivy', 'Joanna', 'Kendra', 'Kimberly', 'Salli',
        'Joey', 'Justin', 'Kevin', 'Matthew', 'Ruth', 'Stephen', 'Gregory'
        # Removed 'Geraint'
    ]
}

POLLY_GENERATIVE_VOICES = {
    'en-AU': ['Olivia'],
    'en-GB': ['Amy', 'Emma', 'Brian', 'Arthur'],  # Added 'Emma', 'Brian', 'Arthur'
    'en-IN': ['Kajal'],
    'en-ZA': ['Ayanda'],  # 'Danielle' also can be removed or tested if needed
    'en-US': ['Danielle', 'Joanna', 'Matthew', 'Ruth', 'Stephen']
}

class UIManager:
    def __init__(self):
        # Initialize window
        self.root = tk.Tk()
        self.root.title("Vis Voice")
        self.setup_window_geometry()

        # Initialize managers
        self.input_manager = InputManager()
        self.output_manager = OutputManager()

        # Initialize all variables first
        self.init_variables()  # This needs to run before load_settings()
        
        # Load settings after variables are initialized
        self.load_settings()
        
        # Create UI elements
        self.create_widgets()
        self.apply_dark_mode()
        
        # Initialize additional features
        self.setup_spellchecker()
        self.setup_voice_capture()
        self.setup_hotkey_listener()
        self.is_speaking = False

    def init_variables(self):
        """Initialize all variables needed for the UI"""
        # Settings variables
        self.input_device = None
        self.output_device = None
        self.chatbox_ip = '127.0.0.1'
        self.chatbox_port = 9000
        self.voice_engine = 'Polly Standard'
        self.voice = None
        self.language = 'en-US'
        self.hotkey = '`'
        
        # Initialize output options dictionary
        self.output_options = {
            'Voice Output': True,
            'Chatbox Output': True
        }
        
        # State variables
        self.running = True
        self.voice_capture_active = False
        self.is_typing = False
        self.max_chatbox_length = 144
        self.is_speaking = False

        # Voice engine variables
        self.voice_engine_var = tk.StringVar(value=list(ENGINES.keys())[0])
        self.language_var = tk.StringVar()
        self.voice_var = tk.StringVar()
        
        # Device variables
        self.output_device_var = tk.StringVar()
        self.input_device_var = tk.StringVar()
        
        # UI variables
        self.chatbox_ip_var = tk.StringVar(value=self.chatbox_ip)
        self.chatbox_port_var = tk.IntVar(value=self.chatbox_port)
        self.hotkey_var = tk.StringVar(value=self.hotkey)
        self.voice_output_var = tk.BooleanVar(value=self.output_options['Voice Output'])
        self.chatbox_output_var = tk.BooleanVar(value=self.output_options['Chatbox Output'])

        # Initialize empty presets dictionary
        self.presets = {}
        self.typing_indicator_enabled_var = tk.BooleanVar(value=True)

    def create_widgets(self):
        # Main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill='both', expand=True)

        # Settings frame
        self.settings_frame = ttk.LabelFrame(self.main_frame, text="Settings")
        self.settings_frame.pack(fill='x', padx=5, pady=5)

        # Chatbox IP input
        ttk.Label(self.settings_frame, text="Chatbox IP:").pack(side='left', padx=5)
        self.chatbox_ip_entry = ttk.Entry(
            self.settings_frame, 
            textvariable=self.chatbox_ip_var,
            width=20
        )
        self.chatbox_ip_entry.pack(side='left', padx=5)

        # Enable Typing Indicator checkbox
        self.typing_indicator_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.settings_frame,
            text="Enable Typing Indicator",
            variable=self.typing_indicator_enabled_var
        ).pack(side='left', padx=5)

        # Voice settings
        self.create_voice_settings()
        
        # Add presets frame
        presets_frame = ttk.LabelFrame(self.main_frame, text="Voice Presets")
        presets_frame.pack(fill='x', padx=5, pady=5)
        
        # Add preset buttons
        for preset_name in self.presets:
            self.create_preset_button(presets_frame, preset_name)

        # Add key bindings for typing indicator
        self.textbox.bind('<Key>', self.on_typing)
        self.textbox.bind('<KeyRelease>', self.on_typing_stop)

    def create_preset_button(self, parent, preset_name):
        """Creates a preset button."""
        button = ttk.Button(parent, text=preset_name, command=lambda: self.apply_preset(preset_name))
        button.pack(side='left', padx=5, pady=5)

        # Optionally, store buttons if needed for further manipulation
        self.preset_buttons[preset_name] = button

    def create_voice_settings(self):
        voice_frame = ttk.LabelFrame(self.main_frame, text="Voice Settings")
        voice_frame.pack(fill='x', padx=5, pady=5)

        # Engine selection
        ttk.Label(voice_frame, text="Engine:").pack(anchor='w', padx=5)
        self.engine_combo = ttk.Combobox(
            voice_frame,
            textvariable=self.voice_engine_var,
            values=list(ENGINES.keys()),
            state='readonly'
        )
        self.engine_combo.pack(fill='x', padx=5, pady=2)

        # Language selection
        ttk.Label(voice_frame, text="Language:").pack(anchor='w', padx=5)
        self.language_combo = ttk.Combobox(
            voice_frame,
            textvariable=self.language_var,
            state='readonly'
        )
        self.language_combo.pack(fill='x', padx=5, pady=2)

        # Voice selection
        ttk.Label(voice_frame, text="Voice:").pack(anchor='w', padx=5)
        self.voice_combo = ttk.Combobox(
            voice_frame,
            textvariable=self.voice_var,
            state='readonly'
        )
        self.voice_combo.pack(fill='x', padx=5, pady=2)

        # Bind events
        self.voice_engine_var.trace_add('write', self.update_language_options)
        self.language_var.trace_add('write', self.update_voice_options)
        self.chatbox_ip_var.trace_add('write', self.save_settings)

    def save_settings(self, *args):
        """Saves the settings when any setting is changed."""
        try:
            self.output_options['Voice Output'] = self.voice_output_var.get()
            self.output_options['Chatbox Output'] = self.chatbox_output_var.get()
            self.voice_engine = self.voice_engine_var.get()
            self.language = self.language_var.get()
            self.voice = self.voice_var.get()
            self.chatbox_ip = self.chatbox_ip_var.get()
            self.chatbox_port = self.chatbox_port_var.get()
            self.hotkey = self.hotkey_var.get()
            
            self.output_manager.update_settings(
                self.chatbox_ip,
                self.chatbox_port,
                self.voice_engine,
                self.voice
            )
            self.save_settings_to_file()
        except Exception as e:
            logging.error(f"Error saving settings: {e}")

    def setup_window_geometry(self):
        """Configure the main window geometry"""
        window_width = 800
        window_height = 600
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def setup_spellchecker(self):
        """Initialize spellchecker"""
        self.spellchecker = SpellChecker()
        self.spellcheck_delay = 1000
        self.spellcheck_job = None

    def setup_voice_capture(self):
        """Setup voice capture thread"""
        threading.Thread(target=self.voice_input_loop, daemon=True).start()

    def apply_initial_settings(self):
        """Apply initial settings after UI is loaded"""
        # Set voice engine first
        self.voice_engine_var.set(self.voice_engine)
        
        # Update language options based on engine
        self.update_language_options()
        
        # Set language
        if self.language:
            self.language_var.set(self.language)
        
        # Update voice options based on language
        self.update_voice_options()
        
        # Set voice if available
        if self.voice:
            self.voice_var.set(self.voice)

    def apply_dark_mode(self):
        """Apply dark mode theme"""
        style = ttk.Style()
        
        # Define colors
        dark_bg = "#2e2e2e"       # Main background
        dark_fg = "#ffffff"        # Main text color
        darker_bg = "#1e1e1e"     # Darker background
        highlight_bg = "#3e3e3e"   # Highlight color
        button_bg = "#c0c0c0"      # Light gray for buttons
        button_fg = "#000000"      # Black text for buttons
        dropdown_bg = "#ffffff"     # White background for dropdowns
        dropdown_fg = "#000000"     # Black text for dropdowns
        entry_bg = "#ffffff"        # White background for entry fields
        entry_fg = "#000000"        # Black text for entry fields
        
        # Configure base style
        style.configure(".", 
            background=dark_bg,
            foreground=dark_fg,
            fieldbackground=darker_bg
        )
        
        # Configure specific elements
        style.configure("TButton", 
            background=button_bg,
            foreground=button_fg,
            padding=5
        )
        
        style.map("TButton",
            background=[("active", "#d0d0d0")],  # Lighter gray when pressed
            foreground=[("active", "#000000")]   # Keep text black when pressed
        )
        
        style.configure("TEntry", 
            fieldbackground=entry_bg,
            foreground=entry_fg
        )
        
        style.configure("TCombobox", 
            fieldbackground=dropdown_bg,
            foreground=dropdown_fg,
            selectbackground=highlight_bg,
            selectforeground=dark_fg,
            background=dropdown_bg
        )
        
        style.map("TCombobox",
            fieldbackground=[("readonly", dropdown_bg)],
            foreground=[("readonly", dropdown_fg)],
            selectbackground=[("readonly", highlight_bg)],
            selectforeground=[("readonly", dark_fg)]
        )
        
        # Make dropdown list readable
        self.root.option_add('*TCombobox*Listbox.background', dropdown_bg)
        self.root.option_add('*TCombobox*Listbox.foreground', dropdown_fg)
        self.root.option_add('*TCombobox*Listbox.selectBackground', highlight_bg)
        self.root.option_add('*TCombobox*Listbox.selectForeground', dark_fg)
        
        # Configure text area
        self.textbox.configure(
            bg=darker_bg,
            fg=dark_fg,
            insertbackground=dark_fg,
            selectbackground=highlight_bg,
            selectforeground=dark_fg
        )
        
        # Configure checkbuttons
        style.configure("TCheckbutton",
            background=dark_bg,
            foreground=dark_fg
        )
        
        style.map("TCheckbutton",
            background=[("active", dark_bg)],
            foreground=[("active", dark_fg)]
        )
        
        # Configure the root window
        self.root.configure(bg=dark_bg)

    def load_settings(self):
        """Loads settings from config.ini or sets defaults."""
        config = configparser.ConfigParser()
        config.read('config.ini')  # Changed from settings.ini to config.ini

        if 'Settings' in config:
            settings = config['Settings']
            self.input_device = settings.get('input_device', self.get_default_input_device())
            self.output_device = settings.get('output_device', self.get_default_output_device())
            self.chatbox_ip = settings.get('chatbox_ip', '127.0.0.1')
            self.chatbox_port = settings.getint('chatbox_port', 9000)
            self.voice_engine = settings.get('voice_engine', 'Polly Standard')  # Changed default to Polly Standard
            self.voice = settings.get('voice')
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
            # Store presets exactly as they appear in config
            self.presets = dict(config['Presets'])
        else:
            # Default presets with consistent naming
            self.presets = {
                'preset 1': 'edge-tts|en-GB-SoniaNeural',
                'preset 2': 'edge-tts|en-GB-MaisieNeural',
                'preset 3': 'edge-tts|en-AU-NatashaNeural',
                'preset 4': 'edge-tts|en-US-EmmaMultilingualNeural',
                'preset 5': 'polly|Salli|standard',
                'preset 6': 'polly|Ivy|neural',
                'preset 7': 'polly|Amy|neural',
                'preset 8': 'polly|Brian|neural'
            }

    def save_settings_to_file(self):
        """Saves settings to config.ini."""
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
        
        # Save presets
        config['Presets'] = self.presets
        
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
            
        logging.info('Settings saved to config.ini')

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
        
        # Add spacebar binding for stop audio
        self.root.bind('<space>', self.handle_spacebar)

        # Preset buttons section
        preset_frame = ttk.Frame(self.root)
        preset_frame.pack(fill='x', padx=10, pady=5)
        
        # Create preset grid (2 rows of 4 buttons)
        self.preset_buttons = {}  # Store buttons for later reference
        for i in range(8):
            preset_name = f"preset {i+1}"  # Changed from "Preset" to "preset " to match config
            voice = self.presets.get(preset_name, '')  # Removed .lower() since we'll maintain case consistency
            btn = ttk.Button(preset_frame, text=preset_name.title(), 
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
        self.col2_frame = col2_frame
        self.init_voice_selection()

        # Now add the trace callbacks
        self.voice_engine_var.trace('w', self.save_settings)
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
        # Change corrected text color to yellow for better visibility on dark background
        self.textbox.tag_config("corrected", foreground="#ffff00")  # Bright yellow

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
        # Stop typing indicator before sending
        self.output_manager.typing_indicator.stop_typing()
        text = self.textbox.get("1.0", tk.END).strip()
        if text:
            self.output_manager.send_to_chatbox(text)
            self.output_manager.speak_text(text)
            self.textbox.delete("1.0", tk.END)
            logging.info('Text submitted and spoken.')
        else:
            logging.info('No text to submit.')
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
            threading.Thread(target=self.voice_input_loop, daemon=True).start()
            logging.info("Voice capture started.")
        else:
            self.toggle_voice_button.config(text='Start Voice Capture')
            self.running = False
            logging.info("Voice capture stopped.")

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
                logging.debug("Voice capture active, attempting to get input...")
                text = self.input_manager.get_voice_input()
                if text:
                    logging.info(f"Voice input received: {text}")
                    # Update UI in thread-safe way
                    self.root.after(0, lambda: self.textbox.insert(tk.END, text + ' '))
                else:
                    logging.debug("No text transcribed from voice input")
            else:
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
        self.is_speaking = True
        for chunk in chunks:
            if not self.running or not self.is_speaking:  # Check if we should stop
                break
            # Output via TTS if enabled
            if self.output_options.get('Voice Output', False):
                self.output_manager.speak_text(chunk)
            # Send to chatbox if enabled
            if self.output_options.get('Chatbox Output', False):
                self.output_manager.send_to_chatbox(chunk)
            # Wait for 10 seconds before processing next chunk
            if self.is_speaking:  # Only wait if we haven't stopped
                time.sleep(10)
        self.is_speaking = False

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
        elif self.voice_engine.startswith('polly'):
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
        wasapi_hostapi = sd.default.hostapi
        devices = sd.query_devices()
        device_names = []
        for idx, dev in enumerate(devices):
            if dev['hostapi'] == wasapi_hostapi:
                if (input and dev['max_input_channels'] > 0) or (output and dev['max_output_channels'] > 0):
                    device_names.append(f"{dev['name']} ({idx})")
        return device_names

    def update_voice_options(self, *args):
        """Updates voice options based on selected engine and language"""
        engine = self.voice_engine_var.get()
        language = self.language_var.get()
        
        voice_map = {
            'Edge TTS': EDGE_VOICES,
            'Polly Standard': POLLY_STANDARD_VOICES,
            'Polly Neural': POLLY_NEURAL_VOICES,
            'Polly Generative': POLLY_GENERATIVE_VOICES
        }
        
        voices = voice_map.get(engine, {}).get(language, [])
        self.voice_combobox['values'] = voices
        if voices:
            self.voice_var.set(voices[0])
        else:
            self.voice_var.set('')

    def get_available_languages(self):
        """Returns a list of available languages for the selected voice engine."""
        selected_engine = self.voice_engine_var.get()
        if selected_engine == 'edge-tts':
            try:
                # Define English locales
                english_locales = ['en-US', 'en-GB', 'en-AU', 'en-CA', 'en-IE', 'en-IN', 'en-NZ']
                voices = self.get_all_edge_tts_voices()
                languages = set()
                for voice in voices:
                    if 'Locale' in voice and voice['Locale'] in english_locales:
                        languages.add(voice['Locale'])
                return sorted(languages)
            except Exception as e:
                logging.error(f"Error getting languages: {e}")
                return []
        elif selected_engine.startswith('polly'):
            return self.get_polly_languages()
        else:
            return []

    def get_polly_languages(self):
        """Returns a list of available languages for Amazon Polly."""
        import boto3
        polly_client = boto3.client('polly')
        
        # Get languages from all engine types
        all_voices = []
        for engine in ['standard', 'neural', 'generative']:
            try:
                response = polly_client.describe_voices(Engine=engine)
                all_voices.extend(response['Voices'])
            except:
                continue

        # Filter for English languages only
        languages = {voice['LanguageCode'] for voice in all_voices 
                    if voice['LanguageCode'].startswith('en-')}
        return sorted(languages)

    def get_polly_voices(self, engine_type):
        """Returns a list of available voices for Amazon Polly by engine type."""
        import boto3
        polly_client = boto3.client('polly')
        
        # Use the engine type directly as it's already in the correct format
        try:
            response = polly_client.describe_voices(Engine=engine_type)
            voices = response['Voices']
            
            # Filter for English voices only
            english_voices = [voice for voice in voices if voice['LanguageCode'].startswith('en-')]
            
            # Sort and format voice names
            voice_names = []
            self.polly_voice_dict = {}
            
            for voice in english_voices:
                display_name = f"{voice['Name']} ({engine_type})"
                voice_names.append(display_name)
                # Store the voice ID with engine type
                self.polly_voice_dict[display_name] = f"{engine_type}|{voice['Id']}"
            
            return sorted(voice_names)
        except Exception as e:
            logging.error(f"Error getting Polly {engine_type} voices: {e}")
            return []

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
        """Stops audio playback and clears the queue."""
        self.is_speaking = False  # Stop future chunks from processing
        self.output_manager.stop_audio()  # Stop current audio

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

    def apply_preset(self, preset_name):
        """Applies a voice preset based on the preset name."""
        preset = self.presets.get(preset_name)
        if preset:
            engine, voice = preset.split('|')
            self.voice_engine_var.set(engine)
            self.voice_var.set(voice)
            logging.info(f"Applied preset '{preset_name}': Engine={engine}, Voice={voice}")
        else:
            logging.error(f"Preset '{preset_name}' not found.")

    def apply_preset(self, voice, preset_name):
        """Applies the selected voice preset."""
        if not voice:
            logging.warning(f"No voice assigned to preset: {preset_name}")
            return

        try:
            # Split preset into engine and voice_id
            if '|' not in voice:
                logging.error(f"Invalid preset format: {voice}")
                return
                
            engine, voice_id = voice.split('|')
            
            # Update voice engine first
            self.voice_engine_var.set(engine)
            
            # Different handling for Edge TTS and Polly
            if engine == 'edge-tts':
                # Edge TTS format: "en-US-JennyNeural" -> "en-US"
                language = '-'.join(voice_id.split('-')[:2])
                self.language_var.set(language)
                # Wait for voice list to update
                self.root.after(100, lambda: self.set_edge_voice(voice_id))
            elif engine.startswith('polly'):
                # Polly format is simpler, just the voice name
                self.root.after(100, lambda: self.set_polly_voice(voice_id))
            
        except Exception as e:
            logging.error(f"Error applying preset: {e}")

    def set_edge_voice(self, voice_id):
        """Set Edge TTS voice after options are updated"""
        self.update_voice_options()  # Refresh voice list
        voices = self.voice_combobox['values']
        for voice in voices:
            if voice_id in voice:
                self.voice_var.set(voice)
                self.save_settings()
                break

    def set_polly_voice(self, voice_id):
        """Set Polly voice after options are updated"""
        self.update_voice_options()  # Refresh voice list
        voices = self.voice_combobox['values']
        for voice in voices:
            if voice_id in voice:
                self.voice_var.set(voice)
                self.voice = voice_id
                self.save_settings()
                break
        # Determine engine based on voice selection
        if voice_id in POLLY_GENERATIVE_VOICES.get(self.language, []):
            self.voice_engine = 'Polly Generative'
        elif voice_id in POLLY_NEURAL_VOICES.get(self.language, []):
            self.voice_engine = 'Polly Neural'
        else:
            self.voice_engine = 'Polly Standard'
        self.voice_var.set(voice_id)
        logging.info(f"Set voice to '{voice_id}' with engine '{self.voice_engine}'")

    def update_preset(self, button, voice):
        """Updates the preset with the new voice."""
        preset_name = button['text'].lower()  # Convert display text to lowercase for consistency
        current_engine = self.voice_engine_var.get()
        
        # Get current voice ID based on engine
        voice_id = None
        if current_engine == 'edge-tts':
            voice_id = self.edge_voice_dict.get(self.voice_var.get(), '')
            if voice_id:
                self.presets[preset_name] = f"{current_engine}|{voice_id}"
        elif current_engine.startswith('polly'):
            voice_id = self.polly_voice_dict.get(self.voice_var.get(), '')
            if voice_id:
                self.presets[preset_name] = f"{current_engine}|{voice_id}"
        
        if voice_id:
            self.save_settings_to_file()
            logging.info(f"Updated preset '{preset_name}' to {self.presets[preset_name]}")
        else:
            logging.warning(f"Cannot update preset '{preset_name}': No voice selected")

    def apply_preset(self, voice, preset_name):
        """Applies the selected voice preset."""
        if not voice:
            logging.warning(f"No voice assigned to preset: {preset_name}")
            return
        
        try:
            engine, voice_id = voice.split('|')
            
            # Update voice engine
            self.voice_engine_var.set(engine)
            
            # Update language based on voice ID
            language = self.get_language_from_voice_id(voice_id, engine)
            if language:
                self.language_var.set(language)
            
            # Wait for voice options to update
            self.root.after(100, lambda: self.set_voice_delayed(voice_id))
            
        except ValueError:
            logging.error(f"Invalid preset format: {voice}")

    def get_language_from_voice_id(self, voice_id, engine):
        """Extract language code from voice ID based on engine"""
        if engine == 'edge-tts':
            # Edge TTS format: "en-US-JennyNeural" -> "en-US"
            return '-'.join(voice_id.split('-')[:2])
        elif engine.startswith('polly'):
            # Get language code from Polly voice ID
            try:
                import boto3
                polly_client = boto3.client('polly')
                # Extract actual voice ID if it includes engine type
                if '|' in voice_id:
                    voice_id = voice_id.split('|')[1]
                response = polly_client.describe_voices()
                for voice in response['Voices']:
                    if voice['Id'] == voice_id:
                        return voice['LanguageCode']
            except Exception as e:
                logging.error(f"Error getting Polly voice language: {e}")
            return 'en-US'  # Default if not found
        return None

    def set_voice_delayed(self, voice_id):
        """Set voice after options are updated"""
        voices = self.voice_combobox['values']
        for voice in voices:
            if voice_id in voice:
                self.voice_var.set(voice)
                self.save_settings()
                break

    def configure_preset(self, event, button):
        """Shows configuration menu for preset button."""
        menu = tk.Menu(self.root, tearoff=0)
        
        # Get current voice selection
        current_voice = self.voice_var.get()  # Changed from edge_voice_dict lookup
        
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
        preset_name = button['text'].lower()
        current_engine = self.voice_engine_var.get()
        
        # Get current voice ID based on engine
        if current_engine == 'edge-tts':
            voice_id = self.edge_voice_dict.get(self.voice_var.get(), '')
        else:  # polly
            voice_id = self.polly_voice_dict.get(self.voice_var.get(), '')
        
        if voice_id:
            # Save in format "engine|voice_id"
            self.presets[preset_name] = f"{current_engine}|{voice_id}"
            self.save_settings_to_file()
            logging.info(f"Updated preset '{preset_name}' to {current_engine}|{voice_id}")
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

        ttk.Button(dialog, text="Save", command=save_rename).pack(pady=5)

    def handle_spacebar(self, event=None):
        """Handle spacebar press only when audio is playing"""
        if self.is_speaking:
            self.stop_audio()
            return 'break'  # Prevent default spacebar behavior
        return None  # Allow normal spacebar behavior

    def init_voice_selection(self):
        """Initialize voice selection components"""
        # Engine Selection
        ttk.Label(self.col2_frame, text='Voice Engine:').pack(anchor='w')
        self.voice_engine_var = tk.StringVar(value=list(ENGINES.keys())[0])
        ttk.Combobox(
            self.col2_frame, 
            textvariable=self.voice_engine_var,
            values=list(ENGINES.keys()),
            state='readonly',
            width=50
        ).pack(anchor='w')

        # Language Selection
        ttk.Label(self.col2_frame, text='Language:').pack(anchor='w')
        self.language_var = tk.StringVar()
        self.language_combobox = ttk.Combobox(
            self.col2_frame,
            textvariable=self.language_var,
            state='readonly',
            width=50
        )
        self.language_combobox.pack(anchor='w')

        # Voice Selection
        ttk.Label(self.col2_frame, text='Voice:').pack(anchor='w')
        self.voice_var = tk.StringVar()
        self.voice_combobox = ttk.Combobox(
            self.col2_frame,
            textvariable=self.voice_var,
            state='readonly',
            width=50
        )
        self.voice_combobox.pack(anchor='w')

        # Bind events
        self.voice_engine_var.trace_add('write', self.update_language_options)
        self.language_var.trace_add('write', self.update_voice_options)

    def update_language_options(self, *args):
        """Update available languages based on selected engine"""
        engine = self.voice_engine_var.get()
        languages = ENGLISH_VARIANTS.get(engine, [])
        self.language_combobox['values'] = languages
        if languages:
            self.language_var.set(languages[0])
        else:
            self.language_var.set('')

    def create_settings_dialog(self):
        """Create settings dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        
        # Create frames
        col1_frame = ttk.Frame(dialog, padding="10")
        col1_frame.pack(side='left', fill='both', expand=True)
        
        col2_frame = ttk.Frame(dialog, padding="10")
        col2_frame.pack(side='left', fill='both', expand=True)
        
        # Output device settings
        ttk.Label(col1_frame, text='Output Device:').pack(anchor='w')
        output_devices = sd.query_devices()
        self.output_device_var = tk.StringVar(value=self.output_device)
        ttk.Combobox(col1_frame, textvariable=self.output_device_var, values=output_devices, width=50).pack(anchor='w')
        
        # Initialize voice selection components
        self.init_voice_selection()

    def on_typing(self, event):
        if self.typing_indicator_enabled_var.get() and not self.is_typing:
            self.is_typing = True
            self.output_manager.typing_indicator.start_typing()

    def on_typing_stop(self, event=None):
        if self.typing_indicator_enabled_var.get() and self.is_typing:
            self.is_typing = False
            self.output_manager.typing_indicator.stop_typing()

    def on_typing(self, event):
        """Handle typing events"""
        # Only trigger on actual typing (not on special keys)
        if event.char and ord(event.char) >= 32:
            if not hasattr(self, '_last_type_time'):
                self._last_type_time = 0
            
            current_time = time.time()
            # Start typing indicator if it's been more than 1 second since last type
            if current_time - self._last_type_time > 1:
                self.output_manager.typing_indicator.start_typing()
            
            self._last_type_time = current_time
            
            # Schedule typing stop after delay
            if hasattr(self, '_typing_timer'):
                self.root.after_cancel(self._typing_timer)
            self._typing_timer = self.root.after(2000, self.on_typing_stop)

    def on_typing_stop(self, event=None):
        """Stop typing indicator after delay"""
        if hasattr(self, '_typing_timer'):
            self.root.after_cancel(self._typing_timer)
        self.output_manager.typing_indicator.stop_typing()
