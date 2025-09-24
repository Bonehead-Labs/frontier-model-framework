"""Integration tests for config system changes."""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.fmf.config.effective import EffectiveConfig
from src.fmf.config.models import FmfConfig
from src.fmf.sdk.client import FMF


class TestConfigIntegration(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_fmf_client_uses_effective_config(self):
        """Test that FMF client uses EffectiveConfig internally."""
        # Create a base config
        base_config = FmfConfig(
            project="test-project",
            artefacts_dir=str(self.temp_path / "artefacts")
        )
        
        # Create FMF instance
        fmf = FMF.from_env(base_config)
        
        # Apply fluent overrides
        fmf = fmf.with_service("aws_bedrock").with_rag(enabled=True, pipeline="test_rag")
        
        # Get effective config
        effective_config = fmf._get_effective_config()
        
        # Should be an EffectiveConfig instance
        self.assertIsInstance(effective_config, EffectiveConfig)
        
        # Should have fluent overrides applied
        self.assertEqual(effective_config.inference["provider"], "aws_bedrock")
        self.assertTrue(effective_config.rag["enabled"])
        self.assertEqual(effective_config.rag["pipeline"], "test_rag")

    def test_chain_runner_accepts_config_objects(self):
        """Test that chain runners accept config objects directly."""
        from src.fmf.chain.runner import run_chain_config
        
        # Create effective config
        effective_config = EffectiveConfig(
            project="test-project",
            artefacts_dir=str(self.temp_path / "artefacts"),
            inference={"provider": "azure_openai"}
        )
        
        # Create a simple chain config
        chain_config = {
            "name": "test_chain",
            "inputs": {"connector": "local_docs"},
            "steps": [
                {
                    "id": "test_step",
                    "prompt": "Test prompt",
                    "inputs": {"text": "test"},
                    "output": "result"
                }
            ],
            "outputs": []
        }
        
        # Mock the actual execution to avoid real API calls
        with patch('src.fmf.chain.runner._run_chain_loaded') as mock_run:
            mock_run.return_value = {"run_id": "test_run", "status": "success"}
            
            # Should accept config object
            result = run_chain_config(
                chain_config,
                fmf_config=effective_config
            )
            
            # Should have called the runner with config object
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            self.assertEqual(call_args[1]['fmf_config'], effective_config)


    def test_legacy_file_path_still_works(self):
        """Test that legacy file path approach still works."""
        from src.fmf.chain.runner import run_chain_config
        
        # Create a config file
        config_data = {
            "project": "test-project",
            "artefacts_dir": str(self.temp_path / "artefacts"),
            "inference": {"provider": "azure_openai"}
        }
        
        config_path = self.temp_path / "fmf.yaml"
        import yaml
        with open(config_path, 'w') as f:
            yaml.safe_dump(config_data, f)
        
        # Create a simple chain config
        chain_config = {
            "name": "test_chain",
            "inputs": {"connector": "local_docs"},
            "steps": [
                {
                    "id": "test_step",
                    "prompt": "Test prompt",
                    "inputs": {"text": "test"},
                    "output": "result"
                }
            ],
            "outputs": []
        }
        
        # Mock the actual execution
        with patch('src.fmf.chain.runner._run_chain_loaded') as mock_run:
            mock_run.return_value = {"run_id": "test_run", "status": "success"}
            
            # Should still work with file path
            result = run_chain_config(
                chain_config,
                fmf_config_path=str(config_path)
            )
            
            # Should have called the runner with file path
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            self.assertEqual(call_args[1]['fmf_config_path'], str(config_path))

    def test_config_precedence_in_fluent_api(self):
        """Test that fluent API correctly applies precedence."""
        # Create base config
        base_config = FmfConfig(
            project="base-project",
            inference={"provider": "azure_openai", "temperature": 0.1}
        )
        
        # Create FMF and apply fluent overrides
        fmf = FMF.from_env(base_config)
        fmf = fmf.with_service("aws_bedrock")  # Should override provider
        
        # Get effective config
        effective_config = fmf._get_effective_config()
        
        # Fluent override should take precedence
        self.assertEqual(effective_config.inference["provider"], "aws_bedrock")
        
        # Base config should be preserved where not overridden
        self.assertEqual(effective_config.inference["temperature"], 0.1)
        self.assertEqual(effective_config.project, "base-project")

    def test_no_temp_files_created(self):
        """Test that no temporary files are created with config objects."""
        from src.fmf.chain.runner import run_chain_config
        
        # Create effective config
        effective_config = EffectiveConfig(
            project="test-project",
            artefacts_dir=str(self.temp_path / "artefacts")
        )
        
        # Create a simple chain config
        chain_config = {
            "name": "test_chain",
            "inputs": {"connector": "local_docs"},
            "steps": [
                {
                    "id": "test_step",
                    "prompt": "Test prompt",
                    "inputs": {"text": "test"},
                    "output": "result"
                }
            ],
            "outputs": []
        }
        
        # Mock the actual execution
        with patch('src.fmf.chain.runner._run_chain_loaded') as mock_run:
            mock_run.return_value = {"run_id": "test_run", "status": "success"}
            
            # Count files before
            files_before = len(list(self.temp_path.glob("*")))
            
            # Run with config object
            result = run_chain_config(
                chain_config,
                fmf_config=effective_config
            )
            
            # Count files after
            files_after = len(list(self.temp_path.glob("*")))
            
            # Should not have created any additional files
            self.assertEqual(files_before, files_after)


if __name__ == "__main__":
    unittest.main()
