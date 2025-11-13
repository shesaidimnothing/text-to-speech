"""
Utility script to list available audio devices.
Run this to see what audio devices are available on your system.
"""

import sounddevice as sd

def list_audio_devices():
    """List all available audio devices."""
    print("=" * 80)
    print("Available Audio Devices")
    print("=" * 80)
    print()
    
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    
    print(f"Total devices: {len(devices)}")
    print()
    
    # Group by host API
    for hostapi_idx, hostapi in enumerate(hostapis):
        print(f"\n{hostapi['name']} (Host API {hostapi_idx}):")
        print("-" * 80)
        
        for device_idx, device in enumerate(devices):
            if device['hostapi'] == hostapi_idx:
                device_type = []
                if device['max_input_channels'] > 0:
                    device_type.append("INPUT")
                if device['max_output_channels'] > 0:
                    device_type.append("OUTPUT")
                
                device_type_str = "/".join(device_type) if device_type else "N/A"
                
                print(f"  [{device_idx}] {device['name']}")
                print(f"      Type: {device_type_str}")
                print(f"      Channels: In={device['max_input_channels']}, Out={device['max_output_channels']}")
                print(f"      Sample Rate: {device['default_samplerate']} Hz")
                
                # Check if this might be a loopback device
                name_lower = device['name'].lower()
                loopback_keywords = ['loopback', 'stereo mix', 'what u hear', 'vb-audio', 'blackhole', 'black hole', 'cable', 'voicemeeter']
                if any(keyword in name_lower for keyword in loopback_keywords):
                    print(f"      *** Possible loopback device ***")
                print()
    
    print("=" * 80)
    import platform
    system = platform.system()
    
    if system == 'Windows':
        print("\nFor system audio capture on Windows:")
        print("1. Enable 'Stereo Mix' in Windows Sound settings:")
        print("   - Right-click speaker icon → Sounds → Recording tab")
        print("   - Right-click empty space → Show Disabled Devices")
        print("   - Enable 'Stereo Mix' and set as default")
        print("2. Or install VB-Audio Virtual Cable:")
        print("   - Download from: https://vb-audio.com/Cable/")
    elif system == 'Darwin':
        print("\nFor system audio capture on macOS:")
        print("1. Install BlackHole virtual audio driver:")
        print("   - Download from: https://github.com/ExistentialAudio/BlackHole")
        print("   - Install the .pkg file")
        print("   - Restart your Mac")
        print("2. After installation, BlackHole will appear as an input device")
        print("3. The app will automatically detect and use BlackHole")
    elif system == 'Linux':
        print("\nFor system audio capture on Linux:")
        print("1. Install PulseAudio: sudo apt-get install pulseaudio")
        print("2. Configure PulseAudio loopback for system audio")
    else:
        print("\nFor system audio capture:")
        print("1. Install a virtual audio cable/loopback driver for your OS")
        print("2. The app will automatically detect loopback devices")
    
    print("=" * 80)

if __name__ == "__main__":
    try:
        list_audio_devices()
    except Exception as e:
        print(f"Error listing devices: {e}")

