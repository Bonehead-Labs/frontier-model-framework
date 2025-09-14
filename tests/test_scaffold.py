import os
import sys
import subprocess
import unittest


def _add_src_to_path():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    src_path = os.path.join(repo_root, "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


class TestScaffold(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _add_src_to_path()

    def test_import_root_and_subpackages(self):
        import fmf  # type: ignore

        # Import subpackages
        from fmf import (
            config,
            auth,
            connectors,
            processing,
            inference,
            prompts,
            observability,
            exporters,
        )  # noqa: F401

        # Basic sanity: __all__ lists expected subpackages
        expected = {
            "config",
            "auth",
            "connectors",
            "processing",
            "inference",
            "prompts",
            "observability",
            "exporters",
        }
        self.assertTrue(hasattr(fmf, "__all__"))
        self.assertTrue(expected.issubset(set(getattr(fmf, "__all__"))))

    def test_python_m_fmf_runs(self):
        # Ensure `python -m fmf` executes and prints scaffold message
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.join(repo_root, "src") + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(
            [sys.executable, "-m", "fmf"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=repo_root,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("FMF package scaffolding is in place.", result.stdout)


if __name__ == "__main__":
    unittest.main()

