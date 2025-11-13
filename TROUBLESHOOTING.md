# Troubleshooting Guide

## Virtual Cable Not Working

If you've installed VB-Audio Virtual Cable (Windows) or BlackHole (macOS) but the app still can't capture system audio, follow these steps:

### Step 1: Run the Diagnostic Tool

**Option A: From the App**
1. Click the "🔍 Diagnose" button in the app
2. Review the diagnostic results

**Option B: From Command Line**
```bash
python diagnose_audio.py
```

This will show you:
- All available audio devices
- Which devices are detected as loopback devices
- Platform-specific setup instructions

### Step 2: Verify Virtual Cable Installation

#### Windows (VB-Audio Virtual Cable)

1. **Check if it's installed:**
   - Right-click speaker icon → Sounds → Playback tab
   - Look for "CABLE Input" in the list
   - Right-click speaker icon → Sounds → Recording tab
   - Look for "CABLE Output" in the list

2. **If not found:**
   - Download from: https://vb-audio.com/Cable/
   - Install the latest version
   - **Restart your computer** (important!)

3. **Route system audio to the cable:**
   - Option A: Set as default output
     - Right-click speaker icon → Sounds → Playback
     - Right-click "CABLE Input" → Set as Default Device
     - All system audio will go to the cable
   
   - Option B: Route specific apps (recommended)
     - Keep your speakers as default
     - Use Windows Sound Mixer (right-click speaker → Open Sound settings → App volume and device preferences)
     - Route specific apps (Teams, Zoom, etc.) to "CABLE Input"

4. **Verify in the app:**
   - Restart the application
   - Click "Start Recording"
   - Check console logs - should see "Found WASAPI loopback device: CABLE Output"

#### macOS (BlackHole)

1. **Check if it's installed:**
   - System Settings → Sound → Output
   - Look for "BlackHole 2ch" (or 16ch) in the list

2. **If not found:**
   - Download from: https://github.com/ExistentialAudio/BlackHole
   - Install BlackHole-2ch.pkg
   - **Restart your Mac** (required!)

3. **Route system audio:**
   - Option A: Set as default output
     - System Settings → Sound → Output → Select "BlackHole 2ch"
     - All system audio goes to BlackHole
   
   - Option B: Multi-Output Device (recommended - you'll still hear audio)
     - Open Audio MIDI Setup (Applications → Utilities)
     - Click "+" → Create Multi-Output Device
     - Check both your speakers AND BlackHole 2ch
     - Set this Multi-Output Device as your system output
     - You'll hear audio AND the app can capture it

4. **Verify in the app:**
   - Restart the application
   - Click "Start Recording"
   - Check console logs - should see "Found macOS loopback device: BlackHole 2ch"

### Step 3: Common Issues

#### Issue: "No loopback device found" error

**Causes:**
- Virtual cable not installed
- Virtual cable installed but not restarted
- Virtual cable disabled in system settings
- App needs to be restarted after installation

**Solutions:**
1. Verify installation (see Step 2)
2. Restart your computer
3. Restart the application
4. Run `python diagnose_audio.py` to see what devices are detected

#### Issue: Device detected but no audio captured

**Causes:**
- System audio not routed to the virtual cable
- Audio is muted
- Wrong device selected

**Solutions:**
1. Make sure system audio output is set to your virtual cable (or Multi-Output Device)
2. Play some audio (YouTube, music, etc.) to test
3. Check that audio is not muted
4. Look at console logs - you should see "Processing audio chunk" messages
5. Check audio level - if you see "Skipping silent audio chunk", the audio isn't reaching the device

#### Issue: Transcription appears but is empty/wrong

**Causes:**
- Audio quality issues
- Wrong audio source
- Whisper model too small

**Solutions:**
1. Increase system audio volume
2. Use "small" Whisper model instead of "base" (in Settings)
3. Make sure you're capturing the right audio source
4. Check that the audio is clear (not too quiet or distorted)

### Step 4: Manual Device Selection (Advanced)

If automatic detection isn't working, you can manually check device IDs:

1. Run `python list_audio_devices.py`
2. Note the device number for your virtual cable
3. Check the console logs when starting recording - it should show which device is being used

### Step 5: Still Not Working?

1. **Check console logs:**
   - Look for error messages
   - Check which device is being selected
   - Look for "⚠️" warnings

2. **Try alternative:**
   - Windows: Enable "Stereo Mix" instead of virtual cable
   - macOS: Try different BlackHole channel version (2ch vs 16ch)

3. **Verify audio is playing:**
   - Make sure you have audio playing (YouTube, music, etc.)
   - Check system volume is not muted
   - Verify the audio is going to the virtual cable

4. **Check permissions:**
   - macOS: System Settings → Privacy & Security → Microphone (should allow access)
   - Windows: Settings → Privacy → Microphone (should be enabled)

5. **Reinstall virtual cable:**
   - Uninstall completely
   - Restart computer
   - Reinstall
   - Restart again
   - Try the app

## Getting Help

If you're still having issues:

1. Run `python diagnose_audio.py` and save the output
2. Check the application console logs
3. Note your operating system and version
4. Describe what happens when you click "Start Recording"
5. Share the diagnostic output and relevant log messages

