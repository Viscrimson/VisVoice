import tkinter as tk
from tkinter import ttk
from managers.Settings_manager import SettingsManager
from managers.TTT_manager import TTTManager

class UIManager:
    def __init__(self, queue_manager):
        self.queue_manager = queue_manager
        self.settings_manager = SettingsManager()
        self.ttt_manager = TTTManager(queue_manager)
        self.root = tk.Tk()
        self.root.title('Viz Voice')
        self.create_widgets()

    def create_widgets(self):
        """Creates the UI components."""
        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill='both')

        # Create tabs
        input_tab = ttk.Frame(notebook)
        output_tab = ttk.Frame(notebook)
        hotkeys_tab = ttk.Frame(notebook)
        advanced_tab = ttk.Frame(notebook)
        ui_tab = ttk.Frame(notebook)

        notebook.add(input_tab, text='Input')
        notebook.add(output_tab, text='Output')
        notebook.add(hotkeys_tab, text='Hotkeys')
        notebook.add(advanced_tab, text='Advanced')
        notebook.add(ui_tab, text='UI')

        # Populate tabs
        self.create_input_tab(input_tab)
        self.create_output_tab(output_tab)
        self.create_hotkeys_tab(hotkeys_tab)
        self.create_advanced_tab(advanced_tab)
        self.create_ui_tab(ui_tab)

        # Typing Interface
        self.create_typing_interface()

        # Save button
        save_button = ttk.Button(self.root, text='Save Settings', command=self.save_settings)
        save_button.pack(side='bottom', pady=10)

    def create_input_tab(self, tab):
        """Creates the Input settings tab."""
        # STT Enabled
        stt_enabled_label = ttk.Label(tab, text='Enable STT:')
        stt_enabled_label.grid(column=0, row=0, padx=5, pady=5, sticky='E')

        stt_enabled_var = tk.BooleanVar(value=self.settings_manager.get_setting('INPUT', 'stt_enabled') == 'True')
        stt_enabled_check = ttk.Checkbutton(tab, variable=stt_enabled_var)
        stt_enabled_check.grid(column=1, row=0, padx=5, pady=5, sticky='W')
        self.stt_enabled_var = stt_enabled_var  # Store for later use

        # Continue adding other input settings as needed...

    def create_output_tab(self, tab):
        """Creates the Output settings tab."""
        # Output Type
        output_type_label = ttk.Label(tab, text='Output Type:')
        output_type_label.grid(column=0, row=0, padx=5, pady=5, sticky='E')

        output_type_options = ['TTC Only', 'TTS Only', 'TTC and TTS']
        output_type_var = tk.StringVar(value=self.settings_manager.get_setting('OUTPUT', 'output_type'))
        output_type_menu = ttk.OptionMenu(tab, output_type_var, output_type_var.get(), *output_type_options)
        output_type_menu.grid(column=1, row=0, padx=5, pady=5, sticky='W')
        self.output_type_var = output_type_var  # Store for later use

        # Continue adding other output settings as needed...

    def create_hotkeys_tab(self, tab):
        """Creates the Hotkeys settings tab."""
        # TTT Hotkey
        ttt_hotkey_label = ttk.Label(tab, text='TTT Hotkey:')
        ttt_hotkey_label.grid(column=0, row=0, padx=5, pady=5, sticky='E')

        ttt_hotkey_var = tk.StringVar(value=self.settings_manager.get_setting('HOTKEYS', 'ttt_hotkey'))
        ttt_hotkey_entry = ttk.Entry(tab, textvariable=ttt_hotkey_var)
        ttt_hotkey_entry.grid(column=1, row=0, padx=5, pady=5, sticky='W')
        self.ttt_hotkey_var = ttt_hotkey_var  # Store for later use

        # Continue adding other hotkey settings as needed...

    def create_advanced_tab(self, tab):
        """Creates the Advanced settings tab."""
        # Process Priority
        priority_label = ttk.Label(tab, text='Process Priority:')
        priority_label.grid(column=0, row=0, padx=5, pady=5, sticky='E')

        priority_options = ['Low', 'Below Normal', 'Normal', 'Above Normal', 'High']
        priority_var = tk.StringVar(value=self.settings_manager.get_setting('ADVANCED', 'process_priority'))
        priority_menu = ttk.OptionMenu(tab, priority_var, priority_var.get(), *priority_options)
        priority_menu.grid(column=1, row=0, padx=5, pady=5, sticky='W')
        self.priority_var = priority_var  # Store for later use

        # Continue adding other advanced settings as needed...

    def create_ui_tab(self, tab):
        """Creates the UI settings tab."""
        # Opacity Label
        opacity_label = ttk.Label(tab, text='Opacity (%):')
        opacity_label.grid(column=0, row=0, padx=5, pady=5, sticky='E')

        # Opacity Variable
        self.opacity_var = tk.IntVar(value=int(self.settings_manager.get_setting('UI', 'opacity')))

        # Opacity Value Label (Define this before assigning the command)
        self.opacity_value_label = ttk.Label(tab, text=f"{self.opacity_var.get()}%")
        self.opacity_value_label.grid(column=2, row=0, padx=5, pady=5, sticky='W')

        # Opacity Scale
        opacity_scale = ttk.Scale(
            tab,
            from_=0,
            to=100,
            variable=self.opacity_var,
            orient='horizontal',
            command=self.update_opacity_label
        )
        opacity_scale.grid(column=1, row=0, padx=5, pady=5, sticky='W')
        opacity_scale.set(self.opacity_var.get())

    def update_opacity_label(self, value):
        """Updates the opacity value label."""
        self.opacity_value_label.config(text=f"{int(float(value))}%")

    def create_typing_interface(self):
        """Creates the typing interface for TTT."""
        typing_frame = ttk.Frame(self.root)
        typing_frame.pack(side='bottom', fill='x', padx=5, pady=5)

        self.input_text_var = tk.StringVar()
        input_entry = ttk.Entry(typing_frame, textvariable=self.input_text_var, width=50)
        input_entry.pack(side='left', padx=5)
        input_entry.bind('<Return>', self.submit_text)  # Submit on Enter key

        submit_button = ttk.Button(typing_frame, text='Send', command=self.submit_text)
        submit_button.pack(side='left', padx=5)

    def submit_text(self, event=None):
        """Handles the submission of typed text."""
        text = self.input_text_var.get().strip()
        if text:
            # Use TTTManager to submit text
            self.ttt_manager.submit_text(text)
            # Clear input field
            self.input_text_var.set('')
        else:
            print('No text entered.')

    def save_settings(self):
        """Saves the settings from the UI to the settings file."""
        self.settings_manager.set_setting('INPUT', 'stt_enabled', str(self.stt_enabled_var.get()))
        # Save other INPUT settings as needed...

        self.settings_manager.set_setting('OUTPUT', 'output_type', self.output_type_var.get())
        self.settings_manager.set_setting('OUTPUT', 'osc_ip', self.osc_ip_var.get())
        self.settings_manager.set_setting('OUTPUT', 'osc_port', self.osc_port_var.get())
        
        self.settings_manager.set_setting('HOTKEYS', 'ttt_hotkey', self.ttt_hotkey_var.get())
        # Save other HOTKEYS settings as needed...

        self.settings_manager.set_setting('ADVANCED', 'process_priority', self.priority_var.get())
        # Save other ADVANCED settings as needed...

        self.settings_manager.set_setting('UI', 'opacity', str(self.opacity_var.get()))
        # Save other UI settings as needed...

        print('Settings have been saved.')

    def run(self):
        """Runs the main loop of the UI."""
        self.root.mainloop()

    def create_output_tab(self, tab):
        """Creates the Output settings tab."""
        # Output Type (existing code)
        # ...

        # OSC IP
        osc_ip_label = ttk.Label(tab, text='OSC IP:')
        osc_ip_label.grid(column=0, row=1, padx=5, pady=5, sticky='E')

        osc_ip_var = tk.StringVar(value=self.settings_manager.get_setting('OUTPUT', 'osc_ip'))
        osc_ip_entry = ttk.Entry(tab, textvariable=osc_ip_var)
        osc_ip_entry.grid(column=1, row=1, padx=5, pady=5, sticky='W')
        self.osc_ip_var = osc_ip_var  # Store for later use

        # OSC Port
        osc_port_label = ttk.Label(tab, text='OSC Port:')
        osc_port_label.grid(column=0, row=2, padx=5, pady=5, sticky='E')

        osc_port_var = tk.StringVar(value=self.settings_manager.get_setting('OUTPUT', 'osc_port'))
        osc_port_entry = ttk.Entry(tab, textvariable=osc_port_var)
        osc_port_entry.grid(column=1, row=2, padx=5, pady=5, sticky='W')
        self.osc_port_var = osc_port_var  # Store for later use