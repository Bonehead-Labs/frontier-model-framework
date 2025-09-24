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
            import yaml

            run_yaml = {
                "metrics": {
                    "streaming_used": True,
                    "time_to_first_byte_ms_avg": 120,
                    "latency_ms_avg": 450,
                    "tokens_out_sum": 84,
                    "retries_total": 2,
                },
                "step_telemetry": {
                    "analyse": {
                        "streaming": True,
                        "selected_mode": "stream",
                        "fallback_reason": None,
                    }
                },
            }
            (run_dir / "run.yaml").write_text(yaml.safe_dump(run_yaml), encoding="utf-8")

        with patch.object(orchestrators, "FMF") as mock_fmf:
            instance = mock_fmf.from_env.return_value
            instance._cfg = {"artefacts_dir": str(artefacts_dir)}
            instance.run_recipe.side_effect = fake_run_recipe

            summary = orchestrators.run_recipe_simple("fmf.yaml", "recipe.yaml")

        self.assertTrue(summary.ok)
        self.assertEqual(summary.run_id, "20250101T000000Z")
        self.assertEqual(summary.inputs, 2)
        self.assertTrue(summary.outputs_path.endswith("outputs.jsonl"))
        self.assertTrue(summary.streaming)
        self.assertEqual(summary.mode, "stream")
        self.assertEqual(summary.time_to_first_byte_ms, 120)
        self.assertEqual(summary.tokens_out, 84)
        self.assertEqual(summary.retries, 2)

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
            import yaml

            run_yaml = {
                "metrics": {
                    "streaming_used": False,
                    "time_to_first_byte_ms_avg": 90,
                    "latency_ms_avg": 300,
                    "retries_total": 0,
                },
            }
            (run_dir / "run.yaml").write_text(yaml.safe_dump(run_yaml), encoding="utf-8")

        with patch.object(orchestrators, "FMF") as mock_fmf:
            instance = mock_fmf.from_env.return_value
            instance._cfg = {"artefacts_dir": str(artefacts_dir)}
            instance.run_recipe.side_effect = fake_run_recipe

            summary = orchestrators.run_recipe_simple("fmf.yaml", "recipe.yaml")

        self.assertTrue(summary.ok)
        self.assertIsNone(summary.inputs)
        self.assertTrue(summary.outputs_path.endswith("20250102T000000Z"))
        self.assertFalse(summary.streaming)
        self.assertIsNone(summary.tokens_out)

    def test_run_recipe_simple_uses_fluent_api(self):
        """Test that run_recipe_simple uses the fluent API instead of run_recipe."""
        from fmf.sdk import orchestrators
        import tempfile
        import yaml

        # Create a temporary recipe file
        recipe_data = {
            "recipe": "csv_analyse",
            "input": "./data/comments.csv",
            "id_col": "ID",
            "text_col": "Comment",
            "prompt": "Summarise this comment",
            "save": {
                "csv": "artefacts/${run_id}/analysis.csv",
                "jsonl": "artefacts/${run_id}/analysis.jsonl"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.safe_dump(recipe_data, f)
            recipe_path = f.name

        artefacts_dir = Path(self.tempdir.name) / "artefacts"
        artefacts_dir.mkdir(parents=True, exist_ok=True)

        def fake_csv_analyse(**kwargs):
            # Verify that the fluent API method is called with correct parameters
            assert kwargs["input"] == "./data/comments.csv"
            assert kwargs["text_col"] == "Comment"
            assert kwargs["id_col"] == "ID"
            assert kwargs["prompt"] == "Summarise this comment"
            assert kwargs["save_csv"] == "artefacts/${run_id}/analysis.csv"
            assert kwargs["save_jsonl"] == "artefacts/${run_id}/analysis.jsonl"
            
            # Create fake run artifacts
            run_dir = artefacts_dir / "20250101T000000Z"
            run_dir.mkdir(parents=True, exist_ok=True)
            outputs = run_dir / "outputs.jsonl"
            outputs.write_text("{\"line\":1}\n{\"line\":2}\n", encoding="utf-8")

        with patch.object(orchestrators, "FMF") as mock_fmf:
            instance = mock_fmf.from_env.return_value
            instance._cfg = {"artefacts_dir": str(artefacts_dir)}
            instance._rag_override = None
            instance._service_override = None
            instance._response_override = None
            instance._source_override = None
            instance.csv_analyse.side_effect = fake_csv_analyse

            summary = orchestrators.run_recipe_simple("fmf.yaml", recipe_path)

        # Verify the fluent API method was called
        instance.csv_analyse.assert_called_once()
        
        # Verify the summary is correct
        self.assertTrue(summary.ok)
        self.assertEqual(summary.run_id, "20250101T000000Z")
        self.assertEqual(summary.inputs, 2)

        # Clean up
        Path(recipe_path).unlink()

    def test_run_recipe_simple_fluent_overrides_precedence(self):
        """Test that fluent overrides take precedence over recipe YAML."""
        from fmf.sdk import orchestrators
        import tempfile
        import yaml

        # Create a recipe with RAG enabled
        recipe_data = {
            "recipe": "csv_analyse",
            "input": "./data/comments.csv",
            "id_col": "ID",
            "text_col": "Comment",
            "prompt": "Summarise this comment",
            "rag": {
                "pipeline": "recipe_rag",
                "top_k_text": 5
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.safe_dump(recipe_data, f)
            recipe_path = f.name

        artefacts_dir = Path(self.tempdir.name) / "artefacts"
        artefacts_dir.mkdir(parents=True, exist_ok=True)

        def fake_csv_analyse(**kwargs):
            # Verify that fluent overrides take precedence
            assert kwargs["prompt"] == "Override prompt"  # From kwargs
            assert kwargs["rag_options"]["pipeline"] == "override_rag"  # From kwargs
            assert kwargs["rag_options"]["top_k_text"] == 3  # From kwargs
            
        with patch.object(orchestrators, "FMF") as mock_fmf:
            instance = mock_fmf.from_env.return_value
            instance._cfg = {"artefacts_dir": str(artefacts_dir)}
            instance._rag_override = {"enabled": True, "pipeline": "override_rag"}
            instance._service_override = None
            instance._response_override = None
            instance._source_override = None
            instance.csv_analyse.side_effect = fake_csv_analyse

            # Pass fluent overrides via kwargs
            summary = orchestrators.run_recipe_simple(
                "fmf.yaml", 
                recipe_path,
                prompt="Override prompt",
                rag_top_k_text=3
            )

        # Verify the fluent API method was called with overrides
        instance.csv_analyse.assert_called_once()
        self.assertTrue(summary.ok)

        # Clean up
        Path(recipe_path).unlink()


if __name__ == "__main__":
    unittest.main()
