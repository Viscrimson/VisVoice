import os
import shutil
import subprocess
import sys
import time
import json

def print_status(message):
    """Print a status message with timestamp."""
    print(f"[{time.strftime('%H:%M:%S')}] {message}")
    sys.stdout.flush()  # Ensure message is displayed immediately

def check_dependencies():
    """Check if all required dependencies are available."""
    required_modules = [
        'whisper', 'torch', 'edge_tts', 'pygame', 'sounddevice',
        'webrtcvad', 'keyboard', 'spellchecker', 'pythonosc'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        raise Exception(f"Missing required modules: {', '.join(missing)}")

def build_executable():
    print_status("Starting build process...")
    try:
        # Check dependencies first
        print_status("Checking dependencies...")
        check_dependencies()
        
        # Ensure resources directory exists
        if not os.path.exists('resources'):
            os.makedirs('resources')
            print_status("Created resources directory")

        # Ensure dictionary file exists
        if not os.path.exists('resources/en.json'):
            print_status("Creating basic dictionary file...")
            with open('resources/en.json', 'w') as f:
                json.dump({
                    "language": "en",
                    "words": {
                        "the": 1, "be": 1, "to": 1, "of": 1, "and": 1,
                        "a": 1, "in": 1, "that": 1, "have": 1, "i": 1
                    }
                }, f, indent=4)

        # Clean previous builds
        if os.path.exists('build'):
            print_status("Cleaning build directory...")
            shutil.rmtree('build')
        if os.path.exists('dist'):
            print_status("Cleaning dist directory...")
            shutil.rmtree('dist')

        # Build using PyInstaller
        print_status("Running PyInstaller...")
        result = subprocess.run(['pyinstaller', 'visvoice.spec'], 
                              capture_output=True, 
                              text=True)
        
        # Check if PyInstaller was successful
        if result.returncode != 0:
            print_status("PyInstaller failed!")
            print("Error output:")
            print(result.stderr)
            raise Exception("PyInstaller build failed")

        # Create release directory
        release_dir = 'release'
        print_status(f"Creating release directory: {release_dir}")
        if not os.path.exists(release_dir):
            os.makedirs(release_dir)

        # Copy executable
        print_status("Copying executable to release directory...")
        if not os.path.exists('dist/VisVoice.exe'):
            raise Exception("Executable not found in dist directory!")
        shutil.copy('dist/VisVoice.exe', release_dir)

        # Handle settings.ini
        print_status("Handling settings.ini...")
        if os.path.exists('settings.ini'):
            shutil.copy('settings.ini', release_dir)
            print_status("Copied existing settings.ini")
        else:
            print_status("Creating default settings.ini")
            with open(os.path.join(release_dir, 'settings.ini'), 'w') as f:
                f.write('''[Settings]
input_device = Default
output_device = Default
chatbox_ip = 127.0.0.1
chatbox_port = 9000
voice_engine = edge-tts
voice = en-US-MichelleNeural
language = en-US
hotkey = `
voice_output = True
chatbox_output = True''')

        print_status("Build completed successfully!")
        print_status(f"Executable can be found in the '{release_dir}' directory")

    except Exception as e:
        print_status(f"Error during build: {str(e)}")
        print("\nPress Enter to exit...")
        input()
        sys.exit(1)

if __name__ == "__main__":
    try:
        build_executable()
        print("\nPress Enter to exit...")
        input()
    except KeyboardInterrupt:
        print_status("\nBuild process interrupted by user.")
        print("\nPress Enter to exit...")
        input()
        sys.exit(1)