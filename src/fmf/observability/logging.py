from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import IO, Any, Dict, Iterable


_RESERVED = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
}


class JsonFormatter(logging.Formatter):
    def __init__(self, *, utc: bool = True) -> None:
        super().__init__()
        self._utc = utc

    def usesTime(self) -> bool:  # pragma: no cover - compatibility
        return True

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003 - match base class
        message = record.getMessage()
        if self._utc:
            ts = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        else:
            ts = datetime.fromtimestamp(record.created).isoformat()

        payload: Dict[str, Any] = {
            "time": ts,
            "level": record.levelname,
            "name": record.name,
            "message": message,
        }

        # Include any non-reserved attributes as extras
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                try:
                    json.dumps(value)
                    # redact secrets by key name
                    lowered = key.lower()
                    if any(s in lowered for s in ("secret", "token", "api_key", "apikey", "password", "authorization", "auth")):
                        payload[key] = "****"
                    else:
                        payload[key] = value
                except (TypeError, ValueError):
                    payload[key] = repr(value)

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, separators=(",", ":"))


class HumanFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(fmt="%(levelname)s %(name)s - %(message)s")


def setup_logging(
    fmt: str | None = None,
    *,
    level: int | str = logging.INFO,
    stream: IO[str] | None = None,
) -> None:
    """Initialize root logger with JSON or human formatting.

    - fmt: 'json' | 'human' | None. If None, reads FMF_LOG_FORMAT env var, default 'human'.
    - level: logging level.
    - stream: When provided, logs are written to this stream; otherwise StreamHandler default (stderr).
    """

    resolved = (fmt or os.getenv("FMF_LOG_FORMAT") or "human").strip().lower()
    if resolved not in {"json", "human"}:
        resolved = "human"

    handler = logging.StreamHandler(stream=stream)
    if resolved == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(HumanFormatter())

    # Force replace existing handlers to ensure deterministic formatting in tests/CLI
    logging.basicConfig(level=level, handlers=[handler], force=True)


__all__ = ["setup_logging", "JsonFormatter", "HumanFormatter"]
