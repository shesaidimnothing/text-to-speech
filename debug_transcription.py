#!/usr/bin/env python3
"""
Debug script to test transcription flow and see why text isn't appearing.
"""

import sys
import logging
import numpy as np
import time

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("=" * 80)
print("Transcription Debug Tool")
print("=" * 80)
print()

# Test 1: Check if transcription engine loads
print("Test 1: Loading transcription engine...")
try:
    from transcription import TranscriptionEngine
    engine = TranscriptionEngine(model_size='base')
    print("✓ TranscriptionEngine created")
    
    # Initialize it
    print("Initializing Whisper model (this may take a moment)...")
    engine.initialize()
    print("✓ Whisper model initialized")
except Exception as e:
    print(f"✗ Failed to load transcription engine: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 2: Test with actual audio
print("Test 2: Testing transcription with audio...")
print("Please speak into your microphone or play audio now!")
print("(Testing for 10 seconds)")
print()

from audio_capture import AudioCapture

transcription_count = 0
last_transcription = None

def test_callback(audio_data):
    global transcription_count, last_transcription
    audio_level = np.abs(audio_data).mean()
    print(f"  Audio chunk received: {len(audio_data)} samples, level: {audio_level:.6f}")
    
    if audio_level < 0.001:
        print(f"    → Skipping (too quiet)")
        return
    
    print(f"    → Transcribing...")
    text = engine.transcribe_chunk(audio_data)
    
    if text and text.strip():
        transcription_count += 1
        last_transcription = text
        print(f"    ✓ TRANSCRIBED: {text}")
    else:
        print(f"    → No text (text={text})")

try:
    # Try to create audio capture
    print("Creating audio capture...")
    audio_capture = AudioCapture(
        sample_rate=16000,
        chunk_duration=3.0,
        callback=test_callback,
        silence_threshold=0.015
    )
    print(f"✓ Audio capture created")
    print(f"  Using device: {audio_capture.device}")
    print()
    
    print("Starting capture (10 seconds)...")
    audio_capture.start()
    
    # Capture for 10 seconds
    for i in range(10):
        time.sleep(1)
        if transcription_count > 0:
            print(f"  Progress: {i+1}/10 seconds, {transcription_count} transcriptions so far...")
    
    audio_capture.stop()
    
    print()
    print("=" * 80)
    print("Results")
    print("=" * 80)
    print()
    
    if transcription_count > 0:
        print(f"✓ SUCCESS: {transcription_count} transcription(s) received!")
        print(f"  Last transcription: {last_transcription}")
        print()
        print("If the app isn't showing transcriptions, the issue is likely:")
        print("  1. UI message queue not processing")
        print("  2. Transcription text not being added to UI")
        print("  3. Sentence accumulation logic blocking display")
    else:
        print("✗ NO TRANSCRIPTIONS RECEIVED")
        print()
        print("Possible issues:")
        print("  1. Audio levels too low (check audio_level in logs)")
        print("  2. Whisper not detecting speech")
        print("  3. Audio not reaching the device")
        print("  4. VAD (Voice Activity Detection) filtering everything out")
        print()
        print("Try:")
        print("  - Speak louder or increase system volume")
        print("  - Check that audio is actually playing/routing to the device")
        print("  - Check console logs for 'Skipping silent audio chunk' messages")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()


