# Quick Start Guide

## Prerequisites Check

Before running the application, make sure you have:

1. **Python 3.8+** installed
2. **Ollama** installed and running
3. **Required models** downloaded

## Step-by-Step Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Verify Ollama

```bash
# Check if Ollama is running
ollama list

# If not running, start it (varies by OS)
# Windows: Should start automatically
# macOS/Linux: ollama serve
```

### 3. Pull Required Models

```bash
# Pull the default LLM model
ollama pull llama3.2:3b

# Optional: Pull Whisper models are downloaded automatically on first use
```

### 4. Check Audio Devices (Optional)

```bash
# List available audio devices
python list_audio_devices.py
```

This will help you identify which device to use for system audio capture.

### 5. Run the Application

```bash
python main.py
```

## First Run Checklist

- [ ] Application starts without errors
- [ ] Ollama status shows "Running ✓" (green)
- [ ] Audio device is detected
- [ ] Click "Start Recording" - status changes to "Recording..."
- [ ] Play some audio (YouTube, music, etc.)
- [ ] Transcription appears in the Transcription tab
- [ ] Ask a question - it should be detected and answered

## Common Issues

### Keyboard Shortcuts Not Working

On Windows, global keyboard shortcuts may require administrator privileges. The application will work without them - you can use the system tray icon instead.

### No Audio Captured

**Windows:**
1. Enable "Stereo Mix" in Windows Sound settings (see README for details)
2. Or install VB-Audio Virtual Cable
3. Run `python list_audio_devices.py` to see available devices
4. Make sure system audio is playing (not muted)

**macOS:**
1. Install BlackHole virtual audio driver (see README for details)
2. After installation, restart your Mac
3. Set your system audio output to "BlackHole 2ch" in System Settings → Sound
4. Run `python list_audio_devices.py` to verify BlackHole is detected
5. Make sure system audio is playing (not muted)

### Ollama Not Detected

1. Make sure Ollama is installed
2. Check if it's running: `ollama list`
3. Verify the model is pulled: `ollama list` should show your model
4. Check the Ollama URL in settings (default: http://localhost:11434)

## Tips

- Start with the "base" Whisper model for faster processing
- Use "small" model for better accuracy (slower)
- Adjust detection sensitivity if questions aren't being detected
- Use "Answer Selected" to manually get answers for any text
- Export conversations regularly if you want to keep them

## Next Steps

- Customize models in Settings
- Adjust question detection sensitivity
- Configure auto-answer behavior
- Set up keyboard shortcuts (may require admin on Windows)

