"""Session storage using Redis"""

import json
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from .redis import get_redis_client


class SessionStore:
    """Session storage using Redis"""
    
    def __init__(self, redis_client=None):
        """
        Initialize session store
        
        Args:
            redis_client: Optional Redis cache instance
        """
        self.redis = redis_client or get_redis_client()
        self.session_prefix = "session:"
        self.refresh_token_prefix = "refresh_token:"
        self.session_timeout = 30 * 60  # 30 minutes
    
    async def create_session(
        self,
        user_id: str,
        session_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new session"""
        if not self.redis:
            # Fallback: generate session ID but don't store
            return secrets.token_urlsafe(32)
        
        await self.redis.connect()
        
        session_id = secrets.token_urlsafe(32)
        session_key = f"{self.session_prefix}{session_id}"
        
        data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            **(session_data or {}),
        }
        
        await self.redis.set(session_key, data, ttl_seconds=self.session_timeout)
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        if not self.redis:
            return None
        
        await self.redis.connect()
        
        session_key = f"{self.session_prefix}{session_id}"
        data = await self.redis.get(session_key)
        
        if data:
            # Update last activity
            data["last_activity"] = datetime.utcnow().isoformat()
            await self.redis.set(session_key, data, ttl_seconds=self.session_timeout)
        
        return data
    
    async def delete_session(self, session_id: str) -> None:
        """Delete a session"""
        if not self.redis:
            return
        
        await self.redis.connect()
        
        session_key = f"{self.session_prefix}{session_id}"
        await self.redis.delete(session_key)
    
    async def store_refresh_token(
        self,
        token_hash: str,
        user_id: str,
        expires_at: datetime,
    ) -> None:
        """Store refresh token in Redis"""
        if not self.redis:
            return
        
        await self.redis.connect()
        
        token_key = f"{self.refresh_token_prefix}{token_hash}"
        data = {
            "user_id": user_id,
            "expires_at": expires_at.isoformat(),
        }
        
        ttl = int((expires_at - datetime.utcnow()).total_seconds())
        if ttl > 0:
            await self.redis.set(token_key, data, ttl_seconds=ttl)
    
    async def get_refresh_token(self, token_hash: str) -> Optional[Dict[str, Any]]:
        """Get refresh token data"""
        if not self.redis:
            return None
        
        await self.redis.connect()
        
        token_key = f"{self.refresh_token_prefix}{token_hash}"
        return await self.redis.get(token_key)
    
    async def revoke_refresh_token(self, token_hash: str) -> None:
        """Revoke a refresh token"""
        if not self.redis:
            return
        
        await self.redis.connect()
        
        token_key = f"{self.refresh_token_prefix}{token_hash}"
        await self.redis.delete(token_key)
    
    async def is_token_blacklisted(self, token_hash: str) -> bool:
        """Check if token is blacklisted"""
        if not self.redis:
            return False
        
        await self.redis.connect()
        
        blacklist_key = f"blacklist:{token_hash}"
        return await self.redis.exists(blacklist_key)
    
    async def blacklist_token(self, token_hash: str, ttl_seconds: int) -> None:
        """Add token to blacklist"""
        if not self.redis:
            return
        
        await self.redis.connect()
        
        blacklist_key = f"blacklist:{token_hash}"
        await self.redis.set(blacklist_key, "1", ttl_seconds=ttl_seconds)
