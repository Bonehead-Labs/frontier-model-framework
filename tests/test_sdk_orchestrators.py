import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestSdkOrchestrators(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        self.tempdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_run_recipe_simple_success(self):
        from fmf.sdk import orchestrators

        artefacts_dir = Path(self.tempdir.name) / "artefacts"
        artefacts_dir.mkdir(parents=True, exist_ok=True)

        def fake_run_recipe(recipe_path, **kwargs):
            run_dir = artefacts_dir / "20250101T000000Z"
            run_dir.mkdir(parents=True, exist_ok=True)
            outputs = run_dir / "outputs.jsonl"
            outputs.write_text("{\"line\":1}\n{\"line\":2}\n", encoding="utf-8")

        with patch.object(orchestrators, "FMF") as mock_fmf:
            instance = mock_fmf.from_env.return_value
            instance._cfg = {"artefacts_dir": str(artefacts_dir)}
            instance.run_recipe.side_effect = fake_run_recipe

            summary = orchestrators.run_recipe_simple("fmf.yaml", "recipe.yaml")

        self.assertTrue(summary.ok)
        self.assertEqual(summary.run_id, "20250101T000000Z")
        self.assertEqual(summary.inputs, 2)
        self.assertTrue(summary.outputs_path.endswith("outputs.jsonl"))

    def test_run_recipe_simple_failure(self):
        from fmf.sdk import orchestrators

        artefacts_dir = Path(self.tempdir.name) / "artefacts"

        with patch.object(orchestrators, "FMF") as mock_fmf:
            instance = mock_fmf.from_env.return_value
            instance._cfg = {"artefacts_dir": str(artefacts_dir)}
            instance.run_recipe.side_effect = RuntimeError("boom")

            summary = orchestrators.run_recipe_simple("fmf.yaml", "recipe.yaml")

        self.assertFalse(summary.ok)
        self.assertIsNone(summary.run_id)
        self.assertIn("Recipe failed", summary.notes or "")

    def test_run_recipe_simple_missing_outputs(self):
        from fmf.sdk import orchestrators

        artefacts_dir = Path(self.tempdir.name) / "artefacts"
        artefacts_dir.mkdir(parents=True, exist_ok=True)

        def fake_run_recipe(recipe_path, **kwargs):
            run_dir = artefacts_dir / "20250102T000000Z"
            run_dir.mkdir(parents=True, exist_ok=True)
            # No outputs.jsonl -> fall back to run directory path

        with patch.object(orchestrators, "FMF") as mock_fmf:
            instance = mock_fmf.from_env.return_value
            instance._cfg = {"artefacts_dir": str(artefacts_dir)}
            instance.run_recipe.side_effect = fake_run_recipe

            summary = orchestrators.run_recipe_simple("fmf.yaml", "recipe.yaml")

        self.assertTrue(summary.ok)
        self.assertIsNone(summary.inputs)
        self.assertTrue(summary.outputs_path.endswith("20250102T000000Z"))


if __name__ == "__main__":
    unittest.main()
