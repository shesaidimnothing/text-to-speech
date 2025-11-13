# Setting Up VB-Cable on macOS

## Current Status
✅ VB-Cable is detected by the application
⚠️ No audio is currently being routed to VB-Cable (audio levels are 0.0000)

## How to Route System Audio to VB-Cable

### Option 1: Set VB-Cable as Default Output (Simple)
1. Open **System Settings** (or System Preferences on older macOS)
2. Go to **Sound** → **Output**
3. Select **VB-Cable** as your output device
4. **Note:** This will route ALL system audio to VB-Cable, so you won't hear it through your speakers

### Option 2: Multi-Output Device (Recommended - You'll Still Hear Audio)
This allows you to hear audio AND capture it:

1. Open **Audio MIDI Setup** (Applications → Utilities → Audio MIDI Setup)
2. Click the **+** button at the bottom left
3. Select **Create Multi-Output Device**
4. In the right panel, check BOTH:
   - ✅ Your speakers (e.g., "MacBook Pro Speakers")
   - ✅ **VB-Cable**
5. Close Audio MIDI Setup
6. Go to **System Settings** → **Sound** → **Output**
7. Select the **Multi-Output Device** you just created
8. Now you'll hear audio AND the app can capture it!

### Option 3: Route Specific Apps (Advanced)
Some apps allow you to select their output device:
- In the app's audio settings, select VB-Cable as the output
- This only routes that app's audio to VB-Cable

## Testing

After setting up, test with:
```bash
python3 test_audio_capture.py
```

You should see audio levels above 0.0000 when audio is playing.

## Troubleshooting

### Still seeing 0.0000 audio levels?
1. ✅ Make sure audio is actually playing (YouTube, music, etc.)
2. ✅ Verify VB-Cable is selected as output (or in Multi-Output Device)
3. ✅ Check system volume is not muted
4. ✅ Try restarting the app after changing audio settings
5. ✅ Test with: `python3 test_audio_capture.py`

### VB-Cable not showing in System Settings?
- VB-Cable should appear in System Settings → Sound → Output
- If it doesn't, try restarting your Mac
- Verify VB-Cable is installed correctly


