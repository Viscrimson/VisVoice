# VisVoice.spec

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

from PyInstaller.utils.hooks import collect_data_files

# Collect data files from the spellchecker module
spellchecker_datas = collect_data_files('spellchecker')

datas = [
    ('settings.ini', '.'),  # Include settings.ini in the root directory
    ('resources/VisVoiceIcon.png', 'resources'),  # Include the icon file
] + spellchecker_datas

a = Analysis(
    ['visvoice.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'webrtcvad',  # Voice Activity Detection
        'collections',  # Built-in module, usually not needed but can be safe to include
        'whisper',  # OpenAI Whisper functionality
        'torch',  # PyTorch
        'numpy',  # Numerical computations
        'sounddevice',  # Audio recording and playback
        'pythonosc',  # Open Sound Control
        'pyttsx3',  # Text-to-Speech
        'edge_tts',  # Edge Text-to-Speech
        'pygame',  # Game development
        'spellchecker',  # Spell checking
        'keyboard',  # Keyboard events
        'tkinter',  # GUI library
        'tkinter.ttk',  # Themed widgets
        'tkinter.messagebox',  # Message boxes
        'tkinter.scrolledtext',  # Scrollable text widget
        'numba',  # For JIT compilation in libraries
        'llvmlite',  # Required by numba
        'concurrent.futures',  # For asynchronous tasks
        'pkg_resources',  # Resource handling in packages
        # Add any additional hidden imports your application requires
    ],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VisVoice',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True if you need a console window for debugging
    icon='resources/VisVoiceIcon.png',
)

# Remove the COLLECT call, as it's unnecessary for a single-file executable
