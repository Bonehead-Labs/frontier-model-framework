from __future__ import annotations

from contextlib import contextmanager


@contextmanager
def trace_span(name: str):
    """Start a tracing span if OpenTelemetry is available; otherwise no-op."""
    try:
        from opentelemetry import trace  # type: ignore

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(name):
            yield
    except Exception:
        # No OpenTelemetry installed or other failure; silently continue
        yield


__all__ = ["trace_span"]

