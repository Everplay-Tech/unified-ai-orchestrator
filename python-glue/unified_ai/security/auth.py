"""Authentication: JWT, API keys, sessions"""

import os
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps

from fastapi import HTTPException, Security, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import load_config
from ..storage import create_storage_backend, DatabaseType, StorageBackend

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Security scheme
security = HTTPBearer(auto_error=False)


def get_secret_key() -> str:
    """Get JWT secret key from config or environment"""
    # Check environment variable first
    secret = os.getenv("JWT_SECRET_KEY")
    
    # Validate that secret is not empty, not just whitespace, and not the placeholder
    if secret and secret.strip() and secret.strip() != "change-me-in-production":
        return secret.strip()
    
    # If env var is not set, is empty, or is the placeholder, use default and validate
    secret = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    if not secret or not secret.strip() or secret.strip() == "change-me-in-production":
        raise ValueError("JWT_SECRET_KEY must be set in production")
    return secret.strip()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA256"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def get_storage_backend() -> StorageBackend:
    """Get storage backend instance"""
    config = load_config()
    db_type = DatabaseType(config.storage.db_type.lower())
    
    if db_type == DatabaseType.POSTGRESQL:
        if not config.storage.connection_string:
            raise ValueError("PostgreSQL requires connection_string in config")
        return create_storage_backend(db_type, connection_string=config.storage.connection_string)
    else:
        from pathlib import Path
        return create_storage_backend(db_type, db_path=Path(config.storage.db_path))


async def get_user_by_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Get user by API key hash from database"""
    storage = get_storage_backend()
    await storage.initialize()
    
    api_key_hash = hash_api_key(api_key)
    user = await storage.get_user_by_api_key_hash(api_key_hash)
    
    await storage.close()
    return user


async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username from database"""
    storage = get_storage_backend()
    await storage.initialize()
    
    user = await storage.get_user_by_username(username)
    
    await storage.close()
    return user


async def create_user(
    username: str,
    email: Optional[str],
    password: Optional[str],
    role: str = "user",
) -> Dict[str, Any]:
    """Create a new user"""
    storage = get_storage_backend()
    await storage.initialize()
    
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password) if password else None
    
    await storage.create_user(
        user_id=user_id,
        username=username,
        email=email,
        password_hash=password_hash,
        role=role,
    )
    
    await storage.close()
    
    return {
        "user_id": user_id,
        "username": username,
        "email": email,
        "role": role,
    }


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        
        # Check token type
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


async def authenticate_jwt(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Dict[str, Any]:
    """Authenticate using JWT token"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    token = credentials.credentials
    payload = verify_token(token, "access")
    return payload


async def authenticate_api_key_from_request(request: Request) -> Optional[str]:
    """Extract API key from request"""
    # Try X-API-Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key
    
    # Try Authorization: Bearer header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # Check if it's an API key (not a JWT)
        if len(token) > 50:  # API keys are typically longer than JWTs
            return token
    
    # Try query parameter
    api_key = request.query_params.get("api_key")
    if api_key:
        return api_key
    
    return None


async def authenticate_api_key(
    request: Request,
) -> Dict[str, Any]:
    """Authenticate using API key"""
    api_key = await authenticate_api_key_from_request(request)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    # Verify API key against database
    user = await get_user_by_api_key(api_key)
    
    if user:
        return user
    
    # Fallback to environment variable for backward compatibility
    valid_key = os.getenv("VALID_API_KEY")
    if valid_key and api_key == valid_key:
        return {"user_id": "api_user", "role": "user"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key"
    )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security, auto_error=False)
) -> Optional[Dict[str, Any]]:
    """Get current authenticated user"""
    # Try JWT first
    if credentials:
        try:
            return await authenticate_jwt(credentials)
        except HTTPException:
            pass
    
    # Try API key authentication
    try:
        return await authenticate_api_key(request)
    except HTTPException:
        pass
    
    return None


async def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security, auto_error=False)
) -> Dict[str, Any]:
    """Dependency to require authentication"""
    user = await get_current_user(request, credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user
