import io
import json
import logging
import os
import sys
import unittest


def _add_src_to_path():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    src_path = os.path.join(repo_root, "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


class TestLoggingSetup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _add_src_to_path()
    def setUp(self) -> None:
        # Ensure environment is clean for each test
        self._old_env = os.environ.get("FMF_LOG_FORMAT")
        if "FMF_LOG_FORMAT" in os.environ:
            del os.environ["FMF_LOG_FORMAT"]
        # Reset root logger handlers
        logging.getLogger().handlers = []

    def tearDown(self) -> None:
        # Restore env
        if self._old_env is not None:
            os.environ["FMF_LOG_FORMAT"] = self._old_env
        else:
            os.environ.pop("FMF_LOG_FORMAT", None)
        logging.getLogger().handlers = []

    def test_json_format_explicit(self):
        from fmf.observability import setup_logging

        buf = io.StringIO()
        setup_logging("json", stream=buf)
        logger = logging.getLogger("test.json")
        logger.info("hello %s", "world", extra={"run_id": "abc123"})
        line = buf.getvalue().strip()
        data = json.loads(line)
        self.assertEqual(data["level"], "INFO")
        self.assertEqual(data["name"], "test.json")
        self.assertEqual(data["message"], "hello world")
        self.assertEqual(data["run_id"], "abc123")
        self.assertIn("time", data)

    def test_human_format_explicit(self):
        from fmf.observability import setup_logging

        buf = io.StringIO()
        setup_logging("human", stream=buf)
        logger = logging.getLogger("test.human")
        logger.info("hello %s", "world")
        out = buf.getvalue().strip()
        self.assertTrue(out.startswith("INFO test.human - hello world"))

    def test_env_controls_default(self):
        from fmf.observability import setup_logging

        os.environ["FMF_LOG_FORMAT"] = "json"
        buf = io.StringIO()
        setup_logging(stream=buf)  # No fmt specified -> env wins
        logging.getLogger("env.json").warning("beep")
        data = json.loads(buf.getvalue().strip())
        self.assertEqual(data["level"], "WARNING")

    def test_redaction_of_secret_keys(self):
        from fmf.observability import setup_logging

        buf = io.StringIO()
        setup_logging("json", stream=buf)
        logging.getLogger("redact").warning("msg", extra={"api_key": "supersecret", "token": "abc", "info": "ok"})
        data = json.loads(buf.getvalue().strip())
        self.assertEqual(data.get("api_key"), "****")
        self.assertEqual(data.get("token"), "****")
        self.assertEqual(data.get("info"), "ok")


if __name__ == "__main__":
    unittest.main()
