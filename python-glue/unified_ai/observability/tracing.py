"""OpenTelemetry tracing setup"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from contextlib import contextmanager
from typing import Optional, Dict, Any
import functools


def setup_tracing(
    service_name: str = "uai-orchestrator",
    endpoint: Optional[str] = None,
    console: bool = False,
) -> None:
    """Setup OpenTelemetry tracing"""
    resource = Resource.create({
        "service.name": service_name,
    })
    
    provider = TracerProvider(resource=resource)
    
    if endpoint:
        exporter = OTLPSpanExporter(endpoint=endpoint)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
    
    if console:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter
        console_exporter = ConsoleSpanExporter()
        console_processor = BatchSpanProcessor(console_exporter)
        provider.add_span_processor(console_processor)
    
    trace.set_tracer_provider(provider)


@contextmanager
def trace_request(
    operation_name: str,
    attributes: Optional[Dict[str, Any]] = None,
):
    """Context manager for tracing a request"""
    tracer = trace.get_tracer(__name__)
    span = tracer.start_span(operation_name)
    
    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, str(value))
    
    try:
        yield span
    except Exception as e:
        span.record_exception(e)
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        raise
    finally:
        span.end()


class Span:
    """Span wrapper for easier usage"""
    
    def __init__(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        self.name = name
        self.attributes = attributes or {}
        self._span = None
    
    def __enter__(self):
        tracer = trace.get_tracer(__name__)
        self._span = tracer.start_span(self.name)
        for key, value in self.attributes.items():
            self._span.set_attribute(key, str(value))
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._span.record_exception(exc_val)
            self._span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc_val)))
        self._span.end()
        return False
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set span attribute"""
        if self._span:
            self._span.set_attribute(key, str(value))
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add event to span"""
        if self._span:
            self._span.add_event(name, attributes or {})


def traced(func):
    """Decorator to trace a function"""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        tracer = trace.get_tracer(func.__module__)
        with tracer.start_as_current_span(func.__name__) as span:
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        tracer = trace.get_tracer(func.__module__)
        with tracer.start_as_current_span(func.__name__) as span:
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper
