"""Fluent-style on/off switch (Qt has no native switch)."""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QWidget

from ..theme import tokens


class ToggleSwitch(QAbstractButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._offset = 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(40, 20)

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = Property(float, _get_offset, _set_offset)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def setChecked(self, checked: bool) -> None:  # noqa: N802
        super().setChecked(checked)
        self._anim.stop()
        self._offset = 1.0 if checked else 0.0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        t = tokens.current()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = QRectF(0.5, 0.5, 39, 19)
        on = self.isChecked()
        enabled = self.isEnabled()
        if on:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(t.accent_fill if enabled else t.surface_highest))
        else:
            p.setPen(QPen(QColor(t.text_secondary if enabled else t.line_default), 1))
            p.setBrush(QColor(t.surface_container))
        p.drawRoundedRect(track, 9.5, 9.5)
        knob_d = 12 if not self.isDown() else 14
        x = 4 + self._offset * (40 - 8 - knob_d)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(t.text_on_accent if on else t.text_secondary))
        p.drawEllipse(QRectF(x, (20 - knob_d) / 2, knob_d, knob_d))
        if self.hasFocus():
            p.setPen(QPen(QColor(t.accent), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(0.5, 0.5, 39, 19).adjusted(-0.0, -0.0, 0, 0), 9.5, 9.5)
        p.end()
