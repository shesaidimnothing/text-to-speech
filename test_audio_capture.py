#!/usr/bin/env python3
"""Test script to verify audio capture from VB-Cable."""

import sys
import time
import numpy as np
import sounddevice as sd
from audio_capture import AudioCapture

def test_audio_capture():
    """Test if we can capture audio from VB-Cable."""
    print("=" * 80)
    print("Testing Audio Capture from VB-Cable")
    print("=" * 80)
    print()
    
    # List all devices
    print("Available audio devices:")
    devices = sd.query_devices()
    for idx, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            device_type = "INPUT"
            if any(kw in device['name'].lower() for kw in ['vb-cable', 'vb cable', 'blackhole', 'loopback']):
                device_type += " (LOOPBACK)"
            print(f"  [{idx}] {device['name']} - {device_type}")
    print()
    
    # Try to create AudioCapture
    print("Creating AudioCapture instance...")
    try:
        audio_capture = AudioCapture(
            sample_rate=16000,
            chunk_duration=3.0,
            callback=audio_received,
            silence_threshold=0.015
        )
        print(f"✓ AudioCapture created successfully")
        print(f"✓ Using device: {devices[audio_capture.device]['name']}")
        print(f"✓ Sample rate: {audio_capture.device_sample_rate} Hz")
        print()
    except Exception as e:
        print(f"✗ Failed to create AudioCapture: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Start capturing
    print("Starting audio capture...")
    print("Please play some audio (YouTube, music, etc.) now!")
    print("You should see audio level messages below.")
    print("=" * 80)
    print()
    
    try:
        audio_capture.start()
        print("✓ Audio capture started")
        print()
        
        # Capture for 10 seconds
        for i in range(10):
            time.sleep(1)
            if audio_received.audio_count > 0:
                print(f"✓ Received {audio_received.audio_count} audio chunks so far...")
        
        audio_capture.stop()
        print()
        print("=" * 80)
        
        if audio_received.audio_count > 0:
            print(f"✓ SUCCESS: Received {audio_received.audio_count} audio chunks")
            print(f"✓ Total audio samples: {audio_received.total_samples}")
            print(f"✓ Average audio level: {audio_received.avg_level:.4f}")
            if audio_received.avg_level > 0.001:
                print("✓ Audio levels look good - transcription should work!")
            else:
                print("⚠ Audio levels are very low - check if audio is playing")
            return True
        else:
            print("✗ FAILED: No audio chunks received")
            print("  - Make sure audio is playing")
            print("  - Check that system audio is routed to VB-Cable")
            print("  - Verify VB-Cable is selected as input device")
            return False
            
    except Exception as e:
        print(f"✗ Error during capture: {e}")
        import traceback
        traceback.print_exc()
        return False

# Callback to track received audio
class AudioReceived:
    def __init__(self):
        self.audio_count = 0
        self.total_samples = 0
        self.audio_levels = []
    
    def __call__(self, audio_data):
        self.audio_count += 1
        self.total_samples += len(audio_data)
        # Calculate RMS level
        rms = np.sqrt(np.mean(audio_data ** 2))
        self.audio_levels.append(rms)
        if self.audio_count <= 5 or self.audio_count % 10 == 0:
            print(f"  Audio chunk #{self.audio_count}: {len(audio_data)} samples, level: {rms:.4f}")
    
    @property
    def avg_level(self):
        if self.audio_levels:
            return np.mean(self.audio_levels)
        return 0.0

audio_received = AudioReceived()

if __name__ == "__main__":
    success = test_audio_capture()
    sys.exit(0 if success else 1)


