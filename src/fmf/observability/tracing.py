from __future__ import annotations

import os
import os
from contextlib import contextmanager


@contextmanager
def trace_span(name: str, **attributes):
    """Start a tracing span if OpenTelemetry is available; otherwise no-op.

    Attributes passed as keyword arguments are applied to the span when OpenTelemetry
    instrumentation is enabled via ``FMF_OBSERVABILITY_OTEL``.
    """
    if os.getenv("FMF_OBSERVABILITY_OTEL", "false").lower() not in {"1", "true", "yes", "on"}:
        yield
        return
    try:
        from opentelemetry import trace  # type: ignore

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(name) as span:
            for key, value in attributes.items():  # pragma: no cover - best effort
                try:
                    span.set_attribute(key, value)
                except Exception:
                    continue
            yield
    except Exception:
        yield


__all__ = ["trace_span"]
