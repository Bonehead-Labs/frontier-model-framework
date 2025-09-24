"""OpenTelemetry tracing support for FMF operations."""

from contextlib import contextmanager
from typing import Any, Dict, Optional
from functools import wraps

# Optional OpenTelemetry imports
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.instrumentation.auto_instrumentation import sitecustomize
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    trace = None
    Status = None
    StatusCode = None
    TracerProvider = None
    BatchSpanProcessor = None
    ConsoleSpanExporter = None
    OTLPSpanExporter = None
    Resource = None


class FMFTracer:
    """OpenTelemetry tracer for FMF operations."""

    def __init__(self, enabled: bool = False, service_name: str = "fmf"):
        self.enabled = enabled and OPENTELEMETRY_AVAILABLE
        self.service_name = service_name
        self.tracer = None

        if self.enabled:
            self._setup_tracer()

    def _setup_tracer(self) -> None:
        """Set up OpenTelemetry tracer."""
        if not OPENTELEMETRY_AVAILABLE:
            return

        # Create resource
        resource = Resource.create({
            "service.name": self.service_name,
            "service.version": "1.0.0",
        })

        # Create tracer provider
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)

        # Add span processor
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)

        # Get tracer
        self.tracer = trace.get_tracer(self.service_name)

    @contextmanager
    def span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Create a span for an operation."""
        if not self.enabled or not self.tracer:
            yield
            return

        with self.tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))

            try:
                yield span
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
            else:
                span.set_status(Status(StatusCode.OK))

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the current span."""
        if not self.enabled or not self.tracer:
            return

        current_span = trace.get_current_span()
        if current_span.is_recording():
            current_span.add_event(name, attributes or {})

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the current span."""
        if not self.enabled or not self.tracer:
            return

        current_span = trace.get_current_span()
        if current_span.is_recording():
            current_span.set_attribute(key, str(value))


# Global tracer instance
_fmf_tracer: Optional[FMFTracer] = None


def get_tracer(enabled: bool = False, service_name: str = "fmf") -> FMFTracer:
    """Get or create the global FMF tracer."""
    global _fmf_tracer
    if _fmf_tracer is None:
        _fmf_tracer = FMFTracer(enabled, service_name)
    return _fmf_tracer


def trace_operation(name: str, attributes: Optional[Dict[str, Any]] = None):
    """Decorator to trace an operation."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.span(name, attributes):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def add_trace_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """Add an event to the current trace."""
    get_tracer().add_event(name, attributes)


def set_trace_attribute(key: str, value: Any) -> None:
    """Set an attribute on the current trace."""
    get_tracer().set_attribute(key, value)


def is_tracing_enabled() -> bool:
    """Check if tracing is enabled."""
    return get_tracer().enabled


def enable_tracing(service_name: str = "fmf") -> None:
    """Enable tracing."""
    global _fmf_tracer
    _fmf_tracer = FMFTracer(enabled=True, service_name=service_name)


def disable_tracing() -> None:
    """Disable tracing."""
    global _fmf_tracer
    _fmf_tracer = FMFTracer(enabled=False)
