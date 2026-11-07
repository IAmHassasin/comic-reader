"""Read-only directory walker that summarizes image folders.

Never writes anything under the scanned root.
"""

from __future__ import annotations

import os
import stat
from collections.abc import Callable, Iterator
from pathlib import Path

from .entities import FolderScanResult
from .image_types import format_label
from .natural_sort import natural_key

SKIPPED_DIR_NAMES = frozenset({"$recycle.bin", "system volume information"})
PREVIEW_COUNT = 3

_HIDDEN = getattr(stat, "FILE_ATTRIBUTE_HIDDEN", 0x2)
_SYSTEM = getattr(stat, "FILE_ATTRIBUTE_SYSTEM", 0x4)
_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _attributes(entry: os.DirEntry[str]) -> int:
    try:
        return getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
    except OSError:
        return 0


def _should_descend(entry: os.DirEntry[str], attrs: int) -> bool:
    if entry.name.casefold() in SKIPPED_DIR_NAMES:
        return False
    if entry.is_symlink() or attrs & _REPARSE:
        return False  # junctions/symlinks can create loops
    return not (attrs & _HIDDEN and attrs & _SYSTEM)


def _join(parent: str, name: str) -> str:
    return f"{parent}/{name}" if parent else name


def scan_tree(
    root: Path,
    image_extensions: frozenset[str],
    should_cancel: Callable[[], bool] = lambda: False,
) -> Iterator[FolderScanResult]:
    """Yield one result per directory under ``root`` (root itself included, rel_path '')."""
    # Stack items: (absolute path, rel_path, parent_rel_path, win_hidden, mtime)
    try:
        root_mtime = root.stat().st_mtime
    except OSError:
        root_mtime = None
    stack: list[tuple[str, str, str | None, bool, float | None]] = [
        (str(root), "", None, False, root_mtime)
    ]
    while stack:
        if should_cancel():
            return
        abs_path, rel_path, parent_rel, win_hidden, mtime = stack.pop()
        image_names: list[str] = []
        total_bytes = 0
        formats: dict[str, int] = {}
        children: list[tuple[str, str, str | None, bool, float | None]] = []
        error: str | None = None
        try:
            with os.scandir(abs_path) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            attrs = _attributes(entry)
                            if not _should_descend(entry, attrs):
                                continue
                            try:
                                child_mtime = entry.stat(follow_symlinks=False).st_mtime
                            except OSError:
                                child_mtime = None
                            children.append(
                                (
                                    entry.path,
                                    _join(rel_path, entry.name),
                                    rel_path,
                                    bool(attrs & _HIDDEN),
                                    child_mtime,
                                )
                            )
                        elif entry.is_file(follow_symlinks=False):
                            ext = os.path.splitext(entry.name)[1].lower()
                            if ext in image_extensions:
                                image_names.append(entry.name)
                                total_bytes += entry.stat(follow_symlinks=False).st_size
                                label = format_label(ext)
                                formats[label] = formats.get(label, 0) + 1
                    except OSError:
                        continue  # one unreadable entry must not abort the folder
        except OSError as exc:
            error = f"{type(exc).__name__}: {exc.strerror or exc}"

        image_names.sort(key=natural_key)
        yield FolderScanResult(
            rel_path=rel_path,
            parent_rel_path=parent_rel,
            image_count=len(image_names),
            subfolder_count=len(children),
            total_bytes=total_bytes,
            cover_name=image_names[0] if image_names else None,
            preview_names=tuple(image_names[:PREVIEW_COUNT]),
            format_stats=formats,
            mtime=mtime,
            win_hidden=win_hidden,
            error=error,
        )
        # Reverse so children are visited in natural order (stack is LIFO).
        children.sort(key=lambda c: natural_key(c[1]), reverse=True)
        stack.extend(children)


def list_images(folder: Path, image_extensions: frozenset[str]) -> list[str]:
    """Image file names in ``folder`` in natural order (non-recursive)."""
    try:
        with os.scandir(folder) as it:
            names = [
                e.name
                for e in it
                if e.is_file(follow_symlinks=False)
                and os.path.splitext(e.name)[1].lower() in image_extensions
            ]
    except OSError:
        return []
    names.sort(key=natural_key)
    return names
