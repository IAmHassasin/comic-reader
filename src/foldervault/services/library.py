"""Library orchestration: root, background scan, DB writes, label colors."""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QImageReader

from ..core.colors import ChipColors, chip_colors
from ..core.entities import FolderScanResult, Label
from ..core.image_types import restrict_to_readable
from ..core.metadata_io import MetadataFile
from ..core.scanner import scan_tree
from ..data.repository import Repository
from .metadata_import import ImportReport, apply_metadata, export_items, normalize_root

log = logging.getLogger(__name__)

BATCH_SIZE = 50
RECENT_ROOTS_MAX = 10


class _ScanBridge(QObject):
    batch = Signal(int, list)  # generation, list[FolderScanResult]
    finished = Signal(int, bool)  # generation, cancelled


class _ScanJob(QRunnable):
    def __init__(
        self,
        generation: int,
        root: Path,
        exts: frozenset[str],
        cancel: threading.Event,
        bridge: _ScanBridge,
    ) -> None:
        super().__init__()
        self.generation, self.root, self.exts = generation, root, exts
        self.cancel, self.bridge = cancel, bridge

    def run(self) -> None:
        batch: list[FolderScanResult] = []
        cancelled = False
        try:
            for result in scan_tree(self.root, self.exts, self.cancel.is_set):
                batch.append(result)
                if len(batch) >= BATCH_SIZE:
                    self.bridge.batch.emit(self.generation, batch)
                    batch = []
            cancelled = self.cancel.is_set()
        except Exception:  # noqa: BLE001 - report as finished; error is logged
            log.exception("Scan crashed")
            cancelled = True
        if batch:
            self.bridge.batch.emit(self.generation, batch)
        self.bridge.finished.emit(self.generation, cancelled)


