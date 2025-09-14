import io
import os
import sys
import tempfile
import textwrap
import unittest


class TestCliPromptRegister(unittest.TestCase):
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

    def test_cli_prompt_register(self):
        import fmf.cli as cli

        tmpdir = tempfile.TemporaryDirectory()
        prompts_dir = os.path.join(tmpdir.name, "prompts")
        os.makedirs(prompts_dir, exist_ok=True)
        pfile = os.path.join(prompts_dir, "sum.yaml")
        with open(pfile, "w", encoding="utf-8") as f:
            f.write(
                textwrap.dedent(
                    """
                    id: summarize
                    versions:
                      - version: v1
                        template: |
                          Test {{ text }}
                    """
                )
            )
        cfg = self._write_yaml(
            f"""
            project: fmf
            prompt_registry: {{ backend: local_yaml, path: {tmpdir.name}, index_file: prompts/index.yaml }}
            """
        )

        buf = io.StringIO()
        orig = sys.stdout
        try:
            sys.stdout = buf
            rc = cli.main(["prompt", "register", f"{pfile}#v1", "-c", cfg])
        finally:
            sys.stdout = orig

        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("registered summarize#v1", out)


if __name__ == "__main__":
    unittest.main()

