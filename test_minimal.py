#!/usr/bin/env python3
"""Minimal test to isolate the crash."""

import sys
import traceback
import logging

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

print("Step 1: Testing imports...")
try:
    import customtkinter as ctk
    print("✓ customtkinter imported")
except Exception as e:
    print(f"✗ customtkinter import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\nStep 2: Testing basic GUI...")
try:
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.title("Test Window")
    root.geometry("400x300")
    print("✓ Basic window created")
except Exception as e:
    print(f"✗ Basic window creation failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\nStep 3: Testing system tray...")
try:
    import pystray
    from PIL import Image, ImageDraw
    image = Image.new('RGB', (64, 64), color='black')
    draw = ImageDraw.Draw(image)
    draw.ellipse([16, 16, 48, 48], fill='blue', outline='white')
    print("✓ System tray icon image created")
except Exception as e:
    print(f"✗ System tray setup failed: {e}")
    traceback.print_exc()

print("\nStep 4: Showing window and running mainloop...")
try:
    root.deiconify()
    root.lift()
    root.focus()
    print("✓ Window shown")
    print("\nWindow should be visible now. Close it to continue...")
    root.mainloop()
    print("✓ Mainloop completed")
except Exception as e:
    print(f"✗ Mainloop failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n✓ All tests passed!")

