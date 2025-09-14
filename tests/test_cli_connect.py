import io
import os
import sys
import tempfile
import textwrap
import unittest


class TestCliConnectLs(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        self.tmpdir = tempfile.TemporaryDirectory()
        root = self.tmpdir.name
        os.makedirs(os.path.join(root, "d"), exist_ok=True)
        with open(os.path.join(root, "a.md"), "wb") as f:
            f.write(b"x")
        with open(os.path.join(root, "d", "b.txt"), "wb") as f:
            f.write(b"y")

    def tearDown(self):
        self.tmpdir.cleanup()

    def _write_yaml(self, content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(content))
        return path

    def test_connect_ls_local(self):
        from fmf.cli import main

        yaml_path = self._write_yaml(
            f"""
            project: fmf
            connectors:
              - name: local_docs
                type: local
                root: {self.tmpdir.name}
                include: ["**/*"]
            """
        )
        buf = io.StringIO()
        sys_stdout = sys.stdout
        try:
            sys.stdout = buf
            rc = main(["connect", "ls", "local_docs", "-c", yaml_path, "--select", "**/*.md"])
        finally:
            sys.stdout = sys_stdout

        self.assertEqual(rc, 0)
        out = buf.getvalue().strip().splitlines()
        # Expect a line for a.md with id and uri separated by a tab
        self.assertTrue(any(line.split("\t")[0] == "a.md" for line in out))


if __name__ == "__main__":
    unittest.main()

