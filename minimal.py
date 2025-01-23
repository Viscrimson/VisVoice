import tkinter as tk
from tkinter import ttk
import logging
import sys
import os

# Basic logging to both console and file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('minimal.log', 'w')
    ]
)

logger = logging.getLogger('Minimal')
logger.info('Starting minimal test')

class MinimalApp:
    def __init__(self):
        logger.info('Creating window')
        self.root = tk.Tk()
        self.root.title('Minimal Test')
        self.root.geometry('400x300')
        
        # Create text area
        self.text = tk.Text(self.root, height=10)
        self.text.pack(pady=10)
        
        # Create button
        self.button = ttk.Button(self.root, text='Send', command=self.on_send)
        self.button.pack(pady=5)
        
        logger.info('Window created')
        
    def on_send(self):
        text = self.text.get('1.0', tk.END).strip()
        logger.info(f'Text sent: {text}')
        self.text.delete('1.0', tk.END)
        
    def run(self):
        logger.info('Starting main loop')
        self.root.mainloop()
        
if __name__ == '__main__':
    try:
        app = MinimalApp()
        app.run()
    except Exception as e:
        logger.exception('Error occurred')
        sys.exit(1)
