"""End-to-end tests for complete workflows"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from unified_ai.api.server import create_app


@pytest.fixture
def client():
    """Create test client"""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_auth():
    """Mock authentication"""
    with patch('unified_ai.api.routes.require_auth') as mock:
        mock.return_value = {"user_id": "test-user", "role": "user"}
        yield mock


@pytest.fixture
def mock_adapters():
    """Mock adapters"""
    with patch('unified_ai.api.routes.get_adapters') as mock:
        mock_adapter = MagicMock()
        mock_adapter.name = "claude"
        mock_adapter.model = "claude-3-5-sonnet-20241022"
        mock_adapter.capabilities.supported_capabilities = []
        mock_adapter.capabilities.supports_streaming = True
        mock_adapter.capabilities.supports_code_context = True
        mock_adapter.capabilities.max_context_length = 200000
        
        async def mock_chat(messages, context=None):
            return MagicMock(
                content="Test response",
                tool="claude",
                metadata={"usage": {"input_tokens": 10, "output_tokens": 20}}
            )
        
        mock_adapter.chat = AsyncMock(side_effect=mock_chat)
        mock.return_value = {"claude": mock_adapter}
        yield mock


def test_complete_chat_workflow(client, mock_auth, mock_adapters):
    """Test complete chat workflow"""
    with patch('unified_ai.api.routes.get_context_manager') as mock_cm:
        mock_context = MagicMock()
        mock_context.conversation_id = "test-conv-1"
        mock_context.messages = []
        mock_context.codebase_context = None
        
        async def mock_get_or_create(conv_id=None, project_id=None):
            return mock_context
        
        async def mock_add_message(context, role, content):
            if not hasattr(mock_context.messages, 'append'):
                mock_context.messages = []
            mock_context.messages.append(MagicMock(role=role, content=content))
        
        async def mock_add_tool_call(context, tool, message, response):
            pass
        
        mock_cm_instance = MagicMock()
        mock_cm_instance.get_or_create_context = AsyncMock(side_effect=mock_get_or_create)
        mock_cm_instance.add_message = AsyncMock(side_effect=mock_add_message)
        mock_cm_instance.add_tool_call = AsyncMock(side_effect=mock_add_tool_call)
        mock_cm.return_value = mock_cm_instance
        
        # Step 1: Start conversation
        response1 = client.post(
            "/api/v1/chat",
            json={"message": "Hello"},
            headers={"Authorization": "Bearer test-token"}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        conversation_id = data1["conversation_id"]
        
        # Step 2: Continue conversation
        response2 = client.post(
            "/api/v1/chat",
            json={
                "message": "Tell me more",
                "conversation_id": conversation_id
            },
            headers={"Authorization": "Bearer test-token"}
        )
        assert response2.status_code == 200
        
        # Step 3: Get conversation history
        response3 = client.get(
            f"/api/v1/conversations/{conversation_id}",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response3.status_code == 200
        data3 = response3.json()
        assert len(data3["messages"]) >= 2  # Should have at least 2 messages


def test_multi_tool_workflow(client, mock_auth):
    """Test workflow using multiple tools"""
    with patch('unified_ai.api.routes.get_adapters') as mock_adapters:
        # Mock multiple adapters
        claude = MagicMock()
        claude.name = "claude"
        claude.chat = AsyncMock(return_value=MagicMock(
            content="Claude response",
            tool="claude",
            metadata={}
        ))
        
        gpt = MagicMock()
        gpt.name = "gpt"
        gpt.chat = AsyncMock(return_value=MagicMock(
            content="GPT response",
            tool="gpt",
            metadata={}
        ))
        
        mock_adapters.return_value = {"claude": claude, "gpt": gpt}
        
        with patch('unified_ai.api.routes.get_context_manager') as mock_cm:
            mock_context = MagicMock()
            mock_context.conversation_id = "test-conv"
            mock_context.messages = []
            
            async def mock_get_or_create(conv_id=None, project_id=None):
                return mock_context
            
            mock_cm_instance = MagicMock()
            mock_cm_instance.get_or_create_context = AsyncMock(side_effect=mock_get_or_create)
            mock_cm_instance.add_message = AsyncMock()
            mock_cm_instance.add_tool_call = AsyncMock()
            mock_cm.return_value = mock_cm_instance
            
            # Use Claude
            response1 = client.post(
                "/api/v1/chat",
                json={"message": "Hello", "tool": "claude"},
                headers={"Authorization": "Bearer test-token"}
            )
            assert response1.status_code == 200
            assert response1.json()["tool"] == "claude"
            
            # Use GPT
            response2 = client.post(
                "/api/v1/chat",
                json={"message": "Hello", "tool": "gpt"},
                headers={"Authorization": "Bearer test-token"}
            )
            assert response2.status_code == 200
            assert response2.json()["tool"] == "gpt"


def test_error_handling_workflow(client, mock_auth):
    """Test error handling in workflow"""
    with patch('unified_ai.api.routes.get_adapters') as mock:
        mock_adapter = MagicMock()
        mock_adapter.name = "claude"
        
        async def failing_chat(messages, context=None):
            raise Exception("API error")
        
        mock_adapter.chat = AsyncMock(side_effect=failing_chat)
        mock.return_value = {"claude": mock_adapter}
        
        with patch('unified_ai.api.routes.get_context_manager') as mock_cm:
            mock_context = MagicMock()
            mock_context.conversation_id = "test-conv"
            mock_context.messages = []
            
            async def mock_get_or_create(conv_id=None, project_id=None):
                return mock_context
            
            mock_cm_instance = MagicMock()
            mock_cm_instance.get_or_create_context = AsyncMock(side_effect=mock_get_or_create)
            mock_cm.return_value = mock_cm_instance
            
            response = client.post(
                "/api/v1/chat",
                json={"message": "Hello"},
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should handle error gracefully
            assert response.status_code == 500
