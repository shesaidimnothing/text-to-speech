# Real-Time Audio Transcription & AI Assistant

A desktop application that captures system audio, transcribes it in real-time, detects questions, and answers them using local AI models. All processing happens locally on your machine for complete privacy.

## Features

- 🎤 **System Audio Capture**: Captures audio from any application (Teams, Zoom, Discord, etc.)
- 🗣️ **Real-Time Transcription**: Uses faster-whisper for fast, local speech-to-text
- ❓ **Question Detection**: Automatically detects questions in transcribed text
- 🤖 **AI Answers**: Uses Ollama (local LLM) to generate answers with conversation context
- 🎨 **Modern UI**: Clean, dark-mode interface with CustomTkinter
- 📋 **Export & Copy**: Export conversations or copy answers to clipboard
- ⚙️ **Configurable**: Customize models, sensitivity, and behavior

## System Requirements

- **OS**: Windows 10/11, macOS, or Linux
- **Python**: 3.8 or higher
- **RAM**: Minimum 4GB (8GB+ recommended)
- **Storage**: ~2GB for models (Whisper + Ollama models)

## Installation

### 1. Install Ollama

**Windows:**
- Download from [https://ollama.ai/download](https://ollama.ai/download)
- Run the installer
- Ollama will start automatically

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Pull Required Models

Open a terminal and run:

```bash
# Pull the default LLM model (llama3.2:3b)
ollama pull llama3.2:3b

# You can also use other models like:
# ollama pull llama3.2:1b  # Smaller, faster
# ollama pull mistral      # Alternative model
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Note for Windows users**: If you encounter issues with `sounddevice`, you may need to install the Visual C++ Redistributable or use `pip install sounddevice --no-binary sounddevice`.

### 4. Verify Ollama is Running

Before running the application, make sure Ollama is running:

```bash
ollama list
```

If this command works, Ollama is running. If not, start it manually or it should start automatically.

## Usage

### Starting the Application

```bash
python main.py
```

### First Run

1. The application will check if Ollama is running
2. It will download the Whisper model on first use (this may take a few minutes)
3. Click "Start Recording" to begin capturing system audio

### Using the Application

1. **Start Recording**: Click the "Start Recording" button to begin capturing system audio
2. **Live Transcription**: Watch as audio is transcribed in real-time
3. **Question Detection**: Questions will be automatically detected and highlighted
4. **AI Answers**: Answers will appear in the answers section
5. **Manual Answer**: Select any text and click "Answer This" to get an answer
6. **Settings**: Click the settings icon to configure models, sensitivity, etc.

### Keyboard Shortcuts

- `Ctrl+Shift+A`: Show/Hide application window
- `Ctrl+Q`: Quit application (when window is focused)

### Settings

- **Whisper Model**: Choose between "base" (faster) or "small" (more accurate)
- **Ollama Model**: Select which Ollama model to use
- **Auto-Answer**: Toggle automatic answering of detected questions
- **Detection Sensitivity**: Adjust how sensitive question detection is
- **Clear History**: Clear all transcription and conversation history

## Troubleshooting

### "Ollama is not running" Error

1. Make sure Ollama is installed
2. Start Ollama manually or restart your computer
3. Verify with `ollama list` command

### "No audio device found" Error

**Windows:**
- Make sure you're using Windows 10/11
- Enable "Stereo Mix" in Windows Sound settings:
  1. Right-click the speaker icon in system tray
  2. Select "Sounds" → "Recording" tab
  3. Right-click in empty space → "Show Disabled Devices"
  4. Enable "Stereo Mix" and set it as default
- Alternatively, install a virtual audio cable:
  - VB-Audio Virtual Cable: https://vb-audio.com/Cable/
  - Voicemeeter: https://vb-audio.com/Voicemeeter/
- Run `python list_audio_devices.py` to see available devices

**macOS:**
- Install BlackHole virtual audio driver for system audio capture:
  1. Download from: https://github.com/ExistentialAudio/BlackHole
  2. Download the latest release (BlackHole-2ch.pkg or BlackHole-16ch.pkg)
  3. Install the .pkg file (may require admin password)
  4. Restart your Mac after installation
  5. The app will automatically detect and use BlackHole
- To route system audio to BlackHole:
  1. Open System Settings → Sound
  2. Set Output to "BlackHole 2ch" (or 16ch if you installed that version)
  3. The app will capture all audio going to BlackHole
- Alternatively, use Audio MIDI Setup to create a Multi-Output Device combining your speakers and BlackHole

**Linux:**
- Install PulseAudio: `sudo apt-get install pulseaudio`
- For system audio, you may need to configure PulseAudio loopback
- Run `python list_audio_devices.py` to see available devices

### Poor Transcription Quality

- Try using the "small" Whisper model instead of "base"
- Ensure system audio is clear and not too quiet
- Check that the correct audio output device is selected

### High CPU/Memory Usage

- Use "base" Whisper model instead of "small"
- Use a smaller Ollama model (e.g., llama3.2:1b)
- Reduce the conversation context window in settings

## Privacy

- All processing happens **locally** on your machine
- No data is sent to external servers
- Audio is processed in memory and not saved by default
- You can export conversations if desired

## License

This project is provided as-is for personal use.

## Contributing

Feel free to submit issues or pull requests for improvements!

