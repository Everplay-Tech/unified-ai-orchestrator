"""Rate limiting implementation"""

import asyncio
import time
from typing import Optional
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class TokenBucket:
    """Token bucket for rate limiting"""
    
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    _lock: Lock = field(default_factory=Lock, init=False)
    
    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_refill = time.time()
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time (must be called with lock held)"""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        
        if tokens_to_add > 0:
            self.tokens = min(self.tokens + tokens_to_add, self.capacity)
            self.last_refill = now
    
    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens"""
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def wait_time(self) -> float:
        """Calculate wait time until tokens available"""
        with self._lock:
            self._refill()
            if self.tokens >= 1:
                return 0.0
            tokens_needed = 1.0 - self.tokens
            return tokens_needed / self.refill_rate


class RateLimiter:
    """Rate limiter using token bucket"""
    
    def __init__(self, capacity: int, refill_rate: float = None):
        """
        Initialize rate limiter
        
        Args:
            capacity: Maximum number of tokens (requests)
            refill_rate: Tokens per second (defaults to capacity/60 for per-minute rate)
        """
        if refill_rate is None:
            # Default: refill at rate that allows capacity requests per minute
            refill_rate = capacity / 60.0
        self.bucket = TokenBucket(capacity, refill_rate)
    
    def allow(self) -> bool:
        """Check if request is allowed (alias for try_acquire)"""
        return self.try_acquire(1)
    
    def remaining(self) -> int:
        """Get remaining tokens"""
        with self.bucket._lock:
            self.bucket._refill()
            return max(0, int(self.bucket.tokens))
    
    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, waiting if necessary"""
        while not self.bucket.try_acquire(tokens):
            wait_time = self.bucket.wait_time()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
    
    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without waiting"""
        return self.bucket.try_acquire(tokens)
