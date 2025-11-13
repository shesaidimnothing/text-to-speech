"""
Audio setup diagnostic tool.
Run this to diagnose audio capture issues.
"""

import sounddevice as sd
import platform
import sys

def diagnose_audio_setup():
    """Diagnose audio setup and provide recommendations."""
    print("=" * 80)
    print("Audio Setup Diagnostic Tool")
    print("=" * 80)
    print()
    
    system = platform.system()
    print(f"Operating System: {system}")
    print()
    
    # List all devices
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    
    print("Available Audio Devices:")
    print("-" * 80)
    
    loopback_devices = []
    input_devices = []
    
    for device_idx, device in enumerate(devices):
        device_name = device['name']
        name_lower = device_name.lower()
        
        # Check if it's an input device
        if device['max_input_channels'] > 0:
            is_loopback = any(keyword in name_lower for keyword in [
                'loopback', 'stereo mix', 'what u hear', 
                'vb-audio', 'cable', 'voicemeeter', 'blackhole', 'black hole'
            ])
            
            hostapi_name = hostapis[device['hostapi']]['name'] if device['hostapi'] < len(hostapis) else 'Unknown'
            
            status = "✓ LOOPBACK" if is_loopback else "  Input"
            print(f"[{device_idx}] {status} - {device_name}")
            print(f"     Host API: {hostapi_name}")
            print(f"     Channels: {device['max_input_channels']} input")
            print(f"     Sample Rate: {device['default_samplerate']} Hz")
            
            if is_loopback:
                loopback_devices.append((device_idx, device_name))
            else:
                input_devices.append((device_idx, device_name))
            print()
    
    print("=" * 80)
    print()
    
    # Diagnose
    if system == 'Windows':
        print("Windows Audio Setup Diagnosis:")
        print("-" * 80)
        
        if loopback_devices:
            print("✓ Found loopback device(s):")
            for idx, name in loopback_devices:
                print(f"  - Device {idx}: {name}")
            print()
            print("The application should be able to use these devices.")
            print()
            print("To route system audio to the virtual cable:")
            print("1. Right-click speaker icon → Sounds → Playback tab")
            print("2. Find your virtual cable (e.g., 'CABLE Input')")
            print("3. Right-click it → Set as Default Device")
            print("4. OR use Windows Sound Mixer to route specific apps")
            print()
        else:
            print("✗ No loopback device detected!")
            print()
            print("Troubleshooting steps:")
            print()
            print("1. Verify VB-Audio Virtual Cable is installed:")
            print("   - Check if 'CABLE Input' appears in Playback devices")
            print("   - Check if 'CABLE Output' appears in Recording devices")
            print("   - If not, reinstall from: https://vb-audio.com/Cable/")
            print()
            print("2. Enable Stereo Mix (alternative):")
            print("   - Right-click speaker icon → Sounds → Recording tab")
            print("   - Right-click empty space → Show Disabled Devices")
            print("   - Right-click 'Stereo Mix' → Enable")
            print("   - Set as Default Device")
            print()
            print("3. Restart the application after installing/enabling devices")
            print()
            print("4. Check Windows Sound settings:")
            print("   - Settings → System → Sound")
            print("   - Verify devices are enabled and not muted")
            print()
        
        if input_devices and not loopback_devices:
            print("Found regular input devices (microphones):")
            for idx, name in input_devices[:3]:  # Show first 3
                print(f"  - Device {idx}: {name}")
            if len(input_devices) > 3:
                print(f"  ... and {len(input_devices) - 3} more")
            print()
            print("⚠️  These are microphones, not system audio loopback devices.")
            print()
    
    elif system == 'Darwin':  # macOS
        print("macOS Audio Setup Diagnosis:")
        print("-" * 80)
        
        if loopback_devices:
            print("✓ Found loopback device(s):")
            for idx, name in loopback_devices:
                print(f"  - Device {idx}: {name}")
            print()
            print("The application should be able to use these devices.")
            print()
            print("To route system audio to BlackHole:")
            print("1. System Settings → Sound → Output")
            print("2. Select 'BlackHole 2ch' (or your installed version)")
            print("3. OR create Multi-Output Device in Audio MIDI Setup")
            print()
        else:
            print("✗ No loopback device detected!")
            print()
            print("Troubleshooting steps:")
            print()
            print("1. Install BlackHole:")
            print("   - Download from: https://github.com/ExistentialAudio/BlackHole")
            print("   - Install BlackHole-2ch.pkg")
            print("   - Restart your Mac")
            print()
            print("2. Verify BlackHole is installed:")
            print("   - System Settings → Sound → Output")
            print("   - Look for 'BlackHole 2ch' in the list")
            print()
            print("3. Restart the application after installation")
            print()
    
    else:  # Linux
        print("Linux Audio Setup Diagnosis:")
        print("-" * 80)
        
        if loopback_devices:
            print("✓ Found loopback device(s):")
            for idx, name in loopback_devices:
                print(f"  - Device {idx}: {name}")
        else:
            print("✗ No loopback device detected!")
            print()
            print("Install and configure PulseAudio loopback:")
            print("1. Install: sudo apt-get install pulseaudio")
            print("2. Configure loopback module")
            print()
    
    print("=" * 80)
    print()
    print("Test Audio Capture:")
    print("-" * 80)
    print("To test if audio capture works:")
    print("1. Make sure system audio is playing (YouTube, music, etc.)")
    print("2. Start the main application")
    print("3. Click 'Start Recording'")
    print("4. Check the console logs for device selection messages")
    print("5. If you see transcriptions, it's working!")
    print()
    print("If still not working, check the application logs for error messages.")
    print("=" * 80)

if __name__ == "__main__":
    try:
        diagnose_audio_setup()
    except Exception as e:
        print(f"Error during diagnosis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

