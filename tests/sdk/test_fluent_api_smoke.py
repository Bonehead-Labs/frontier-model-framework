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

    def test_run_inference_raises_not_implemented(self):
        """Test that run_inference raises NotImplementedError as expected."""
        fmf = FMF.from_env()
        
        with pytest.raises(NotImplementedError, match="run_inference is a stub"):
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
