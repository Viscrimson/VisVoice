import tkinter as tk
import logging
import sys

# Basic console logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(message)s',
    stream=sys.stdout
)

print("Starting minimal test...")

try:
    # Create main window
    root = tk.Tk()
    root.title("Test Window")
    root.geometry("400x300")
    
    # Add a label
    label = tk.Label(root, text="If you can see this, the window is working")
    label.pack(pady=20)
    
    # Add a button
    btn = tk.Button(root, text="Click Me", command=lambda: print("Button clicked!"))
    btn.pack(pady=20)
    
    print("Window created, starting mainloop...")
    root.mainloop()
    print("Window closed")
    
except Exception as e:
    print(f"Error: {str(e)}")
    logging.exception("Error occurred")
