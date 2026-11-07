"""Open images in Windows Photos / the default app, or reveal them in Explorer."""

from __future__ import annotations

import logging
import os
import subprocess
from enum import Enum

log = logging.getLogger(__name__)


class OpenMode(str, Enum):
    PHOTOS = "photos"
    DEFAULT = "default"


class OpenResult(Enum):
    PHOTOS = "photos"
    DEFAULT_APP = "default"
    FALLBACK = "fallback"  # Photos was requested but failed; default app used
    FAILED = "failed"


def _startfile(target: str) -> None:
    os.startfile(target)  # noqa: S606 - opening the user's own file with its associated app


def open_image(path: str, mode: OpenMode) -> OpenResult:
    """Open ``path``. Never raises; returns how it was opened."""
    if mode == OpenMode.PHOTOS:
        try:
            # Raw (not percent-encoded) path, as ShellExecute passes it to the Photos protocol.
            _startfile(f"ms-photos:viewer?fileName={path}")
            return OpenResult.PHOTOS
        except OSError:
            log.warning("Windows Photos protocol failed; falling back to the default app")
            try:
                _startfile(path)
                return OpenResult.FALLBACK
            except OSError:
                log.exception("Default app also failed")
                return OpenResult.FAILED
    try:
        _startfile(path)
        return OpenResult.DEFAULT_APP
    except OSError:
        log.exception("Could not open image with the default app")
        return OpenResult.FAILED


def reveal_in_explorer(path: str) -> bool:
    try:
        if os.path.isdir(path):
            subprocess.Popen(["explorer.exe", os.path.normpath(path)])  # noqa: S603,S607
        else:
            subprocess.Popen(["explorer.exe", f"/select,{os.path.normpath(path)}"])  # noqa: S603,S607
        return True
    except OSError:
        log.exception("Could not start Explorer")
        return False
