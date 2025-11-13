"""
Answer generation module using Ollama API.
"""

import requests
import logging
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Generates answers using Ollama local LLM."""
    
    def __init__(self, 
                 model: str = "llama3.2:3b",
                 base_url: str = "http://localhost:11434"):
        """
        Initialize answer generator.
        
        Args:
            model: Ollama model name
            base_url: Ollama API base URL
        """
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
        self.chat_url = f"{base_url}/api/chat"
    
    def check_ollama_running(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama check failed: {e}")
            return False
    
    def check_model_available(self) -> bool:
        """Check if the specified model is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                return any(self.model in name for name in model_names)
            return False
        except Exception as e:
            logger.error(f"Model check failed: {e}")
            return False
    
    def generate_answer(self, 
                       question: str, 
                       context: Optional[str] = None,
                       max_tokens: int = 150) -> Optional[str]:
        """
        Generate an answer to a question.
        
        Args:
            question: The question to answer
            context: Optional conversation context
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated answer or None if error
        """
        if not self.check_ollama_running():
            logger.error("Ollama is not running")
            return None
        
        # Build prompt
        if context:
            prompt = f"""Based on the following conversation context, provide a concise and direct answer to the question.

Context: {context}

Question: {question}

Answer:"""
        else:
            prompt = f"""Provide a concise and direct answer to the following question.

Question: {question}

Answer:"""
        
        try:
            # Use chat API for better results
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant. Provide concise, direct answers to questions. Keep responses brief and to the point."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.7
                }
            }
            
            response = requests.post(
                self.chat_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('message', {}).get('content', '').strip()
                
                if answer:
                    logger.info(f"Generated answer for question: {question[:50]}...")
                    return answer
                else:
                    logger.warning("Empty answer from Ollama")
                    return None
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("Ollama API timeout")
            return None
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return None
    
    def set_model(self, model: str):
        """Update the model to use."""
        self.model = model
        logger.info(f"Answer generator model set to {model}")


