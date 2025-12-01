import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from transcription import TranscriptionEngine


class TestTranscriptionEngine:
    
    @pytest.fixture
    def mock_whisper_model(self):
        with patch('transcription.WhisperModel') as mock_model_class:
            mock_instance = MagicMock()
            mock_model_class.return_value = mock_instance
            yield mock_instance
    
    def test_transcription_engine_initialization(self, mock_whisper_model):
        engine = TranscriptionEngine(model_size="base")
        assert engine.model_size == "base"
        assert engine.device == "cpu"
        assert engine.compute_type == "int8"
        assert engine.is_initialized is False
    
    def test_transcription_engine_initialization_custom(self, mock_whisper_model):
        engine = TranscriptionEngine(
            model_size="small",
            device="cuda",
            compute_type="float16"
        )
        assert engine.model_size == "small"
        assert engine.device == "cuda"
        assert engine.compute_type == "float16"
    
    def test_initialize_lazy_loading(self, mock_whisper_model):
        engine = TranscriptionEngine(model_size="base")
        assert engine.is_initialized is False
        
        engine.initialize()
        assert engine.is_initialized is True
        mock_whisper_model.assert_called_once()
    
    def test_initialize_idempotent(self, mock_whisper_model):
        engine = TranscriptionEngine(model_size="base")
        engine.initialize()
        engine.initialize()
        
        assert mock_whisper_model.call_count == 1
    
    def test_transcribe_chunk_not_initialized(self, mock_whisper_model):
        engine = TranscriptionEngine(model_size="base")
        
        mock_segment = MagicMock()
        mock_segment.text = "Hello world"
        mock_whisper_model.transcribe.return_value = (
            [mock_segment],
            MagicMock()
        )
        
        audio_data = np.random.randn(16000).astype(np.float32) * 0.1
        result = engine.transcribe_chunk(audio_data)
        
        assert engine.is_initialized is True
        assert result == "Hello world"
    
    def test_transcribe_chunk_silent_audio(self, mock_whisper_model):
        engine = TranscriptionEngine(model_size="base")
        engine.initialize()
        
        audio_data = np.zeros(16000, dtype=np.float32)
        result = engine.transcribe_chunk(audio_data)
        
        assert result is None
    
    def test_transcribe_chunk_success(self, mock_whisper_model):
        engine = TranscriptionEngine(model_size="base")
        engine.initialize()
        
        mock_segment1 = MagicMock()
        mock_segment1.text = "Hello"
        mock_segment2 = MagicMock()
        mock_segment2.text = "world"
        
        mock_whisper_model.transcribe.return_value = (
            [mock_segment1, mock_segment2],
            MagicMock()
        )
        
        audio_data = np.random.randn(16000).astype(np.float32) * 0.1
        result = engine.transcribe_chunk(audio_data)
        
        assert result == "Hello world"
    
    def test_transcribe_chunk_empty_segments(self, mock_whisper_model):
        engine = TranscriptionEngine(model_size="base")
        engine.initialize()
        
        mock_whisper_model.transcribe.return_value = (
            [],
            MagicMock()
        )
        
        audio_data = np.random.randn(16000).astype(np.float32) * 0.1
        result = engine.transcribe_chunk(audio_data)
        
        assert result is None
    
    def test_get_recent_context_empty(self, mock_whisper_model):
        engine = TranscriptionEngine()
        context = engine.get_recent_context(num_exchanges=3)
        assert context == ""
    
    def test_get_recent_context(self, mock_whisper_model):
        engine = TranscriptionEngine()
        engine.initialize()
        
        from datetime import datetime
        with engine.lock:
            engine.conversation_buffer.append((datetime.now(), "First message"))
            engine.conversation_buffer.append((datetime.now(), "Second message"))
            engine.conversation_buffer.append((datetime.now(), "Third message"))
        
        context = engine.get_recent_context(num_exchanges=2)
        assert "Second message" in context
        assert "Third message" in context
    
    def test_clear_buffer(self, mock_whisper_model):
        engine = TranscriptionEngine()
        engine.initialize()
        
        from datetime import datetime
        with engine.lock:
            engine.conversation_buffer.append((datetime.now(), "Test message"))
        
        assert len(engine.conversation_buffer) > 0
        
        engine.clear_buffer()
        assert len(engine.conversation_buffer) == 0
    
    def test_transcribe_chunk_exception_handling(self, mock_whisper_model):
        engine = TranscriptionEngine(model_size="base")
        engine.initialize()
        
        mock_whisper_model.transcribe.side_effect = Exception("Transcription error")
        
        audio_data = np.random.randn(16000).astype(np.float32) * 0.1
        result = engine.transcribe_chunk(audio_data)
        
        assert result is None
