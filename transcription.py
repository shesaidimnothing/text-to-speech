"""
Transcription module using faster-whisper for real-time speech-to-text.
"""

import logging
import re
from typing import Optional, Callable, List, Tuple
from faster_whisper import WhisperModel
import numpy as np
import threading
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)


class TranscriptionEngine:
    """Real-time transcription using faster-whisper."""
    
    def __init__(self, 
                 model_size: str = "base",
                 device: str = "cpu",
                 compute_type: str = "int8",
                 callback: Optional[Callable] = None):
        """
        Initialize transcription engine.
        
        Args:
            model_size: Whisper model size ("tiny", "base", "small", "medium", "large")
            device: Device to use ("cpu" or "cuda")
            compute_type: Compute type ("int8", "int8_float16", "float16", "float32")
            callback: Function to call with transcribed text (text, is_final)
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.callback = callback
        
        self.model: Optional[WhisperModel] = None
        self.is_initialized = False
        self.lock = threading.Lock()
        
        # Conversation buffer (stores (timestamp, text) tuples)
        self.conversation_buffer = deque(maxlen=100)  # Roughly 5 minutes
        self.buffer_minutes = 5
    
    def initialize(self):
        """Initialize the Whisper model (lazy loading)."""
        if self.is_initialized:
            return
        
        try:
            logger.info(f"Loading Whisper model: {self.model_size} on {self.device}")
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            self.is_initialized = True
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def transcribe_chunk(self, audio_data: np.ndarray) -> Optional[str]:
        """
        Transcribe a single audio chunk.
        Uses VAD to ensure we only transcribe complete phrases.
        
        Args:
            audio_data: Audio data as numpy array (float32, mono, 16kHz)
            
        Returns:
            Transcribed text or None if no speech detected
        """
        if not self.is_initialized:
            self.initialize()
        
        if self.model is None:
            return None
        
        # Check if audio has meaningful content
        audio_level = np.abs(audio_data).mean()
        if audio_level < 0.001:  # Very quiet, likely silence
            logger.debug("Skipping silent audio chunk")
            return None
        
        try:
            # Transcribe with VAD (Voice Activity Detection)
            # Increased min_silence_duration to better detect phrase boundaries
            segments, info = self.model.transcribe(
                audio_data,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=1200,  # Wait for 1.2 seconds of silence (increased for sentence completion)
                    threshold=0.5,  # VAD threshold
                    min_speech_duration_ms=250  # Minimum speech duration
                ),
                condition_on_previous_text=True  # Better context for phrase completion
                # Removed initial_prompt as it was being transcribed as actual text
            )
            
            # Collect all segments
            text_parts = []
            for segment in segments:
                text = segment.text.strip()
                if text:  # Only add non-empty segments
                    text_parts.append(text)
            
            if text_parts:
                # Join segments with proper spacing
                full_text = " ".join(text_parts)
                
                # Clean up the text
                full_text = full_text.strip()
                
                # Filter out common prompt phrases that might be transcribed
                prompt_phrases = [
                    "this is a conversation",
                    "transcribe complete sentences",
                    "transcribe complete sentences and phrases",
                    "wait for sentence endings"
                ]
                for phrase in prompt_phrases:
                    # Remove the phrase if it appears (case-insensitive)
                    full_text = re.sub(re.escape(phrase), "", full_text, flags=re.IGNORECASE)
                    # Also remove with period
                    full_text = re.sub(re.escape(phrase + "."), "", full_text, flags=re.IGNORECASE)
                
                # Clean up extra spaces
                full_text = re.sub(r'\s+', ' ', full_text).strip()
                
                # Only return if we have meaningful text
                if len(full_text) > 0:
                    # Add to conversation buffer
                    with self.lock:
                        self.conversation_buffer.append((datetime.now(), full_text))
                    
                    logger.debug(f"Transcribed: {full_text[:100]}...")
                    return full_text
            
            return None
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
    
    def get_recent_context(self, num_exchanges: int = 3) -> str:
        """
        Get recent conversation context for LLM.
        
        Args:
            num_exchanges: Number of recent exchanges to include
            
        Returns:
            Formatted context string
        """
        with self.lock:
            if not self.conversation_buffer:
                return ""
            
            # Get last N entries
            recent = list(self.conversation_buffer)[-num_exchanges:]
            context_parts = [text for _, text in recent]
            return " ".join(context_parts)
    
    def get_full_buffer(self) -> List[Tuple[datetime, str]]:
        """Get full conversation buffer."""
        with self.lock:
            return list(self.conversation_buffer)
    
    def clear_buffer(self):
        """Clear the conversation buffer."""
        with self.lock:
            self.conversation_buffer.clear()
        logger.info("Conversation buffer cleared")
    
    def __del__(self):
        """Cleanup."""
        self.model = None


