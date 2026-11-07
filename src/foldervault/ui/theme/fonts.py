"""Text styles derived from the system UI font (same font as Windows Explorer)."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


def _derive(delta_pt: float, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont(QApplication.font())
    base = font.pointSizeF() if font.pointSizeF() > 0 else 9.0
    font.setPointSizeF(max(6.0, base + delta_pt))
    font.setWeight(weight)
    return font


def title() -> QFont:
    return _derive(5, QFont.Weight.DemiBold)


def heading() -> QFont:
    return _derive(2, QFont.Weight.DemiBold)


def subheading() -> QFont:
    return _derive(0, QFont.Weight.DemiBold)


def body() -> QFont:
    return _derive(0)


def body_medium() -> QFont:
    return _derive(0, QFont.Weight.Medium)


def caption() -> QFont:
    return _derive(-1)


def caption_bold() -> QFont:
    return _derive(-1, QFont.Weight.DemiBold)


def micro() -> QFont:
    font = _derive(-1.5, QFont.Weight.DemiBold)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.4)
    return font


def micro_upper() -> QFont:
    font = micro()
    font.setCapitalization(QFont.Capitalization.AllUppercase)
    return font
