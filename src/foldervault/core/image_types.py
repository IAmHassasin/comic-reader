"""Image file extensions the library counts as comic pages."""

from __future__ import annotations

from collections.abc import Iterable

# Candidate extensions. Formats Qt can read but that are not comic pages (pdf, svg, ico)
# are intentionally absent.
CANDIDATE_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".jfif", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff"}
)

_FORMAT_ALIASES = {
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".jfif": "jpeg",
    ".tif": "tiff",
    ".tiff": "tiff",
}


def restrict_to_readable(readable_formats: Iterable[str]) -> frozenset[str]:
    """Keep only candidate extensions whose format the image backend can decode."""
    readable = {fmt.lower() for fmt in readable_formats}
    result = set()
    for ext in CANDIDATE_EXTENSIONS:
        fmt = _FORMAT_ALIASES.get(ext, ext.lstrip("."))
        if fmt in readable or ext.lstrip(".") in readable:
            result.add(ext)
    return frozenset(result)


def format_label(ext: str) -> str:
    """Display name for an extension, e.g. ``.jpg`` -> ``JPEG``."""
    return _FORMAT_ALIASES.get(ext.lower(), ext.lower().lstrip(".")).upper()
