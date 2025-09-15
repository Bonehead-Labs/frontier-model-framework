import os
import sys
import tempfile
import textwrap
import unittest


class TestCliDoctor(unittest.TestCase):
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

    def test_doctor_prints_provider_and_connector(self):
        import fmf.cli as cli
        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        cfg = self._write_yaml(
            f"""
            project: fmf
            artefacts_dir: {root}
            connectors: [{{ name: local_docs, type: local, root: {root}, include: ["**/*"] }}]
            inference: {{ provider: azure_openai, azure_openai: {{ endpoint: https://x, api_version: v, deployment: d }} }}
            """
        )
        # capture stdout
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli.main(["doctor", "-c", cfg])
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("provider=azure_openai", out)
        self.assertIn("connector=local_docs", out)


if __name__ == "__main__":
    unittest.main()

