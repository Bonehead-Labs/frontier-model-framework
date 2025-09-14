import io
import os
import sys
import tempfile
import textwrap
import unittest


class TestCliInfer(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def _write_yaml(self, content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(content))
        return path

    def test_infer_uses_unified_client(self):
        import fmf.cli as cli

        # Patch build_llm_client to return a dummy client
        class Dummy:
            def complete(self, messages, **kwargs):
                # Echo last user content
                user = [m for m in messages if m.role == "user"][0]
                return type("C", (), {"text": f"ECHO: {user.content}"})()

        cli.build_llm_client = lambda cfg: Dummy()  # type: ignore

        yaml_path = self._write_yaml(
            """
            project: fmf
            inference:
              provider: azure_openai
              azure_openai:
                endpoint: https://example
                api_version: 2024-02-15-preview
                deployment: test
            """
        )

        fd, inpath = tempfile.mkstemp(suffix=".txt")
        os.close(fd)
        with open(inpath, "w", encoding="utf-8") as f:
            f.write("Hello")

        buf = io.StringIO()
        sys_stdout = sys.stdout
        try:
            sys.stdout = buf
            rc = cli.main(["infer", "--input", inpath, "-c", yaml_path])
        finally:
            sys.stdout = sys_stdout

        self.assertEqual(rc, 0)
        self.assertIn("ECHO: Hello", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
