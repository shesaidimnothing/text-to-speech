# Building Windows Executable (.exe)

This guide explains how to create a standalone Windows .exe file from the Python application.

## Why Create an .exe?

- **Windows Sound Mixer Recognition**: The .exe will be recognized as a separate application in Windows Sound Mixer, allowing you to route audio from specific apps
- **Easy Distribution**: No need to install Python or dependencies
- **Standalone**: Everything bundled in one file

## Prerequisites

1. **Python 3.8+** installed
2. **All dependencies** installed (from requirements.txt)
3. **PyInstaller** installed

## Step 1: Install PyInstaller

```bash
pip install pyinstaller
```

## Step 2: Build the Executable

### Option A: Using the Build Script (Recommended)

```bash
python build_exe.py
```

This will create `dist/AudioTranscriptionAssistant.exe`

### Option B: Manual PyInstaller Command

```bash
pyinstaller --name AudioTranscriptionAssistant --onefile --windowed --add-data "config.json;." main.py
```

## Step 3: Test the Executable

1. Navigate to the `dist` folder
2. Run `AudioTranscriptionAssistant.exe`
3. The first run may be slow as it extracts files
4. Test that it works correctly

## Step 4: Using with Windows Sound Mixer

Once you have the .exe:

1. **Route audio to the app:**
   - Right-click speaker icon → Open Sound settings
   - Click "App volume and device preferences"
   - Find "AudioTranscriptionAssistant" in the list
   - Set its output to "CABLE Input" (or your virtual cable)

2. **Or route system audio:**
   - Set "CABLE Input" as default system output
   - The app will capture all system audio

## Build Options

### Include Console Window (for debugging)

Edit `build_exe.py` and change:
```python
'--windowed',  # Remove this line
'--console',   # Add this line
```

Or use the manual command:
```bash
pyinstaller --name AudioTranscriptionAssistant --onefile --console --add-data "config.json;." main.py
```

### Add an Icon

1. Create or download a `.ico` file
2. Edit `build_exe.py` and change:
   ```python
   '--icon=NONE',  # Change to '--icon=icon.ico'
   ```

### Include Additional Files

If you need to include other files, add to `build_exe.py`:
```python
'--add-data', 'other_file.txt;.',
```

## Troubleshooting

### "PyInstaller not found"
```bash
pip install pyinstaller
```

### "Module not found" errors
Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Large file size
The .exe includes Python and all dependencies, so it will be large (100-200MB). This is normal.

### Antivirus warnings
Some antivirus software may flag PyInstaller executables. This is a false positive. You can:
- Add an exception in your antivirus
- Sign the executable with a code signing certificate (advanced)

### First run is slow
The .exe extracts files to a temporary directory on first run. This is normal.

## Distribution

To distribute the application:

1. Copy `dist/AudioTranscriptionAssistant.exe` to the target computer
2. The user doesn't need Python installed
3. They still need:
   - Ollama installed and running
   - Virtual cable installed (VB-Audio or Stereo Mix)
   - The .exe file

## Advanced: Creating an Installer

For a more professional distribution, you can use:
- **Inno Setup** (free): Create a Windows installer
- **NSIS** (free): Another installer creator
- **cx_Freeze** or **py2exe**: Alternative to PyInstaller

## File Structure After Build

```
project/
├── dist/
│   └── AudioTranscriptionAssistant.exe  ← The executable
├── build/                                ← Build artifacts (can be deleted)
├── AudioTranscriptionAssistant.spec     ← PyInstaller spec file
└── ... (other project files)
```

You only need to distribute the `.exe` file from the `dist` folder.

