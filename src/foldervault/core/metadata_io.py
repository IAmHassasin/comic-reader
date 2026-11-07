"""Metadata exchange file format, version 1 (docs/03 §S6). Pure Python."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
META_FIELDS = ("title", "series", "type", "language")
# "name" and "image_count" are informational keys written by export; accepted and ignored.
_KNOWN_KEYS = frozenset(
    {"path", *META_FIELDS, "labels", "labels_mode", "extra", "name", "image_count"}
)
_UNSET: Any = object()


class MetadataFileError(ValueError):
    """The file as a whole is invalid; nothing must be applied."""


@dataclass
class MetadataItem:
    path: str
    # Each field is _UNSET (leave unchanged), None (clear) or a string (set).
    fields: dict[str, Any] = field(default_factory=dict)
    labels: list[str] | None = None
    labels_mode: str = "merge"
    extra: dict[str, str] | None = None


@dataclass
class MetadataFile:
    root: str | None
    items: list[MetadataItem]
    warnings: list[str]


def _check_str_or_null(value: Any, where: str) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise MetadataFileError(f"{where}: expected a string or null")


def parse_metadata(data: Any) -> MetadataFile:
    if not isinstance(data, dict):
        raise MetadataFileError("Top level must be a JSON object")
    if data.get("version") != SCHEMA_VERSION:
        raise MetadataFileError(
            f"Unsupported version {data.get('version')!r}; expected {SCHEMA_VERSION}"
        )
    root = data.get("root")
    if root is not None and not isinstance(root, str):
        raise MetadataFileError("'root' must be a string")
    raw_items = data.get("items")
    if not isinstance(raw_items, list):
        raise MetadataFileError("'items' must be a list")

    warnings: list[str] = []
    items: list[MetadataItem] = []
    for index, raw in enumerate(raw_items):
        where = f"items[{index}]"
        if not isinstance(raw, dict):
            raise MetadataFileError(f"{where}: must be an object")
        path = raw.get("path")
        if not isinstance(path, str) or not path.strip():
            raise MetadataFileError(f"{where}: 'path' is required")
        for key in raw:
            if key not in _KNOWN_KEYS:
                warnings.append(f"{where}: unknown key '{key}' ignored")
        fields = {
            name: _check_str_or_null(raw[name], f"{where}.{name}")
            for name in META_FIELDS
            if name in raw
        }
        labels = raw.get("labels")
        if labels is not None and (
            not isinstance(labels, list) or not all(isinstance(x, str) for x in labels)
        ):
            raise MetadataFileError(f"{where}.labels: must be a list of strings")
        mode = raw.get("labels_mode", "merge")
        if mode not in ("merge", "replace"):
            raise MetadataFileError(f"{where}.labels_mode: must be 'merge' or 'replace'")
        extra = raw.get("extra")
        if extra is not None:
            if not isinstance(extra, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in extra.items()
            ):
                raise MetadataFileError(f"{where}.extra: must be an object of strings")
        items.append(
            MetadataItem(path=path, fields=fields, labels=labels, labels_mode=mode, extra=extra)
        )
    return MetadataFile(root=root, items=items, warnings=warnings)


def load_metadata_file(path: Path) -> MetadataFile:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise MetadataFileError(f"Cannot read {path}: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MetadataFileError(f"Invalid JSON: {exc}") from exc
    return parse_metadata(data)


def write_export_file(path: Path, root: str, items: list[dict[str, Any]]) -> None:
    payload = {"version": SCHEMA_VERSION, "root": root, "items": items}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
