import tkinter as tk
import logging
import sys
import os

# Setup basic logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('debug.log', mode='w')
    ]
)

logger = logging.getLogger('VisVoice')

class SimpleVisVoice:
    def __init__(self):
        logger.info("Creating window...")
        
        # Create window
        self.root = tk.Tk()
        self.root.title('VisVoice')
        self.root.geometry('800x600')
        
        # Dark theme
        self.dark_bg = '#2b2b2b'
        self.dark_fg = '#ffffff'
        self.root.configure(bg=self.dark_bg)
        
        # Text area
        self.text_area = tk.Text(
            self.root,
            wrap='word',
            bg=self.dark_bg,
            fg=self.dark_fg,
            insertbackground=self.dark_fg,
            height=20
        )
        self.text_area.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Button frame
        button_frame = tk.Frame(self.root, bg=self.dark_bg)
        button_frame.pack(side='bottom', fill='x', padx=10, pady=5)
        
        # Voice button
        self.voice_button = tk.Button(
            button_frame,
            text='Start Voice Capture',
            command=self.toggle_voice,
            bg=self.dark_bg,
            fg=self.dark_fg
        )
        self.voice_button.pack(side='left', padx=5)
        
        # Send button
        tk.Button(
            button_frame,
            text='Send',
            command=self.send_text,
            bg=self.dark_bg,
            fg=self.dark_fg
        ).pack(side='right', padx=5)
        
        logger.info('UI initialized')
    
    def toggle_voice(self):
        logger.info('Voice capture toggled')
        current = self.voice_button['text']
        new_text = 'Stop Voice Capture' if current == 'Start Voice Capture' else 'Start Voice Capture'
        self.voice_button.configure(text=new_text)
    
    def send_text(self):
        text = self.text_area.get('1.0', tk.END).strip()
        if text:
            logger.info(f'Text sent: {text}')
            self.text_area.delete('1.0', tk.END)
    
    def run(self):
        logger.info('Starting application')
        self.root.mainloop()

if __name__ == '__main__':
    try:
        app = SimpleVisVoice()
        app.run()
    except Exception as e:
        logger.exception('Error running application')
        sys.exit(1)
