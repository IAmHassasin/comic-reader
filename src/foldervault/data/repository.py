"""Data access. All SQL is parameterized."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Any

from ..core.entities import FolderMeta, FolderRow, FolderScanResult, Label
from ..core.labels import normalize_label


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


_ID_CHUNK = 500


def _placeholders(n: int) -> str:
    return ",".join("?" * n)


class Repository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    # ------------------------------------------------------------------ roots
    def get_or_create_root(self, path: str) -> int:
        row = self.conn.execute("SELECT id FROM roots WHERE path = ?", (path,)).fetchone()
        if row:
            return int(row["id"])
        cur = self.conn.execute("INSERT INTO roots(path) VALUES (?)", (path,))
        self.conn.commit()
        return int(cur.lastrowid)

    def find_root(self, path: str) -> int | None:
        row = self.conn.execute("SELECT id FROM roots WHERE path = ?", (path,)).fetchone()
        return int(row["id"]) if row else None

    def root_last_scanned(self, root_id: int) -> str | None:
        row = self.conn.execute(
            "SELECT last_scanned_at FROM roots WHERE id = ?", (root_id,)
        ).fetchone()
        return row["last_scanned_at"] if row else None

    def mark_root_scanned(self, root_id: int) -> None:
        self.conn.execute("UPDATE roots SET last_scanned_at = ? WHERE id = ?", (now_iso(), root_id))
        self.conn.commit()

    # --------------------------------------------------------------- scanning
    def upsert_scan_results(self, root_id: int, results: Sequence[FolderScanResult]) -> None:
        self.conn.executemany(
            """
            INSERT INTO folders (root_id, rel_path, parent_rel_path, image_count,
                subfolder_count, total_bytes, cover_name, preview_names, format_stats,
                mtime, win_hidden, missing)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            ON CONFLICT(root_id, rel_path) DO UPDATE SET
                parent_rel_path = excluded.parent_rel_path,
                image_count = excluded.image_count,
                subfolder_count = excluded.subfolder_count,
                total_bytes = excluded.total_bytes,
                cover_name = excluded.cover_name,
                preview_names = excluded.preview_names,
                format_stats = excluded.format_stats,
                mtime = excluded.mtime,
                win_hidden = excluded.win_hidden,
                missing = 0
            """,
            [
                (
                    root_id,
                    r.rel_path,
                    r.parent_rel_path,
                    r.image_count,
                    r.subfolder_count,
                    r.total_bytes,
                    r.cover_name,
                    json.dumps(list(r.preview_names)),
                    json.dumps(r.format_stats),
                    r.mtime,
                    int(r.win_hidden),
                )
                for r in results
            ],
        )
        self.conn.commit()

    def mark_missing_except(self, root_id: int, seen: set[str]) -> int:
        rows = self.conn.execute(
            "SELECT id, rel_path FROM folders WHERE root_id = ? AND missing = 0", (root_id,)
        ).fetchall()
        gone = [(r["id"],) for r in rows if r["rel_path"] not in seen]
        self.conn.executemany("UPDATE folders SET missing = 1 WHERE id = ?", gone)
        self.conn.commit()
        return len(gone)

    # ------------------------------------------------------------------ reads
    def load_rows(self, root_id: int, folder_ids: Iterable[int] | None = None) -> list[FolderRow]:
        if folder_ids is None:
            return self._load_rows_chunk(root_id, None)
        ids = list(folder_ids)
        result: list[FolderRow] = []
        for start in range(0, len(ids), _ID_CHUNK):  # stay under SQLite's variable limit
            result.extend(self._load_rows_chunk(root_id, ids[start : start + _ID_CHUNK]))
        return result

    def _load_rows_chunk(self, root_id: int, ids: list[int] | None) -> list[FolderRow]:
        """Load rows; when ``ids`` is given, labels/meta are queried for those ids only."""
        id_filter, id_params = "", []
        if ids is not None:
            if not ids:
                return []
            id_filter = f" AND f.id IN ({_placeholders(len(ids))})"
            id_params = list(ids)
        rows = self.conn.execute(
            "SELECT f.* FROM folders f WHERE f.root_id = ? AND f.missing = 0" + id_filter,
            [root_id, *id_params],
        ).fetchall()
        label_rows = self.conn.execute(
            """
            SELECT fl.folder_id, l.name FROM folder_labels fl
            JOIN labels l ON l.id = fl.label_id
            JOIN folders f ON f.id = fl.folder_id
            WHERE f.root_id = ?"""
            + id_filter
            + " ORDER BY l.name COLLATE NOCASE",
            [root_id, *id_params],
        ).fetchall()
        labels: dict[int, list[str]] = {}
        for r in label_rows:
            labels.setdefault(r["folder_id"], []).append(r["name"])
        meta_rows = self.conn.execute(
            "SELECT m.* FROM folder_meta m JOIN folders f ON f.id = m.folder_id WHERE f.root_id = ?"
            + id_filter,
            [root_id, *id_params],
        ).fetchall()
        metas = {r["folder_id"]: _meta_from_row(r) for r in meta_rows}
        return [self._to_row(r, tuple(labels.get(r["id"], ())), metas.get(r["id"])) for r in rows]

    def folder_ids_for_paths(self, root_id: int, rel_paths: Sequence[str]) -> list[int]:
        ids: list[int] = []
        paths = list(rel_paths)
        for start in range(0, len(paths), _ID_CHUNK):
            chunk = paths[start : start + _ID_CHUNK]
            rows = self.conn.execute(
                f"SELECT id FROM folders WHERE root_id = ? AND rel_path IN ({_placeholders(len(chunk))})",
                [root_id, *chunk],
            ).fetchall()
            ids.extend(r["id"] for r in rows)
        return ids

    @staticmethod
    def _to_row(r: sqlite3.Row, labels: tuple[str, ...], meta: FolderMeta | None) -> FolderRow:
        return FolderRow(
            id=r["id"],
            rel_path=r["rel_path"],
            parent_rel_path=r["parent_rel_path"],
            image_count=r["image_count"],
            subfolder_count=r["subfolder_count"],
            total_bytes=r["total_bytes"],
            cover_name=r["cover_name"],
            preview_names=tuple(json.loads(r["preview_names"] or "[]")),
            format_stats=json.loads(r["format_stats"] or "{}"),
            mtime=r["mtime"],
            win_hidden=bool(r["win_hidden"]),
            is_hidden=bool(r["is_hidden"]),
            is_favorite=bool(r["is_favorite"]),
            view_count=r["view_count"],
            last_opened_at=r["last_opened_at"],
            labels=labels,
            meta=meta if meta and not meta.is_empty() else None,
        )

    def folder_ids_by_path(self, root_id: int) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT id, rel_path FROM folders WHERE root_id = ? AND missing = 0", (root_id,)
        ).fetchall()
        return {r["rel_path"]: r["id"] for r in rows}

    # ------------------------------------------------------------------ flags
    def set_favorite(self, folder_ids: Sequence[int], value: bool) -> None:
        self._set_flag("is_favorite", folder_ids, value)

    def set_hidden(self, folder_ids: Sequence[int], value: bool) -> None:
        self._set_flag("is_hidden", folder_ids, value)

    def _set_flag(self, column: str, folder_ids: Sequence[int], value: bool) -> None:
        if column not in ("is_favorite", "is_hidden"):
            raise ValueError(column)
        self.conn.executemany(
            f"UPDATE folders SET {column} = ? WHERE id = ?",
            [(int(value), fid) for fid in folder_ids],
        )
        self.conn.commit()

    def record_open(self, folder_id: int) -> None:
        self.conn.execute(
            "UPDATE folders SET view_count = view_count + 1, last_opened_at = ? WHERE id = ?",
            (now_iso(), folder_id),
        )
        self.conn.commit()

    # ----------------------------------------------------------------- labels
    def all_labels(self) -> list[Label]:
        rows = self.conn.execute(
            "SELECT id, name, color FROM labels ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [Label(r["id"], r["name"], r["color"]) for r in rows]

    def label_usage(self) -> dict[int, int]:
        rows = self.conn.execute(
            """
            SELECT fl.label_id, COUNT(*) AS n FROM folder_labels fl
            JOIN folders f ON f.id = fl.folder_id AND f.missing = 0
            GROUP BY fl.label_id
            """
        ).fetchall()
        return {r["label_id"]: r["n"] for r in rows}

    def _label_id(self, name: str, create: bool = True) -> int | None:
        name = normalize_label(name)
        row = self.conn.execute("SELECT id FROM labels WHERE name = ?", (name,)).fetchone()
        if row:
            return int(row["id"])
        if not create:
            return None
        return int(self.conn.execute("INSERT INTO labels(name) VALUES (?)", (name,)).lastrowid)

    def set_folder_labels(self, folder_id: int, names: Sequence[str], commit: bool = True) -> None:
        ids = [self._label_id(n) for n in names]
        self.conn.execute("DELETE FROM folder_labels WHERE folder_id = ?", (folder_id,))
        self.conn.executemany(
            "INSERT OR IGNORE INTO folder_labels(folder_id, label_id) VALUES (?, ?)",
            [(folder_id, lid) for lid in ids],
        )
        if commit:
            self.conn.commit()

    def add_labels(
        self, folder_ids: Sequence[int], names: Sequence[str], commit: bool = True
    ) -> None:
        ids = [self._label_id(n) for n in names]
        self.conn.executemany(
            "INSERT OR IGNORE INTO folder_labels(folder_id, label_id) VALUES (?, ?)",
            [(fid, lid) for fid in folder_ids for lid in ids],
        )
        if commit:
            self.conn.commit()

    def remove_labels(self, folder_ids: Sequence[int], names: Sequence[str]) -> None:
        ids = [lid for n in names if (lid := self._label_id(n, create=False)) is not None]
        self.conn.executemany(
            "DELETE FROM folder_labels WHERE folder_id = ? AND label_id = ?",
            [(fid, lid) for fid in folder_ids for lid in ids],
        )
        self.conn.commit()

    def set_label_color(self, name: str, color: str | None) -> None:
        self.conn.execute("UPDATE labels SET color = ? WHERE name = ?", (color, name))
        self.conn.commit()

    def rename_label(self, old: str, new: str) -> None:
        """Rename a label; merges into ``new`` if it already exists."""
        new = normalize_label(new)
        old_id = self._label_id(old, create=False)
        if old_id is None:
            return
        existing = self.conn.execute(
            "SELECT id FROM labels WHERE name = ? AND id != ?", (new, old_id)
        ).fetchone()
        try:
            if existing:
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO folder_labels(folder_id, label_id)
                    SELECT folder_id, ? FROM folder_labels WHERE label_id = ?
                    """,
                    (existing["id"], old_id),
                )
                self.conn.execute("DELETE FROM labels WHERE id = ?", (old_id,))
            else:
                self.conn.execute("UPDATE labels SET name = ? WHERE id = ?", (new, old_id))
            self.conn.commit()
        except sqlite3.Error:
            self.conn.rollback()
            raise

    def label_exists(self, name: str) -> bool:
        return self._label_id(name, create=False) is not None

    def delete_label(self, name: str) -> None:
        self.conn.execute("DELETE FROM labels WHERE name = ?", (name,))
        self.conn.commit()

    # ------------------------------------------------------------------- meta
    def get_meta(self, folder_id: int) -> FolderMeta | None:
        row = self.conn.execute(
            "SELECT * FROM folder_meta WHERE folder_id = ?", (folder_id,)
        ).fetchone()
        return _meta_from_row(row) if row else None

    def put_meta(self, folder_id: int, meta: FolderMeta, commit: bool = True) -> None:
        self.conn.execute(
            """
            INSERT INTO folder_meta(folder_id, title, series, type, language, extra, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(folder_id) DO UPDATE SET
                title = excluded.title, series = excluded.series, type = excluded.type,
                language = excluded.language, extra = excluded.extra,
                updated_at = excluded.updated_at
            """,
            (
                folder_id,
                meta.title,
                meta.series,
                meta.type,
                meta.language,
                json.dumps(meta.extra, ensure_ascii=False) if meta.extra else None,
                now_iso(),
            ),
        )
        if commit:
            self.conn.commit()

    def folder_labels(self, folder_id: int) -> list[str]:
        rows = self.conn.execute(
            """
            SELECT l.name FROM folder_labels fl JOIN labels l ON l.id = fl.label_id
            WHERE fl.folder_id = ? ORDER BY l.name COLLATE NOCASE
            """,
            (folder_id,),
        ).fetchall()
        return [r["name"] for r in rows]

    # --------------------------------------------------------------- settings
    def get_setting(self, key: str, default: Any = None) -> Any:
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if not row:
            return default
        try:
            return json.loads(row["value"])
        except json.JSONDecodeError:
            return default

    def set_setting(self, key: str, value: Any) -> None:
        self.conn.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)),
        )
        self.conn.commit()


def _meta_from_row(r: sqlite3.Row) -> FolderMeta:
    extra = json.loads(r["extra"]) if r["extra"] else {}
    return FolderMeta(
        title=r["title"], series=r["series"], type=r["type"], language=r["language"], extra=extra
    )
