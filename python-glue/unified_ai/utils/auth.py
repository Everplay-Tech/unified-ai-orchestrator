"""API key management with OS keychain"""

import os
import keyring
from typing import Optional


def get_api_key(service: str, username: str = "default") -> Optional[str]:
    """
    Get API key from keyring or environment variable
    
    Args:
        service: Service name (e.g., "anthropic", "openai")
        username: Username/key identifier
        
    Returns:
        API key or None if not found
    """
    # First try environment variable
    env_var = f"{service.upper()}_API_KEY"
    api_key = os.getenv(env_var)
    if api_key:
        return api_key
    
    # Then try keyring
    try:
        api_key = keyring.get_password(f"uai-{service}", username)
        return api_key
    except Exception:
        return None


def set_api_key(service: str, api_key: str, username: str = "default") -> None:
    """
    Store API key in keyring
    
    Args:
        service: Service name
        api_key: API key to store
        username: Username/key identifier
    """
    try:
        keyring.set_password(f"uai-{service}", username, api_key)
    except Exception as e:
        raise RuntimeError(f"Failed to store API key: {e}")


def delete_api_key(service: str, username: str = "default") -> None:
    """
    Delete API key from keyring
    
    Args:
        service: Service name
        username: Username/key identifier
    """
    try:
        keyring.delete_password(f"uai-{service}", username)
    except Exception:
        pass  # Ignore if key doesn't exist


def get_secret(secret_name: str) -> Optional[str]:
    """
    Get secret from keyring or environment variable
    
    Args:
        secret_name: Name of the secret (e.g., "cursor_api_key")
    
    Returns:
        Secret value or None if not found
    """
    # Try environment variable first
    env_var = secret_name.upper().replace("-", "_")
    value = os.getenv(env_var)
    if value:
        return value
    
    # Try keyring with uai-secrets namespace
    try:
        return keyring.get_password("uai-secrets", secret_name)
    except Exception:
        pass
    
    # Fallback: try as API key
    return get_api_key(secret_name.replace("_api_key", ""))


def set_secret(secret_name: str, secret_value: str) -> None:
    """
    Store secret in keyring
    
    Args:
        secret_name: Name of the secret (e.g., "mobile_api_key")
        secret_value: Secret value to store
    """
    try:
        keyring.set_password("uai-secrets", secret_name, secret_value)
    except Exception as e:
        raise RuntimeError(f"Failed to store secret: {e}")
