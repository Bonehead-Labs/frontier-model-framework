"""Tests for FMF SDK ergonomics features."""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.fmf.sdk.client import FMF
from src.fmf.sdk.types import RunResult, SourceConfig
from src.fmf.config.models import FmfConfig


class TestFMFErgonomics(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.tempdir.name)
        
        # Create a minimal config
        self.base_config = FmfConfig(
            project="test-project",
            artefacts_dir=str(self.temp_path / "artefacts")
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_defaults_method(self):
        """Test the .defaults() method for setting common options."""
        fmf = FMF.from_env(self.base_config)
        
        # Test setting multiple defaults at once
        fmf_with_defaults = fmf.defaults(
            service="azure_openai",
            rag=True,
            response="csv"
        )
        
        # Should return self for chaining
        self.assertIs(fmf_with_defaults, fmf)
        
        # Should have applied the defaults
        self.assertEqual(fmf._service_override, "azure_openai")
        self.assertTrue(fmf._rag_override["enabled"])
        self.assertEqual(fmf._response_format, "csv")

    def test_defaults_with_rag_config(self):
        """Test .defaults() with RAG configuration dict."""
        fmf = FMF.from_env(self.base_config)
        
        fmf.defaults(
            rag={"pipeline": "documents", "top_k_text": 5}
        )
        
        # Should have applied RAG config
        self.assertTrue(fmf._rag_override["enabled"])
        self.assertEqual(fmf._rag_override["pipeline"], "documents")

    def test_defaults_with_source_config(self):
        """Test .defaults() with source configuration."""
        fmf = FMF.from_env(self.base_config)
        
        fmf.defaults(
            source={"type": "s3", "bucket": "test-bucket", "prefix": "data/"}
        )
        
        # Should have applied source config
        self.assertEqual(fmf._source_connector, "s3")
        self.assertIn("bucket", fmf._source_kwargs)

    def test_context_manager(self):
        """Test context manager support."""
        fmf = FMF.from_env(self.base_config)
        
        # Should work as context manager
        with fmf as context_fmf:
            self.assertIs(context_fmf, fmf)
            # Should be able to call methods
            self.assertIsNotNone(context_fmf._get_effective_config())

    def test_from_sharepoint(self):
        """Test SharePoint source helper."""
        fmf = FMF.from_env(self.base_config)
        
        result = fmf.from_sharepoint(
            site_url="https://contoso.sharepoint.com/sites/test",
            list_name="Documents",
            drive="Documents",
            root_path="Policies"
        )
        
        # Should return self for chaining
        self.assertIs(result, fmf)
        
        # Should have configured SharePoint source
        self.assertEqual(fmf._source_connector, "sharepoint")
        self.assertIn("site_url", fmf._source_kwargs)
        self.assertEqual(fmf._source_kwargs["site_url"], "https://contoso.sharepoint.com/sites/test")

    def test_from_s3(self):
        """Test S3 source helper."""
        fmf = FMF.from_env(self.base_config)
        
        result = fmf.from_s3(
            bucket="test-bucket",
            prefix="data/",
            region="us-east-1",
            kms_required=True
        )
        
        # Should return self for chaining
        self.assertIs(result, fmf)
        
        # Should have configured S3 source
        self.assertEqual(fmf._source_connector, "s3")
        self.assertIn("bucket", fmf._source_kwargs)
        self.assertEqual(fmf._source_kwargs["bucket"], "test-bucket")
        self.assertEqual(fmf._source_kwargs["region"], "us-east-1")

    def test_from_local(self):
        """Test local filesystem source helper."""
        fmf = FMF.from_env(self.base_config)
        
        result = fmf.from_local(
            root_path="./data",
            include_patterns=["**/*.md", "**/*.txt"],
            exclude_patterns=["**/.git/**"]
        )
        
        # Should return self for chaining
        self.assertIs(result, fmf)
        
        # Should have configured local source
        self.assertEqual(fmf._source_connector, "local")
        self.assertIn("root", fmf._source_kwargs)
        self.assertEqual(fmf._source_kwargs["root"], "./data")

    def test_fluent_chaining(self):
        """Test fluent method chaining with new ergonomics."""
        fmf = (FMF.from_env(self.base_config)
               .defaults(service="azure_openai", rag=True)
               .from_s3("test-bucket", "data/")
               .with_response("csv"))
        
        # Should have all configurations applied
        self.assertEqual(fmf._service_override, "azure_openai")
        self.assertTrue(fmf._rag_override["enabled"])
        self.assertEqual(fmf._source_connector, "s3")
        self.assertEqual(fmf._response_format, "csv")

    def test_run_result_creation(self):
        """Test RunResult creation and properties."""
        # Mock chain execution
        with patch.object(FMF, '_run_chain_with_effective_config') as mock_run:
            mock_run.return_value = {
                "run_id": "test_run_123",
                "run_dir": str(self.temp_path / "artefacts" / "test_run_123")
            }
            
            # Create artefacts directory and mock output file
            run_dir = self.temp_path / "artefacts" / "test_run_123"
            run_dir.mkdir(parents=True, exist_ok=True)
            
            # Create mock output files
            (run_dir / "outputs.jsonl").write_text('{"id": 1, "text": "test"}\n{"id": 2, "text": "test2"}\n')
            (run_dir / "analysis.csv").write_text("id,text\n1,test\n2,test2\n")
            
            fmf = FMF.from_env(self.base_config)
            fmf._service_override = "azure_openai"
            fmf._rag_override = {"enabled": True, "pipeline": "test_rag"}
            fmf._source_connector = "s3"
            
            # Mock the _read_jsonl function
            with patch('src.fmf.sdk.client._read_jsonl') as mock_read:
                mock_read.return_value = [{"id": 1, "text": "test"}, {"id": 2, "text": "test2"}]
                
                result = fmf.csv_analyse(
                    input="test.csv",
                    text_col="Comment",
                    id_col="ID",
                    prompt="Test prompt",
                    return_records=True
                )
            
            # Should return RunResult
            self.assertIsInstance(result, RunResult)
            self.assertTrue(result.success)
            self.assertEqual(result.run_id, "test_run_123")
            self.assertEqual(result.records_processed, 2)
            self.assertEqual(result.records_returned, 2)
            self.assertEqual(result.service_used, "azure_openai")
            self.assertTrue(result.rag_enabled)
            self.assertEqual(result.rag_pipeline, "test_rag")
            self.assertEqual(result.source_connector, "s3")
            self.assertIsNotNone(result.duration_ms)
            self.assertTrue(result.has_outputs)

    def test_run_result_error_handling(self):
        """Test RunResult creation with errors."""
        # Mock chain execution to raise exception
        with patch.object(FMF, '_run_chain_with_effective_config') as mock_run:
            mock_run.side_effect = Exception("Test error")
            
            fmf = FMF.from_env(self.base_config)
            
            result = fmf.csv_analyse(
                input="test.csv",
                text_col="Comment",
                id_col="ID",
                prompt="Test prompt"
            )
            
            # Should return failed RunResult
            self.assertIsInstance(result, RunResult)
            self.assertFalse(result.success)
            self.assertEqual(result.error, "Test error")
            self.assertIn("exception_type", result.error_details)

    def test_run_result_string_representation(self):
        """Test RunResult string representation."""
        result = RunResult(
            success=True,
            run_id="test_123",
            records_processed=5,
            records_returned=5,
            duration_ms=1500.0,
            service_used="azure_openai",
            rag_enabled=True,
            rag_pipeline="test_rag",
            csv_path="/path/to/output.csv"
        )
        
        str_repr = str(result)
        
        # Should contain key information
        self.assertIn("✅ Success", str_repr)
        self.assertIn("test_123", str_repr)
        self.assertIn("5 processed", str_repr)
        self.assertIn("1500.0ms", str_repr)
        self.assertIn("azure_openai", str_repr)

    def test_source_config_helpers(self):
        """Test SourceConfig helper methods."""
        # Test SharePoint config
        sp_config = SourceConfig.for_sharepoint(
            site_url="https://contoso.sharepoint.com/sites/test",
            list_name="Documents",
            drive="Documents",
            root_path="Policies"
        )
        
        self.assertEqual(sp_config.connector_type, "sharepoint")
        self.assertEqual(sp_config.name, "sharepoint_Documents")
        self.assertIn("site_url", sp_config.config)
        
        # Test S3 config
        s3_config = SourceConfig.for_s3(
            bucket="test-bucket",
            prefix="data/",
            region="us-east-1"
        )
        
        self.assertEqual(s3_config.connector_type, "s3")
        self.assertEqual(s3_config.name, "s3_test-bucket_data_")
        self.assertIn("bucket", s3_config.config)
        
        # Test local config
        local_config = SourceConfig.for_local(
            root_path="./data",
            include_patterns=["**/*.md"]
        )
        
        self.assertEqual(local_config.connector_type, "local")
        self.assertEqual(local_config.name, "local_data")
        self.assertIn("root", local_config.config)

    def test_context_manager_with_actual_usage(self):
        """Test context manager with actual method calls."""
        # Mock the chain execution
        with patch.object(FMF, '_run_chain_with_effective_config') as mock_run:
            mock_run.return_value = {
                "run_id": "context_test_123",
                "run_dir": str(self.temp_path / "artefacts" / "context_test_123")
            }
            
            # Create mock output
            run_dir = self.temp_path / "artefacts" / "context_test_123"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "outputs.jsonl").write_text('{"id": 1, "text": "test"}\n')
            
            with patch('src.fmf.sdk.client._read_jsonl') as mock_read:
                mock_read.return_value = [{"id": 1, "text": "test"}]
                
                with FMF.from_env(self.base_config).defaults(service="azure_openai") as fmf:
                    result = fmf.csv_analyse(
                        input="test.csv",
                        text_col="Comment",
                        id_col="ID",
                        prompt="Test prompt"
                    )
                
                # Should work within context
                self.assertIsInstance(result, RunResult)
                self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
