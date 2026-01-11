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
    
    @pytest.mark.asyncio
    async def test_claude_adapter_is_available(self):
        """Test Claude adapter availability check"""
        adapter = ClaudeAdapter(api_key="test-key")
        assert await adapter.is_available() is True
        
        adapter_no_key = ClaudeAdapter(api_key=None)
        assert await adapter_no_key.is_available() is False
    
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


class TestLocalLLMAdapter:
    """Test Local LLM adapter"""
    
    def test_local_adapter_init(self):
        """Test Local LLM adapter initialization"""
        from unified_ai.adapters.local import LocalLLMAdapter
        
        adapter = LocalLLMAdapter(base_url="http://localhost:11434", model="llama2")
        assert adapter.name == "local"
        assert adapter.model == "llama2"
        assert adapter.capabilities.supports_streaming is True
    
    @pytest.mark.asyncio
    async def test_local_adapter_is_available(self):
        """Test Local LLM adapter availability check"""
        from unified_ai.adapters.local import LocalLLMAdapter
        
        adapter = LocalLLMAdapter()
        
        with patch('unified_ai.adapters.local.LocalLLMAdapter._get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": [{"name": "llama2"}]}
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client
            
            available = await adapter.is_available()
            assert available is True
    
    @pytest.mark.asyncio
    async def test_local_adapter_list_models(self):
        """Test listing available models"""
        from unified_ai.adapters.local import LocalLLMAdapter
        
        adapter = LocalLLMAdapter()
        
        with patch('unified_ai.adapters.local.LocalLLMAdapter._get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [
                    {"name": "llama2"},
                    {"name": "mistral"},
                ]
            }
            mock_response.raise_for_status = Mock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client
            
            models = await adapter.list_models()
            assert "llama2" in models
            assert "mistral" in models
    
    @pytest.mark.asyncio
    async def test_local_adapter_chat(self):
        """Test Local LLM adapter chat"""
        from unified_ai.adapters.local import LocalLLMAdapter
        
        adapter = LocalLLMAdapter(model="llama2")
        
        with patch('unified_ai.adapters.local.LocalLLMAdapter._get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": "Hello from local LLM!",
                "done": True,
            }
            mock_response.raise_for_status = Mock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client
            
            from unified_ai.adapters.base import Message
            messages = [Message(role="user", content="Hello")]
            
            response = await adapter.chat(messages)
            assert response.content == "Hello from local LLM!"
            assert response.tool == "local"


class TestCursorAdapter:
    """Test Cursor adapter"""
    
    def test_cursor_adapter_init(self):
        """Test Cursor adapter initialization"""
        from unified_ai.adapters.cursor import CursorAdapter
        
        adapter = CursorAdapter(api_key="test-key")
        assert adapter.name == "cursor"
        assert adapter.capabilities.supports_code_context is True
    
    @pytest.mark.asyncio
    async def test_cursor_adapter_is_available(self):
        """Test Cursor adapter availability check"""
        from unified_ai.adapters.cursor import CursorAdapter
        
        adapter = CursorAdapter(api_key="test-key")
        # Should be available if API key is set
        assert await adapter.is_available() is True
        
        adapter_no_key = CursorAdapter(api_key=None)
        # May not be available without key
        # (depends on local Cursor instance)
    
    @pytest.mark.asyncio
    async def test_cursor_adapter_chat(self):
        """Test Cursor adapter chat"""
        from unified_ai.adapters.cursor import CursorAdapter
        
        adapter = CursorAdapter(api_key="test-key")
        
        with patch('unified_ai.adapters.cursor.CursorAdapter._get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "content": "Hello from Cursor!",
                "model": "cursor",
                "usage": {"input_tokens": 10, "output_tokens": 20},
            }
            mock_response.raise_for_status = Mock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client
            
            from unified_ai.adapters.base import Message
            messages = [Message(role="user", content="Hello")]
            
            response = await adapter.chat(messages)
            assert response.content == "Hello from Cursor!"
            assert response.tool == "cursor"
    
    @pytest.mark.asyncio
    async def test_cursor_adapter_error_handling(self):
        """Test Cursor adapter error handling"""
        from unified_ai.adapters.cursor import CursorAdapter
        import httpx
        
        adapter = CursorAdapter(api_key="test-key")
        
        with patch('unified_ai.adapters.cursor.CursorAdapter._get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 404
            mock_error = httpx.HTTPStatusError("Not found", request=Mock(), response=mock_response)
            mock_client.post = AsyncMock(side_effect=mock_error)
            mock_get_client.return_value = mock_client
            
            from unified_ai.adapters.base import Message
            messages = [Message(role="user", content="Hello")]
            
            with pytest.raises(ValueError, match="Cursor API endpoint not found"):
                await adapter.chat(messages)
