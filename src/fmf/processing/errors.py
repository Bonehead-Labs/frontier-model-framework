class ProcessingError(Exception):
    """Raised when processing fails (unsupported format, parse error, missing deps)."""


__all__ = ["ProcessingError"]

