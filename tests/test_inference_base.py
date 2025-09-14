import os
import sys
import unittest


class TestInferenceBase(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_retry_backoff_wraps_exceptions(self):
        from fmf.inference.base_client import with_retries, InferenceError

        calls = {"n": 0}

        class E(Exception):
            def __init__(self, status_code):
                super().__init__("error")
                self.status_code = status_code

        def fn():
            calls["n"] += 1
            if calls["n"] < 3:
                raise E(429)
            return "ok"

        # with_retries expects a function returning Completion; we simulate by wrapper
        from fmf.inference.base_client import Completion

        result = with_retries(lambda: Completion(text=fn()))
        self.assertEqual(result.text, "ok")
        self.assertGreaterEqual(calls["n"], 3)


if __name__ == "__main__":
    unittest.main()

