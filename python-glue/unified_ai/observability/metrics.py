"""Prometheus metrics collection"""

from prometheus_client import Counter, Histogram, Gauge, REGISTRY
from typing import Optional, Dict
from dataclasses import dataclass
import time


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
    
    def record_request(self, metrics: RequestMetrics) -> None:
        """Record request metrics"""
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
        """Increment active requests counter"""
        self.active_requests.labels(tool=tool).inc()
    
    def decrement_active(self, tool: str) -> None:
        """Decrement active requests counter"""
        self.active_requests.labels(tool=tool).dec()
    
    def export(self) -> str:
        """Export metrics in Prometheus format"""
        from prometheus_client import generate_latest
        return generate_latest(REGISTRY).decode("utf-8")


# Convenience functions
def Counter(name: str, **kwargs):
    """Create a counter metric"""
    return Counter(name, **kwargs)


def Histogram(name: str, **kwargs):
    """Create a histogram metric"""
    return Histogram(name, **kwargs)


def Gauge(name: str, **kwargs):
    """Create a gauge metric"""
    return Gauge(name, **kwargs)
