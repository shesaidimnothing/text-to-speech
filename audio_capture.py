"""
Audio capture module for system audio loopback.
Supports WASAPI on Windows, PulseAudio on Linux, and CoreAudio on macOS.
"""

import sounddevice as sd
import numpy as np
import queue
import threading
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)

try:
    from scipy import signal
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    logger.warning("scipy not available, will use device's native sample rate")


class AudioCapture:
    """Captures system audio output (loopback) for real-time transcription."""
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 chunk_duration: float = 3.0,
                 callback: Optional[Callable] = None,
                 silence_threshold: float = 0.015,
                 min_silence_duration: float = 1.0,
                 max_buffer_duration: float = 10.0,
                 device: Optional[int] = None):
        """
        Initialize audio capture.
        
        Args:
            sample_rate: Audio sample rate (16000 for Whisper)
            chunk_duration: Duration of each audio chunk in seconds (legacy, not used for phrase detection)
            callback: Function to call with audio chunks (numpy array)
            silence_threshold: Audio level threshold for silence detection (0.0-1.0)
            min_silence_duration: Minimum seconds of silence before processing a phrase
            max_buffer_duration: Maximum seconds to buffer before forcing processing
            device: Optional device index to use. If None, will auto-detect loopback device.
        """
        self.target_sample_rate = sample_rate  # Target rate for Whisper (16000)
        self.chunk_duration = chunk_duration
        self.callback = callback
        self.silence_threshold = silence_threshold
        self.min_silence_duration = min_silence_duration
        self.max_buffer_duration = max_buffer_duration
        
        self.is_recording = False
        self.stream = None
        self.audio_queue = queue.Queue()
        self.thread = None
        
        # Find loopback device or use specified device
        if device is not None:
            self.device = device
            devices = sd.query_devices()
            if self.device < len(devices):
                logger.info(f"Using specified device: {devices[self.device]['name']}")
            else:
                raise ValueError(f"Invalid device index: {device}")
        else:
            self.device = self._find_loopback_device()
            if self.device is None:
                raise RuntimeError("No loopback audio device found. Please check your audio setup.")
        
        # Get device's supported sample rate
        self.device_sample_rate = self._get_device_sample_rate()
        self.chunk_samples = int(self.device_sample_rate * chunk_duration)
        
        logger.info(f"Using device sample rate: {self.device_sample_rate} Hz (target: {self.target_sample_rate} Hz)")
    
    def _find_loopback_device(self) -> Optional[int]:
        """Find the appropriate loopback device for system audio capture."""
        import platform
        devices = sd.query_devices()
        system = platform.system()
        
        try:
            hostapis = sd.query_hostapis()
            
            # macOS: Look for CoreAudio and BlackHole
            if system == 'Darwin':
                for hostapi_idx, hostapi in enumerate(hostapis):
                    if 'Core Audio' in hostapi['name'] or 'CoreAudio' in hostapi['name']:
                        loopback_candidates = []
                        regular_inputs = []
                        
                        for device_idx, device in enumerate(devices):
                            if (device['hostapi'] == hostapi_idx and 
                                device['max_input_channels'] > 0):
                                device_name = device['name'].lower()
                                
                                # Check for BlackHole or VB-Cable (macOS virtual audio drivers)
                                if any(keyword in device_name for keyword in [
                                    'blackhole', 'black hole', 'loopback',
                                    'vb-cable', 'vb cable', 'vbaudio', 'virtual cable'
                                ]):
                                    loopback_candidates.append((device_idx, device))
                                else:
                                    # Regular input device (likely a microphone)
                                    regular_inputs.append((device_idx, device))
                        
                        # Prefer BlackHole loopback devices
                        if loopback_candidates:
                            device_idx, device = loopback_candidates[0]
                            logger.info(f"Found macOS loopback device: {device['name']}")
                            return device_idx
                        
                        # Warn if we're using a regular input (likely a mic, not system audio)
                        if regular_inputs:
                            device_idx, device = regular_inputs[0]
                            logger.warning(f"⚠️  Using macOS input device (likely microphone, not system audio): {device['name']}")
                            logger.warning("⚠️  For system audio capture on macOS, install BlackHole:")
                            logger.warning("⚠️  https://github.com/ExistentialAudio/BlackHole")
                            return device_idx
            
            # Windows: Look for WASAPI loopback devices
            elif system == 'Windows':
                for hostapi_idx, hostapi in enumerate(hostapis):
                    if 'WASAPI' in hostapi['name']:
                        loopback_candidates = []
                        regular_inputs = []
                        
                        for device_idx, device in enumerate(devices):
                            if (device['hostapi'] == hostapi_idx and 
                                device['max_input_channels'] > 0):
                                device_name = device['name'].lower()
                                
                                # Check for explicit loopback indicators
                                # VB-Audio devices can be named: "CABLE Output", "VB-Audio Virtual Cable", etc.
                                if any(keyword in device_name for keyword in [
                                    'loopback', 'stereo mix', 'what u hear', 
                                    'vb-audio', 'cable', 'voicemeeter', 'virtual cable',
                                    'vb cable', 'vbaudio'
                                ]):
                                    loopback_candidates.append((device_idx, device))
                                else:
                                    # Regular input device (likely a microphone)
                                    regular_inputs.append((device_idx, device))
                        
                        # Prefer explicit loopback devices
                        if loopback_candidates:
                            device_idx, device = loopback_candidates[0]
                            logger.info(f"Found WASAPI loopback device: {device['name']}")
                            return device_idx
                        
                        # Warn if we're using a regular input (likely a mic, not system audio)
                        if regular_inputs:
                            device_idx, device = regular_inputs[0]
                            logger.warning(f"⚠️  Using WASAPI input device (likely microphone, not system audio): {device['name']}")
                            logger.warning("⚠️  For system audio capture, enable 'Stereo Mix' or install VB-Audio Virtual Cable")
                            return device_idx
            
            # Linux: Look for PulseAudio or ALSA
            elif system == 'Linux':
                for hostapi_idx, hostapi in enumerate(hostapis):
                    if 'PulseAudio' in hostapi['name'] or 'ALSA' in hostapi['name']:
                        loopback_candidates = []
                        regular_inputs = []
                        
                        for device_idx, device in enumerate(devices):
                            if (device['hostapi'] == hostapi_idx and 
                                device['max_input_channels'] > 0):
                                device_name = device['name'].lower()
                                
                                # Check for loopback indicators
                                if any(keyword in device_name for keyword in [
                                    'loopback', 'monitor', 'pulse'
                                ]):
                                    loopback_candidates.append((device_idx, device))
                                else:
                                    regular_inputs.append((device_idx, device))
                        
                        if loopback_candidates:
                            device_idx, device = loopback_candidates[0]
                            logger.info(f"Found Linux loopback device: {device['name']}")
                            return device_idx
                        
                        if regular_inputs:
                            device_idx, device = regular_inputs[0]
                            logger.warning(f"⚠️  Using Linux input device (may be microphone): {device['name']}")
                            logger.warning("⚠️  For system audio, configure PulseAudio loopback")
                            return device_idx
                        
        except Exception as e:
            logger.warning(f"Error querying host APIs: {e}")
        
        # Fallback: try to find default input device
        try:
            default_input = sd.default.device[0]
            if default_input is not None:
                device_name = devices[default_input]['name'].lower()
                loopback_keywords = [
                    'loopback', 'stereo mix', 'vb-audio', 'blackhole', 'black hole',
                    'cable', 'virtual cable', 'vb cable', 'vbaudio', 'voicemeeter'
                ]
                if any(keyword in device_name for keyword in loopback_keywords):
                    logger.info(f"Using default loopback device: {devices[default_input]['name']}")
                else:
                    logger.warning(f"⚠️  Using default input device (may be microphone): {devices[default_input]['name']}")
                    if system == 'Darwin':
                        logger.warning("⚠️  Install BlackHole for system audio: https://github.com/ExistentialAudio/BlackHole")
                    elif system == 'Windows':
                        logger.warning("⚠️  Enable 'Stereo Mix' or install VB-Audio Virtual Cable")
                return default_input
        except Exception as e:
            logger.warning(f"Error getting default input device: {e}")
        
        # Last resort: list all devices and try first input device
        logger.warning("No specific loopback device found, listing available devices:")
        for idx, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                logger.info(f"  Device {idx}: {device['name']} ({device['hostapi']})")
                # Return first input device as fallback
                logger.warning("⚠️  This may be a microphone, not system audio!")
                if system == 'Darwin':
                    logger.warning("⚠️  Install BlackHole for system audio: https://github.com/ExistentialAudio/BlackHole")
                return idx
        
        return None
    
    def _get_device_sample_rate(self) -> int:
        """Get the device's default or supported sample rate."""
        devices = sd.query_devices()
        if self.device is not None and self.device < len(devices):
            device_info = devices[self.device]
            default_rate = int(device_info.get('default_samplerate', 44100))
            
            # Try common sample rates in order of preference
            # Start with device's default and common rates
            test_rates = [default_rate, 48000, 44100, 96000, 192000, 32000, 16000]
            # Remove duplicates while preserving order
            test_rates = list(dict.fromkeys(test_rates))
            
            # Check if target rate is supported first
            if self.target_sample_rate in test_rates:
                try:
                    # Test if we can open a stream with target rate
                    test_stream = sd.InputStream(
                        device=self.device,
                        channels=1,
                        samplerate=self.target_sample_rate,
                        dtype=np.float32,
                        blocksize=1024
                    )
                    test_stream.close()
                    logger.info(f"Device supports target rate {self.target_sample_rate} Hz")
                    return self.target_sample_rate
                except Exception as e:
                    logger.debug(f"Device does not support {self.target_sample_rate} Hz: {e}")
            
            # Try device's default rate first
            try:
                test_stream = sd.InputStream(
                    device=self.device,
                    channels=1,
                    samplerate=default_rate,
                    dtype=np.float32,
                    blocksize=1024
                )
                test_stream.close()
                logger.info(f"Using device default sample rate: {default_rate} Hz")
                return default_rate
            except Exception as e:
                logger.debug(f"Device default rate {default_rate} Hz failed: {e}")
            
            # Try other common rates
            for rate in test_rates:
                if rate == default_rate:
                    continue  # Already tried
                try:
                    test_stream = sd.InputStream(
                        device=self.device,
                        channels=1,
                        samplerate=rate,
                        dtype=np.float32,
                        blocksize=1024
                    )
                    test_stream.close()
                    logger.info(f"Using sample rate: {rate} Hz")
                    return rate
                except Exception as e:
                    logger.debug(f"Rate {rate} Hz not supported: {e}")
                    continue
            
            # Last resort: try device default anyway (might work)
            logger.warning(f"Could not test sample rates, using device default: {default_rate} Hz")
            return default_rate
        
        # Fallback
        return 44100
    
    def _resample_audio(self, audio_data: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
        """Resample audio from one rate to another."""
        if from_rate == to_rate:
            return audio_data
        
        if HAS_SCIPY:
            # Calculate number of samples after resampling
            num_samples = int(len(audio_data) * to_rate / from_rate)
            resampled = signal.resample(audio_data, num_samples)
            return resampled.astype(np.float32)
        else:
            # Simple linear interpolation (less accurate but works without scipy)
            num_samples = int(len(audio_data) * to_rate / from_rate)
            indices = np.linspace(0, len(audio_data) - 1, num_samples)
            resampled = np.interp(indices, np.arange(len(audio_data)), audio_data)
            return resampled.astype(np.float32)
    
    def _audio_callback(self, indata, frames, time, status):
        """Callback function for audio stream."""
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        if self.is_recording:
            # Convert to float32 and ensure mono
            audio_data = indata[:, 0] if indata.ndim > 1 else indata
            audio_data = audio_data.astype(np.float32)
            
            # Add to queue
            try:
                self.audio_queue.put_nowait(audio_data.copy())
            except queue.Full:
                logger.warning("Audio queue full, dropping chunk")
    
    def _detect_silence(self, audio_data: np.ndarray, threshold: float = 0.01, min_duration_samples: int = None) -> bool:
        """
        Detect if audio contains silence.
        
        Args:
            audio_data: Audio data to check
            threshold: Amplitude threshold for silence (0.0-1.0)
            min_duration_samples: Minimum samples of silence to consider it silent
            
        Returns:
            True if audio is silent
        """
        if min_duration_samples is None:
            min_duration_samples = int(self.target_sample_rate * 0.5)  # 0.5 seconds
        
        # Calculate RMS (Root Mean Square) energy
        rms = np.sqrt(np.mean(audio_data ** 2))
        
        # Check if below threshold
        if rms < threshold:
            return True
        
        # Also check if most of the chunk is silent
        abs_audio = np.abs(audio_data)
        silent_samples = np.sum(abs_audio < threshold)
        silent_ratio = silent_samples / len(audio_data)
        
        # Consider silent if more than 80% is below threshold
        return silent_ratio > 0.8
    
    def _process_audio_chunks(self):
        """Process audio chunks from queue and call callback with phrase-aware buffering."""
        import time
        buffer = np.array([], dtype=np.float32)
        silence_duration = 0  # Track consecutive silence
        last_process_time = time.time()
        min_silence_duration_samples = int(self.target_sample_rate * self.min_silence_duration)
        max_buffer_duration_samples = int(self.target_sample_rate * self.max_buffer_duration)
        # Process every 6 seconds even without silence (for continuous audio, but wait longer for sentences)
        max_time_between_processes = 6.0
        
        while self.is_recording:
            try:
                # Get audio chunk with timeout
                chunk = self.audio_queue.get(timeout=0.1)
                
                # Resample to target rate if needed
                if self.device_sample_rate != self.target_sample_rate:
                    chunk = self._resample_audio(
                        chunk,
                        self.device_sample_rate,
                        self.target_sample_rate
                    )
                
                buffer = np.concatenate([buffer, chunk])
                
                # Check if current chunk is silent
                is_silent = self._detect_silence(chunk, threshold=self.silence_threshold)
                
                if is_silent:
                    silence_duration += len(chunk)
                else:
                    # Reset silence counter if we detect speech
                    silence_duration = 0
                
                # Process buffer when:
                # 1. We have enough silence (phrase ended), OR
                # 2. Buffer is getting too large (force process to avoid memory issues), OR
                # 3. Enough time has passed (for continuous audio like videos)
                should_process = False
                min_audio_duration = int(self.target_sample_rate * 1.5)  # At least 1.5 seconds of audio
                time_since_last_process = time.time() - last_process_time
                
                if silence_duration >= min_silence_duration_samples and len(buffer) >= min_audio_duration:
                    # We have silence and at least 0.5 seconds of audio - phrase likely ended
                    should_process = True
                    logger.debug(f"Processing buffer: {len(buffer)/self.target_sample_rate:.2f}s audio, {silence_duration/self.target_sample_rate:.2f}s silence")
                elif len(buffer) >= max_buffer_duration_samples:
                    # Buffer too large - force process
                    should_process = True
                    logger.debug(f"Processing buffer: Max duration reached ({len(buffer)/self.target_sample_rate:.2f}s)")
                elif time_since_last_process >= max_time_between_processes and len(buffer) >= min_audio_duration:
                    # Enough time passed - process for continuous audio
                    should_process = True
                    logger.debug(f"Processing buffer: Time-based trigger ({time_since_last_process:.2f}s since last process)")
                
                if should_process and len(buffer) > 0:
                    # Process the accumulated buffer (excluding the trailing silence)
                    # Keep last 0.3 seconds in buffer for overlap
                    overlap_samples = int(self.target_sample_rate * 0.3)
                    if len(buffer) > overlap_samples:
                        chunk_to_process = buffer[:-overlap_samples]
                        buffer = buffer[-overlap_samples:]
                    else:
                        chunk_to_process = buffer
                        buffer = np.array([], dtype=np.float32)
                    
                    # Reset silence counter and timer
                    silence_duration = 0
                    last_process_time = time.time()
                    
                    if self.callback and len(chunk_to_process) > 0:
                        try:
                            self.callback(chunk_to_process)
                        except Exception as e:
                            logger.error(f"Error in audio callback: {e}")
                            
            except queue.Empty:
                # If we have accumulated audio and haven't received new data for a while, process it
                time_since_last_process = time.time() - last_process_time
                if len(buffer) > 0 and (len(buffer) >= min_audio_duration or time_since_last_process >= max_time_between_processes):
                    # Process remaining buffer
                    if self.callback:
                        try:
                            self.callback(buffer)
                            buffer = np.array([], dtype=np.float32)
                            silence_duration = 0
                            last_process_time = time.time()
                        except Exception as e:
                            logger.error(f"Error in audio callback: {e}")
                continue
            except Exception as e:
                logger.error(f"Error processing audio: {e}")
    
    def start(self):
        """Start audio capture."""
        if self.is_recording:
            logger.warning("Audio capture already running")
            return
        
        try:
            # Open audio stream with device's native sample rate
            self.stream = sd.InputStream(
                device=self.device,
                channels=1,  # Mono
                samplerate=self.device_sample_rate,
                dtype=np.float32,
                blocksize=int(self.device_sample_rate * 0.5),  # 0.5 second blocks
                callback=self._audio_callback
            )
            
            self.stream.start()
            self.is_recording = True
            
            # Start processing thread
            self.thread = threading.Thread(target=self._process_audio_chunks, daemon=True)
            self.thread.start()
            
            logger.info("Audio capture started")
            
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            raise
    
    def stop(self):
        """Stop audio capture."""
        if not self.is_recording:
            logger.debug("Stop called but not recording")
            return
        
        logger.info("Stopping audio capture...")
        self.is_recording = False
        
        # Stop the stream first
        if self.stream:
            try:
                if self.stream.active:
                    self.stream.stop()
                self.stream.close()
            except Exception as e:
                logger.warning(f"Error stopping stream: {e}")
            finally:
                self.stream = None
        
        # Wait for processing thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)
            if self.thread.is_alive():
                logger.warning("Processing thread did not stop in time")
            self.thread = None
        
        # Clear queue
        cleared = 0
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
                cleared += 1
            except:
                break
        if cleared > 0:
            logger.debug(f"Cleared {cleared} items from audio queue")
        
        logger.info("Audio capture stopped")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