class LibraryService(QObject):
    rows_reset = Signal(list)  # list[FolderRow]: full replacement
    rows_changed = Signal(list)  # list[FolderRow]: inserted or updated
    rows_removed = Signal(list)  # list[int]: folder ids
    labels_changed = Signal()
    scan_started = Signal()
    scan_progress = Signal(int)  # folders scanned so far
    scan_finished = Signal(bool, int)  # cancelled, error count
    root_changed = Signal(str)
    root_missing = Signal(str)

    def __init__(self, repo: Repository, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.repo = repo
        self.root: Path | None = None
        self.root_id: int | None = None
        self.image_extensions = restrict_to_readable(
            bytes(f.data()).decode("ascii", "ignore") for f in QImageReader.supportedImageFormats()
        )
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._bridge = _ScanBridge()
        self._bridge.batch.connect(self._on_batch, Qt.ConnectionType.QueuedConnection)
        self._bridge.finished.connect(self._on_finished, Qt.ConnectionType.QueuedConnection)
        self._generation = 0
        self._cancel = threading.Event()
        self._seen: set[str] = set()
        self._errors = 0
        self._scanning = False
        self._label_cache: dict[str, Label] = {}
        self._reload_labels()

    # ------------------------------------------------------------------ root
    @property
    def scanning(self) -> bool:
        return self._scanning

    def open_root(self, path: str, scan: bool = True) -> None:
        root = Path(normalize_root(path))
        self.cancel_scan()
        self.root = root
        self.root_id = self.repo.get_or_create_root(str(root))
        self._remember_root(str(root))
        self.root_changed.emit(str(root))
        if not root.is_dir():
            self.rows_reset.emit([])
            self.root_missing.emit(str(root))
            return
        self.rows_reset.emit(self.repo.load_rows(self.root_id))
        if scan:
            self.start_scan()

    def close_root(self) -> None:
        self.cancel_scan()
        self.root = None
        self.root_id = None
        self.rows_reset.emit([])
        self.root_changed.emit("")

    def _remember_root(self, root: str) -> None:
        self.repo.set_setting("last_root", root)
        recent = [
            r for r in self.repo.get_setting("recent_roots", []) if r.casefold() != root.casefold()
        ]
        self.repo.set_setting("recent_roots", [root, *recent][:RECENT_ROOTS_MAX])

    def abs_path(self, rel_path: str) -> str:
        if self.root is None:
            return ""
        return (
            os.path.normpath(os.path.join(str(self.root), rel_path)) if rel_path else str(self.root)
        )

    def root_name(self) -> str:
        return self.root.name or str(self.root) if self.root else ""

    # ------------------------------------------------------------------ scan
    def start_scan(self) -> None:
        if self.root is None or self.root_id is None:
            return
        if not self.root.is_dir():
            self.root_missing.emit(str(self.root))
            return
        self.cancel_scan(notify=False)  # a restart is not a user-visible cancel
        self._generation += 1
        self._cancel = threading.Event()
        self._seen = set()
        self._errors = 0
        self._scanning = True
        self._scan_started_at = time.monotonic()
        self.scan_started.emit()
        self._pool.start(
            _ScanJob(self._generation, self.root, self.image_extensions, self._cancel, self._bridge)
        )

    def cancel_scan(self, notify: bool = True) -> None:
        if self._scanning:
            self._cancel.set()
            # Invalidate in-flight batches so they can never be written to another root.
            self._generation += 1
            self._scanning = False
            if notify:
                self.scan_finished.emit(True, self._errors)

    def _on_batch(self, generation: int, batch: list[FolderScanResult]) -> None:
        if generation != self._generation or self.root_id is None:
            return
        self.repo.upsert_scan_results(self.root_id, batch)
        self._seen.update(r.rel_path for r in batch)
        self._errors += sum(1 for r in batch if r.error)
        for r in batch:
            if r.error:
                log.warning("Scan error in '%s': %s", r.rel_path, r.error)
        ids = self.repo.folder_ids_for_paths(self.root_id, [r.rel_path for r in batch])
        self.rows_changed.emit(self.repo.load_rows(self.root_id, ids))
        self.scan_progress.emit(len(self._seen))

    def _on_finished(self, generation: int, cancelled: bool) -> None:
        if generation != self._generation:
            return
        self._scanning = False
        if not cancelled and self.root_id is not None:
            before = self.repo.folder_ids_by_path(self.root_id)
            self.repo.mark_missing_except(self.root_id, self._seen)
            removed = [fid for path, fid in before.items() if path not in self._seen]
            if removed:
                self.rows_removed.emit(removed)
            self.repo.mark_root_scanned(self.root_id)
            log.info(
                "Scan finished: %d folders, %d errors, %.1fs",
                len(self._seen),
                self._errors,
                time.monotonic() - self._scan_started_at,
            )
        self.scan_finished.emit(cancelled, self._errors)

    def shutdown(self) -> None:
        self.cancel_scan()
        self._pool.waitForDone(3000)

    # ------------------------------------------------------------- folders
    def _emit_rows(self, ids: Sequence[int]) -> None:
        if self.root_id is not None:
            self.rows_changed.emit(self.repo.load_rows(self.root_id, ids))

    def reload_all(self) -> None:
        if self.root_id is not None:
            self.rows_reset.emit(self.repo.load_rows(self.root_id))

    def set_favorite(self, ids: Sequence[int], value: bool) -> None:
        self.repo.set_favorite(ids, value)
        self._emit_rows(ids)

    def set_hidden(self, ids: Sequence[int], value: bool) -> None:
        self.repo.set_hidden(ids, value)
        self._emit_rows(ids)

    def record_open(self, folder_id: int) -> None:
        self.repo.record_open(folder_id)
        self._emit_rows([folder_id])

    def set_labels(self, folder_id: int, names: Sequence[str]) -> None:
        self.repo.set_folder_labels(folder_id, names)
        self._reload_labels()
        self._emit_rows([folder_id])

    def add_labels(self, ids: Sequence[int], names: Sequence[str]) -> None:
        self.repo.add_labels(ids, names)
        self._reload_labels()
        self._emit_rows(ids)

    def remove_labels(self, ids: Sequence[int], names: Sequence[str]) -> None:
        self.repo.remove_labels(ids, names)
        self._emit_rows(ids)

    # -------------------------------------------------------------- labels
    def _reload_labels(self) -> None:
        self._label_cache = {lbl.name.casefold(): lbl for lbl in self.repo.all_labels()}
        self.labels_changed.emit()

    def labels(self) -> list[Label]:
        return sorted(self._label_cache.values(), key=lambda lbl: lbl.name.casefold())

    def label_usage(self) -> dict[int, int]:
        return self.repo.label_usage()

    def chip_colors(self, name: str) -> ChipColors:
        label = self._label_cache.get(name.casefold())
        return chip_colors(name, label.color if label else None)

    def set_label_color(self, name: str, color: str | None) -> None:
        self.repo.set_label_color(name, color)
        self._reload_labels()

    def rename_label(self, old: str, new: str) -> None:
        self.repo.rename_label(old, new)
        self._reload_labels()
        self.reload_all()

    def delete_label(self, name: str) -> None:
        self.repo.delete_label(name)
        self._reload_labels()
        self.reload_all()

    def label_exists(self, name: str) -> bool:
        return name.casefold() in self._label_cache

    # ------------------------------------------------------------ metadata
    def import_metadata(self, data: MetadataFile, dry_run: bool = False) -> ImportReport:
        if self.root is None or self.root_id is None:
            raise RuntimeError("No root is open")
        report = apply_metadata(self.repo, self.root_id, str(self.root), data, dry_run=dry_run)
        if not dry_run:
            self._reload_labels()
            self.reload_all()
        return report

    def export_metadata_items(self) -> list[dict]:
        if self.root_id is None:
            return []
        return export_items(self.repo, self.root_id)


def debounce(parent: QObject, msec: int, callback) -> QTimer:
    timer = QTimer(parent)
    timer.setSingleShot(True)
    timer.setInterval(msec)
    timer.timeout.connect(callback)
    return timer
