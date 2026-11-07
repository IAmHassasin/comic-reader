"""SQLite connection setup and migration runner."""

from __future__ import annotations

import logging
import shutil
import sqlite3
from pathlib import Path

from .migrations import MIGRATIONS

log = logging.getLogger(__name__)


def connect(path: Path) -> sqlite3.Connection:
    """Open the database, apply PRAGMAs and pending migrations."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=3.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 3000")
    migrate(conn, path)
    return conn


def current_version(conn: sqlite3.Connection) -> int:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return int(row[0] or 0)


def migrate(conn: sqlite3.Connection, path: Path | None = None) -> None:
    version = current_version(conn)
    pending = [(v, sql) for v, sql in MIGRATIONS if v > version]
    if not pending:
        return
    if version > 0 and path is not None and path.exists():
        backup = path.with_suffix(f".v{version}.bak")
        conn.commit()
        shutil.copy2(path, backup)
        log.info("Backed up database before migration to %s", backup.name)
    for v, sql in pending:
        log.info("Applying migration %d", v)
        try:
            conn.executescript(
                "BEGIN;\n" + sql + f"\nINSERT INTO schema_version VALUES ({v});\nCOMMIT;"
            )
        except sqlite3.Error:
            conn.rollback()
            raise
