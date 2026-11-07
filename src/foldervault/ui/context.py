"""Shared UI dependencies passed to widgets and delegates."""

from __future__ import annotations

import os
from dataclasses import dataclass

from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap

from ..core.entities import FolderRow
from ..services.library import LibraryService
from ..services.thumbnails import ThumbnailService


@dataclass
class UiContext:
    library: LibraryService
    thumbnails: ThumbnailService
    list_thumbnails: bool = False
    cache_hidden_thumbnails: bool = True

    def image_path(self, row: FolderRow, name: str | None = None) -> str | None:
        name = name or row.cover_name
        if not name:
            return None
        return os.path.join(self.library.abs_path(row.rel_path), name)

    def thumbnail(self, row: FolderRow, size: QSize, name: str | None = None) -> QPixmap | None:
        path = self.image_path(row, name)
        if path is None:
            return None
        allow_disk = self.cache_hidden_thumbnails or not row.effectively_hidden
        return self.thumbnails.request(path, size, allow_disk=allow_disk)
