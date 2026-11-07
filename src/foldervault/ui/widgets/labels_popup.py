"""Labels multi-select filter popup (docs/03 §S3)."""

from __future__ import annotations

from collections import Counter

from PySide6.QtCore import QModelIndex, QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QKeyEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

from ...core.colors import ChipColors
from ...core.entities import Label
from ..theme import fonts, icons, tokens

NameRole = Qt.ItemDataRole.UserRole + 1
CountRole = Qt.ItemDataRole.UserRole + 2
DotRole = Qt.ItemDataRole.UserRole + 3


class _LabelRowDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index) -> QSize:  # noqa: N802
        return QSize(200, 34)

    def editorEvent(self, event, model, option, index) -> bool:  # noqa: N802
        return False  # toggling is handled by LabelsPopup (avoids a double toggle)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        t = tokens.current()
        r = option.rect
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if option.state & (QStyle.StateFlag.State_MouseOver | QStyle.StateFlag.State_Selected):
            painter.fillRect(r, QColor(t.surface_high))
        count = index.data(CountRole) or 0
        if not count:
            painter.setOpacity(0.5)
        checked = index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked.value
        box = QRect(r.x() + 12, r.center().y() - 7, 14, 14)
        painter.setPen(QPen(QColor(t.accent if checked else "#4C4D4E"), 1))
        painter.setBrush(QColor(t.accent_fill if checked else t.surface_container))
        painter.drawRoundedRect(box, 3, 3)
        if checked:
            painter.drawPixmap(
                box.adjusted(1, 1, -1, -1),
                icons.pixmap("check", t.text_on_accent, 12, painter.device().devicePixelRatioF()),
            )
        dot = QColor(index.data(DotRole) or t.text_secondary)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(dot)
        painter.drawEllipse(QRect(box.right() + 12, r.center().y() - 4, 8, 8))
        painter.setFont(fonts.body())
        painter.setPen(QColor(t.text_primary))
        count_text = str(count)
        painter.setFont(fonts.micro())
        cw = QFontMetrics(fonts.micro()).horizontalAdvance(count_text) + 12
        pill = QRect(r.right() - cw - 12, r.center().y() - 9, cw, 18)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(t.surface_base))
        painter.drawRoundedRect(pill, 4, 4)
        painter.setPen(QColor(t.text_secondary))
        painter.drawText(pill, Qt.AlignmentFlag.AlignCenter, count_text)
        painter.setFont(fonts.body())
        painter.setPen(QColor(t.text_primary))
        text_rect = QRect(box.right() + 30, r.y(), pill.left() - box.right() - 40, r.height())
        name = index.data(NameRole) or ""
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter,
            QFontMetrics(fonts.body()).elidedText(
                name, Qt.TextElideMode.ElideRight, text_rect.width()
            ),
        )
        painter.restore()


