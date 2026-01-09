"""Circuit breaker pattern implementation"""

import asyncio
import time
from enum import Enum
from typing import TypeVar, Callable, Awaitable, Optional
from dataclasses import dataclass, field
from threading import Lock

T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker for preventing cascading failures"""
    
    name: str
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: float = 60.0
    
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failures: int = field(default=0, init=False)
    _successes: int = field(default=0, init=False)
    _last_failure_time: Optional[float] = field(default=None, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit breaker state"""
        with self._lock:
            return self._state
    
    def _check_state(self) -> None:
        """Check and update circuit breaker state"""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.timeout:
                        self._state = CircuitState.HALF_OPEN
                        self._successes = 0
    
    def _on_success(self) -> None:
        """Handle successful call"""
        with self._lock:
            self._failures = 0
            if self._state == CircuitState.HALF_OPEN:
                self._successes += 1
                if self._successes >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._successes = 0
    
    def _on_failure(self) -> None:
        """Handle failed call"""
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
            elif self._state == CircuitState.CLOSED:
                if self._failures >= self.failure_threshold:
                    self._state = CircuitState.OPEN
    
    async def call(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection"""
        self._check_state()
        
        if self._state == CircuitState.OPEN:
            raise RuntimeError(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Retry after {self.timeout}s"
            )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
