"""
Build script to create a Windows .exe file using PyInstaller.
"""

import PyInstaller.__main__
import os
import sys

def build_exe():
    """Build the application as a Windows executable."""
    
    # Application name
    app_name = "AudioTranscriptionAssistant"
    
    # PyInstaller arguments
    args = [
        'main.py',  # Main script
        '--name', app_name,
        '--onefile',  # Create a single executable file
        '--windowed',  # No console window (use --console if you want console for debugging)
        '--icon=NONE',  # You can add an icon file later (e.g., '--icon=icon.ico')
        '--add-data', 'config.json;.',  # Include config file
        '--hidden-import', 'customtkinter',
        '--hidden-import', 'faster_whisper',
        '--hidden-import', 'sounddevice',
        '--hidden-import', 'numpy',
        '--hidden-import', 'scipy',
        '--hidden-import', 'requests',
        '--hidden-import', 'pystray',
        '--hidden-import', 'PIL',
        '--hidden-import', 'keyboard',
        '--hidden-import', 'ollama',
        '--hidden-import', 'ctranslate2',  # Required by faster-whisper
        '--hidden-import', 'whisper',  # Required by faster-whisper
        '--collect-all', 'customtkinter',
        '--collect-all', 'faster_whisper',
        '--collect-all', 'PIL',
        '--collect-all', 'ctranslate2',
        '--noconfirm',  # Overwrite output without asking
        '--clean',  # Clean cache before building
    ]
    
    # Add console window for debugging (remove --windowed and add --console)
    # Uncomment the line below if you want to see console output for debugging
    # args.append('--console')
    
    print("Building Windows executable...")
    print(f"Output will be: dist/{app_name}.exe")
    print()
    
    try:
        PyInstaller.__main__.run(args)
        print()
        print("=" * 60)
        print("Build completed successfully!")
        print("=" * 60)
        print(f"Executable location: dist/{app_name}.exe")
        print()
        print("Note: The first run may be slow as it extracts files.")
        print("The .exe will be recognized by Windows Sound Mixer.")
        print("=" * 60)
    except Exception as e:
        print(f"Error building executable: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller is not installed.")
        print("Install it with: pip install pyinstaller")
        sys.exit(1)
    
    build_exe()

