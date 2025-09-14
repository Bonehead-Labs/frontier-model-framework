import io
import os
import sys
import tempfile
import unittest


class TestLocalConnector(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        self.tmpdir = tempfile.TemporaryDirectory()
        root = self.tmpdir.name
        os.makedirs(os.path.join(root, "a/b"), exist_ok=True)
        os.makedirs(os.path.join(root, ".git", "objects"), exist_ok=True)
        with open(os.path.join(root, "a", "x.txt"), "wb") as f:
            f.write(b"hello x")
        with open(os.path.join(root, "a", "b", "y.md"), "wb") as f:
            f.write(b"hello y")
        with open(os.path.join(root, "notes.md"), "wb") as f:
            f.write(b"top-level")
        with open(os.path.join(root, ".git", "objects", "blob"), "wb") as f:
            f.write(b"ignore")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_list_include_exclude_and_open_info(self):
        from fmf.connectors.local import LocalConnector
        from fmf.connectors import ResourceRef

        conn = LocalConnector(
            name="local_docs",
            root=self.tmpdir.name,
            include=["**/*.txt", "**/*.md"],
            exclude=["**/.git/**"],
        )

        refs = list(conn.list())
        ids = {r.id for r in refs}
        self.assertIn("a/x.txt", ids)
        self.assertIn("a/b/y.md", ids)
        self.assertIn("notes.md", ids)
        # .git blob excluded
        self.assertTrue(all(".git" not in r.id for r in refs))

        # Open and read bytes
        r = next(r for r in refs if r.id.endswith("x.txt"))
        with conn.open(r) as f:
            self.assertEqual(f.read(), b"hello x")

        # Info returns size and uri
        info = conn.info(r)
        self.assertEqual(info.size, 7)
        self.assertTrue(info.source_uri.startswith("file:"))

    def test_selector_overrides_include(self):
        from fmf.connectors.local import LocalConnector

        conn = LocalConnector(
            name="local_docs",
            root=self.tmpdir.name,
            include=["**/*.md"],
        )
        # selector limits to txt only
        refs = list(conn.list(selector=["**/*.txt"]))
        self.assertTrue(all(r.id.endswith(".txt") for r in refs))


if __name__ == "__main__":
    unittest.main()

