"""Asynchronous thumbnail loading with a memory LRU and an optional disk cache."""

from __future__ import annotations

import hashlib
import itertools
import logging
import os
import shutil
from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, Signal
from PySide6.QtGui import QImage, QImageReader, QPixmap

from .. import config

log = logging.getLogger(__name__)

MEMORY_BUDGET_BYTES = 200 * 1024 * 1024


class _Bridge(QObject):
    done = Signal(str, QImage)


class _ThumbJob(QRunnable):
    def __init__(
        self, key: str, path: str, size: QSize, allow_disk: bool, cache_dir: Path, bridge: _Bridge
    ) -> None:
        super().__init__()
        self.key, self.path, self.size = key, path, size
        self.allow_disk, self.cache_dir, self.bridge = allow_disk, cache_dir, bridge

    def run(self) -> None:
        image = QImage()
        try:
            image = self._load()
        except Exception:  # noqa: BLE001 - a bad file must never kill the worker
            log.exception("Thumbnail failed for %s", self.path)
        self.bridge.done.emit(self.key, image)

    def _load(self) -> QImage:
        try:
            st = os.stat(self.path)
        except OSError:
            return QImage()
        digest = hashlib.sha1(
            f"{self.path}|{st.st_mtime_ns}|{st.st_size}|{self.size.width()}x{self.size.height()}".encode()
        ).hexdigest()
        cached = self.cache_dir / f"{digest}.jpg"
        if self.allow_disk and cached.exists():
            image = QImage(str(cached))
            if not image.isNull():
                return image
        reader = QImageReader(self.path)
        reader.setAutoTransform(True)
        original = reader.size()
        if original.isValid() and (
            original.width() > self.size.width() or original.height() > self.size.height()
        ):
            reader.setScaledSize(original.scaled(self.size, Qt.AspectRatioMode.KeepAspectRatio))
        image = reader.read()
        if image.isNull():
            log.debug("Cannot decode %s: %s", self.path, reader.errorString())
            return image
        if image.width() > self.size.width() or image.height() > self.size.height():
            image = image.scaled(
                self.size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        if self.allow_disk:
            if image.hasAlphaChannel():
                image = image.convertToFormat(QImage.Format.Format_RGB32)
            if not image.save(str(cached), "JPG", 85):
                log.debug("Could not write thumbnail cache %s", cached.name)
        return image


class ThumbnailService(QObject):
    """Call ``request`` from paint code; listen to ``ready`` to repaint."""

    ready = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(max(2, min(4, (os.cpu_count() or 4) // 2)))
        self._bridge = _Bridge()
        self._bridge.done.connect(self._on_done, Qt.ConnectionType.QueuedConnection)
        self._cache: OrderedDict[str, QPixmap] = OrderedDict()
        self._bytes = 0
        self._pending: set[str] = set()
        self._failed: set[str] = set()
        self._priority = itertools.count()
        self._cache_dir = config.thumbs_dir()

    @staticmethod
    def make_key(path: str, size: QSize) -> str:
        return f"{path}|{size.width()}x{size.height()}"

    def request(self, path: str, size: QSize, allow_disk: bool = True) -> QPixmap | None:
        key = self.make_key(path, size)
        pixmap = self._cache.get(key)
        if pixmap is not None:
            self._cache.move_to_end(key)
            return pixmap
        if key in self._pending or key in self._failed:
            return None
        self._pending.add(key)
        job = _ThumbJob(key, path, size, allow_disk, self._cache_dir, self._bridge)
        # Later requests (what is on screen now) run first.
        self._pool.start(job, min(next(self._priority), 2**30))
        return None

    def is_failed(self, path: str, size: QSize) -> bool:
        return self.make_key(path, size) in self._failed

    def _on_done(self, key: str, image: QImage) -> None:
        self._pending.discard(key)
        if image.isNull():
            self._failed.add(key)
            self.ready.emit(key)
            return
        pixmap = QPixmap.fromImage(image)
        self._cache[key] = pixmap
        self._bytes += pixmap.width() * pixmap.height() * 4
        while self._bytes > MEMORY_BUDGET_BYTES and self._cache:
            _, old = self._cache.popitem(last=False)
            self._bytes -= old.width() * old.height() * 4
        self.ready.emit(key)

    def clear_memory(self) -> None:
        self._cache.clear()
        self._bytes = 0
        self._failed.clear()

    def clear_disk_cache(self) -> int:
        """Delete the disk cache. Returns the number of bytes freed."""
        self._pool.clear()
        freed = 0
        folder = self._cache_dir
        if folder.exists():
            for entry in folder.iterdir():
                try:
                    freed += entry.stat().st_size
                except OSError:
                    pass
            shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True, exist_ok=True)
        self.clear_memory()
        return freed

    def shutdown(self) -> None:
        self._pool.clear()
        self._pool.waitForDone(2000)
