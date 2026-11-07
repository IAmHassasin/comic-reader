"""Small stroke icon set (authored for this project), recolored at runtime."""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_STROKE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    "{body}</svg>"
)

_PATHS: dict[str, str] = {
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "folder_stack": '<path d="M2 10a2 2 0 0 1 2-2h4l2 2h7a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H4'
    'a2 2 0 0 1-2-2z"/><path d="M6 5h4l2 2h7a2 2 0 0 1 2 2v6"/>',
    "refresh": '<path d="M20 12a8 8 0 1 1-2.34-5.66"/><path d="M20 4v4h-4"/>',
    "arrow_up": '<path d="M12 19V5"/><path d="M5 12l7-7 7 7"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    "star": '<path d="M12 3l2.8 5.9 6.2.7-4.6 4.3 1.2 6.1L12 17l-5.6 3 1.2-6.1L3 9.6l6.2-.7z"/>',
    "star_filled": '<path fill="{color}" d="M12 3l2.8 5.9 6.2.7-4.6 4.3 1.2 6.1L12 17l-5.6 3 '
    '1.2-6.1L3 9.6l6.2-.7z"/>',
    "settings": '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/>'
    '<circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    "shuffle": '<path d="M16 3h5v5"/><path d="M4 20L21 3"/><path d="M21 16v5h-5"/>'
    '<path d="M15 15l6 6"/><path d="M4 4l5 5"/>',
    "list": '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    "cards": '<rect x="3" y="4" width="18" height="7" rx="1.5"/>'
    '<rect x="3" y="13" width="18" height="7" rx="1.5"/>',
    "eye_off": '<path d="M3 3l18 18"/><path d="M10.6 5.1A10 10 0 0 1 12 5c6 0 10 7 10 7a17 17 0 0 '
    '1-3.2 3.9"/><path d="M6.6 6.6C3.9 8.3 2 12 2 12s4 7 10 7a9.6 9.6 0 0 0 5.4-1.6"/>'
    '<path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
    "eye": '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "tag": '<path d="M20.6 13.4l-7.2 7.2a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/>'
    '<circle cx="7.5" cy="7.5" r="1.5"/>',
    "more": '<circle cx="5" cy="12" r="1.2" fill="{color}"/><circle cx="12" cy="12" r="1.2" '
    'fill="{color}"/><circle cx="19" cy="12" r="1.2" fill="{color}"/>',
    "external": '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
    '<path d="M15 3h6v6"/><path d="M10 14L21 3"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "warning": '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18h.01"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/>'
    '<path d="M21 15l-5-5L5 21"/>',
    "chevron_down": '<path d="M6 9l6 6 6-6"/>',
    "check": '<path d="M5 12l5 5L20 7"/>',
    "import": '<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M4 21h16"/>',
    "export": '<path d="M12 15V3"/><path d="M7 8l5-5 5 5"/><path d="M4 21h16"/>',
    "keyboard": '<rect x="2" y="6" width="20" height="12" rx="2"/>'
    '<path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/>',
}


def svg(name: str, color: str) -> bytes:
    body = _PATHS[name].replace("{color}", color)
    return _STROKE.format(color=color, body=body).encode("utf-8")


@lru_cache(maxsize=512)
def pixmap(name: str, color: str, size: int, dpr: float = 1.0) -> QPixmap:
    px_size = max(1, round(size * dpr))
    pm = QPixmap(px_size, px_size)
    pm.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(svg(name, color)))
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, px_size, px_size))
    painter.end()
    pm.setDevicePixelRatio(dpr)
    return pm


@lru_cache(maxsize=256)
def icon(name: str, color: str, active_color: str | None = None) -> QIcon:
    result = QIcon()
    for size in (16, 20, 24, 32, 48):
        result.addPixmap(pixmap(name, color, size), QIcon.Mode.Normal, QIcon.State.Off)
        if active_color:
            result.addPixmap(pixmap(name, active_color, size), QIcon.Mode.Normal, QIcon.State.On)
            result.addPixmap(pixmap(name, active_color, size), QIcon.Mode.Active, QIcon.State.On)
    return result


def clear_cache() -> None:
    pixmap.cache_clear()
    icon.cache_clear()
