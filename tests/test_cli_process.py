import io
import os
import sys
import tempfile
import textwrap
import unittest


class TestCliProcess(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        self.tmpdir = tempfile.TemporaryDirectory()
        self.artdir = tempfile.TemporaryDirectory()
        root = self.tmpdir.name
        os.makedirs(root, exist_ok=True)
        with open(os.path.join(root, "doc.md"), "w", encoding="utf-8") as f:
            f.write("# Title\nHello world.")

    def tearDown(self):
        self.tmpdir.cleanup()
        self.artdir.cleanup()

    def _write_yaml(self, content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(content))
        return path

    def test_process_local_markdown(self):
        from fmf.cli import main

        yaml_path = self._write_yaml(
            f"""
            project: fmf
            artefacts_dir: {self.artdir.name}
            connectors:
              - name: local_docs
                type: local
                root: {self.tmpdir.name}
                include: ["**/*.md"]
            processing:
              text:
                normalize_whitespace: true
                preserve_markdown: true
                chunking:
                  strategy: recursive
                  max_tokens: 10
                  overlap: 2
                  splitter: by_sentence
            """
        )

        buf = io.StringIO()
        sys_stdout = sys.stdout
        try:
            sys.stdout = buf
            rc = main(["process", "--connector", "local_docs", "--select", "**/*.md", "-c", yaml_path])
        finally:
            sys.stdout = sys_stdout

        self.assertEqual(rc, 0)
        out = buf.getvalue()
        # Extract paths printed
        self.assertIn("run_id=", out)
        self.assertIn(self.artdir.name, out)
        # Verify docs.jsonl exists
        # find created run dir
        runs = [d for d in os.listdir(self.artdir.name) if os.path.isdir(os.path.join(self.artdir.name, d))]
        self.assertTrue(len(runs) >= 1)
        run_dir = os.path.join(self.artdir.name, sorted(runs)[-1])
        docs_path = os.path.join(run_dir, "docs.jsonl")
        self.assertTrue(os.path.exists(docs_path))
        with open(docs_path, "r", encoding="utf-8") as f:
            data = f.read()
            self.assertIn("Title", data)


if __name__ == "__main__":
    unittest.main()

