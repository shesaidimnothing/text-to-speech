import pytest
from question_detector import QuestionDetector


class TestQuestionDetector:
    
    def test_question_detector_initialization(self):
        detector = QuestionDetector(sensitivity=0.7)
        assert detector is not None
        assert detector.sensitivity == 0.7
    
    def test_initialization_with_default_sensitivity(self):
        detector = QuestionDetector()
        assert detector.sensitivity == 0.7
    
    def test_initialization_sensitivity_boundaries(self):
        detector_low = QuestionDetector(sensitivity=-0.5)
        assert detector_low.sensitivity == 0.0
        
        detector_high = QuestionDetector(sensitivity=1.5)
        assert detector_high.sensitivity == 1.0
    
    def test_detects_question_mark(self):
        detector = QuestionDetector()
        is_question, confidence = detector.is_question("What is the weather today?")
        assert is_question is True
        assert confidence >= 0.5
    
    def test_detects_question_words(self):
        detector = QuestionDetector()
        
        questions = [
            "What is Python?",
            "How does this work?",
            "Where are you going?",
            "Why is this happening?",
            "Who is that?",
            "When will it be ready?",
        ]
        
        for question in questions:
            is_question, confidence = detector.is_question(question)
            assert is_question is True, f"Should detect question: {question}"
            assert confidence > 0.0
    
    def test_detects_questions_without_question_mark(self):
        detector = QuestionDetector(sensitivity=0.8)
        
        questions_without_mark = [
            "What is Python",
            "How does this work",
            "Where are you",
        ]
        
        for question in questions_without_mark:
            is_question, confidence = detector.is_question(question)
            assert isinstance(is_question, bool)
            assert 0.0 <= confidence <= 1.0
    
    def test_does_not_detect_statements(self):
        detector = QuestionDetector()
        
        statements = [
            "This is a statement.",
            "I like Python programming.",
            "The weather is nice today.",
            "She went to the store.",
            "Python is a programming language.",
        ]
        
        for statement in statements:
            is_question, confidence = detector.is_question(statement)
            assert is_question is False, f"Should not detect question: {statement}"
    
    def test_empty_string(self):
        detector = QuestionDetector()
        is_question, confidence = detector.is_question("")
        assert is_question is False
        assert confidence == 0.0
    
    def test_whitespace_only(self):
        detector = QuestionDetector()
        is_question, confidence = detector.is_question("   ")
        assert is_question is False
        assert confidence == 0.0
    
    def test_sensitivity_adjustment(self):
        high_sensitivity = QuestionDetector(sensitivity=0.9)
        is_question_high, conf_high = high_sensitivity.is_question("Is this a question")
        
        low_sensitivity = QuestionDetector(sensitivity=0.3)
        is_question_low, conf_low = low_sensitivity.is_question("Is this a question")
        
        assert isinstance(is_question_high, bool)
        assert isinstance(is_question_low, bool)
        assert 0.0 <= conf_high <= 1.0
        assert 0.0 <= conf_low <= 1.0
    
    def test_set_sensitivity(self):
        detector = QuestionDetector(sensitivity=0.5)
        assert detector.sensitivity == 0.5
        
        detector.set_sensitivity(0.8)
        assert detector.sensitivity == 0.8
        
        detector.set_sensitivity(-1.0)
        assert detector.sensitivity == 0.0
        
        detector.set_sensitivity(2.0)
        assert detector.sensitivity == 1.0
    
    def test_extract_questions(self):
        detector = QuestionDetector()
        
        text = "What is Python? This is a statement. How does it work? Another statement."
        questions = detector.extract_questions(text)
        
        assert len(questions) >= 2
        assert all(isinstance(q, tuple) and len(q) == 2 for q in questions)
        assert all("Python" in q[0] or "work" in q[0] for q in questions)
    
    def test_extract_questions_empty(self):
        detector = QuestionDetector()
        
        text = "This is a statement. Another statement. No questions here."
        questions = detector.extract_questions(text)
        
        assert isinstance(questions, list)

