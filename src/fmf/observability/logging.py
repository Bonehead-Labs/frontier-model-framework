"""Structured logging for FMF operations."""

import json
import logging
import re
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional, Union
from pathlib import Path

# Configure the root logger for FMF
logger = logging.getLogger("fmf")
logger.setLevel(logging.INFO)

# Prevent duplicate handlers
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class FMFLogger:
    """Structured logger for FMF operations with secret redaction."""
    
    def __init__(self, name: str = "fmf", verbose: bool = False):
        self.logger = logging.getLogger(name)
        if verbose:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        
        # Secret patterns to redact (quoted patterns first to avoid conflicts)
        self.secret_patterns = [
            r'(?i)(api[_-]?key|secret|password|token|auth[_-]?key)\s*=\s*"([^"]+)"',
            r'(?i)(api[_-]?key|secret|password|token|auth[_-]?key)\s*:\s*"([^"]+)"',
            r'(?i)(api[_-]?key|secret|password|token|auth[_-]?key)\s*=\s*([^\s]+)',
            r'(?i)(api[_-]?key|secret|password|token|auth[_-]?key)\s*:\s*([^\s]+)',
            r'(?i)(openai[_-]?api[_-]?key|bedrock[_-]?api[_-]?key|azure[_-]?api[_-]?key)\s*=\s*"([^"]+)"',
            r'(?i)(openai[_-]?api[_-]?key|bedrock[_-]?api[_-]?key|azure[_-]?api[_-]?key)\s*:\s*"([^"]+)"',
            r'(?i)(openai[_-]?api[_-]?key|bedrock[_-]?api[_-]?key|azure[_-]?api[_-]?key)\s*=\s*([^\s]+)',
            r'(?i)(openai[_-]?api[_-]?key|bedrock[_-]?api[_-]?key|azure[_-]?api[_-]?key)\s*:\s*([^\s]+)',
        ]
        
        # Simple key-value patterns for dictionary redaction
        self.secret_keys = [
            'api_key', 'api-key', 'API_KEY', 'API-KEY',
            'secret', 'SECRET', 'password', 'PASSWORD',
            'token', 'TOKEN', 'auth_key', 'AUTH_KEY',
            'openai_api_key', 'OPENAI_API_KEY',
            'bedrock_api_key', 'BEDROCK_API_KEY',
            'azure_api_key', 'AZURE_API_KEY',
        ]
    
    def _redact_secrets(self, message: str) -> str:
        """Redact secrets from log messages."""
        # Check if message contains any secrets - if so, don't log it
        for pattern in self.secret_patterns:
            if re.search(pattern, message, flags=re.IGNORECASE):
                return "[REDACTED: Contains secrets]"
        return message
    
    def _log_structured(self, level: int, message: str, **kwargs: Any) -> None:
        """Log a structured message with optional context."""
        # Redact secrets from the message
        safe_message = self._redact_secrets(message)
        
        # Create structured log entry
        log_entry = {
            "message": safe_message,
            "timestamp": time.time(),
            "level": logging.getLevelName(level),
        }
        
        # Add context if provided
        if kwargs:
            # Redact secrets from context
            safe_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    safe_kwargs[key] = self._redact_secrets(value)
                elif isinstance(value, dict):
                    safe_kwargs[key] = self._redact_dict(value)
                else:
                    safe_kwargs[key] = value
            log_entry["context"] = safe_kwargs
        
        # Log as JSON for structured logging
        self.logger.log(level, json.dumps(log_entry, default=str))
    
    def _redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact secrets from a dictionary."""
        redacted = {}
        for key, value in data.items():
            if isinstance(value, str):
                # Check if the key itself indicates a secret
                if any(secret_key.lower() in key.lower() for secret_key in self.secret_keys):
                    redacted[key] = "[REDACTED]"
                else:
                    # Check if the value contains secrets
                    if any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in self.secret_patterns):
                        redacted[key] = "[REDACTED]"
                    else:
                        redacted[key] = value
            elif isinstance(value, dict):
                redacted[key] = self._redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [
                    "[REDACTED]" if isinstance(item, str) and any(re.search(pattern, item, flags=re.IGNORECASE) for pattern in self.secret_patterns) else item
                    for item in value
                ]
            else:
                redacted[key] = value
        return redacted
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message."""
        self._log_structured(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message."""
        self._log_structured(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message."""
        self._log_structured(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message."""
        self._log_structured(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message."""
        self._log_structured(logging.CRITICAL, message, **kwargs)
    
    @contextmanager
    def operation(self, operation_name: str, **context: Any):
        """Context manager for logging operation start/stop."""
        start_time = time.time()
        self.info(f"Starting {operation_name}", operation=operation_name, **context)
        
        try:
            yield self
        except Exception as e:
            duration = time.time() - start_time
            self.error(
                f"Operation {operation_name} failed",
                operation=operation_name,
                error=str(e),
                duration_ms=duration * 1000,
                **context
            )
            raise
        else:
            duration = time.time() - start_time
            self.info(
                f"Completed {operation_name}",
                operation=operation_name,
                duration_ms=duration * 1000,
                **context
            )
    
    def config_fingerprint(self, config: Dict[str, Any]) -> None:
        """Log configuration fingerprint with secrets redacted."""
        safe_config = self._redact_dict(config)
        self.info("Configuration loaded", config_fingerprint=safe_config)
    
    def connector_summary(self, connector_name: str, connector_type: str, **details: Any) -> None:
        """Log connector summary information."""
        self.info(
            f"Using connector: {connector_name}",
            connector_name=connector_name,
            connector_type=connector_type,
            **details
        )
    
    def processing_stats(self, records_processed: int, records_returned: int, **stats: Any) -> None:
        """Log processing statistics."""
        self.info(
            f"Processing complete: {records_processed} processed, {records_returned} returned",
            records_processed=records_processed,
            records_returned=records_returned,
            **stats
        )
    
    def timing(self, operation: str, duration_ms: float, **context: Any) -> None:
        """Log timing information."""
        self.info(
            f"Timing: {operation} took {duration_ms:.1f}ms",
            operation=operation,
            duration_ms=duration_ms,
            **context
        )


# Global logger instance
_fmf_logger: Optional[FMFLogger] = None


def get_logger(name: str = "fmf", verbose: bool = False) -> FMFLogger:
    """Get or create the global FMF logger."""
    global _fmf_logger
    if _fmf_logger is None:
        _fmf_logger = FMFLogger(name, verbose)
    return _fmf_logger


def set_verbose(verbose: bool) -> None:
    """Set verbose logging mode."""
    logger = get_logger()
    if verbose:
        logger.logger.setLevel(logging.DEBUG)
    else:
        logger.logger.setLevel(logging.INFO)


def log_config_fingerprint(config: Dict[str, Any]) -> None:
    """Log configuration fingerprint."""
    get_logger().config_fingerprint(config)


def log_connector_summary(connector_name: str, connector_type: str, **details: Any) -> None:
    """Log connector summary."""
    get_logger().connector_summary(connector_name, connector_type, **details)


def log_processing_stats(records_processed: int, records_returned: int, **stats: Any) -> None:
    """Log processing statistics."""
    get_logger().processing_stats(records_processed, records_returned, **stats)


def log_timing(operation: str, duration_ms: float, **context: Any) -> None:
    """Log timing information."""
    get_logger().timing(operation, duration_ms, **context)