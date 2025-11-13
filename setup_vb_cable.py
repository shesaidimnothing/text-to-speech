#!/usr/bin/env python3
"""
Helper script to set up VB-Cable routing on macOS.
This script helps you configure your system to route audio to VB-Cable.
"""

import subprocess
import sys
import sounddevice as sd

def list_devices():
    """List all available audio devices."""
    print("=" * 80)
    print("Available Audio Devices")
    print("=" * 80)
    print()
    
    devices = sd.query_devices()
    input_devices = []
    
    for idx, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            device_name = device['name']
            is_loopback = any(kw in device_name.lower() for kw in [
                'vb-cable', 'vb cable', 'blackhole', 'loopback'
            ])
            marker = " (LOOPBACK)" if is_loopback else ""
            print(f"  [{idx}] {device_name}{marker}")
            input_devices.append((idx, device_name, is_loopback))
    
    print()
    return input_devices

def check_vb_cable_status():
    """Check if VB-Cable is receiving audio."""
    print("=" * 80)
    print("Checking VB-Cable Status")
    print("=" * 80)
    print()
    
    devices = sd.query_devices()
    vb_cable_idx = None
    
    # Find VB-Cable
    for idx, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            if 'vb-cable' in device['name'].lower() or 'vb cable' in device['name'].lower():
                vb_cable_idx = idx
                print(f"✓ Found VB-Cable at device index {idx}")
                break
    
    if vb_cable_idx is None:
        print("✗ VB-Cable not found!")
        print("  Make sure VB-Cable is installed and your Mac has been restarted.")
        return False
    
    # Test audio levels
    print()
    print("Testing audio levels from VB-Cable...")
    print("Please play some audio (YouTube, music, etc.) now!")
    print("(This will test for 5 seconds)")
    print()
    
    import numpy as np
    import time
    
    max_level = 0.0
    chunk_count = 0
    
    def audio_callback(indata, frames, time, status):
        nonlocal max_level, chunk_count
        if status:
            print(f"  Status: {status}")
        audio_level = np.abs(indata).mean()
        max_level = max(max_level, audio_level)
        chunk_count += 1
        if chunk_count <= 3 or chunk_count % 10 == 0:
            print(f"  Chunk #{chunk_count}: level = {audio_level:.4f}")
    
    try:
        stream = sd.InputStream(
            device=vb_cable_idx,
            channels=1,
            samplerate=48000,
            dtype=np.float32,
            blocksize=4800,
            callback=audio_callback
        )
        stream.start()
        time.sleep(5)
        stream.stop()
        stream.close()
        
        print()
        print("=" * 80)
        if max_level > 0.001:
            print(f"✓ SUCCESS: VB-Cable is receiving audio! (max level: {max_level:.4f})")
            print("  Your app should work now!")
            return True
        else:
            print(f"✗ PROBLEM: VB-Cable is NOT receiving audio (max level: {max_level:.4f})")
            print()
            print("This means no audio is being routed to VB-Cable.")
            print("You need to route system audio to VB-Cable:")
            print()
            print("OPTION 1: Multi-Output Device (Recommended)")
            print("  1. Open Audio MIDI Setup (Applications → Utilities)")
            print("  2. Click '+' → Create Multi-Output Device")
            print("  3. Check both your speakers AND VB-Cable")
            print("  4. System Settings → Sound → Output → Select Multi-Output Device")
            print()
            print("OPTION 2: Direct Output")
            print("  1. System Settings → Sound → Output")
            print("  2. Select VB-Cable")
            print("  3. Note: You won't hear audio through speakers")
            print()
            return False
            
    except Exception as e:
        print(f"✗ Error testing VB-Cable: {e}")
        return False

def main():
    print()
    print("VB-Cable Setup Helper for macOS")
    print("=" * 80)
    print()
    
    # List devices
    input_devices = list_devices()
    
    # Check VB-Cable
    vb_cable_working = check_vb_cable_status()
    
    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print()
    
    if vb_cable_working:
        print("✓ VB-Cable is set up correctly!")
        print("  You can now use the transcription app.")
    else:
        print("⚠ VB-Cable needs to be configured.")
        print()
        print("Quick Setup:")
        print("  1. Open Audio MIDI Setup")
        print("  2. Create Multi-Output Device with your speakers + VB-Cable")
        print("  3. Set it as system output")
        print("  4. Run this script again to verify")
        print()
        print("Or use your microphone instead:")
        print("  Edit config.json and set: \"audio_device_index\": 0")
        print("  (This will use your MacBook Pro Microphone)")
    
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


