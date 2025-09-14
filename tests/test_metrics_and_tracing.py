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


if __name__ == "__main__":
    unittest.main()

