"""Tests for the unified FMF CLI."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from fmf.cli import app, csv_analyse, text_to_json, images_analyse, keys_test


class TestFMFCLI:
    """Test the unified FMF CLI."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_app_help(self):
        """Test that the main app shows help."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Frontier Model Framework - Unified CLI for LLM workflows" in result.output
        assert "csv" in result.output
        assert "text" in result.output
        assert "images" in result.output

    def test_version_command(self):
        """Test version command."""
        result = self.runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        # Should show version string
        assert "0." in result.output

    def test_csv_analyse_help(self):
        """Test CSV analyse command help."""
        result = self.runner.invoke(app, ["csv", "analyse", "--help"])
        assert result.exit_code == 0
        assert "Analyze CSV files using FMF fluent API" in result.output
        assert "input_file" in result.output
        assert "text_col" in result.output
        assert "id_col" in result.output
        assert "prompt" in result.output

    def test_text_help(self):
        """Test text command help."""
        result = self.runner.invoke(app, ["text", "--help"])
        assert result.exit_code == 0
        assert "Convert text files to JSON using FMF fluent API" in result.output
        assert "input_pattern" in result.output
        assert "prompt" in result.output

    def test_images_help(self):
        """Test images command help."""
        result = self.runner.invoke(app, ["images", "--help"])
        assert result.exit_code == 0
        assert "Analyze images using FMF fluent API" in result.output
        assert "input_pattern" in result.output
        assert "prompt" in result.output

    @patch('fmf.cli.FMF')
    def test_csv_analyse_calls_fluent_api(self, mock_fmf_class):
        """Test that CSV analyse calls the fluent API correctly."""
        # Mock FMF instance
        mock_fmf = MagicMock()
        mock_fmf_class.from_env.return_value = mock_fmf
        mock_fmf.with_service.return_value = mock_fmf
        mock_fmf.with_rag.return_value = mock_fmf
        mock_fmf.with_response.return_value = mock_fmf
        mock_fmf.with_source.return_value = mock_fmf
        mock_fmf.csv_analyse.return_value = [{"id": "1", "text": "test"}]

        # Create a temporary CSV file
        csv_file = Path("test.csv")
        csv_file.write_text("ID,Comment\n1,Test comment")

        try:
            result = self.runner.invoke(app, [
                "csv", "analyse",
                "test.csv", "Comment", "ID", "Test prompt",
                "--service", "azure_openai",
                "--rag",
                "--response", "both"
            ])

            assert result.exit_code == 0
            assert "✓ Processed 1 records from test.csv" in result.output

            # Verify FMF was called correctly
            mock_fmf_class.from_env.assert_called_once_with("fmf.yaml")
            mock_fmf.with_service.assert_called_once_with("azure_openai")
            mock_fmf.with_rag.assert_called_once_with(enabled=True, pipeline="default_rag")
            mock_fmf.with_response.assert_called_once_with("both")
            mock_fmf.csv_analyse.assert_called_once()

        finally:
            # Clean up
            if csv_file.exists():
                csv_file.unlink()

    @patch('fmf.cli.FMF')
    def test_csv_analyse_dry_run(self, mock_fmf_class):
        """Test CSV analyse dry run mode."""
        # Create a temporary CSV file
        csv_file = Path("test.csv")
        csv_file.write_text("ID,Comment\n1,Test comment")

        try:
            result = self.runner.invoke(app, [
                "csv", "analyse",
                "test.csv", "Comment", "ID", "Test prompt",
                "--dry-run"
            ])

            assert result.exit_code == 0
            assert "Would analyze CSV: test.csv" in result.output
            assert "Text column: Comment" in result.output
            assert "ID column: ID" in result.output
            assert "Prompt: Test prompt" in result.output

            # Should not call FMF methods
            mock_fmf_class.from_env.assert_not_called()

        finally:
            # Clean up
            if csv_file.exists():
                csv_file.unlink()

    @patch('fmf.cli.FMF')
    def test_text_to_json_calls_fluent_api(self, mock_fmf_class):
        """Test that text to JSON calls the fluent API correctly."""
        # Mock FMF instance
        mock_fmf = MagicMock()
        mock_fmf_class.from_env.return_value = mock_fmf
        mock_fmf.with_service.return_value = mock_fmf
        mock_fmf.with_rag.return_value = mock_fmf
        mock_fmf.with_response.return_value = mock_fmf
        mock_fmf.with_source.return_value = mock_fmf
        mock_fmf.text_to_json.return_value = [{"id": "1", "text": "test"}]

        # Create a temporary text file
        text_file = Path("test.txt")
        text_file.write_text("Test content")

        try:
            result = self.runner.invoke(app, [
                "text",
                "test.txt", "Test prompt",
                "--service", "azure_openai",
                "--rag",
                "--response", "jsonl"
            ])

            assert result.exit_code == 0
            assert "✓ Processed 1 text chunks from test.txt" in result.output

            # Verify FMF was called correctly
            mock_fmf_class.from_env.assert_called_once_with("fmf.yaml")
            mock_fmf.with_service.assert_called_once_with("azure_openai")
            mock_fmf.with_rag.assert_called_once_with(enabled=True, pipeline="default_rag")
            mock_fmf.with_response.assert_called_once_with("jsonl")
            mock_fmf.text_to_json.assert_called_once()

        finally:
            # Clean up
            if text_file.exists():
                text_file.unlink()

    @patch('fmf.cli.FMF')
    def test_images_analyse_calls_fluent_api(self, mock_fmf_class):
        """Test that images analyse calls the fluent API correctly."""
        # Mock FMF instance
        mock_fmf = MagicMock()
        mock_fmf_class.from_env.return_value = mock_fmf
        mock_fmf.with_service.return_value = mock_fmf
        mock_fmf.with_rag.return_value = mock_fmf
        mock_fmf.with_response.return_value = mock_fmf
        mock_fmf.with_source.return_value = mock_fmf
        mock_fmf.images_analyse.return_value = [{"id": "1", "text": "test"}]

        # Create a temporary image file
        image_file = Path("test.png")
        image_file.write_bytes(b"fake image data")

        try:
            result = self.runner.invoke(app, [
                "images",
                "test.png", "Test prompt",
                "--service", "azure_openai",
                "--rag",
                "--response", "jsonl"
            ])

            assert result.exit_code == 0
            assert "✓ Processed 1 image chunks from test.png" in result.output

            # Verify FMF was called correctly
            mock_fmf_class.from_env.assert_called_once_with("fmf.yaml")
            mock_fmf.with_service.assert_called_once_with("azure_openai")
            mock_fmf.with_rag.assert_called_once_with(enabled=True, pipeline="default_rag")
            mock_fmf.with_response.assert_called_once_with("jsonl")
            mock_fmf.images_analyse.assert_called_once()

        finally:
            # Clean up
            if image_file.exists():
                image_file.unlink()

    def test_csv_analyse_missing_file(self):
        """Test CSV analyse with missing input file."""
        result = self.runner.invoke(app, [
            "csv", "analyse",
            "nonexistent.csv", "Comment", "ID", "Test prompt"
        ])

        assert result.exit_code == 1
        assert "Error: Input file 'nonexistent.csv' not found" in result.output

    def test_text_missing_file(self):
        """Test text command with missing input file."""
        result = self.runner.invoke(app, [
            "text",
            "nonexistent.txt", "Test prompt"
        ])

        assert result.exit_code == 1
        assert "Error: Input file 'nonexistent.txt' not found" in result.output

    def test_images_missing_file(self):
        """Test images command with missing input file."""
        result = self.runner.invoke(app, [
            "images",
            "nonexistent.png", "Test prompt"
        ])

        assert result.exit_code == 1
        assert "Error: Input file 'nonexistent.png' not found" in result.output

    @patch('fmf.cli.build_provider')
    @patch('fmf.cli.load_config')
    def test_keys_test_command(self, mock_load_config, mock_build_provider):
        """Test keys test command."""
        # Mock config and provider
        mock_config = MagicMock()
        mock_config.auth.provider = "env"
        mock_load_config.return_value = mock_config
        
        mock_provider = MagicMock()
        mock_provider.resolve.return_value = {"OPENAI_API_KEY": "test-key"}
        mock_build_provider.return_value = mock_provider

        result = self.runner.invoke(app, [
            "keys", "test",
            "OPENAI_API_KEY"
        ])

        assert result.exit_code == 0
        assert "OPENAI_API_KEY=**** OK" in result.output

    def test_keys_test_json_output(self):
        """Test keys test command with JSON output."""
        with patch('fmf.cli.build_provider') as mock_build_provider, \
             patch('fmf.cli.load_config') as mock_load_config:
            
            # Mock config and provider
            mock_config = MagicMock()
            mock_config.auth.provider = "env"
            mock_load_config.return_value = mock_config
            
            mock_provider = MagicMock()
            mock_provider.resolve.return_value = {"OPENAI_API_KEY": "test-key"}
            mock_build_provider.return_value = mock_provider

            result = self.runner.invoke(app, [
                "keys", "test",
                "OPENAI_API_KEY",
                "--json"
            ])

            assert result.exit_code == 0
            output_data = json.loads(result.output)
            assert "secrets" in output_data
            assert len(output_data["secrets"]) == 1
            assert output_data["secrets"][0]["name"] == "OPENAI_API_KEY"
            assert output_data["secrets"][0]["status"] == "OK"


class TestScriptDelegation:
    """Test that scripts properly delegate to the CLI."""

    def test_analyse_csv_script_delegation(self):
        """Test that analyse_csv.py delegates to the CLI."""
        script_path = Path("scripts/analyse_csv.py")
        
        # Test help delegation
        result = subprocess.run([
            sys.executable, str(script_path), "--help"
        ], capture_output=True, text=True, cwd=Path.cwd())
        
        # Should show deprecation warning and delegate to CLI
        assert "deprecated" in result.stderr.lower() or "deprecated" in result.stdout.lower()

    def test_text_to_json_script_delegation(self):
        """Test that text_to_json.py delegates to the CLI."""
        script_path = Path("scripts/text_to_json.py")
        
        # Test help delegation
        result = subprocess.run([
            sys.executable, str(script_path), "--help"
        ], capture_output=True, text=True, cwd=Path.cwd())
        
        # Should show deprecation warning and delegate to CLI
        assert "deprecated" in result.stderr.lower() or "deprecated" in result.stdout.lower()

    def test_images_multi_script_delegation(self):
        """Test that images_multi.py delegates to the CLI."""
        script_path = Path("scripts/images_multi.py")
        
        # Test help delegation
        result = subprocess.run([
            sys.executable, str(script_path), "--help"
        ], capture_output=True, text=True, cwd=Path.cwd())
        
        # Should show deprecation warning and delegate to CLI
        assert "deprecated" in result.stderr.lower() or "deprecated" in result.stdout.lower()
