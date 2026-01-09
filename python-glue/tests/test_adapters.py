"""Tests for tool adapters"""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from unified_ai.adapters import (
    ClaudeAdapter,
    GPTAdapter,
    PerplexityAdapter,
    ToolAdapter,
)


class TestClaudeAdapter:
    """Test Claude adapter"""
    
    def test_claude_adapter_init(self):
        """Test Claude adapter initialization"""
        adapter = ClaudeAdapter(api_key="test-key")
        
        assert adapter.name == "claude"
        assert adapter.capabilities.supports_streaming is True
        assert adapter.capabilities.supports_code_context is True
    
    def test_claude_adapter_is_available(self):
        """Test Claude adapter availability check"""
        adapter = ClaudeAdapter(api_key="test-key")
        assert adapter.is_available() is True
        
        adapter_no_key = ClaudeAdapter(api_key=None)
        assert adapter_no_key.is_available() is False
    
    @pytest.mark.asyncio
    async def test_claude_adapter_chat(self):
        """Test Claude adapter chat (mocked)"""
        adapter = ClaudeAdapter(api_key="test-key")
        
        with patch.object(adapter, "_get_async_client") as mock_client:
            mock_response = AsyncMock()
            mock_response.content = [
                Mock(text="Hello, this is Claude!")
            ]
            mock_response.usage = Mock(input_tokens=10, output_tokens=5)
            
            mock_async_client = AsyncMock()
            mock_async_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client
            
            from unified_ai.adapters.base import Message
            messages = [Message(role="user", content="Hello")]
            
            response = await adapter.chat(messages)
            
            assert response.content == "Hello, this is Claude!"
            assert response.tool == "claude"


class TestGPTAdapter:
    """Test GPT adapter"""
    
    def test_gpt_adapter_init(self):
        """Test GPT adapter initialization"""
        adapter = GPTAdapter(api_key="test-key")
        
        assert adapter.name == "gpt"
        assert adapter.capabilities.supports_streaming is True
    
    @pytest.mark.asyncio
    async def test_gpt_adapter_chat(self):
        """Test GPT adapter chat (mocked)"""
        adapter = GPTAdapter(api_key="test-key")
        
        with patch.object(adapter, "_get_client") as mock_client:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="Hello from GPT!"))]
            mock_response.usage = Mock(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
            )
            
            mock_async_client = AsyncMock()
            mock_async_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client
            
            from unified_ai.adapters.base import Message
            messages = [Message(role="user", content="Hello")]
            
            response = await adapter.chat(messages)
            
            assert response.content == "Hello from GPT!"
            assert response.tool == "gpt"


class TestPerplexityAdapter:
    """Test Perplexity adapter"""
    
    def test_perplexity_adapter_init(self):
        """Test Perplexity adapter initialization"""
        adapter = PerplexityAdapter(api_key="test-key")
        
        from unified_ai.adapters.base import ToolCapability
        assert adapter.name == "perplexity"
        assert ToolCapability.WEB_SEARCH in adapter.capabilities.supported_capabilities
