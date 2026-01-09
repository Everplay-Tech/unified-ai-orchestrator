"""Retry decorators and policies"""

import asyncio
import functools
from typing import Callable, TypeVar, Awaitable, Optional
from dataclasses import dataclass
import random
import time

T = TypeVar("T")


@dataclass
class RetryPolicy:
    """Retry policy configuration"""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    def delay(self, attempt: int) -> float:
        """Calculate delay for attempt number"""
        base_delay = self.initial_delay * (self.exponential_base ** attempt)
        delay = min(base_delay, self.max_delay)
        
        if self.jitter:
            # Add ±25% jitter
            jitter_factor = 0.75 + (random.random() * 0.25)
            delay *= jitter_factor
        
        return delay
    
    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Determine if we should retry after this error"""
        if attempt >= self.max_attempts:
            return False
        
        # Retry on network errors, timeouts, rate limits
        error_type = type(error).__name__
        retryable_errors = [
            "ConnectionError",
            "TimeoutError",
            "RateLimitError",
            "HTTPError",
        ]
        
        return any(err in error_type for err in retryable_errors)


class ExponentialBackoffRetry(RetryPolicy):
    """Exponential backoff retry policy"""
    pass


def retry(
    policy: Optional[RetryPolicy] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
):
    """Decorator for retrying async functions"""
    if policy is None:
        policy = ExponentialBackoffRetry()
    
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            attempt = 0
            last_error = None
            
            while attempt < policy.max_attempts:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    attempt += 1
                    
                    if not policy.should_retry(attempt, e):
                        raise
                    
                    if on_retry:
                        on_retry(attempt, e)
                    
                    delay = policy.delay(attempt)
                    await asyncio.sleep(delay)
            
            raise last_error
        
        return wrapper
    return decorator
