import io
import os
import sys
import tempfile
import textwrap
import unittest


class TestCliKeys(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        self._old_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._old_env)

    def _write_yaml(self, content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(content))
        return path

    def test_keys_test_env_provider_success(self):
        from fmf.cli import main

        yaml_path = self._write_yaml(
            """
            project: fmf
            auth: { provider: env }
            """
        )
        os.environ["API_KEY"] = "sekrit"

        buf = io.StringIO()
        sys_stdout = sys.stdout
        try:
            sys.stdout = buf
            rc = main(["keys", "test", "-c", yaml_path, "API_KEY"])
        finally:
            sys.stdout = sys_stdout

        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("API_KEY", out)
        self.assertIn("****", out)
        self.assertNotIn("sekrit", out)

    def test_keys_test_needs_names_without_mapping(self):
        from fmf.cli import main

        yaml_path = self._write_yaml(
            """
            project: fmf
            auth: { provider: env }
            """
        )

        buf = io.StringIO()
        sys_stdout = sys.stdout
        try:
            sys.stdout = buf
            rc = main(["keys", "test", "-c", yaml_path])
        finally:
            sys.stdout = sys_stdout

        self.assertEqual(rc, 2)
        self.assertIn("No secret names provided", buf.getvalue())


if __name__ == "__main__":
    unittest.main()

