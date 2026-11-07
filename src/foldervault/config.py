"""App data locations. Nothing is ever stored inside the scanned library."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "FolderVault"
STEALTH_TITLE = "Image Library"
DATA_DIR_ENV = "FOLDERVAULT_DATA_DIR"  # override, used by tests


def data_dir() -> Path:
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        base = Path(override)
    else:
        local = os.environ.get("LOCALAPPDATA")
        base = Path(local) / APP_NAME if local else Path.home() / f".{APP_NAME.lower()}"
    base.mkdir(parents=True, exist_ok=True)
    return base


def db_path() -> Path:
    return data_dir() / "library.db"


def thumbs_dir() -> Path:
    path = data_dir() / "thumbs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
