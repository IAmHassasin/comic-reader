"""Shared paint helpers: label chips, pixmap fitting."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPixmap

from ..core.colors import ChipColors
from .theme import tokens

CHIP_HEIGHT = 18
CHIP_PAD_X = 6
CHIP_GAP = 4
CHIP_RADIUS = 4


def chip_width(fm: QFontMetrics, text: str) -> int:
    return fm.horizontalAdvance(text) + CHIP_PAD_X * 2


def paint_chip(painter: QPainter, rect: QRect, text: str, colors: ChipColors, font: QFont) -> None:
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor(colors.border))
    painter.setBrush(QColor(colors.fill))
    painter.drawRoundedRect(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), CHIP_RADIUS, CHIP_RADIUS)
    painter.setFont(font)
    painter.setPen(QColor(colors.text))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    painter.restore()


def paint_chips(
    painter: QPainter,
    rect: QRect,
    labels: Sequence[str],
    colors_for: Callable[[str], ChipColors],
    font: QFont,
    max_lines: int = 1,
) -> None:
    """Paint chips left-to-right, wrapping up to ``max_lines``; overflow becomes '+N'."""
    if not labels:
        return
    fm = QFontMetrics(font)
    overflow_colors = ChipColors(
        fill=tokens.current().surface_highest,
        border=tokens.current().line_strong,
        text=tokens.current().text_secondary,
        dot=tokens.current().text_secondary,
    )
    line_h = CHIP_HEIGHT + CHIP_GAP
    total_h = min(max_lines, max(1, rect.height() // line_h)) * line_h - CHIP_GAP
    y = rect.top() + max(0, (rect.height() - total_h) // 2) if max_lines == 1 else rect.top()
    x = rect.left()
    line = 1
    for i, label in enumerate(labels):
        w = chip_width(fm, label)
        remaining = len(labels) - i - 1
        plus_w = chip_width(fm, f"+{remaining}") + CHIP_GAP if remaining else 0
        if x + w + plus_w > rect.right():
            if line < max_lines and x > rect.left():
                line += 1
                x = rect.left()
                y += line_h
            else:
                more = f"+{len(labels) - i}"
                mw = chip_width(fm, more)
                if x + mw <= rect.right() + 1:
                    paint_chip(painter, QRect(x, y, mw, CHIP_HEIGHT), more, overflow_colors, font)
                return
        w = min(w, rect.right() - x)
        paint_chip(
            painter,
            QRect(x, y, w, CHIP_HEIGHT),
            fm.elidedText(label, Qt.TextElideMode.ElideRight, w - 4),
            colors_for(label),
            font,
        )
        x += w + CHIP_GAP


def fit_rect(pixmap: QPixmap, box: QRect) -> QRect:
    """Aspect-fit rectangle for ``pixmap`` (logical size) centered inside ``box``."""
    dpr = pixmap.devicePixelRatio() or 1.0
    w, h = pixmap.width() / dpr, pixmap.height() / dpr
    if w <= 0 or h <= 0:
        return box
    scale = min(box.width() / w, box.height() / h)
    sw, sh = int(w * scale), int(h * scale)
    return QRect(box.x() + (box.width() - sw) // 2, box.y() + (box.height() - sh) // 2, sw, sh)
