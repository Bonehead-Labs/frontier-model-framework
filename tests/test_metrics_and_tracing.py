import os
import sys
import unittest


class TestMetricsAndTracing(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_metrics_retry_increment(self):
        from fmf.inference.base_client import with_retries, InferenceError
        from fmf.observability import metrics

        metrics.clear()

        calls = {"n": 0}

        class E(Exception):
            def __init__(self, status_code):
                super().__init__("error")
                self.status_code = status_code

        def fn():
            calls["n"] += 1
            if calls["n"] < 2:
                raise E(429)
            return "ok"

        from fmf.inference.base_client import Completion

        res = with_retries(lambda: Completion(text=fn()))
        self.assertEqual(res.text, "ok")
        self.assertGreaterEqual(metrics.get_all().get("retries", 0), 1)

    def test_tracing_noop(self):
        from fmf.observability.tracing import trace_span
        # Should not raise even without OpenTelemetry installed
        with trace_span("unit-test"):
            pass

    def test_tracing_with_fake_otel(self):
        import types
        from contextlib import contextmanager
        import sys
        from fmf.observability.tracing import trace_span

        os.environ["FMF_OBSERVABILITY_OTEL"] = "true"

        class FakeSpan:
            def __init__(self):
                self.attrs = {}

            def set_attribute(self, key, value):
                self.attrs[key] = value

        class FakeTracer:
            def __init__(self):
                self.captured = []

            def start_as_current_span(self, name):
                span = FakeSpan()
                self.captured.append((name, span))

                @contextmanager
                def _cm():
                    yield span

                return _cm()

        tracer = FakeTracer()
        trace_module = types.ModuleType("opentelemetry.trace")
        trace_module.get_tracer = lambda _: tracer
        pkg = types.ModuleType("opentelemetry")
        pkg.trace = trace_module
        sys.modules["opentelemetry"] = pkg
        sys.modules["opentelemetry.trace"] = trace_module
        try:
            with trace_span("unit-test", example="value"):
                pass
        finally:
            os.environ.pop("FMF_OBSERVABILITY_OTEL", None)
            sys.modules.pop("opentelemetry", None)
            sys.modules.pop("opentelemetry.trace", None)

        self.assertEqual(len(tracer.captured), 1)
        name, span = tracer.captured[0]
        self.assertEqual(name, "unit-test")
        self.assertEqual(span.attrs.get("example"), "value")


if __name__ == "__main__":
    unittest.main()
