"""Natural ("human") sort keys, matching Windows Explorer: ``2.jpg`` < ``10.jpg``."""

from __future__ import annotations

import re
import unicodedata

_CHUNK_RE = re.compile(r"(\d+)")


def fold_text(text: str) -> str:
    """Case- and accent-insensitive form of ``text`` for searching and sorting."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.casefold()


def natural_key(text: str) -> tuple[tuple[int, int, str], ...]:
    """Return a sort key; digit runs compare numerically and sort before letters."""
    parts: list[tuple[int, int, str]] = []
    for chunk in _CHUNK_RE.split(fold_text(text)):
        if not chunk:
            continue
        if chunk.isdigit():
            parts.append((0, int(chunk), chunk))
        else:
            parts.append((1, 0, chunk))
    return tuple(parts)
