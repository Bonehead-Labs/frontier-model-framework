import io
import os
import sys
import tempfile
import textwrap
import unittest


class TestCliRun(unittest.TestCase):
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

    def test_cli_run_invokes_runner(self):
        import fmf.cli as cli

        tmp_chain = self._write_yaml("name: t\ninputs: {}\nsteps: []\n")
        tmp_cfg = self._write_yaml("project: fmf\n")

        called = {"ok": False}

        def fake_run_chain(path, *, fmf_config_path, set_overrides=None):
            called["ok"] = True
            return {"run_id": "r1", "run_dir": "/tmp/x"}

        cli.run_chain = fake_run_chain  # type: ignore

        buf = io.StringIO()
        orig = sys.stdout
        try:
            sys.stdout = buf
            rc = cli.main(["run", "--chain", tmp_chain, "-c", tmp_cfg])
        finally:
            sys.stdout = orig

        self.assertEqual(rc, 0)
        self.assertTrue(called["ok"])
        out = buf.getvalue()
        self.assertIn("run_id=r1", out)


if __name__ == "__main__":
    unittest.main()
