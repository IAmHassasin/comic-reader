"""Keyboard shortcut cheat sheet (F1)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

SHORTCUTS: list[tuple[str, str]] = [
    ("Ctrl+O", "Open root folder"),
    ("F5 / Ctrl+R", "Refresh (rescan)"),
    ("Alt+↑", "Up one level"),
    ("Alt+← / Backspace / Mouse back", "Back"),
    ("Alt+→ / Mouse forward", "Forward"),
    ("Ctrl+F / Ctrl+E / F3", "Search"),
    ("Esc (in search)", "Clear search"),
    ("Enter / double-click", "Open in Photos (or enter a group folder)"),
    ("Ctrl+Enter", "Browse subfolders"),
    ("Ctrl+Shift+E", "Open in Explorer"),
    ("F2", "Edit labels"),
    ("Alt+Enter", "Show folder properties"),
    ("Alt+P", "Show / hide the details pane"),
    ("Ctrl+Shift+6", "List (Details) view"),
    ("Ctrl+Shift+8", "Album Cards (Content) view"),
    ("Ctrl+A", "Select all"),
    ("Ctrl+Shift+C", "Copy path"),
    ("Shift+F10 / Menu key", "Context menu"),
    ("Ctrl+D", "Toggle favorite"),
    ("Ctrl+H", "Hide / unhide in FolderVault"),
    ("Ctrl+Shift+H", "Show hidden folders"),
    ("Ctrl+Shift+L", "Labels filter"),
    ("Ctrl+,", "Settings"),
    ("F11", "Full screen"),
    ("F1", "This list"),
]


class ShortcutsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Keyboard shortcuts"))
        self.resize(520, 620)
        lay = QVBoxLayout(self)
        table = QTableWidget(len(SHORTCUTS), 2, self)
        table.setHorizontalHeaderLabels([self.tr("Keys"), self.tr("Action")])
        table.verticalHeader().hide()
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i, (keys, action) in enumerate(SHORTCUTS):
            table.setItem(i, 0, QTableWidgetItem(keys))
            table.setItem(i, 1, QTableWidgetItem(self.tr(action)))
        lay.addWidget(table)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)
