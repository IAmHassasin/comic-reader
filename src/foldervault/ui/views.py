"""Folder table (List mode) and card list (Album Cards mode)."""

from __future__ import annotations

from PySide6.QtCore import QElapsedTimer, QModelIndex, Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QListView, QTableView, QWidget

from .models import COL_IMAGES, COL_LABELS, COL_NAME, COL_STAR, COL_SUBFOLDERS, COL_VIEWS

TYPE_AHEAD_RESET_MS = 900


class _TypeAheadMixin:
    """Explorer-style type-ahead that always searches the folder name column."""

    def _init_type_ahead(self) -> None:
        self._ta_text = ""
        self._ta_timer = QElapsedTimer()

    def keyboardSearch(self, search: str) -> None:  # noqa: N802
        view: QAbstractItemView = self  # type: ignore[assignment]
        model = view.model()
        if model is None or not search:
            return
        if not self._ta_timer.isValid() or self._ta_timer.elapsed() > TYPE_AHEAD_RESET_MS:
            self._ta_text = ""
        self._ta_timer.restart()
        self._ta_text += search
        current = view.currentIndex()
        start_row = current.row() if current.isValid() else 0
        if len(self._ta_text) == 1 and current.isValid():
            start_row += 1  # repeated single letter cycles through matches
        start = model.index(start_row % max(1, model.rowCount()), COL_NAME)
        hits = model.match(
            start,
            Qt.ItemDataRole.DisplayRole,
            self._ta_text,
            1,
            Qt.MatchFlag.MatchStartsWith | Qt.MatchFlag.MatchWrap,
        )
        if hits:
            index = hits[0].siblingAtColumn(self.name_column())
            view.setCurrentIndex(index)
            view.scrollTo(index)

    def name_column(self) -> int:
        return COL_NAME


class FolderTable(_TypeAheadMixin, QTableView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_type_ahead()
        self.setObjectName("folderTable")
        self.setAccessibleName(self.tr("Folders"))
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setMouseTracking(True)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setTabKeyNavigation(False)
        self.verticalHeader().hide()
        header = self.horizontalHeader()
        header.setSectionsMovable(True)
        header.setHighlightSections(False)
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setMinimumSectionSize(32)

    def configure_columns(self) -> None:
        header = self.horizontalHeader()
        header.setSectionResizeMode(COL_STAR, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(COL_STAR, 34)
        header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(COL_NAME, 340)
        for col, width in ((COL_IMAGES, 80), (COL_SUBFOLDERS, 96), (COL_VIEWS, 64)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(col, width)
        header.setSectionResizeMode(COL_LABELS, QHeaderView.ResizeMode.Stretch)

    def set_row_height(self, height: int) -> None:
        self.verticalHeader().setDefaultSectionSize(height)
        self.verticalHeader().setMinimumSectionSize(height)


class CardList(_TypeAheadMixin, QListView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_type_ahead()
        self.setObjectName("cardList")
        self.setAccessibleName(self.tr("Album cards"))
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setUniformItemSizes(True)
        self.setMouseTracking(True)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(32)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.doItemsLayout()

    def current_or_none(self) -> QModelIndex | None:
        index = self.currentIndex()
        return index if index.isValid() else None
