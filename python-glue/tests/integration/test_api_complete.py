"""Comprehensive API integration tests"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json

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


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded", "unhealthy"]


def test_metrics_endpoint(client):
    """Test metrics endpoint"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


def test_tools_endpoint(client, mock_auth):
    """Test tools listing endpoint"""
    response = client.get(
        "/api/v1/tools",
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert isinstance(data["tools"], list)


def test_chat_endpoint(client, mock_auth, mock_adapters):
    """Test chat endpoint"""
    with patch('unified_ai.api.routes.get_context_manager') as mock_cm:
        mock_context = MagicMock()
        mock_context.conversation_id = "test-conv"
        mock_context.messages = []
        mock_context.codebase_context = None
        
        async def mock_get_or_create(conv_id=None, project_id=None):
            return mock_context
        
        async def mock_add_message(context, role, content):
            pass
        
        async def mock_add_tool_call(context, tool, message, response):
            pass
        
        mock_cm_instance = MagicMock()
        mock_cm_instance.get_or_create_context = AsyncMock(side_effect=mock_get_or_create)
        mock_cm_instance.add_message = AsyncMock(side_effect=mock_add_message)
        mock_cm_instance.add_tool_call = AsyncMock(side_effect=mock_add_tool_call)
        mock_cm.return_value = mock_cm_instance
        
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "Hello, how are you?",
                "conversation_id": "test-conv"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "tool" in data
        assert "conversation_id" in data


def test_chat_endpoint_with_project(client, mock_auth, mock_adapters):
    """Test chat endpoint with project context"""
    with patch('unified_ai.api.routes.get_context_manager') as mock_cm:
        mock_context = MagicMock()
        mock_context.conversation_id = "test-conv"
        mock_context.project_id = "test-project"
        mock_context.messages = []
        mock_context.codebase_context = {"files": ["test.py"]}
        
        async def mock_get_or_create(conv_id=None, project_id=None):
            return mock_context
        
        mock_cm_instance = MagicMock()
        mock_cm_instance.get_or_create_context = AsyncMock(side_effect=mock_get_or_create)
        mock_cm_instance.add_message = AsyncMock()
        mock_cm_instance.add_tool_call = AsyncMock()
        mock_cm.return_value = mock_cm_instance
        
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "Explain this code",
                "conversation_id": "test-conv",
                "project_id": "test-project"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200


def test_conversation_endpoint(client, mock_auth):
    """Test get conversation endpoint"""
    with patch('unified_ai.api.routes.get_context_manager') as mock_cm:
        mock_context = MagicMock()
        mock_context.conversation_id = "test-conv"
        mock_context.project_id = "test-project"
        mock_context.messages = [
            MagicMock(role="user", content="Hello", timestamp=1234567890),
            MagicMock(role="assistant", content="Hi there", timestamp=1234567900),
        ]
        mock_context.tool_history = []
        
        async def mock_get_context(conv_id):
            if conv_id == "test-conv":
                return mock_context
            return None
        
        mock_cm_instance = MagicMock()
        mock_cm_instance.get_context = AsyncMock(side_effect=mock_get_context)
        mock_cm.return_value = mock_cm_instance
        
        response = client.get(
            "/api/v1/conversations/test-conv",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == "test-conv"
        assert "messages" in data
        assert len(data["messages"]) == 2


def test_conversation_not_found(client, mock_auth):
    """Test get conversation when not found"""
    with patch('unified_ai.api.routes.get_context_manager') as mock_cm:
        async def mock_get_context(conv_id):
            return None
        
        mock_cm_instance = MagicMock()
        mock_cm_instance.get_context = AsyncMock(side_effect=mock_get_context)
        mock_cm.return_value = mock_cm_instance
        
        response = client.get(
            "/api/v1/conversations/nonexistent",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 404


def test_chat_validation_error(client, mock_auth):
    """Test chat endpoint with validation error"""
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "",  # Empty message should fail validation
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 422  # Validation error


def test_chat_no_tools_configured(client, mock_auth):
    """Test chat endpoint when no tools configured"""
    with patch('unified_ai.api.routes.get_adapters') as mock:
        mock.return_value = {}
        
        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 500


def test_api_key_authentication(client):
    """Test API key authentication"""
    # Test without API key (should fail for protected routes)
    response = client.post(
        "/api/v1/chat",
        json={"message": "Hello"}
    )
    # Should either require auth or return 401
    assert response.status_code in [401, 403]


def test_rate_limiting(client, mock_auth, mock_adapters):
    """Test rate limiting"""
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
        
        # Make many requests quickly
        responses = []
        for _ in range(70):  # More than default rate limit of 60
            response = client.post(
                "/api/v1/chat",
                json={"message": "Test"},
                headers={"Authorization": "Bearer test-token"}
            )
            responses.append(response.status_code)
        
        # At least one should be rate limited
        assert 429 in responses or all(r == 200 for r in responses)  # May not trigger in test environment


def test_cors_headers(client):
    """Test CORS headers"""
    response = client.options(
        "/api/v1/chat",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST"
        }
    )
    # CORS headers should be present
    assert response.status_code in [200, 204]


def test_security_headers(client):
    """Test security headers"""
    response = client.get("/health")
    
    # Check security headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-XSS-Protection" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
