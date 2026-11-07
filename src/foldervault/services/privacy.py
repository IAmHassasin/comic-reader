"""App-level privacy actions only. Never changes Windows settings."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ..data.repository import Repository
from .thumbnails import ThumbnailService

log = logging.getLogger(__name__)


@dataclass
class ClearResult:
    recent_roots: int
    cache_bytes: int

    def summary(self) -> str:
        mb = self.cache_bytes / (1024 * 1024)
        return f"Cleared {self.recent_roots} recent roots and {mb:.1f} MB of thumbnail cache"


def clear_app_history(
    repo: Repository, thumbnails: ThumbnailService, keep_root: str | None
) -> ClearResult:
    """Clear recent roots (keeping the open one, if any) and the thumbnail disk cache."""
    recent = repo.get_setting("recent_roots", [])
    kept = [keep_root] if keep_root else []
    repo.set_setting("recent_roots", kept)
    if not keep_root:
        repo.set_setting("last_root", None)
    freed = thumbnails.clear_disk_cache()
    result = ClearResult(recent_roots=max(0, len(recent) - len(kept)), cache_bytes=freed)
    log.info(result.summary())
    return result
