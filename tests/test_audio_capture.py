import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from audio_capture import AudioCapture


class TestAudioCapture:
    
    @pytest.fixture
    def mock_sounddevice(self):
        with patch('audio_capture.sd') as mock_sd:
            mock_sd.query_devices.return_value = [
                {
                    'name': 'Test Microphone',
                    'max_input_channels': 1,
                    'max_output_channels': 0,
                    'default_samplerate': 44100,
                    'hostapi': 0
                },
                {
                    'name': 'VB-Cable',
                    'max_input_channels': 2,
                    'max_output_channels': 2,
                    'default_samplerate': 48000,
                    'hostapi': 0
                }
            ]
            
            mock_sd.query_hostapis.return_value = [
                {'name': 'Core Audio'}
            ]
            
            mock_sd.default.device = [0, None]
            
            yield mock_sd
    
    def test_audio_capture_initialization_default(self, mock_sounddevice):
        with patch('platform.system', return_value='Darwin'):
            capture = AudioCapture()
            assert capture.target_sample_rate == 16000
            assert capture.chunk_duration == 3.0
            assert capture.silence_threshold == 0.015
    
    def test_audio_capture_initialization_custom(self, mock_sounddevice):
        callback = Mock()
        capture = AudioCapture(
            sample_rate=22050,
            chunk_duration=5.0,
            callback=callback,
            silence_threshold=0.02
        )
        assert capture.target_sample_rate == 22050
        assert capture.chunk_duration == 5.0
        assert capture.callback == callback
        assert capture.silence_threshold == 0.02
    
    def test_find_loopback_device_macos(self, mock_sounddevice):
        with patch('platform.system', return_value='Darwin'):
            capture = AudioCapture()
            assert capture.device is not None
    
    def test_find_loopback_device_windows(self, mock_sounddevice):
        mock_sounddevice.query_devices.return_value = [
            {
                'name': 'Stereo Mix',
                'max_input_channels': 2,
                'max_output_channels': 0,
                'default_samplerate': 44100,
                'hostapi': 0
            }
        ]
        mock_sounddevice.query_hostapis.return_value = [
            {'name': 'WASAPI'}
        ]
        
        with patch('platform.system', return_value='Windows'):
            capture = AudioCapture()
            assert capture.device is not None
    
    def test_audio_capture_with_specific_device(self, mock_sounddevice):
        callback = Mock()
        capture = AudioCapture(device=1, callback=callback)
        assert capture.device == 1
    
    def test_audio_capture_invalid_device(self, mock_sounddevice):
        with pytest.raises(ValueError):
            AudioCapture(device=999)
    
    def test_start_stop_recording(self, mock_sounddevice):
        mock_stream = MagicMock()
        mock_stream.active = True
        mock_sounddevice.InputStream.return_value = mock_stream
        
        capture = AudioCapture()
        capture.start()
        
        assert capture.is_recording is True
        assert capture.stream is not None
        mock_sounddevice.InputStream.assert_called_once()
        
        capture.stop()
        assert capture.is_recording is False
    
    def test_start_already_recording(self, mock_sounddevice):
        mock_stream = MagicMock()
        mock_sounddevice.InputStream.return_value = mock_stream
        
        capture = AudioCapture()
        capture.start()
        capture.start()
        
        assert mock_sounddevice.InputStream.call_count == 1
    
    def test_stop_when_not_recording(self, mock_sounddevice):
        capture = AudioCapture()
        capture.stop()
        assert capture.is_recording is False
    
    def test_detect_silence(self, mock_sounddevice):
        capture = AudioCapture()
        
        silent_audio = np.zeros(16000, dtype=np.float32)
        assert capture._detect_silence(silent_audio) is True
        
        noisy_audio = np.random.randn(16000).astype(np.float32) * 0.1
        assert capture._detect_silence(noisy_audio) is False
    
    def test_resample_audio_same_rate(self, mock_sounddevice):
        capture = AudioCapture()
        audio = np.random.randn(16000).astype(np.float32)
        resampled = capture._resample_audio(audio, 16000, 16000)
        assert len(resampled) == len(audio)
    
    def test_resample_audio_different_rate(self, mock_sounddevice):
        capture = AudioCapture()
        audio = np.random.randn(16000).astype(np.float32)
        resampled = capture._resample_audio(audio, 16000, 8000)
        assert len(resampled) == 8000
    
    def test_audio_callback(self, mock_sounddevice):
        callback = Mock()
        capture = AudioCapture(callback=callback)
        capture.is_recording = True
        
        indata = np.random.randn(4800, 1).astype(np.float32) * 0.1
        capture._audio_callback(indata, 4800, None, None)
        
        assert not capture.audio_queue.empty()
