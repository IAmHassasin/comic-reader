"""Wrapping layout (port of the Qt "Flow Layout" example)."""

from __future__ import annotations

from PySide6.QtCore import QMargins, QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QLayoutItem, QSizePolicy, QWidget


class FlowLayout(QLayout):
    def __init__(
        self, parent: QWidget | None = None, margin: int = 0, h_spacing: int = 4, v_spacing: int = 4
    ) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._h, self._v = h_spacing, v_spacing
        self.setContentsMargins(QMargins(margin, margin, margin, margin))

    def addItem(self, item: QLayoutItem) -> None:  # noqa: N802
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def insertWidget(self, index: int, widget: QWidget) -> None:  # noqa: N802
        self.addChildWidget(widget)
        from PySide6.QtWidgets import QWidgetItem

        self._items.insert(index, QWidgetItem(widget))
        self.invalidate()

    def expandingDirections(self) -> Qt.Orientation:  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:  # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        m = self.contentsMargins()
        effective = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, line_h = effective.x(), effective.y(), 0
        for item in self._items:
            widget = item.widget()
            if widget is not None and widget.isHidden():
                continue
            hint = item.sizeHint()
            stretch = (
                widget is not None
                and widget.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding
            )
            w = hint.width()
            if stretch:
                w = max(hint.width(), min(effective.right() - x, widget.maximumWidth()))
            next_x = x + w + self._h
            if next_x - self._h > effective.right() + 1 and line_h > 0:
                x = effective.x()
                y += line_h + self._v
                if stretch:
                    w = max(hint.width(), min(effective.width(), widget.maximumWidth()))
                next_x = x + w + self._h
                line_h = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), QSize(w, hint.height())))
            x = next_x
            line_h = max(line_h, hint.height())
        return y + line_h - rect.y() + m.bottom()
