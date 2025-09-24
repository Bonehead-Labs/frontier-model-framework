#!/usr/bin/env python3
"""Tests for DataFrame analysis functionality."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from fmf.sdk import FMF, RunResult


class TestDataFrameAnalysis(unittest.TestCase):
    """Test DataFrame analysis functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.fmf = FMF(config_path="test_config.yaml")
        
        # Mock the effective config and chain runner
        self.fmf._get_effective_config = Mock()
        self.fmf._run_chain_with_effective_config = Mock()
        
        # Create sample DataFrame
        self.sample_df = pd.DataFrame({
            'id': [1, 2, 3],
            'comment': ['Great product!', 'Not bad', 'Terrible quality'],
            'rating': [5, 3, 1]
        })

    def test_dataframe_analyse_basic(self):
        """Test basic DataFrame analysis."""
        # Mock successful chain execution
        mock_result = {
            'run_id': 'test_run_123',
            'run_dir': '/tmp/test_run_123'
        }
        self.fmf._run_chain_with_effective_config.return_value = mock_result
        
        # Mock file operations
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=['analysis.csv', 'analysis.jsonl']), \
             patch('builtins.open', mock_open()):
            
            result = self.fmf.dataframe_analyse(
                df=self.sample_df,
                text_col="comment",
                id_col="id",
                prompt="Analyze sentiment"
            )
        
        # Verify chain was called with correct configuration
        self.fmf._run_chain_with_effective_config.assert_called_once()
        chain_config = self.fmf._run_chain_with_effective_config.call_args[0][0]
        
        self.assertEqual(chain_config['name'], 'dataframe-analyse')
        self.assertEqual(chain_config['inputs']['mode'], 'dataframe_rows')
        self.assertEqual(len(chain_config['inputs']['rows']), 3)
        
        # Verify row structure
        rows = chain_config['inputs']['rows']
        self.assertEqual(rows[0]['id'], '1')
        self.assertEqual(rows[0]['text'], 'Great product!')
        self.assertEqual(rows[0]['rating'], 5)

    def test_dataframe_analyse_no_id_col(self):
        """Test DataFrame analysis without ID column."""
        # Mock successful chain execution
        mock_result = {
            'run_id': 'test_run_123',
            'run_dir': '/tmp/test_run_123'
        }
        self.fmf._run_chain_with_effective_config.return_value = mock_result
        
        # Mock file operations
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=['analysis.csv']), \
             patch('builtins.open', mock_open()):
            
            result = self.fmf.dataframe_analyse(
                df=self.sample_df,
                text_col="comment",
                prompt="Analyze sentiment"
            )
        
        # Verify index was used as ID
        chain_config = self.fmf._run_chain_with_effective_config.call_args[0][0]
        rows = chain_config['inputs']['rows']
        self.assertEqual(rows[0]['id'], '0')  # Index 0
        self.assertEqual(rows[1]['id'], '1')  # Index 1

    def test_dataframe_analyse_missing_text_col(self):
        """Test DataFrame analysis with missing text column."""
        with self.assertRaises(ValueError) as context:
            self.fmf.dataframe_analyse(
                df=self.sample_df,
                text_col="nonexistent",
                prompt="Analyze sentiment"
            )
        
        self.assertIn("Text column 'nonexistent' not found", str(context.exception))

    def test_dataframe_analyse_missing_id_col(self):
        """Test DataFrame analysis with missing ID column."""
        with self.assertRaises(ValueError) as context:
            self.fmf.dataframe_analyse(
                df=self.sample_df,
                text_col="comment",
                id_col="nonexistent",
                prompt="Analyze sentiment"
            )
        
        self.assertIn("ID column 'nonexistent' not found", str(context.exception))

    def test_dataframe_analyse_not_dataframe(self):
        """Test DataFrame analysis with non-DataFrame input."""
        with self.assertRaises(ValueError) as context:
            self.fmf.dataframe_analyse(
                df="not a dataframe",
                text_col="comment",
                prompt="Analyze sentiment"
            )
        
        self.assertIn("df must be a pandas DataFrame", str(context.exception))

    def test_dataframe_analyse_pandas_import_error(self):
        """Test DataFrame analysis when pandas is not available."""
        with patch('builtins.__import__', side_effect=ImportError("No module named 'pandas'")):
            with self.assertRaises(ImportError) as context:
                self.fmf.dataframe_analyse(
                    df=self.sample_df,
                    text_col="comment",
                    prompt="Analyze sentiment"
                )
            
            self.assertIn("pandas is required for DataFrame analysis", str(context.exception))

    def test_dataframe_analyse_with_rag(self):
        """Test DataFrame analysis with RAG enabled."""
        # Mock successful chain execution
        mock_result = {
            'run_id': 'test_run_123',
            'run_dir': '/tmp/test_run_123'
        }
        self.fmf._run_chain_with_effective_config.return_value = mock_result
        
        # Mock file operations
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=['analysis.jsonl']), \
             patch('builtins.open', mock_open()):
            
            result = self.fmf.dataframe_analyse(
                df=self.sample_df,
                text_col="comment",
                id_col="id",
                prompt="Analyze sentiment",
                rag_options={"pipeline": "documents", "top_k_text": 3}
            )
        
        # Verify RAG configuration was included
        chain_config = self.fmf._run_chain_with_effective_config.call_args[0][0]
        step = chain_config['steps'][0]
        self.assertIn('rag', step)
        self.assertEqual(step['rag']['pipeline'], 'documents')
        self.assertEqual(step['rag']['top_k_text'], 3)

    def test_dataframe_analyse_error_handling(self):
        """Test DataFrame analysis error handling."""
        # Mock chain execution failure
        self.fmf._run_chain_with_effective_config.side_effect = Exception("Chain execution failed")
        
        result = self.fmf.dataframe_analyse(
            df=self.sample_df,
            text_col="comment",
            prompt="Analyze sentiment"
        )
        
        # Verify error result
        self.assertIsInstance(result, RunResult)
        self.assertFalse(result.success)
        self.assertIn("Chain execution failed", result.error)


def mock_open():
    """Mock file open for testing."""
    return MagicMock()


if __name__ == "__main__":
    unittest.main()
