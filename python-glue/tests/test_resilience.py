"""Tests for resilience patterns"""

import pytest
import asyncio
from unified_ai.resilience import (
    RetryPolicy,
    ExponentialBackoffRetry,
    CircuitBreaker,
    CircuitState,
    RateLimiter,
)


class TestRetryPolicy:
    """Test retry policies"""
    
    def test_exponential_backoff_retry(self):
        """Test exponential backoff retry policy"""
        policy = ExponentialBackoffRetry(
            max_attempts=3,
            initial_delay=1.0,
            max_delay=10.0,
        )
        
        assert policy.max_attempts == 3
        assert policy.should_retry(1, ConnectionError()) is True
        assert policy.should_retry(3, ConnectionError()) is False
        
        delay = policy.delay(1)
        assert 0.75 <= delay <= 2.0  # With jitter
    
    @pytest.mark.asyncio
    async def test_retry_decorator(self):
        """Test retry decorator"""
        from unified_ai.resilience.retry import retry
        
        attempt_count = 0
        
        @retry(policy=ExponentialBackoffRetry(max_attempts=3, initial_delay=0.01))
        async def failing_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = await failing_function()
        assert result == "success"
        assert attempt_count == 3


class TestCircuitBreaker:
    """Test circuit breaker"""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_closed(self):
        """Test circuit breaker in closed state"""
        cb = CircuitBreaker("test", failure_threshold=3, timeout=1.0)
        
        assert cb.state == CircuitState.CLOSED
        
        # Successful calls should work
        async def success():
            return "ok"
        
        result = await cb.call(success)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens(self):
        """Test circuit breaker opens after failures"""
        cb = CircuitBreaker("test", failure_threshold=2, timeout=0.1)
        
        async def fail():
            raise RuntimeError("Failure")
        
        # First failure
        with pytest.raises(RuntimeError):
            await cb.call(fail)
        
        # Second failure should open circuit
        with pytest.raises(RuntimeError):
            await cb.call(fail)
        
        # Circuit should be open now
        assert cb.state == CircuitState.OPEN
        
        # Next call should fail immediately
        with pytest.raises(RuntimeError):
            await cb.call(fail)


class TestRateLimiter:
    """Test rate limiter"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter(self):
        """Test rate limiter"""
        limiter = RateLimiter("test", capacity=2, refill_rate=1.0)
        
        # Should allow first two tokens
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True
        
        # Third should fail
        assert limiter.try_acquire() is False
        
        # Wait and try again
        await asyncio.sleep(1.1)
        assert limiter.try_acquire() is True
    
    @pytest.mark.asyncio
    async def test_rate_limiter_acquire(self):
        """Test rate limiter acquire with waiting"""
        limiter = RateLimiter("test", capacity=1, refill_rate=2.0)
        
        # Acquire first token
        await limiter.acquire()
        
        # Second should wait
        import time
        start = time.time()
        await limiter.acquire()
        elapsed = time.time() - start
        
        # Should have waited approximately 0.5 seconds
        assert 0.4 <= elapsed <= 0.7
