from __future__ import annotations

import re
from html import unescape


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def html_to_text(html: str) -> str:
    # crude HTML to text: remove tags and unescape entities
    return unescape(_TAG_RE.sub(" ", html)).strip()


def normalize_text(text: str, *, normalize_whitespace: bool = True) -> str:
    if not normalize_whitespace:
        return text
    return _WS_RE.sub(" ", text).strip()


__all__ = ["html_to_text", "normalize_text"]

