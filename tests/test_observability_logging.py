"""Tests for FMF observability logging functionality."""

import json
import logging
import re
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.fmf.observability.logging import FMFLogger, get_logger, set_verbose


class TestFMFLogger(unittest.TestCase):
    """Test FMFLogger functionality."""
    
    def setUp(self):
        """Set up test logger."""
        self.logger = FMFLogger("test", verbose=True)
    
    def test_secret_redaction(self):
        """Test that secrets are properly redacted from log messages."""
        # Test various secret patterns
        test_cases = [
            ("api_key=secret123", "[REDACTED: Contains secrets]"),
            ("API_KEY: secret123", "[REDACTED: Contains secrets]"),
            ("password: secret123", "[REDACTED: Contains secrets]"),
            ("token=\"secret123\"", "[REDACTED: Contains secrets]"),
            ("openai_api_key=sk-1234567890", "[REDACTED: Contains secrets]"),
            ("bedrock_api_key=secret123", "[REDACTED: Contains secrets]"),
            ("azure_api_key=secret123", "[REDACTED: Contains secrets]"),
            ("normal_text with no secret", "normal_text with no secret"),
        ]
        
        for input_msg, expected in test_cases:
            with self.subTest(input_msg=input_msg):
                result = self.logger._redact_secrets(input_msg)
                self.assertEqual(result, expected)
    
    def test_dict_redaction(self):
        """Test that secrets are redacted from dictionaries."""
        test_dict = {
            "api_key": "secret123",
            "nested": {
                "password": "secret456",
                "normal_field": "not_secret"
            },
            "list_field": ["api_key=secret789", "normal_item"]
        }
        
        redacted = self.logger._redact_dict(test_dict)
        
        self.assertEqual(redacted["api_key"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["password"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["normal_field"], "not_secret")
        self.assertEqual(redacted["list_field"][0], "[REDACTED]")
        self.assertEqual(redacted["list_field"][1], "normal_item")
    
    def test_structured_logging(self):
        """Test that structured logging works correctly."""
        with patch.object(self.logger.logger, 'log') as mock_log:
            self.logger.info("Test message", key1="value1", key2="value2")
            
            # Verify log was called
            mock_log.assert_called_once()
            
            # Get the log call arguments
            call_args = mock_log.call_args
            level, message = call_args[0]
            
            # Verify level
            self.assertEqual(level, logging.INFO)
            
            # Verify message is JSON
            log_data = json.loads(message)
            self.assertEqual(log_data["message"], "Test message")
            self.assertEqual(log_data["level"], "INFO")
            self.assertIn("timestamp", log_data)
            self.assertEqual(log_data["context"]["key1"], "value1")
            self.assertEqual(log_data["context"]["key2"], "value2")
    
    def test_operation_context_manager(self):
        """Test operation context manager."""
        with patch.object(self.logger.logger, 'log') as mock_log:
            with self.logger.operation("test_operation", param1="value1"):
                pass
            
            # Should have start and completion logs
            self.assertEqual(mock_log.call_count, 2)
            
            # Check start log
            start_call = mock_log.call_args_list[0]
            start_data = json.loads(start_call[0][1])
            self.assertIn("Starting test_operation", start_data["message"])
            self.assertEqual(start_data["context"]["operation"], "test_operation")
            
            # Check completion log
            completion_call = mock_log.call_args_list[1]
            completion_data = json.loads(completion_call[0][1])
            self.assertIn("Completed test_operation", completion_data["message"])
            self.assertIn("duration_ms", completion_data["context"])
    
    def test_operation_context_manager_exception(self):
        """Test operation context manager with exception."""
        with patch.object(self.logger.logger, 'log') as mock_log:
            with self.assertRaises(ValueError):
                with self.logger.operation("test_operation", param1="value1"):
                    raise ValueError("Test error")
            
            # Should have start and error logs
            self.assertEqual(mock_log.call_count, 2)
            
            # Check error log
            error_call = mock_log.call_args_list[1]
            error_data = json.loads(error_call[0][1])
            self.assertIn("Operation test_operation failed", error_data["message"])
            self.assertEqual(error_data["context"]["error"], "Test error")
    
    def test_config_fingerprint(self):
        """Test config fingerprint logging."""
        with patch.object(self.logger.logger, 'log') as mock_log:
            config = {
                "api_key": "secret123",
                "normal_field": "value",
                "nested": {
                    "password": "secret456"
                }
            }
            
            self.logger.config_fingerprint(config)
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            log_data = json.loads(call_args[0][1])
            
            self.assertEqual(log_data["message"], "Configuration loaded")
            self.assertEqual(log_data["context"]["config_fingerprint"]["api_key"], "[REDACTED]")
            self.assertEqual(log_data["context"]["config_fingerprint"]["normal_field"], "value")
            self.assertEqual(log_data["context"]["config_fingerprint"]["nested"]["password"], "[REDACTED]")
    
    def test_connector_summary(self):
        """Test connector summary logging."""
        with patch.object(self.logger.logger, 'log') as mock_log:
            self.logger.connector_summary("test_connector", "s3", bucket="my-bucket")
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            log_data = json.loads(call_args[0][1])
            
            self.assertIn("Using connector: test_connector", log_data["message"])
            self.assertEqual(log_data["context"]["connector_name"], "test_connector")
            self.assertEqual(log_data["context"]["connector_type"], "s3")
            self.assertEqual(log_data["context"]["bucket"], "my-bucket")
    
    def test_processing_stats(self):
        """Test processing stats logging."""
        with patch.object(self.logger.logger, 'log') as mock_log:
            self.logger.processing_stats(100, 95, duration_ms=1500.5)
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            log_data = json.loads(call_args[0][1])
            
            self.assertIn("Processing complete: 100 processed, 95 returned", log_data["message"])
            self.assertEqual(log_data["context"]["records_processed"], 100)
            self.assertEqual(log_data["context"]["records_returned"], 95)
            self.assertEqual(log_data["context"]["duration_ms"], 1500.5)
    
    def test_timing(self):
        """Test timing logging."""
        with patch.object(self.logger.logger, 'log') as mock_log:
            self.logger.timing("test_operation", 2500.75, extra_info="test")
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            log_data = json.loads(call_args[0][1])
            
            self.assertIn("Timing: test_operation took 2500.8ms", log_data["message"])
            self.assertEqual(log_data["context"]["operation"], "test_operation")
            self.assertEqual(log_data["context"]["duration_ms"], 2500.75)
            self.assertEqual(log_data["context"]["extra_info"], "test")


class TestLoggingIntegration(unittest.TestCase):
    """Test logging integration with FMF."""
    
    def test_get_logger(self):
        """Test get_logger function."""
        logger = get_logger("test_logger", verbose=True)
        self.assertIsInstance(logger, FMFLogger)
        self.assertEqual(logger.logger.name, "test_logger")
    
    def test_set_verbose(self):
        """Test set_verbose function."""
        logger = get_logger("test_verbose")
        
        # Test setting verbose mode
        set_verbose(True)
        self.assertEqual(logger.logger.level, logging.DEBUG)
        
        # Test setting non-verbose mode
        set_verbose(False)
        self.assertEqual(logger.logger.level, logging.INFO)
    
    def test_global_logger_singleton(self):
        """Test that global logger is a singleton."""
        logger1 = get_logger("fmf")
        logger2 = get_logger("fmf")
        self.assertIs(logger1, logger2)


class TestLoggingInFMFClient(unittest.TestCase):
    """Test logging integration in FMF client."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create a minimal config file
        self.config_path = self.temp_path / "fmf.yaml"
        config_data = {
            "project": "test_project",
            "inference": {
                "provider": "azure_openai",
                "azure_openai": {
                    "endpoint": "https://test.openai.azure.com/",
                    "api_version": "2024-02-15-preview",
                    "deployment": "gpt-4o-mini"
                }
            },
            "artefacts_dir": str(self.temp_path / "artefacts")
        }
        
        import yaml
        with open(self.config_path, 'w') as f:
            yaml.safe_dump(config_data, f)
    
    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()
    
    def test_fmf_client_logging(self):
        """Test that FMF client logs configuration loading."""
        from src.fmf.sdk.client import FMF
        
        with patch('src.fmf.sdk.client.log_config_fingerprint') as mock_log_config:
            fmf = FMF(config_path=str(self.config_path))
            
            # Should have logged config fingerprint
            mock_log_config.assert_called_once()
            
            # Verify the logged config has secrets redacted
            call_args = mock_log_config.call_args[0][0]
            self.assertIn("inference", call_args)
            self.assertIn("azure_openai", call_args["inference"])
            # The endpoint should be present (not a secret)
            self.assertIn("endpoint", call_args["inference"]["azure_openai"])
    
    def test_fmf_client_logging_failure(self):
        """Test that FMF client logs config loading failures."""
        from src.fmf.sdk.client import FMF
        
        with patch('src.fmf.sdk.client.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Create FMF with non-existent config
            fmf = FMF(config_path="non_existent.yaml")
            
            # Should have logged warning about config loading failure
            mock_logger.warning.assert_called_once()
            self.assertIn("Failed to load config", mock_logger.warning.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