class LabelsPopup(QFrame):
    """Emits ``filter_changed(selected_casefolded_names, match_all, no_label)`` live."""

    filter_changed = Signal(frozenset, bool, bool)
    color_requested = Signal(str)
    rename_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("popup")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top = QWidget(self)
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(10, 10, 10, 6)
        top_layout.setSpacing(8)
        self.search = QLineEdit(top)
        self.search.setPlaceholderText(self.tr("Search labels…"))
        self.search.addAction(
            icons.icon("search", tokens.current().text_secondary),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self.search.textChanged.connect(self._apply_search)
        self.search.installEventFilter(self)
        top_layout.addWidget(self.search)
        options = QHBoxLayout()
        self.match_all = QCheckBox(self.tr("Match ALL"), top)
        self.match_all.setToolTip(
            self.tr("On: folders must have every checked label. Off: any of them.")
        )
        self.no_label = QCheckBox(self.tr("(no label)"), top)
        self.clear_btn = QPushButton(self.tr("Clear"), top)
        self.clear_btn.setObjectName("linkBtn")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        options.addWidget(self.match_all)
        options.addWidget(self.no_label)
        options.addStretch(1)
        options.addWidget(self.clear_btn)
        top_layout.addLayout(options)
        layout.addWidget(top)

        self.list = QListWidget(self)
        self.list.setItemDelegate(_LabelRowDelegate(self.list))
        self.list.setMouseTracking(True)
        self.list.setMaximumHeight(300)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
        self.list.itemClicked.connect(self._toggle_item)
        self.list.installEventFilter(self)
        layout.addWidget(self.list)

        self.empty = QLabel(self.tr("No labels yet. Add one in the inspector."), self)
        self.empty.setObjectName("emptyText")
        self.empty.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self.empty)

        footer = QFrame(self)
        footer.setObjectName("popupFooter")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(12, 6, 12, 6)
        hint = QLabel(self.tr("Space to toggle  ·  Right-click for color  ·  Esc to close"), footer)
        hint.setFont(fonts.micro())
        hint.setObjectName("tertiary")
        fl.addWidget(hint)
        layout.addWidget(footer)

        self.match_all.toggled.connect(self._on_options)
        self.no_label.toggled.connect(self._on_options)
        self.clear_btn.clicked.connect(self.clear)
        self._updating = False

    # -------------------------------------------------------------- data
    def set_data(
        self,
        labels: list[Label],
        colors_for,
        counts: Counter,
        unlabeled: int,
        selected: frozenset[str],
        match_all: bool,
        no_label: bool,
    ) -> None:
        self._updating = True
        self.list.clear()
        for label in labels:
            item = QListWidgetItem()
            item.setData(NameRole, label.name)
            item.setData(CountRole, counts.get(label.name.casefold(), 0))
            colors: ChipColors = colors_for(label.name)
            item.setData(DotRole, colors.dot)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setCheckState(
                Qt.CheckState.Checked
                if label.name.casefold() in selected
                else Qt.CheckState.Unchecked
            )
            item.setToolTip(label.name)
            self.list.addItem(item)
        self.match_all.setChecked(match_all)
        self.no_label.setChecked(no_label)
        self.no_label.setText(self.tr("(no label) {0}").format(unlabeled))
        self.no_label.setEnabled(not match_all)
        self.empty.setVisible(not labels)
        self.list.setVisible(bool(labels))
        self.list.setFixedHeight(min(len(labels), 9) * 34 + 4)
        self._apply_search(self.search.text())
        self._updating = False
        self.adjustSize()

    def selected(self) -> frozenset[str]:
        out = set()
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                out.add(item.data(NameRole).casefold())
        return frozenset(out)

    # ------------------------------------------------------------ events
    def popup_below(self, anchor: QWidget) -> None:
        pos = anchor.mapToGlobal(QPoint(0, anchor.height() + 4))
        screen = QApplication.screenAt(pos) or QApplication.primaryScreen()
        geo = screen.availableGeometry()
        self.adjustSize()
        x = min(pos.x(), geo.right() - self.width())
        self.move(max(geo.left(), x), pos.y())
        self.show()
        self.search.setFocus()

    def clear(self) -> None:
        self._updating = True
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(Qt.CheckState.Unchecked)
        self.no_label.setChecked(False)
        self.match_all.setChecked(False)
        self._updating = False
        self._emit()

    def _toggle_item(self, item: QListWidgetItem) -> None:
        item.setCheckState(
            Qt.CheckState.Unchecked
            if item.checkState() == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        self._emit()

    def _on_options(self) -> None:
        self.no_label.setEnabled(not self.match_all.isChecked())
        if not self._updating:
            self._emit()

    def _emit(self) -> None:
        if self._updating:
            return
        no_label = self.no_label.isChecked() and not self.match_all.isChecked()
        self.filter_changed.emit(self.selected(), self.match_all.isChecked(), no_label)

    def _apply_search(self, text: str) -> None:
        q = text.strip().casefold()
        first_visible = None
        for i in range(self.list.count()):
            item = self.list.item(i)
            hide = bool(q) and q not in item.data(NameRole).casefold()
            item.setHidden(hide)
            if not hide and first_visible is None:
                first_visible = item
        if first_visible is not None:
            self.list.setCurrentItem(first_visible)

    def _context_menu(self, pos: QPoint) -> None:
        item = self.list.itemAt(pos)
        if item is None:
            return
        name = item.data(NameRole)
        menu = QMenu(self)
        menu.addAction(self.tr("Change color…"), lambda: self.color_requested.emit(name))
        menu.addAction(self.tr("Rename…"), lambda: self.rename_requested.emit(name))
        menu.addSeparator()
        menu.addAction(self.tr("Delete label…"), lambda: self.delete_requested.emit(name))
        menu.exec(self.list.viewport().mapToGlobal(pos))

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if isinstance(event, QKeyEvent) and event.type() == QKeyEvent.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.close()
                return True
            if obj is self.search and key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                self.list.setFocus()
                QApplication.sendEvent(self.list, event)
                return True
            if obj is self.list and key == Qt.Key.Key_Space:
                item = self.list.currentItem()
                if item is not None:
                    self._toggle_item(item)
                return True
            if (
                obj is self.list
                and event.text()
                and event.text().isprintable()
                and key != Qt.Key.Key_Space
            ):
                self.search.setFocus()
                self.search.insert(event.text())
                return True
        return super().eventFilter(obj, event)
