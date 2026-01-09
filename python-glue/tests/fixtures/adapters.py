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
