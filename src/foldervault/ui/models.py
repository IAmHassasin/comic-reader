"""Folder table model and its filter/sort proxy."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QSortFilterProxyModel,
    Qt,
)
from PySide6.QtGui import QColor

from ..core.entities import FolderRow
from ..core.filtering import FilterState, accepts
from ..core.natural_sort import fold_text, natural_key
from .theme import tokens

COL_STAR, COL_NAME, COL_IMAGES, COL_SUBFOLDERS, COL_LABELS, COL_VIEWS = range(6)
HEADERS = ("★", "Folder", "Images", "Subfolders", "Labels", "Views")
RowRole = Qt.ItemDataRole.UserRole + 1

_Index = QModelIndex | QPersistentModelIndex


class FolderTableModel(QAbstractTableModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[FolderRow] = []
        self._pos: dict[int, int] = {}
        self._location = ""

    # ---------------------------------------------------------------- data
    def rowCount(self, parent: _Index = QModelIndex()) -> int:  # noqa: B008, N802
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: _Index = QModelIndex()) -> int:  # noqa: B008, N802
        return 0 if parent.isValid() else len(HEADERS)

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:  # noqa: N802
        if orientation != Qt.Orientation.Horizontal:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return HEADERS[section]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if section in (COL_IMAGES, COL_SUBFOLDERS, COL_VIEWS):
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if section == COL_STAR:
                return int(Qt.AlignmentFlag.AlignCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ToolTipRole and section == COL_STAR:
            return "Favorite"
        return None

    def display_name(self, row: FolderRow) -> str:
        if row.meta and row.meta.title:
            return row.meta.title
        loc = self._location
        if loc and row.rel_path.startswith(loc + "/"):
            return row.rel_path[len(loc) + 1 :]
        return row.rel_path

    def data(self, index: _Index, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        col = index.column()
        if role == RowRole:
            return row
        if role == Qt.ItemDataRole.DisplayRole:
            if col == COL_NAME:
                return self.display_name(row)
            if col == COL_IMAGES:
                return f"{row.image_count:,}" if row.image_count else "—"
            if col == COL_SUBFOLDERS:
                return f"{row.subfolder_count:,}" if row.subfolder_count else "—"
            if col == COL_VIEWS:
                return str(row.view_count) if row.view_count else ""
            return None
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (COL_IMAGES, COL_SUBFOLDERS, COL_VIEWS):
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ForegroundRole:
            t = tokens.current()
            if (col == COL_IMAGES and not row.image_count) or (
                col == COL_SUBFOLDERS and not row.subfolder_count
            ):
                return QColor(t.text_tertiary)
            if row.effectively_hidden:
                return QColor(t.text_tertiary)
            return None
        if role == Qt.ItemDataRole.ToolTipRole:
            if col == COL_NAME:
                tip = row.rel_path
                if row.win_hidden:
                    tip += "\nHidden in Windows (Explorer attribute)"
                elif row.is_hidden:
                    tip += "\nHidden in FolderVault"
                return tip
            if col == COL_LABELS and row.labels:
                return ", ".join(row.labels)
            if col == COL_STAR:
                return "Unfavorite (Ctrl+D)" if row.is_favorite else "Favorite (Ctrl+D)"
        if role == Qt.ItemDataRole.AccessibleTextRole and col == COL_NAME:
            return self.display_name(row)
        return None

    # ------------------------------------------------------------- updates
    def row_at(self, source_row: int) -> FolderRow:
        return self._rows[source_row]

    def row_by_id(self, folder_id: int) -> FolderRow | None:
        pos = self._pos.get(folder_id)
        return self._rows[pos] if pos is not None else None

    def all_rows(self) -> list[FolderRow]:
        return self._rows

    def index_of(self, folder_id: int, column: int = COL_NAME) -> QModelIndex:
        pos = self._pos.get(folder_id)
        return self.index(pos, column) if pos is not None else QModelIndex()

    def set_location(self, location: str) -> None:
        self._location = location
        if self._rows:
            self.dataChanged.emit(
                self.index(0, COL_NAME), self.index(len(self._rows) - 1, COL_NAME)
            )

    def reset_rows(self, rows: Sequence[FolderRow]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self._reindex()
        self.endResetModel()

    def upsert_rows(self, rows: Iterable[FolderRow]) -> None:
        new: list[FolderRow] = []
        for row in rows:
            pos = self._pos.get(row.id)
            if pos is None:
                new.append(row)
                continue
            self._rows[pos] = row
            self.dataChanged.emit(self.index(pos, 0), self.index(pos, len(HEADERS) - 1))
        if new:
            start = len(self._rows)
            self.beginInsertRows(QModelIndex(), start, start + len(new) - 1)
            self._rows.extend(new)
            for i, row in enumerate(new, start):
                self._pos[row.id] = i
            self.endInsertRows()

    def remove_ids(self, ids: Iterable[int]) -> None:
        for pos in sorted((self._pos[i] for i in ids if i in self._pos), reverse=True):
            self.beginRemoveRows(QModelIndex(), pos, pos)
            del self._rows[pos]
            self.endRemoveRows()
        self._reindex()

    def refresh_all(self) -> None:
        if self._rows:
            self.dataChanged.emit(
                self.index(0, 0), self.index(len(self._rows) - 1, len(HEADERS) - 1)
            )

    def _reindex(self) -> None:
        self._pos = {row.id: i for i, row in enumerate(self._rows)}


class FolderFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._state = FilterState()
        self.setDynamicSortFilter(True)

    @property
    def state(self) -> FilterState:
        return self._state

    def set_state(self, state: FilterState) -> None:
        if state == self._state:
            return
        self.beginFilterChange()
        self._state = state
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def source(self) -> FolderTableModel:
        model = self.sourceModel()
        assert isinstance(model, FolderTableModel)
        return model

    def filterAcceptsRow(self, source_row: int, source_parent: _Index) -> bool:  # noqa: N802
        return accepts(self.source().row_at(source_row), self._state)

    def lessThan(self, left: _Index, right: _Index) -> bool:  # noqa: N802
        model = self.source()
        a, b = model.row_at(left.row()), model.row_at(right.row())
        col = left.column()
        if col == COL_STAR:
            ka, kb = (not a.is_favorite,), (not b.is_favorite,)
        elif col == COL_IMAGES:
            ka, kb = (a.image_count,), (b.image_count,)
        elif col == COL_SUBFOLDERS:
            ka, kb = (a.subfolder_count,), (b.subfolder_count,)
        elif col == COL_VIEWS:
            ka, kb = (a.view_count,), (b.view_count,)
        elif col == COL_LABELS:
            ka = (not a.labels, fold_text(a.labels[0]) if a.labels else "")
            kb = (not b.labels, fold_text(b.labels[0]) if b.labels else "")
        else:
            ka, kb = (), ()
        if ka != kb:
            return ka < kb
        return natural_key(model.display_name(a)) < natural_key(model.display_name(b))

    def row_at(self, proxy_row: int) -> FolderRow:
        return self.data(self.index(proxy_row, COL_NAME), RowRole)

    def visible_rows(self) -> list[FolderRow]:
        return [self.row_at(i) for i in range(self.rowCount())]
