#!/usr/bin/env python3
"""
Safe launcher that disables problematic features that can cause crashes on macOS.
"""

import sys
import os

# Disable system tray to avoid crashes
os.environ['DISABLE_SYSTEM_TRAY'] = '1'

# Run the main app
if __name__ == "__main__":
    try:
        from main import TranscriptionApp
        app = TranscriptionApp()
        
        # Disable system tray if it was created
        if hasattr(app, 'tray_icon') and app.tray_icon:
            try:
                app.tray_icon.stop()
            except:
                pass
            app.tray_icon = None
        
        app.mainloop()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


