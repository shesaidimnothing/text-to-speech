"""
Question detection module that identifies questions in transcribed text.
"""

import re
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class QuestionDetector:
    """Detects questions in text using pattern matching."""
    
    # Question words
    QUESTION_WORDS = {
        'who', 'what', 'where', 'when', 'why', 'how',
        'which', 'whose', 'whom', 'can', 'could', 'would',
        'should', 'will', 'is', 'are', 'was', 'were',
        'do', 'does', 'did', 'has', 'have', 'had'
    }
    
    # Question patterns
    QUESTION_PATTERNS = [
        r'\?',  # Question mark
        r'^(who|what|where|when|why|how|which|whose|whom)\s+',  # Starts with question word
        r'\b(can|could|would|should|will|is|are|was|were|do|does|did|has|have|had)\s+\w+\s+\?',  # Auxiliary verb + subject + ?
        r'^(is|are|was|were|do|does|did|can|could|would|should|will)\s+',  # Starts with auxiliary
    ]
    
    def __init__(self, sensitivity: float = 0.7):
        """
        Initialize question detector.
        
        Args:
            sensitivity: Detection sensitivity (0.0-1.0). Higher = more sensitive.
        """
        self.sensitivity = max(0.0, min(1.0, sensitivity))
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.QUESTION_PATTERNS]
    
    def is_question(self, text: str) -> Tuple[bool, float]:
        """
        Check if text contains a question.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (is_question, confidence)
        """
        if not text or not text.strip():
            return False, 0.0
        
        text = text.strip()
        confidence = 0.0
        
        # Check for explicit question mark
        if '?' in text:
            confidence += 0.5
        
        # Check question words at start
        first_word = text.split()[0].lower().rstrip('?.,!') if text.split() else ""
        if first_word in self.QUESTION_WORDS:
            confidence += 0.3
        
        # Check patterns
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                confidence += 0.2
                break
        
        # Check for question structure (auxiliary verb inversion)
        words = text.lower().split()
        if len(words) >= 2:
            if words[0] in {'is', 'are', 'was', 'were', 'do', 'does', 'did', 
                           'can', 'could', 'would', 'should', 'will', 'has', 'have', 'had'}:
                confidence += 0.2
        
        # Normalize confidence
        confidence = min(1.0, confidence)
        
        # Apply sensitivity threshold
        threshold = 0.3 + (0.4 * (1.0 - self.sensitivity))  # Inverted: higher sensitivity = lower threshold
        is_question = confidence >= threshold
        
        return is_question, confidence
    
    def extract_questions(self, text: str) -> List[Tuple[str, float]]:
        """
        Extract all questions from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of (question_text, confidence) tuples
        """
        questions = []
        
        # Split by sentences
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            is_q, confidence = self.is_question(sentence)
            if is_q:
                questions.append((sentence, confidence))
        
        return questions
    
    def set_sensitivity(self, sensitivity: float):
        """Update detection sensitivity."""
        self.sensitivity = max(0.0, min(1.0, sensitivity))
        logger.info(f"Question detection sensitivity set to {self.sensitivity}")


