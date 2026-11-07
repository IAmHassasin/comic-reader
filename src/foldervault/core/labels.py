"""Label name normalization rules (docs/04-architecture.md §3)."""

from __future__ import annotations

import re

MAX_LABEL_LENGTH = 40
_WS_RE = re.compile(r"\s+")


class InvalidLabelError(ValueError):
    """Raised when a label name cannot be normalized into a valid label."""


def normalize_label(raw: str) -> str:
    """Trim and collapse whitespace. Raises InvalidLabelError for invalid names."""
    name = _WS_RE.sub(" ", raw).strip()
    if not name:
        raise InvalidLabelError("Label name is empty")
    if "," in name:
        raise InvalidLabelError("Label name must not contain a comma")
    if len(name) > MAX_LABEL_LENGTH:
        raise InvalidLabelError(f"Label name is longer than {MAX_LABEL_LENGTH} characters")
    return name


def split_label_input(text: str) -> list[str]:
    """Split comma-separated editor input into normalized, de-duplicated names."""
    result: list[str] = []
    seen: set[str] = set()
    for part in text.split(","):
        if not part.strip():
            continue
        name = normalize_label(part)
        key = name.casefold()
        if key not in seen:
            seen.add(key)
            result.append(name)
    return result
