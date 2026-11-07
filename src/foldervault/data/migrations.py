"""Ordered schema migrations. Never edit a released migration; append a new one."""

from __future__ import annotations

MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE roots (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL UNIQUE COLLATE NOCASE,
            last_scanned_at TEXT
        );

        CREATE TABLE folders (
            id INTEGER PRIMARY KEY,
            root_id INTEGER NOT NULL REFERENCES roots(id) ON DELETE CASCADE,
            rel_path TEXT NOT NULL,
            parent_rel_path TEXT,
            image_count INTEGER NOT NULL DEFAULT 0,
            subfolder_count INTEGER NOT NULL DEFAULT 0,
            total_bytes INTEGER NOT NULL DEFAULT 0,
            cover_name TEXT,
            preview_names TEXT,
            format_stats TEXT,
            mtime REAL,
            win_hidden INTEGER NOT NULL DEFAULT 0,
            is_hidden INTEGER NOT NULL DEFAULT 0,
            is_favorite INTEGER NOT NULL DEFAULT 0,
            view_count INTEGER NOT NULL DEFAULT 0,
            last_opened_at TEXT,
            missing INTEGER NOT NULL DEFAULT 0,
            UNIQUE (root_id, rel_path)
        );

        CREATE TABLE folder_meta (
            folder_id INTEGER PRIMARY KEY REFERENCES folders(id) ON DELETE CASCADE,
            title TEXT,
            series TEXT,
            type TEXT,
            language TEXT,
            extra TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            color TEXT
        );

        CREATE TABLE folder_labels (
            folder_id INTEGER NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
            label_id INTEGER NOT NULL REFERENCES labels(id) ON DELETE CASCADE,
            PRIMARY KEY (folder_id, label_id)
        );
        CREATE INDEX idx_folder_labels_label ON folder_labels(label_id);

        CREATE TABLE settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """,
    ),
]
