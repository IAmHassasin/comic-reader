"""Apply / export script-provided folder metadata. No Qt imports (used by the CLI)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.entities import FolderMeta
from ..core.labels import InvalidLabelError, normalize_label
from ..core.metadata_io import META_FIELDS, MetadataFile, MetadataItem
from ..data.repository import Repository

log = logging.getLogger(__name__)


@dataclass
class ImportReport:
    matched: int = 0
    updated: int = 0
    unchanged: int = 0
    not_found: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dry_run: bool = False

    def summary(self) -> str:
        prefix = "[dry run] " if self.dry_run else ""
        return (
            f"{prefix}matched {self.matched}, updated {self.updated}, "
            f"unchanged {self.unchanged}, not found {len(self.not_found)}, "
            f"warnings {len(self.warnings)}"
        )


def normalize_root(path: str) -> str:
    return os.path.normpath(os.path.abspath(path))


def to_rel_path(item_path: str, root: str) -> str | None:
    """Convert an absolute or root-relative path to the stored '/'-separated rel_path."""
    candidate = item_path.strip()
    if os.path.isabs(candidate):
        abs_item = os.path.normpath(candidate)
        abs_root = normalize_root(root).rstrip("\\/")
        item_key, root_key = os.path.normcase(abs_item), os.path.normcase(abs_root)
        if item_key == root_key:
            return ""
        if not item_key.startswith(root_key + os.sep):
            return None
        candidate = abs_item[len(abs_root) + 1 :]  # keep the original case
    return candidate.replace("\\", "/").strip("/")


def apply_metadata(
    repo: Repository, root_id: int, root: str, data: MetadataFile, dry_run: bool = False
) -> ImportReport:
    report = ImportReport(dry_run=dry_run, warnings=list(data.warnings))
    by_path = {p.casefold(): fid for p, fid in repo.folder_ids_by_path(root_id).items()}
    conn = repo.conn
    try:
        for index, item in enumerate(data.items):
            rel = to_rel_path(item.path, root)
            folder_id = by_path.get(rel.casefold()) if rel is not None else None
            if folder_id is None:
                report.not_found.append(item.path)
                continue
            report.matched += 1
            if _apply_item(repo, folder_id, item, report, f"items[{index}]"):
                report.updated += 1
            else:
                report.unchanged += 1
        if dry_run:
            conn.rollback()
        else:
            conn.commit()
    except BaseException:
        # Any failure (not only sqlite3.Error) must leave nothing half-applied.
        conn.rollback()
        log.exception("Metadata import failed; rolled back")
        raise
    return report


def _apply_item(
    repo: Repository, folder_id: int, item: MetadataItem, report: ImportReport, where: str
) -> bool:
    old = repo.get_meta(folder_id) or FolderMeta()
    values: dict[str, Any] = {name: getattr(old, name) for name in META_FIELDS}
    values.update(item.fields)
    extra = dict(item.extra) if item.extra is not None else dict(old.extra)
    new = FolderMeta(extra=extra, **values)
    changed = False
    if new != old:
        repo.put_meta(folder_id, new, commit=False)
        changed = True

    if item.labels is not None:
        names: list[str] = []
        for raw in item.labels:
            try:
                names.append(normalize_label(raw))
            except InvalidLabelError as exc:
                report.warnings.append(f"{where}.labels: '{raw}' skipped ({exc})")
        before = {n.casefold() for n in repo.folder_labels(folder_id)}
        if item.labels_mode == "replace":
            after = {n.casefold() for n in names}
            if after != before:
                repo.set_folder_labels(folder_id, names, commit=False)
                changed = True
        else:
            missing = [n for n in names if n.casefold() not in before]
            if missing:
                repo.add_labels([folder_id], missing, commit=False)
                changed = True
    return changed


def export_items(repo: Repository, root_id: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in sorted(repo.load_rows(root_id), key=lambda r: r.rel_path.casefold()):
        if not row.rel_path:
            continue
        meta = row.meta or FolderMeta()
        items.append(
            {
                "path": row.rel_path,
                "name": row.name,
                "image_count": row.image_count,
                "title": meta.title,
                "series": meta.series,
                "type": meta.type,
                "language": meta.language,
                "labels": list(row.labels),
                "extra": meta.extra,
            }
        )
    return items


def resolve_root(repo: Repository, explicit: str | None, from_file: str | None) -> Path | None:
    for candidate in (explicit, from_file, repo.get_setting("last_root")):
        if candidate:
            return Path(normalize_root(candidate))
    return None
