"""Label / accent color picker: palette swatches + any custom color."""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ...core.colors import PALETTE, chip_colors, is_hex_color
from ..painting import chip_width, paint_chip
from ..theme import fonts, icons, tokens


class Swatch(QAbstractButton):
    def __init__(self, color: str | None, tooltip: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.color = color  # None = the "custom" swatch
        self.setCheckable(True)
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(26, 26)

    def paintEvent(self, event) -> None:  # noqa: N802
        t = tokens.current()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        inner = QRect(3, 3, 20, 20)
        if self.color:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(self.color))
            p.drawEllipse(inner)
        else:
            p.setPen(QPen(QColor(t.line_strong), 1))
            p.setBrush(QColor(t.surface_container))
            p.drawEllipse(inner)
            p.drawPixmap(
                inner.adjusted(3, 3, -3, -3),
                icons.pixmap("plus", t.text_primary, 14, self.devicePixelRatioF()),
            )
        if self.isChecked() or self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(t.text_primary if self.isChecked() else t.accent), 2))
            p.drawEllipse(QRect(1, 1, 24, 24))
        p.end()


class ChipPreview(QWidget):
    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.name = name
        self.color: str | None = None
        self.setMinimumHeight(24)

    def set_color(self, color: str | None) -> None:
        self.color = color
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        font = fonts.micro()
        from PySide6.QtGui import QFontMetrics

        w = chip_width(QFontMetrics(font), self.name)
        paint_chip(p, QRect(0, 3, w, 18), self.name, chip_colors(self.name, self.color), font)
        p.end()


class ColorRow(QWidget):
    """Row of palette swatches plus a 'Custom…' swatch. Emits a palette key or '#RRGGBB'."""

    color_changed = Signal(str)

    def __init__(self, palette: dict[str, str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self._swatches: list[Swatch] = []
        self._keys: dict[Swatch, str] = {}
        for key, hex_color in palette.items():
            sw = Swatch(hex_color, key.capitalize(), self)
            self._keys[sw] = key
            sw.clicked.connect(lambda _=False, s=sw: self._pick(s))
            layout.addWidget(sw)
            self._swatches.append(sw)
        self._custom = Swatch(None, self.tr("Custom color…"), self)
        self._custom.clicked.connect(self._pick_custom)
        layout.addWidget(self._custom)
        layout.addStretch(1)
        self._value: str | None = None

    def value(self) -> str | None:
        return self._value

    def set_value(self, value: str | None) -> None:
        self._value = value
        for sw, key in self._keys.items():
            sw.setChecked(value == key)
        is_custom = bool(value) and value not in self._keys.values()
        self._custom.setChecked(is_custom)
        self._custom.color = value if is_custom and value and is_hex_color(value) else None
        self._custom.update()

    def _pick(self, sw: Swatch) -> None:
        self.set_value(self._keys[sw])
        self.color_changed.emit(self._keys[sw])

    def _pick_custom(self) -> None:
        start = (
            QColor(self._value)
            if self._value and is_hex_color(self._value)
            else QColor(tokens.current().accent)
        )
        color = QColorDialog.getColor(start, self, self.tr("Choose a color"))
        if not color.isValid():
            self.set_value(self._value)
            return
        value = color.name(QColor.NameFormat.HexRgb).upper()
        self.set_value(value)
        self.color_changed.emit(value)


class LabelColorDialog(QDialog):
    def __init__(self, label_name: str, current: str | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Label color"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(12)
        title = QLabel(self.tr("Color for “{0}”").format(label_name))
        title.setFont(fonts.subheading())
        layout.addWidget(title)
        self.row = ColorRow({k: v.dot for k, v in PALETTE.items()}, self)
        layout.addWidget(self.row)
        self.preview = ChipPreview(label_name, self)
        layout.addWidget(self.preview)
        self.row.color_changed.connect(self.preview.set_color)
        initial = current
        self.row.set_value(initial)
        self.preview.set_color(initial)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primaryBtn")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(self._reset)
        layout.addWidget(buttons)
        self._reset_requested = False

    def _reset(self) -> None:
        self.row.set_value(None)
        self.preview.set_color(None)

    def chosen(self) -> str | None:
        return self.row.value()
