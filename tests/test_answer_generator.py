import pytest
from unittest.mock import Mock, patch, MagicMock
from answer_generator import AnswerGenerator


class TestAnswerGenerator:
    
    @pytest.fixture
    def mock_requests(self):
        with patch('answer_generator.requests') as mock_requests:
            yield mock_requests
    
    def test_answer_generator_initialization_default(self):
        generator = AnswerGenerator()
        assert generator.model == "llama3.2:3b"
        assert generator.base_url == "http://localhost:11434"
        assert generator.api_url == "http://localhost:11434/api/generate"
        assert generator.chat_url == "http://localhost:11434/api/chat"
    
    def test_answer_generator_initialization_custom(self):
        generator = AnswerGenerator(
            model="mistral",
            base_url="http://localhost:11435"
        )
        assert generator.model == "mistral"
        assert generator.base_url == "http://localhost:11435"
        assert generator.api_url == "http://localhost:11435/api/generate"
    
    def test_check_ollama_running_success(self, mock_requests):
        mock_requests.get.return_value.status_code = 200
        mock_requests.get.return_value.json.return_value = {"models": []}
        
        generator = AnswerGenerator()
        result = generator.check_ollama_running()
        
        assert result is True
        mock_requests.get.assert_called_once()
    
    def test_check_ollama_running_failure_connection_error(self, mock_requests):
        mock_requests.get.side_effect = Exception("Connection refused")
        
        generator = AnswerGenerator()
        result = generator.check_ollama_running()
        
        assert result is False
    
    def test_check_ollama_running_failure_status_code(self, mock_requests):
        mock_requests.get.return_value.status_code = 500
        
        generator = AnswerGenerator()
        result = generator.check_ollama_running()
        
        assert result is False
    
    def test_check_model_available_success(self, mock_requests):
        mock_requests.get.return_value.status_code = 200
        mock_requests.get.return_value.json.return_value = {
            "models": [{"name": "llama3.2:3b"}]
        }
        
        generator = AnswerGenerator(model="llama3.2:3b")
        result = generator.check_model_available()
        
        assert result is True
    
    def test_check_model_not_available(self, mock_requests):
        mock_requests.get.return_value.status_code = 200
        mock_requests.get.return_value.json.return_value = {
            "models": [{"name": "other-model"}]
        }
        
        generator = AnswerGenerator(model="llama3.2:3b")
        result = generator.check_model_available()
        
        assert result is False
    
    def test_check_model_available_no_models(self, mock_requests):
        mock_requests.get.return_value.status_code = 200
        mock_requests.get.return_value.json.return_value = {"models": []}
        
        generator = AnswerGenerator()
        result = generator.check_model_available()
        
        assert result is False
    
    @pytest.mark.slow
    def test_generate_answer_success(self, mock_requests):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Python is a high-level programming language."
        }
        mock_requests.post.return_value = mock_response
        
        generator = AnswerGenerator()
        answer = generator.generate_answer("What is Python?", context=None)
        
        assert answer == "Python is a high-level programming language."
        mock_requests.post.assert_called_once()
    
    @pytest.mark.slow
    def test_generate_answer_with_context(self, mock_requests):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Based on the context, Python is a programming language."
        }
        mock_requests.post.return_value = mock_response
        
        generator = AnswerGenerator()
        context = "We were discussing programming languages."
        answer = generator.generate_answer("What is Python?", context=context)
        
        assert "Python" in answer
        call_args = mock_requests.post.call_args
        assert call_args is not None
        call_kwargs = call_args[1]
        payload = call_kwargs.get('json', {})
        assert 'context' in str(payload) or context in str(payload)
    
    def test_generate_answer_api_error(self, mock_requests):
        mock_requests.post.side_effect = Exception("API Error")
        
        generator = AnswerGenerator()
        answer = generator.generate_answer("What is Python?")
        
        assert answer is None
    
    def test_generate_answer_bad_status(self, mock_requests):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_requests.post.return_value = mock_response
        
        generator = AnswerGenerator()
        answer = generator.generate_answer("What is Python?")
        
        assert answer is None
    
    def test_set_model(self):
        generator = AnswerGenerator(model="llama3.2:3b")
        assert generator.model == "llama3.2:3b"
        
        generator.set_model("mistral")
        assert generator.model == "mistral"
    
    def test_generate_answer_empty_question(self, mock_requests):
        generator = AnswerGenerator()
        answer = generator.generate_answer("", context=None)
        assert answer is None or answer == ""

