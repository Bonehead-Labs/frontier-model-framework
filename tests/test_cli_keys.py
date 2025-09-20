import io
import json
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
        self.assertIn("Secrets:", out)
        self.assertIn("Diagnostics:", out)

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

    def test_keys_diagnostics_detects_missing_fields(self):
        from fmf.cli import main

        yaml_path = self._write_yaml(
            """
            project: fmf
            auth: { provider: env }
            connectors:
              - name: s3_raw
                type: s3
            inference:
              provider: aws_bedrock
              aws_bedrock: { region: us-east-1 }
            export:
              sinks:
                - name: ddb
                  type: dynamodb
            """
        )
        os.environ["DUMMY"] = "value"

        buf = io.StringIO()
        sys_stdout = sys.stdout
        try:
            sys.stdout = buf
            rc = main(["keys", "test", "-c", yaml_path, "DUMMY"])
        finally:
            sys.stdout = sys_stdout

        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("Connector", out)
        self.assertIn("WARN", out)
        self.assertIn("missing fields", out)

    def test_keys_json_output(self):
        from fmf.cli import main

        yaml_path = self._write_yaml(
            """
            project: fmf
            auth: { provider: env }
            """
        )
        os.environ["SECRET"] = "value"

        buf = io.StringIO()
        sys_stdout = sys.stdout
        try:
            sys.stdout = buf
            rc = main(["keys", "test", "-c", yaml_path, "--json", "SECRET"])
        finally:
            sys.stdout = sys_stdout

        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["secrets"][0]["name"], "SECRET")
        self.assertEqual(payload["secrets"][0]["status"], "OK")


if __name__ == "__main__":
    unittest.main()
