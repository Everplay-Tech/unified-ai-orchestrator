"""Prometheus metrics collection"""

from prometheus_client import Counter, Histogram, Gauge, REGISTRY
from typing import Optional, Dict
from dataclasses import dataclass
import time
from contextlib import contextmanager


@dataclass
class RequestMetrics:
    """Request metrics data"""
    request_id: str
    tool: str
    duration_ms: float
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    cost_usd: Optional[float] = None
    success: bool = True
    error: Optional[str] = None


class MetricsCollector:
    """Metrics collector using Prometheus"""
    
    def __init__(self):
        # API request metrics
        self.api_requests_total = Counter(
            "api_requests_total",
            "Total number of API requests",
            ["endpoint", "method", "status"],
        )
        
        self.api_request_duration_seconds = Histogram(
            "api_request_duration_seconds",
            "API request duration in seconds",
            ["endpoint", "method"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )
        
        # AI API call metrics
        self.ai_api_calls_total = Counter(
            "ai_api_calls_total",
            "Total number of AI API calls",
            ["tool", "model", "status"],
        )
        
        self.ai_api_latency_seconds = Histogram(
            "ai_api_latency_seconds",
            "AI API call latency in seconds",
            ["tool", "model"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
        )
        
        # Cost metrics
        self.cost_usd_total = Counter(
            "cost_usd_total",
            "Total cost in USD",
            ["tool", "model", "project_id"],
        )
        
        # Token metrics
        self.tokens_input_total = Counter(
            "tokens_input_total",
            "Total input tokens",
            ["tool", "model"],
        )
        
        self.tokens_output_total = Counter(
            "tokens_output_total",
            "Total output tokens",
            ["tool", "model"],
        )
        
        # Active resources
        self.active_conversations = Gauge(
            "active_conversations",
            "Number of active conversations",
        )
        
        self.active_users = Gauge(
            "active_users",
            "Number of active users",
        )
        
        # Database metrics
        self.database_connections_active = Gauge(
            "database_connections_active",
            "Number of active database connections",
        )
        
        self.database_query_duration_seconds = Histogram(
            "database_query_duration_seconds",
            "Database query duration in seconds",
            ["query_type"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
        )
        
        # Cache metrics
        self.cache_hits_total = Counter(
            "cache_hits_total",
            "Total cache hits",
            ["cache_type"],
        )
        
        self.cache_misses_total = Counter(
            "cache_misses_total",
            "Total cache misses",
            ["cache_type"],
        )
        
        # Legacy metrics (for backward compatibility)
        self.request_counter = Counter(
            "uai_requests_total",
            "Total number of requests",
            ["tool", "status"],
        )
        
        self.request_duration = Histogram(
            "uai_request_duration_seconds",
            "Request duration in seconds",
            ["tool"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
        )
        
        self.request_cost = Counter(
            "uai_request_cost_usd_total",
            "Total cost in USD",
            ["tool"],
        )
        
        self.tokens_input = Counter(
            "uai_tokens_input_total",
            "Total input tokens",
            ["tool"],
        )
        
        self.tokens_output = Counter(
            "uai_tokens_output_total",
            "Total output tokens",
            ["tool"],
        )
        
        self.active_requests = Gauge(
            "uai_active_requests",
            "Number of active requests",
            ["tool"],
        )
    
    def record_api_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        """Record API request metrics"""
        status_label = f"{status_code // 100}xx"
        self.api_requests_total.labels(
            endpoint=endpoint,
            method=method,
            status=status_label,
        ).inc()
        
        self.api_request_duration_seconds.labels(
            endpoint=endpoint,
            method=method,
        ).observe(duration_seconds)
    
    def record_ai_api_call(
        self,
        tool: str,
        model: str,
        success: bool,
        duration_seconds: float,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        cost_usd: Optional[float] = None,
        project_id: Optional[str] = None,
    ) -> None:
        """Record AI API call metrics"""
        status_label = "success" if success else "error"
        
        self.ai_api_calls_total.labels(
            tool=tool,
            model=model,
            status=status_label,
        ).inc()
        
        self.ai_api_latency_seconds.labels(
            tool=tool,
            model=model,
        ).observe(duration_seconds)
        
        if input_tokens:
            self.tokens_input_total.labels(
                tool=tool,
                model=model,
            ).inc(input_tokens)
        
        if output_tokens:
            self.tokens_output_total.labels(
                tool=tool,
                model=model,
            ).inc(output_tokens)
        
        if cost_usd:
            project_label = project_id or "unknown"
            self.cost_usd_total.labels(
                tool=tool,
                model=model,
                project_id=project_label,
            ).inc(cost_usd)
    
    def record_database_query(
        self,
        query_type: str,
        duration_seconds: float,
    ) -> None:
        """Record database query metrics"""
        self.database_query_duration_seconds.labels(
            query_type=query_type,
        ).observe(duration_seconds)
    
    def record_cache_hit(self, cache_type: str) -> None:
        """Record cache hit"""
        self.cache_hits_total.labels(cache_type=cache_type).inc()
    
    def record_cache_miss(self, cache_type: str) -> None:
        """Record cache miss"""
        self.cache_misses_total.labels(cache_type=cache_type).inc()
    
    def set_active_conversations(self, count: int) -> None:
        """Set active conversations count"""
        self.active_conversations.set(count)
    
    def set_active_users(self, count: int) -> None:
        """Set active users count"""
        self.active_users.set(count)
    
    def set_database_connections(self, count: int) -> None:
        """Set active database connections count"""
        self.database_connections_active.set(count)
    
    @contextmanager
    def track_api_request(self, endpoint: str, method: str):
        """Context manager to track API request"""
        start_time = time.time()
        status_code = 200
        try:
            yield
        except Exception as e:
            status_code = getattr(e, 'status_code', 500)
            raise
        finally:
            duration = time.time() - start_time
            self.record_api_request(endpoint, method, status_code, duration)
    
    @contextmanager
    def track_database_query(self, query_type: str):
        """Context manager to track database query"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_database_query(query_type, duration)
    
    def record_request(self, metrics: RequestMetrics) -> None:
        """Record request metrics (legacy method)"""
        status = "success" if metrics.success else "error"
        
        self.request_counter.labels(
            tool=metrics.tool,
            status=status,
        ).inc()
        
        self.request_duration.labels(
            tool=metrics.tool,
        ).observe(metrics.duration_ms / 1000.0)
        
        if metrics.cost_usd:
            self.request_cost.labels(
                tool=metrics.tool,
            ).inc_by(metrics.cost_usd)
        
        if metrics.tokens_input:
            self.tokens_input.labels(
                tool=metrics.tool,
            ).inc_by(metrics.tokens_input)
        
        if metrics.tokens_output:
            self.tokens_output.labels(
                tool=metrics.tool,
            ).inc_by(metrics.tokens_output)
    
    def increment_active(self, tool: str) -> None:
        """Increment active requests counter (legacy)"""
        self.active_requests.labels(tool=tool).inc()
    
    def decrement_active(self, tool: str) -> None:
        """Decrement active requests counter (legacy)"""
        self.active_requests.labels(tool=tool).dec()
    
    def export(self) -> str:
        """Export metrics in Prometheus format"""
        from prometheus_client import generate_latest
        return generate_latest(REGISTRY).decode("utf-8")
