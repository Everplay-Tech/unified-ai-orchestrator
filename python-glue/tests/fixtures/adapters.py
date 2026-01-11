"""Adapter fixtures for testing"""

import pytest
from unittest.mock import AsyncMock, Mock
from unified_ai.adapters.base import ToolAdapter, ToolCapabilities, ToolCapability, Message, Response


class MockAdapter(ToolAdapter):
    """Mock adapter for testing"""
    
    def __init__(self, name: str = "mock"):
        self._name = name
        self._capabilities = ToolCapabilities(
            supports_streaming=True,
            supports_code_context=False,
            supported_capabilities=[ToolCapability.GENERAL_CHAT],
        )
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def capabilities(self) -> ToolCapabilities:
        return self._capabilities
    
    async def is_available(self) -> bool:
        return True
    
    async def chat(self, messages, context=None):
        return Response(
            content=f"Mock response from {self._name}",
            tool=self._name,
        )
    
    async def stream_chat(self, messages, context=None):
        async def _stream():
            yield f"Mock stream from {self._name}"
        return _stream()


@pytest.fixture
def mock_adapter():
    """Create a mock adapter"""
    return MockAdapter()


@pytest.fixture
def mock_claude_adapter():
    """Create a mock Claude adapter"""
    adapter = MockAdapter("claude")
    adapter.model = "claude-3-5-sonnet-20241022"
    adapter._capabilities.supports_code_context = True
    adapter._capabilities.max_context_length = 200000
    return adapter


@pytest.fixture
def mock_gpt_adapter():
    """Create a mock GPT adapter"""
    adapter = MockAdapter("gpt")
    adapter.model = "gpt-4"
    adapter._capabilities.supports_code_context = True
    adapter._capabilities.max_context_length = 128000
    return adapter


@pytest.fixture
def mock_adapters_dict():
    """Create a dictionary of mock adapters"""
    return {
        "claude": MockAdapter("claude"),
        "gpt": MockAdapter("gpt"),
    }


class AdapterFactory:
    """Factory for creating test adapters"""
    
    @staticmethod
    def create(name: str, **kwargs):
        """Create an adapter with custom configuration"""
        adapter = MockAdapter(name)
        for key, value in kwargs.items():
            setattr(adapter, key, value)
        return adapter
    
    @staticmethod
    def create_with_response(name: str, response_content: str):
        """Create an adapter that returns a specific response"""
        adapter = MockAdapter(name)
        
        async def custom_chat(messages, context=None):
            return Response(
                content=response_content,
                tool=name,
                metadata={"usage": {"input_tokens": 10, "output_tokens": 20}}
            )
        
        adapter.chat = custom_chat
        return adapter
    
    @staticmethod
    def create_failing(name: str, error_message: str = "API Error"):
        """Create an adapter that fails"""
        adapter = MockAdapter(name)
        
        async def failing_chat(messages, context=None):
            raise Exception(error_message)
        
        adapter.chat = failing_chat
        return adapter


@pytest.fixture
def adapter_factory():
    """Adapter factory fixture"""
    return AdapterFactory
