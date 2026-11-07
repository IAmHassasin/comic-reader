"""Locale-aware display formatting."""

from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import QDateTime, QLocale, QTimeZone


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit in ("B", "KB") else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_count(n: int) -> str:
    return QLocale.system().toString(n)


def format_timestamp(ts: float | None) -> str:
    if not ts:
        return ""
    dt = QDateTime.fromSecsSinceEpoch(int(ts), QTimeZone.systemTimeZone())
    return QLocale.system().toString(dt, QLocale.FormatType.ShortFormat)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def relative_time(iso_value: str | None) -> str:
    dt = _parse_iso(iso_value)
    if dt is None:
        return ""
    seconds = (datetime.now(UTC) - dt).total_seconds()
    if seconds < 60:
        return "just now"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} h ago"
    days = hours // 24
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days} days ago"
    if days < 60:
        return f"{days // 7} weeks ago"
    return QLocale.system().toString(
        QDateTime.fromSecsSinceEpoch(int(dt.timestamp())).date(), QLocale.FormatType.ShortFormat
    )
