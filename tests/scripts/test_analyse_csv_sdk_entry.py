"""Tests for the analyse_csv.py script using fluent API."""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os
from pathlib import Path

# Add scripts directory to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

import analyse_csv


class TestAnalyseCsvSDKEntry:
    """Test the analyse_csv.py script entry point."""

    def test_help_shows_fluent_api_arguments(self):
        """Test that --help shows SDK-centric help text."""
        with patch('sys.argv', ['analyse_csv.py', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                analyse_csv.main()
            # Should exit with 0 for help
            assert exc_info.value.code == 0

    def test_requires_input_arguments(self):
        """Test that script requires input arguments."""
        with patch('sys.argv', ['analyse_csv.py']):
            with pytest.raises(SystemExit) as exc_info:
                analyse_csv.main()
            # Should exit with 2 for missing required arguments
            assert exc_info.value.code == 2

    def test_fluent_api_path_called_with_valid_args(self):
        """Test that fluent API path is called with valid arguments."""
        with patch('sys.argv', [
            'analyse_csv.py',
            '--input', 'test.csv',
            '--text-col', 'Comment',
            '--id-col', 'ID',
            '--prompt', 'Test prompt'
        ]):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('analyse_csv.FMF') as mock_fmf_class:
                    # Mock FMF instance and its methods
                    mock_fmf = MagicMock()
                    mock_fmf_class.from_env.return_value = mock_fmf
                    mock_fmf.with_service.return_value = mock_fmf
                    mock_fmf.with_rag.return_value = mock_fmf
                    mock_fmf.with_response.return_value = mock_fmf
                    mock_fmf.with_source.return_value = mock_fmf
                    mock_fmf.csv_analyse.return_value = [{"id": "1", "text": "test"}]
                    
                    result = analyse_csv.main()
                    
                    # Should call FMF.from_env
                    mock_fmf_class.from_env.assert_called_once_with("fmf.yaml")
                    
                    # Should call csv_analyse with correct arguments
                    mock_fmf.csv_analyse.assert_called_once()
                    call_args = mock_fmf.csv_analyse.call_args
                    assert call_args[1]['input'] == 'test.csv'
                    assert call_args[1]['text_col'] == 'Comment'
                    assert call_args[1]['id_col'] == 'ID'
                    assert call_args[1]['prompt'] == 'Test prompt'
                    assert call_args[1]['return_records'] is True
                    
                    # Should return success
                    assert result == 0

    def test_fluent_api_with_service_configuration(self):
        """Test that service configuration is applied."""
        with patch('sys.argv', [
            'analyse_csv.py',
            '--input', 'test.csv',
            '--text-col', 'Comment',
            '--id-col', 'ID',
            '--prompt', 'Test prompt',
            '--service', 'azure_openai'
        ]):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('analyse_csv.FMF') as mock_fmf_class:
                    mock_fmf = MagicMock()
                    mock_fmf_class.from_env.return_value = mock_fmf
                    mock_fmf.with_service.return_value = mock_fmf
                    mock_fmf.with_rag.return_value = mock_fmf
                    mock_fmf.with_response.return_value = mock_fmf
                    mock_fmf.with_source.return_value = mock_fmf
                    mock_fmf.csv_analyse.return_value = []
                    
                    analyse_csv.main()
                    
                    # Should call with_service
                    mock_fmf.with_service.assert_called_once_with('azure_openai')

    def test_fluent_api_with_rag_configuration(self):
        """Test that RAG configuration is applied."""
        with patch('sys.argv', [
            'analyse_csv.py',
            '--input', 'test.csv',
            '--text-col', 'Comment',
            '--id-col', 'ID',
            '--prompt', 'Test prompt',
            '--enable-rag',
            '--rag-pipeline', 'test_pipeline'
        ]):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('analyse_csv.FMF') as mock_fmf_class:
                    mock_fmf = MagicMock()
                    mock_fmf_class.from_env.return_value = mock_fmf
                    mock_fmf.with_service.return_value = mock_fmf
                    mock_fmf.with_rag.return_value = mock_fmf
                    mock_fmf.with_response.return_value = mock_fmf
                    mock_fmf.with_source.return_value = mock_fmf
                    mock_fmf.csv_analyse.return_value = []
                    
                    analyse_csv.main()
                    
                    # Should call with_rag
                    mock_fmf.with_rag.assert_called_once_with(enabled=True, pipeline='test_pipeline')

    def test_fluent_api_with_response_format(self):
        """Test that response format configuration is applied."""
        with patch('sys.argv', [
            'analyse_csv.py',
            '--input', 'test.csv',
            '--text-col', 'Comment',
            '--id-col', 'ID',
            '--prompt', 'Test prompt',
            '--output-format', 'csv'
        ]):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('analyse_csv.FMF') as mock_fmf_class:
                    mock_fmf = MagicMock()
                    mock_fmf_class.from_env.return_value = mock_fmf
                    mock_fmf.with_service.return_value = mock_fmf
                    mock_fmf.with_rag.return_value = mock_fmf
                    mock_fmf.with_response.return_value = mock_fmf
                    mock_fmf.with_source.return_value = mock_fmf
                    mock_fmf.csv_analyse.return_value = []
                    
                    analyse_csv.main()
                    
                    # Should call with_response
                    mock_fmf.with_response.assert_called_once_with('csv')


    def test_missing_input_file_returns_error(self):
        """Test that missing input file returns error."""
        with patch('sys.argv', [
            'analyse_csv.py',
            '--input', 'nonexistent.csv',
            '--text-col', 'Comment',
            '--id-col', 'ID',
            '--prompt', 'Test prompt'
        ]):
            with patch('pathlib.Path.exists', return_value=False):
                result = analyse_csv.main()
                assert result == 1

    def test_json_output_format(self):
        """Test JSON output format."""
        with patch('sys.argv', [
            'analyse_csv.py',
            '--input', 'test.csv',
            '--text-col', 'Comment',
            '--id-col', 'ID',
            '--prompt', 'Test prompt',
            '--json'
        ]):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('analyse_csv.FMF') as mock_fmf_class:
                    mock_fmf = MagicMock()
                    mock_fmf_class.from_env.return_value = mock_fmf
                    mock_fmf.with_service.return_value = mock_fmf
                    mock_fmf.with_rag.return_value = mock_fmf
                    mock_fmf.with_response.return_value = mock_fmf
                    mock_fmf.with_source.return_value = mock_fmf
                    mock_fmf.csv_analyse.return_value = [{"id": "1", "text": "test"}]
                    
                    with patch('builtins.print') as mock_print:
                        result = analyse_csv.main()
                        
                        # Should print JSON output
                        mock_print.assert_called()
                        json_output = mock_print.call_args[0][0]
                        assert '"status": "success"' in json_output
                        assert '"records_processed": 1' in json_output
                        assert result == 0

    def test_error_handling_with_json_output(self):
        """Test error handling with JSON output."""
        with patch('sys.argv', [
            'analyse_csv.py',
            '--input', 'test.csv',
            '--text-col', 'Comment',
            '--id-col', 'ID',
            '--prompt', 'Test prompt',
            '--json'
        ]):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('analyse_csv.FMF') as mock_fmf_class:
                    mock_fmf = MagicMock()
                    mock_fmf_class.from_env.return_value = mock_fmf
                    mock_fmf.with_service.return_value = mock_fmf
                    mock_fmf.with_rag.return_value = mock_fmf
                    mock_fmf.with_response.return_value = mock_fmf
                    mock_fmf.with_source.return_value = mock_fmf
                    mock_fmf.csv_analyse.side_effect = Exception("Test error")
                    
                    with patch('builtins.print') as mock_print:
                        result = analyse_csv.main()
                        
                        # Should print error JSON
                        mock_print.assert_called()
                        json_output = mock_print.call_args[0][0]
                        assert '"status": "error"' in json_output
                        assert '"error": "Test error"' in json_output
                        assert result == 1
