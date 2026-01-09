"""Authentication: JWT, API keys, sessions"""

import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps

from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import load_config

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Security scheme
security = HTTPBearer()


def get_secret_key() -> str:
    """Get JWT secret key from config or environment"""
    # Check environment variable first
    secret = os.getenv("JWT_SECRET_KEY")
    
    # Validate that secret is not empty or just whitespace
    if secret and secret.strip():
        return secret.strip()
    
    # If env var is not set or is empty, use default and validate
    secret = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    if not secret or not secret.strip() or secret == "change-me-in-production":
        raise ValueError("JWT_SECRET_KEY must be set in production")
    return secret.strip()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


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
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """Authenticate using JWT token"""
    token = credentials.credentials
    payload = verify_token(token, "access")
    return payload


async def authenticate_api_key(
    api_key: Optional[str] = None,
    header_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Authenticate using API key"""
    # Try to get API key from various sources
    key = api_key or header_key or os.getenv("API_KEY")
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    # Verify API key against database
    # TODO: Implement API key lookup in database when migrations are ready
    # For now, check against environment variable
    valid_key = os.getenv("VALID_API_KEY")
    if valid_key and key != valid_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return {"user_id": "api_user", "role": "user"}


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security, auto_error=False)
) -> Optional[Dict[str, Any]]:
    """Get current authenticated user"""
    if credentials:
        try:
            return await authenticate_jwt(credentials)
        except HTTPException:
            pass
    
    # Try API key authentication
    try:
        return await authenticate_api_key()
    except HTTPException:
        pass
    
    return None


def require_auth(func):
    """Decorator to require authentication"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        user = await get_current_user()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        return await func(*args, **kwargs)
    return wrapper
