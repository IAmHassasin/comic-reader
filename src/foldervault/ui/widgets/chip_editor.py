"""Label chip editor: chips with × plus a text input (Enter or comma adds)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QRect, QSize, QStringListModel, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QKeyEvent, QMouseEvent, QPainter, QPalette
from PySide6.QtWidgets import QCompleter, QFrame, QLineEdit, QSizePolicy, QWidget

from ...core.colors import ChipColors
from ...core.labels import InvalidLabelError, split_label_input
from ..painting import CHIP_PAD_X, paint_chip
from ..theme import fonts, icons, tokens
from .flow_layout import FlowLayout

CLOSE_W = 14


class ChipWidget(QWidget):
    remove_requested = Signal(str)
    context_requested = Signal(str)

    def __init__(self, name: str, colors: ChipColors, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.name, self.colors = name, colors
        self.setToolTip(self.tr("Right-click to change the color"))
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda _pos: self.context_requested.emit(self.name))

    def sizeHint(self) -> QSize:  # noqa: N802
        fm = QFontMetrics(fonts.micro())
        return QSize(fm.horizontalAdvance(self.name) + CHIP_PAD_X * 2 + CLOSE_W, 20)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        r = QRect(0, 1, self.width(), 18)
        paint_chip(p, r, "", self.colors, fonts.micro())
        p.setFont(fonts.micro())
        p.setPen(QColor(self.colors.text))
        p.drawText(r.adjusted(CHIP_PAD_X, 0, -CLOSE_W, 0), Qt.AlignmentFlag.AlignVCenter, self.name)
        p.drawPixmap(
            r.right() - CLOSE_W + 1,
            r.y() + 4,
            icons.pixmap("close", self.colors.text, 10, self.devicePixelRatioF()),
        )
        p.end()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if (
            event.button() == Qt.MouseButton.LeftButton
            and event.position().x() >= self.width() - CLOSE_W - 2
        ):
            self.remove_requested.emit(self.name)
            return
        super().mouseReleaseEvent(event)


class ChipEditor(QFrame):
    labels_edited = Signal(list)  # full new label list
    color_requested = Signal(str)
    invalid_input = Signal(str)

    def __init__(
        self, colors_for: Callable[[str], ChipColors], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("chipEditor")
        self.colors_for = colors_for
        self._labels: list[str] = []
        self._layout = FlowLayout(self, margin=4, h_spacing=4, v_spacing=4)
        self.input = QLineEdit(self)
        self.input.setObjectName("chipInput")
        self.input.setPlaceholderText(self.tr("Add label…"))
        self.input.setAccessibleName(self.tr("Add label"))
        self.input.setMinimumWidth(90)
        self.input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        pal = self.input.palette()
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(tokens.current().text_tertiary))
        self.input.setPalette(pal)
        self.input.installEventFilter(self)
        self._completer_model = QStringListModel(self)
        completer = QCompleter(self._completer_model, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.input.setCompleter(completer)
        self._layout.addWidget(self.input)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

    def set_known_labels(self, names: list[str]) -> None:
        self._completer_model.setStringList(names)

    def labels(self) -> list[str]:
        return list(self._labels)

    def set_labels(self, labels: list[str] | tuple[str, ...]) -> None:
        self._labels = list(labels)
        self._rebuild()

    def refresh_colors(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        for i, name in enumerate(self._labels):
            chip = ChipWidget(name, self.colors_for(name), self)
            chip.remove_requested.connect(self._remove)
            chip.context_requested.connect(self.color_requested)
            self._layout.insertWidget(i, chip)
            chip.show()
        self.updateGeometry()

    def _remove(self, name: str) -> None:
        self._labels = [n for n in self._labels if n != name]
        self._rebuild()
        self.labels_edited.emit(self.labels())

    def add_from_text(self, text: str) -> bool:
        try:
            names = split_label_input(text)
        except InvalidLabelError as exc:
            self.invalid_input.emit(str(exc))
            return False
        existing = {n.casefold() for n in self._labels}
        added = [n for n in names if n.casefold() not in existing]
        if added:
            self._labels.extend(added)
            self._rebuild()
            self.labels_edited.emit(self.labels())
        return True

    def eventFilter(self, obj, event: QEvent) -> bool:  # noqa: N802
        if obj is self.input:
            if event.type() == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
                key = event.key()
                popup = self.input.completer().popup()
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
                    popup and popup.isVisible()
                ):
                    if self.input.text().strip() and self.add_from_text(self.input.text()):
                        self.input.clear()
                    return True
                if key == Qt.Key.Key_Comma:
                    if self.input.text().strip() and self.add_from_text(self.input.text()):
                        self.input.clear()
                    return True
                if key == Qt.Key.Key_Backspace and not self.input.text() and self._labels:
                    self._remove(self._labels[-1])
                    return True
                if key == Qt.Key.Key_Escape and self.input.text():
                    self.input.clear()
                    return True
            elif event.type() == QEvent.Type.FocusIn:
                self.setProperty("focused", True)
                self.style().polish(self)
            elif event.type() == QEvent.Type.FocusOut:
                self.setProperty("focused", False)
                self.style().polish(self)
        return super().eventFilter(obj, event)

    def focus_input(self) -> None:
        self.input.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.focus_input()
        super().mousePressEvent(event)
