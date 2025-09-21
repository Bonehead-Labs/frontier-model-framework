from __future__ import annotations

from typing import Optional


class FmfError(Exception):
    """Base exception for the Frontier Model Framework."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message


class ConfigError(FmfError):
    pass


class AuthError(FmfError):
    pass


class ConnectorError(FmfError):
    pass


class ProcessingError(FmfError):
    pass


class InferenceError(FmfError):
    def __init__(self, message: str, *, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ProviderError(InferenceError):
    """Raised when a provider capability (e.g. streaming) is unavailable."""


class ExportError(FmfError):
    pass


EXIT_CODES: dict[type[FmfError], int] = {
    FmfError: 1,
    ConfigError: 2,
    AuthError: 3,
    ConnectorError: 4,
    ProcessingError: 5,
    InferenceError: 6,
    ProviderError: 6,
    ExportError: 7,
}


def get_exit_code(exc: FmfError) -> int:
    for cls in exc.__class__.__mro__:
        if cls in EXIT_CODES:
            return EXIT_CODES[cls]  # type: ignore[index]
    return 1


__all__ = [
    "FmfError",
    "ConfigError",
    "AuthError",
    "ConnectorError",
    "ProcessingError",
    "InferenceError",
    "ProviderError",
    "ExportError",
    "EXIT_CODES",
    "get_exit_code",
]
