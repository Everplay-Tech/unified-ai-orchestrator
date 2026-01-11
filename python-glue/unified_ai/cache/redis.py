"""Redis cache implementation"""

import json
import os
from typing import Optional, Any, Dict
import redis.asyncio as redis
from datetime import timedelta


class RedisCache:
    """Redis-based cache"""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis cache
        
        Args:
            redis_url: Redis connection URL (defaults to REDIS_URL env var)
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        """Connect to Redis"""
        if self.client is None:
            self.client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            await self.client.ping()
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            self.client = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if self.client is None:
            await self.connect()
        
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Set value in cache"""
        if self.client is None:
            await self.connect()
        
        try:
            serialized = json.dumps(value)
            if ttl_seconds:
                await self.client.setex(key, ttl_seconds, serialized)
            else:
                await self.client.set(key, serialized)
        except Exception:
            pass  # Fail silently - cache is not critical
    
    async def delete(self, key: str) -> None:
        """Delete key from cache"""
        if self.client is None:
            await self.connect()
        
        try:
            await self.client.delete(key)
        except Exception:
            pass
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if self.client is None:
            await self.connect()
        
        try:
            return await self.client.exists(key) > 0
        except Exception:
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter"""
        if self.client is None:
            await self.connect()
        
        try:
            return await self.client.incrby(key, amount)
        except Exception:
            return 0
    
    async def expire(self, key: str, seconds: int) -> None:
        """Set expiration on a key"""
        if self.client is None:
            await self.connect()
        
        try:
            await self.client.expire(key, seconds)
        except Exception:
            pass


# Global Redis cache instance
_redis_cache: Optional[RedisCache] = None


def get_redis_client() -> Optional[RedisCache]:
    """Get global Redis cache instance"""
    global _redis_cache
    
    if _redis_cache is None:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            _redis_cache = RedisCache(redis_url)
        else:
            # Redis not configured
            return None
    
    return _redis_cache
