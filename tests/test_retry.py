from __future__ import annotations

import unittest

from fmf.core.retry import retry_call


class TestRetryHelpers(unittest.TestCase):
    def test_retry_succeeds_after_transient(self) -> None:
        calls = {"count": 0}

        class Dummy(Exception):
            status_code = 500

        def func():
            calls["count"] += 1
            if calls["count"] < 3:
                raise Dummy()
            return "ok"

        result = retry_call(func, max_attempts=5, base_delay=0.0, max_delay=0.0, sleep=lambda _d: None)
        self.assertEqual(result, "ok")
        self.assertEqual(calls["count"], 3)

    def test_retry_stops_on_non_retriable(self) -> None:
        class CustomError(Exception):
            status_code = 400

        with self.assertRaises(CustomError):
            retry_call(lambda: (_ for _ in ()).throw(CustomError()), max_attempts=2, sleep=lambda _d: None)


if __name__ == "__main__":
    unittest.main()
