"""Smoke tests for the fluent API to ensure basic contract validation."""

import pytest
from fmf.sdk import FMF


class TestFluentAPISmoke:
    """Test fluent API instantiation and method chaining."""

    def test_from_env_returns_fmf_instance(self):
        """Test that from_env returns an FMF instance."""
        fmf = FMF.from_env()
        assert isinstance(fmf, FMF)

    def test_from_env_with_path_returns_fmf_instance(self):
        """Test that from_env with path returns an FMF instance."""
        fmf = FMF.from_env("fmf.yaml")
        assert isinstance(fmf, FMF)

    def test_fluent_chaining_returns_fmf_instance(self):
        """Test that fluent methods return FMF instances for chaining."""
        fmf = FMF.from_env()
        
        # Test that each fluent method returns self
        result = (fmf
                 .with_service("azure_openai")
                 .with_rag(enabled=True, pipeline="documents")
                 .with_response("csv")
                 .with_source("local", root="./data"))
        
        assert isinstance(result, FMF)
        assert result is fmf  # Should be the same instance

    def test_fluent_methods_accept_expected_parameters(self):
        """Test that fluent methods accept their expected parameters."""
        fmf = FMF.from_env()
        
        # Test with_service
        result = fmf.with_service("aws_bedrock")
        assert isinstance(result, FMF)
        
        # Test with_rag
        result = fmf.with_rag(enabled=True)
        assert isinstance(result, FMF)
        
        result = fmf.with_rag(enabled=False, pipeline="test_pipeline")
        assert isinstance(result, FMF)
        
        # Test with_response
        for response_type in ["csv", "json", "text", "jsonl"]:
            result = fmf.with_response(response_type)
            assert isinstance(result, FMF)
        
        # Test with_source
        result = fmf.with_source("s3", bucket="test-bucket")
        assert isinstance(result, FMF)
        
        result = fmf.with_source("local", root="./data", include=["**/*.txt"])
        assert isinstance(result, FMF)

    def test_run_inference_requires_parameters(self):
        """Test that run_inference requires proper parameters."""
        fmf = FMF.from_env()
        
        # Should raise TypeError due to missing required parameters
        with pytest.raises(TypeError, match="missing.*required keyword-only arguments"):
            fmf.run_inference("csv", "analyse")

    def test_convenience_methods_exist(self):
        """Test that convenience methods exist and have correct signatures."""
        fmf = FMF.from_env()
        
        # Test that convenience methods exist
        assert hasattr(fmf, "csv_analyse")
        assert hasattr(fmf, "text_files")
        assert hasattr(fmf, "text_to_json")
        assert hasattr(fmf, "images_analyse")
        assert hasattr(fmf, "run_recipe")

    def test_text_to_json_wrapper(self):
        """Test that text_to_json is a proper wrapper around text_files."""
        fmf = FMF.from_env()
        
        # Both methods should exist and be callable
        assert callable(fmf.text_files)
        assert callable(fmf.text_to_json)
        
        # They should have similar signatures (text_to_json is a wrapper)
        import inspect
        
        text_files_sig = inspect.signature(fmf.text_files)
        text_to_json_sig = inspect.signature(fmf.text_to_json)
        
        # Both should have the same parameter names
        text_files_params = set(text_files_sig.parameters.keys())
        text_to_json_params = set(text_to_json_sig.parameters.keys())
        
        # text_to_json should have the same parameters as text_files
        assert text_files_params == text_to_json_params

    def test_fluent_api_preserves_existing_functionality(self):
        """Test that fluent API doesn't break existing functionality."""
        fmf = FMF.from_env()
        
        # Test that existing methods still work (even if they might fail at runtime)
        # We're just testing that the methods exist and are callable
        assert callable(fmf.csv_analyse)
        assert callable(fmf.text_files)
        assert callable(fmf.images_analyse)
        assert callable(fmf.run_recipe)
        
        # Test that we can still access internal attributes
        assert hasattr(fmf, "_config_path")
        assert hasattr(fmf, "_cfg")

    def test_type_hints_are_present(self):
        """Test that type hints are present for better IDE support."""
        import inspect
        
        fmf = FMF.from_env()
        
        # Check that fluent methods have return type hints
        with_service_sig = inspect.signature(fmf.with_service)
        assert with_service_sig.return_annotation == "FMF" or str(with_service_sig.return_annotation) == "'FMF'"
        
        with_rag_sig = inspect.signature(fmf.with_rag)
        assert with_rag_sig.return_annotation == "FMF" or str(with_rag_sig.return_annotation) == "'FMF'"
        
        with_response_sig = inspect.signature(fmf.with_response)
        assert with_response_sig.return_annotation == "FMF" or str(with_response_sig.return_annotation) == "'FMF'"
        
        with_source_sig = inspect.signature(fmf.with_source)
        assert with_source_sig.return_annotation == "FMF" or str(with_source_sig.return_annotation) == "'FMF'"

    def test_fluent_methods_set_internal_state(self):
        """Test that fluent methods actually set internal state."""
        fmf = FMF.from_env()
        
        # Test with_service
        fmf.with_service("azure_openai")
        assert fmf._service_override == "azure_openai"
        
        # Test with_rag
        fmf.with_rag(enabled=True, pipeline="test_pipeline")
        assert fmf._rag_override is not None
        assert fmf._rag_override["pipelines"][0]["name"] == "test_pipeline"
        
        # Test with_response
        fmf.with_response("csv")
        assert fmf._response_format == "csv"
        
        # Test with_source
        fmf.with_source("local", root="./test_data")
        assert fmf._source_connector == "local_docs"
        assert fmf._source_kwargs["type"] == "local"
        assert fmf._source_kwargs["root"] == "./test_data"

    def test_effective_config_includes_fluent_overrides(self):
        """Test that _get_effective_config includes fluent overrides."""
        fmf = FMF.from_env()
        
        # Set up fluent configuration
        fmf.with_service("aws_bedrock")
        fmf.with_rag(enabled=True, pipeline="test_rag")
        fmf.with_response("jsonl")
        fmf.with_source("s3", bucket="test-bucket", region="us-west-2")
        
        # Get effective config
        effective = fmf._get_effective_config()
        
        # Verify fluent overrides are included
        assert effective["inference"]["provider"] == "aws_bedrock"
        assert "rag" in effective
        assert effective["rag"]["pipelines"][0]["name"] == "test_rag"
        
        # Verify connector was added
        connectors = effective.get("connectors", [])
        s3_connector = next((c for c in connectors if c.get("name") == "s3_docs"), None)
        assert s3_connector is not None
        assert s3_connector["type"] == "s3"
        assert s3_connector["bucket"] == "test-bucket"
        assert s3_connector["region"] == "us-west-2"

    def test_run_inference_delegates_to_existing_methods(self):
        """Test that run_inference delegates to existing methods."""
        fmf = FMF.from_env()
        
        # Test that run_inference calls the right methods by checking they exist and are callable
        assert callable(fmf.csv_analyse)
        assert callable(fmf.text_to_json)
        assert callable(fmf.images_analyse)
        
        # Test that run_inference validates method names
        with pytest.raises(ValueError, match="Unknown CSV method"):
            fmf.run_inference("csv", "invalid_method")
        
        with pytest.raises(ValueError, match="Unknown text method"):
            fmf.run_inference("text", "invalid_method")
        
        with pytest.raises(ValueError, match="Unknown images method"):
            fmf.run_inference("images", "invalid_method")
        
        with pytest.raises(ValueError, match="Unknown inference kind"):
            fmf.run_inference("invalid_kind", "analyse")

    def test_run_inference_applies_fluent_configuration(self):
        """Test that run_inference applies fluent configuration to kwargs."""
        fmf = (FMF.from_env()
               .with_source("local", root="./test_data")
               .with_response("csv")
               .with_rag(enabled=True, pipeline="test_rag"))
        
        # Mock the csv_analyse method to capture kwargs
        original_csv_analyse = fmf.csv_analyse
        captured_kwargs = {}
        
        def mock_csv_analyse(**kwargs):
            captured_kwargs.update(kwargs)
            raise Exception("Mocked for testing")
        
        fmf.csv_analyse = mock_csv_analyse
        
        try:
            fmf.run_inference("csv", "analyse", input="test.csv", text_col="text", id_col="id", prompt="test")
        except Exception:
            pass  # Expected due to mocking
        
        # Verify fluent configuration was applied
        assert captured_kwargs.get("connector") == "local_docs"
        assert "save_csv" in captured_kwargs
        assert captured_kwargs.get("rag_options") is not None
        assert captured_kwargs["rag_options"]["pipeline"] == "test_rag"
        
        # Restore original method
        fmf.csv_analyse = original_csv_analyse

    def test_fluent_api_preserves_backward_compatibility(self):
        """Test that fluent API doesn't break existing functionality."""
        fmf = FMF.from_env()
        
        # Test that existing methods still work
        assert callable(fmf.csv_analyse)
        assert callable(fmf.text_files)
        assert callable(fmf.images_analyse)
        assert callable(fmf.run_recipe)
        
        # Test that we can still access internal attributes
        assert hasattr(fmf, "_config_path")
        assert hasattr(fmf, "_cfg")
        
        # Test that fluent state is initialized
        assert hasattr(fmf, "_service_override")
        assert hasattr(fmf, "_rag_override")
        assert hasattr(fmf, "_response_format")
        assert hasattr(fmf, "_source_connector")
        assert hasattr(fmf, "_source_kwargs")
