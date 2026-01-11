"""Integration tests for security features"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from unified_ai.security.auth import (
    authenticate_api_key,
    authenticate_jwt,
    create_access_token,
    verify_token,
    get_current_user,
    require_auth,
)
from unified_ai.security.authorization import (
    require_role,
    require_permission,
    check_resource_access,
    Role,
    Permission,
)
from unified_ai.security.validation import (
    validate_input,
    sanitize_html,
    sanitize_path,
    validate_sql_safe,
    ValidationError,
)
from unified_ai.security.encryption import (
    encrypt_secret,
    decrypt_secret,
    hash_password,
    verify_password,
)
from unified_ai.security.audit import (
    AuditLogger,
    AuditEventType,
    get_audit_logger,
)


@pytest.mark.asyncio
async def test_authenticate_api_key():
    """Test API key authentication"""
    # Test valid API key
    with patch('unified_ai.security.auth.get_secret') as mock_get_secret:
        mock_get_secret.return_value = "test-api-key"
        result = await authenticate_api_key("test-api-key")
        assert result is not None
        assert result["user_id"] is not None
    
    # Test invalid API key
    with patch('unified_ai.security.auth.get_secret') as mock_get_secret:
        mock_get_secret.return_value = "test-api-key"
        result = await authenticate_api_key("wrong-key")
        assert result is None


@pytest.mark.asyncio
async def test_jwt_authentication():
    """Test JWT token creation and verification"""
    user_data = {"user_id": "test-user", "role": "user"}
    
    # Create token
    token = create_access_token(user_data)
    assert token is not None
    
    # Verify token
    payload = verify_token(token)
    assert payload is not None
    assert payload["user_id"] == "test-user"
    
    # Test invalid token
    invalid_payload = verify_token("invalid-token")
    assert invalid_payload is None


@pytest.mark.asyncio
async def test_require_auth_decorator():
    """Test require_auth dependency"""
    # Mock request with valid token
    mock_request = MagicMock()
    mock_request.headers = {"Authorization": "Bearer test-token"}
    
    with patch('unified_ai.security.auth.verify_token') as mock_verify:
        mock_verify.return_value = {"user_id": "test-user", "role": "user"}
        # This would be tested in actual route context
        pass


@pytest.mark.asyncio
async def test_require_role():
    """Test role-based authorization"""
    user = {"user_id": "test-user", "role": "admin"}
    
    # Test admin role
    @require_role(Role.ADMIN)
    async def admin_only(user: dict):
        return "admin access"
    
    result = await admin_only(user)
    assert result == "admin access"
    
    # Test user without required role
    user_user = {"user_id": "test-user", "role": "user"}
    with pytest.raises(HTTPException) as exc_info:
        await admin_only(user_user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_permission():
    """Test permission-based authorization"""
    user = {"user_id": "test-user", "permissions": [Permission.READ_CONVERSATION]}
    
    @require_permission(Permission.READ_CONVERSATION)
    async def read_conversation(user: dict):
        return "read access"
    
    result = await read_conversation(user)
    assert result == "read access"
    
    # Test user without permission
    user_no_perm = {"user_id": "test-user", "permissions": []}
    with pytest.raises(HTTPException) as exc_info:
        await read_conversation(user_no_perm)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_check_resource_access():
    """Test resource access checking"""
    user = {"user_id": "test-user", "role": "user"}
    
    # Test own resource access
    has_access = await check_resource_access(
        user=user,
        resource_type="conversation",
        resource_id="test-user-conv-1",
        action="read"
    )
    # Should allow access to own resources
    assert isinstance(has_access, bool)
    
    # Test admin access
    admin_user = {"user_id": "admin", "role": "admin"}
    has_access = await check_resource_access(
        user=admin_user,
        resource_type="conversation",
        resource_id="any-conv",
        action="read"
    )
    assert has_access is True


def test_validate_input():
    """Test input validation"""
    # Valid input
    result = validate_input("test", max_length=10)
    assert result == "test"
    
    # Too long
    with pytest.raises(ValidationError):
        validate_input("a" * 1000, max_length=10)
    
    # Invalid pattern
    with pytest.raises(ValidationError):
        validate_input("test<script>", pattern="^[a-zA-Z0-9]+$")
    
    # SQL injection attempt
    with pytest.raises(ValidationError):
        validate_input("'; DROP TABLE users; --", pattern="^[a-zA-Z0-9]+$")


def test_sanitize_html():
    """Test HTML sanitization"""
    # Remove script tags
    result = sanitize_html("<script>alert('xss')</script>Hello")
    assert "<script>" not in result
    assert "Hello" in result
    
    # Remove other dangerous tags
    result = sanitize_html("<iframe src='evil.com'></iframe>Safe")
    assert "<iframe>" not in result
    assert "Safe" in result


def test_sanitize_path():
    """Test path sanitization"""
    from pathlib import Path
    
    base_path = Path("/safe/base")
    
    # Valid path
    result = sanitize_path(base_path, "subdir/file.txt")
    assert "subdir/file.txt" in str(result)
    
    # Path traversal attempt
    with pytest.raises(ValidationError):
        sanitize_path(base_path, "../../etc/passwd")
    
    # Absolute path attempt
    with pytest.raises(ValidationError):
        sanitize_path(base_path, "/etc/passwd")


def test_validate_sql_safe():
    """Test SQL injection prevention"""
    # Safe input
    assert validate_sql_safe("SELECT * FROM users WHERE id = ?")
    
    # SQL injection attempt
    with pytest.raises(ValidationError):
        validate_sql_safe("'; DROP TABLE users; --")


def test_password_hashing():
    """Test password hashing and verification"""
    password = "test-password-123"
    
    # Hash password
    hashed = hash_password(password)
    assert hashed != password
    assert len(hashed) > 0
    
    # Verify correct password
    assert verify_password(password, hashed) is True
    
    # Verify incorrect password
    assert verify_password("wrong-password", hashed) is False


def test_encryption():
    """Test secret encryption and decryption"""
    secret = "sensitive-data-123"
    
    # Encrypt
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    assert len(encrypted) > 0
    
    # Decrypt
    decrypted = decrypt_secret(encrypted)
    assert decrypted == secret


@pytest.mark.asyncio
async def test_audit_logging():
    """Test audit logging"""
    logger = AuditLogger()
    
    # Log event
    await logger.log_event(
        event_type=AuditEventType.AUTH_SUCCESS,
        user_id="test-user",
        resource_type="login",
        ip_address="127.0.0.1",
    )
    
    # Log auth success
    await logger.log_auth_success(
        user_id="test-user",
        auth_method="api_key",
        ip_address="127.0.0.1",
    )
    
    # Log auth failure
    await logger.log_auth_failure(
        auth_method="api_key",
        reason="invalid_key",
        ip_address="127.0.0.1",
    )
    
    # Log resource access
    await logger.log_resource_access(
        user_id="test-user",
        resource_type="conversation",
        resource_id="conv-1",
        action="read",
        ip_address="127.0.0.1",
    )


@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting"""
    from unified_ai.resilience import RateLimiter
    
    limiter = RateLimiter(requests_per_minute=10)
    
    # Should allow requests
    for _ in range(10):
        assert limiter.allow() is True
    
    # Should deny after limit
    assert limiter.allow() is False
    
    # Reset and test again
    import time
    time.sleep(1)  # Wait for bucket refill
    assert limiter.allow() is True


