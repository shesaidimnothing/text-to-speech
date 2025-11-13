#!/usr/bin/env python3
"""Test script to run the app and capture all errors."""

import sys
import traceback
import logging

# Enable all logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

try:
    print("=" * 80)
    print("Starting Transcription App Test")
    print("=" * 80)
    
    from main import TranscriptionApp
    
    print("\n1. Import successful")
    print("2. Creating app instance...")
    
    app = TranscriptionApp()
    
    print("3. App created successfully")
    print("4. Window should be visible now")
    print("5. Starting mainloop (this will block until window is closed)...")
    print("\nIf you see this message, the app should be running!")
    print("Look for the GUI window on your screen.")
    print("=" * 80)
    
    app.mainloop()
    
    print("\nMainloop finished - app closed normally")
    
except KeyboardInterrupt:
    print("\n\nInterrupted by user")
    sys.exit(0)
except Exception as e:
    print(f"\n\nERROR: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)


