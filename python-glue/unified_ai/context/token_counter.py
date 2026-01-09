"""Token counting utilities for various models"""

import tiktoken
from typing import Dict, Optional


# Model tokenizer mappings
MODEL_ENCODINGS: Dict[str, str] = {
    # OpenAI models
    "gpt-4": "cl100k_base",
    "gpt-4-turbo": "cl100k_base",
    "gpt-4o": "o200k_base",
    "gpt-3.5-turbo": "cl100k_base",
    "gpt-3.5-turbo-16k": "cl100k_base",
    # Claude models (approximate, using cl100k_base)
    "claude-3-opus": "cl100k_base",
    "claude-3-sonnet": "cl100k_base",
    "claude-3-haiku": "cl100k_base",
    "claude-3-5-sonnet": "cl100k_base",
    # Default
    "default": "cl100k_base",
}

# Model context window sizes (approximate)
MODEL_CONTEXT_WINDOWS: Dict[str, int] = {
    "gpt-4": 8192,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-3.5-turbo": 16385,
    "gpt-3.5-turbo-16k": 16385,
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    "claude-3-5-sonnet": 200000,
    "default": 8192,
}


class TokenCounter:
    """Token counter for various models"""
    
    def __init__(self):
        self._encodings: Dict[str, tiktoken.Encoding] = {}
    
    def _get_encoding(self, model: str) -> tiktoken.Encoding:
        """Get or create encoding for a model"""
        encoding_name = MODEL_ENCODINGS.get(model, MODEL_ENCODINGS["default"])
        
        if encoding_name not in self._encodings:
            try:
                self._encodings[encoding_name] = tiktoken.get_encoding(encoding_name)
            except KeyError:
                # Fallback to default
                self._encodings[encoding_name] = tiktoken.get_encoding(MODEL_ENCODINGS["default"])
        
        return self._encodings[encoding_name]
    
    def count_tokens(self, text: str, model: str = "default") -> int:
        """
        Count tokens in text for a specific model
        
        Args:
            text: Text to count tokens for
            model: Model name
        
        Returns:
            Number of tokens
        """
        encoding = self._get_encoding(model)
        return len(encoding.encode(text))
    
    def count_message_tokens(
        self,
        messages: list,
        model: str = "default"
    ) -> int:
        """
        Count tokens for a list of messages (OpenAI format)
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name
        
        Returns:
            Number of tokens
        """
        encoding = self._get_encoding(model)
        
        # Approximate token count for messages
        # Format: role + content + separators
        tokens = 0
        for message in messages:
            tokens += 4  # Base tokens per message
            if isinstance(message, dict):
                if "role" in message:
                    tokens += len(encoding.encode(message["role"]))
                if "content" in message:
                    content = message["content"]
                    if isinstance(content, str):
                        tokens += len(encoding.encode(content))
                    elif isinstance(content, list):
                        # Handle multimodal content
                        for item in content:
                            if isinstance(item, dict) and "text" in item:
                                tokens += len(encoding.encode(item["text"]))
            elif isinstance(message, str):
                tokens += len(encoding.encode(message))
        
        return tokens
    
    def get_context_window(self, model: str) -> int:
        """Get context window size for a model"""
        return MODEL_CONTEXT_WINDOWS.get(model, MODEL_CONTEXT_WINDOWS["default"])
    
    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str
    ) -> float:
        """
        Estimate cost based on token counts
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name
        
        Returns:
            Estimated cost in USD
        """
        # Pricing per 1M tokens (approximate)
        pricing = {
            "gpt-4": {"input": 30.0, "output": 60.0},
            "gpt-4-turbo": {"input": 10.0, "output": 30.0},
            "gpt-4o": {"input": 2.5, "output": 10.0},
            "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
            "claude-3-opus": {"input": 15.0, "output": 75.0},
            "claude-3-sonnet": {"input": 3.0, "output": 15.0},
            "claude-3-haiku": {"input": 0.25, "output": 1.25},
            "claude-3-5-sonnet": {"input": 3.0, "output": 15.0},
        }
        
        model_pricing = pricing.get(model, {"input": 1.0, "output": 2.0})
        
        input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (output_tokens / 1_000_000) * model_pricing["output"]
        
        return input_cost + output_cost


# Global token counter instance
_token_counter: Optional[TokenCounter] = None


def get_token_counter() -> TokenCounter:
    """Get global token counter instance"""
    global _token_counter
    if _token_counter is None:
        _token_counter = TokenCounter()
    return _token_counter


def count_tokens(text: str, model: str = "default") -> int:
    """Convenience function to count tokens"""
    return get_token_counter().count_tokens(text, model)


def count_message_tokens(messages: list, model: str = "default") -> int:
    """Convenience function to count message tokens"""
    return get_token_counter().count_message_tokens(messages, model)
