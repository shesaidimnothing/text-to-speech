# Why Audio is 0.0000 and How to Fix It

## The Problem

**Audio levels are 0.0000 because:**
- ✅ VB-Cable is **detected** correctly (device index 4)
- ❌ **No audio is being routed** to VB-Cable
- The app is listening to VB-Cable, but it's receiving silence

## Why This Happens

The app listens to VB-Cable, but your system audio is still going to your speakers, not to VB-Cable. VB-Cable is like a "virtual microphone" - it only receives audio if you route it there.

## Solutions

### Solution 1: Route Audio to VB-Cable (Recommended for System Audio)

**Option A: Multi-Output Device (Best - You'll Still Hear Audio)**

1. Open **Audio MIDI Setup** (Applications → Utilities → Audio MIDI Setup)
2. Click the **+** button (bottom left)
3. Select **Create Multi-Output Device**
4. In the right panel, check BOTH:
   - ✅ Your speakers (e.g., "MacBook Pro Speakers")
   - ✅ **VB-Cable**
5. Close Audio MIDI Setup
6. Go to **System Settings** → **Sound** → **Output**
7. Select the **Multi-Output Device** you just created
8. Now audio goes to BOTH your speakers AND VB-Cable!

**Option B: Direct Output (Simple but No Sound)**

1. **System Settings** → **Sound** → **Output**
2. Select **VB-Cable**
3. ⚠️ You won't hear audio through speakers (it all goes to VB-Cable)

### Solution 2: Use Your Microphone Instead (Quick Fix)

If you just want to transcribe what you say (not system audio), use your microphone:

1. Edit `config.json`
2. Add this line: `"audio_device_index": 0`
3. Save and restart the app
4. Now it will use your MacBook Pro Microphone

**Example config.json:**
```json
{
  "whisper_model": "large",
  "ollama_model": "llama3.2",
  "audio_device_index": 0,
  ...
}
```

### Solution 3: Test and Verify

After setting up, test with:
```bash
python3 setup_vb_cable.py
```

This will:
- Show all available devices
- Test if VB-Cable is receiving audio
- Give you specific instructions if it's not working

## Quick Reference

**Device Indexes:**
- `0` = MacBook Pro Microphone
- `4` = VB-Cable (when audio is routed to it)

**To use microphone instead of VB-Cable:**
- Edit `config.json`: `"audio_device_index": 0`

**To use VB-Cable (after routing audio):**
- Edit `config.json`: `"audio_device_index": 4`
- Or remove the line to auto-detect

## Still Not Working?

1. ✅ Run `python3 setup_vb_cable.py` to diagnose
2. ✅ Make sure audio is actually playing (YouTube, music, etc.)
3. ✅ Check system volume is not muted
4. ✅ Restart the app after changing audio settings
5. ✅ Try using microphone (device 0) as a test


