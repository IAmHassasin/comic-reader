"""Search box with a leading icon, a Ctrl+F hint and a debounced change signal."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeyEvent, QPalette
from PySide6.QtWidgets import QLabel, QLineEdit, QWidget

from ..theme import fonts, icons, tokens

DEBOUNCE_MS = 150


class SearchField(QLineEdit):
    search_changed = Signal(str)
    escape_pressed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        t = tokens.current()
        self.setPlaceholderText(self.tr("Search name, label or title…"))
        self.setAccessibleName(self.tr("Search"))
        self.addAction(
            icons.icon("search", t.text_secondary), QLineEdit.ActionPosition.LeadingPosition
        )
        self.setClearButtonEnabled(False)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(t.text_tertiary))
        self.setPalette(pal)
        self._hint = QLabel("Ctrl+F", self)
        self._hint.setFont(fonts.micro())
        self._hint.setObjectName("tertiary")
        self._hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(DEBOUNCE_MS)
        self._timer.timeout.connect(lambda: self.search_changed.emit(self.text()))
        self.textChanged.connect(self._on_text)
        self.setMinimumWidth(220)
        self.setMaximumWidth(360)

    def _on_text(self, text: str) -> None:
        self._hint.setVisible(not text)
        self._timer.start()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        hint = self._hint.sizeHint()
        self._hint.move(self.width() - hint.width() - 8, (self.height() - hint.height()) // 2)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            if self.text():
                self.clear()
                self._timer.stop()
                self.search_changed.emit("")
            self.escape_pressed.emit()
            return
        super().keyPressEvent(event)