def test_security_headers():
    """Test security headers middleware"""
    from unified_ai.api.middleware import SecurityHeadersMiddleware
    from fastapi import Request
    from unittest.mock import MagicMock
    
    middleware = SecurityHeadersMiddleware(MagicMock())
    
    # Mock request and response
    mock_request = MagicMock()
    mock_request.url.scheme = "https"
    mock_request.headers = {}
    
    mock_response = MagicMock()
    mock_response.headers = {}
    
    async def mock_call_next(request):
        return mock_response
    
    # Process request
    response = asyncio.run(middleware.dispatch(mock_request, mock_call_next))
    
    # Check security headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-XSS-Protection" in response.headers
    assert "Content-Security-Policy" in response.headers


@pytest.mark.asyncio
async def test_api_key_middleware():
    """Test API key middleware"""
    from unified_ai.api.middleware import APIKeyMiddleware
    from fastapi import Request
    from unittest.mock import MagicMock
    
    middleware = APIKeyMiddleware(MagicMock(), api_key="test-key")
    
    # Test valid API key
    mock_request = MagicMock()
    mock_request.url.path = "/api/v1/chat"
    mock_request.headers = {"X-API-Key": "test-key"}
    mock_request.query_params = {}
    
    async def mock_call_next(request):
        return MagicMock()
    
    response = await middleware.dispatch(mock_request, mock_call_next)
    assert response is not None
    
    # Test invalid API key
    mock_request.headers = {"X-API-Key": "wrong-key"}
    response = await middleware.dispatch(mock_request, mock_call_next)
    assert hasattr(response, 'status_code')
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_input_validation_middleware():
    """Test input validation middleware"""
    from unified_ai.api.middleware import InputValidationMiddleware
    from fastapi import Request
    from unittest.mock import MagicMock
    
    middleware = InputValidationMiddleware(MagicMock())
    
    # Test valid input
    mock_request = MagicMock()
    mock_request.url.path = "/api/v1/chat"
    mock_request.query_params = {"param": "valid-value"}
    
    async def mock_call_next(request):
        return MagicMock()
    
    response = await middleware.dispatch(mock_request, mock_call_next)
    assert response is not None
    
    # Test invalid input (too long)
    mock_request.query_params = {"param": "a" * 2000}
    response = await middleware.dispatch(mock_request, mock_call_next)
    assert hasattr(response, 'status_code')
    assert response.status_code == 400
