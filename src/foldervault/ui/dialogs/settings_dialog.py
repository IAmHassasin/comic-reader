"""Settings: General / Appearance / Labels / Privacy (docs/03 §S5)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QColorDialog,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...services.library import LibraryService
from ...services.windows_accent import windows_accent_color
from ..settings import Preferences
from ..theme import fonts, icons, tokens
from ..widgets.toggle_switch import ToggleSwitch


def _group(parent: QWidget) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame(parent)
    frame.setObjectName("settingsGroup")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    return frame, lay


def _section(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("sectionLabel")
    label.setFont(fonts.micro_upper())
    label.setContentsMargins(2, 8, 0, 2)
    return label


def _switch_row(title: str, caption: str, switch: ToggleSwitch, last: bool = False) -> QFrame:
    row = QFrame()
    if not last:
        row.setObjectName("settingsRow")
    lay = QHBoxLayout(row)
    lay.setContentsMargins(12, 8, 12, 8)
    text = QVBoxLayout()
    text.setSpacing(2)
    t = QLabel(title)
    t.setFont(fonts.body_medium())
    c = QLabel(caption)
    c.setObjectName("secondary")
    c.setFont(fonts.caption())
    c.setWordWrap(True)
    text.addWidget(t)
    text.addWidget(c)
    lay.addLayout(text, 1)
    switch.setAccessibleName(title)
    lay.addWidget(switch, 0, Qt.AlignmentFlag.AlignVCenter)
    t.setBuddy(switch)
    return row


def _swatch_icon(color: str) -> QIcon:
    pm = QPixmap(16, 16)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawEllipse(2, 2, 12, 12)
    p.end()
    return QIcon(pm)


class SettingsDialog(QDialog):
    """Preferences are applied on Save. Label edits apply immediately."""

    clear_history_requested = Signal()

    PAGES = ("General", "Appearance", "Labels", "Privacy")

    def __init__(
        self,
        prefs: Preferences,
        library: LibraryService,
        recent_roots: list[str],
        on_label_color: Callable[[str], None],
        on_label_rename: Callable[[str], None],
        on_label_delete: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Settings"))
        self.resize(760, 560)
        self.prefs = replace(prefs)
        self.library = library
        self.recent_roots = list(recent_roots)
        self._on_label_color = on_label_color
        self._on_label_rename = on_label_rename
        self._on_label_delete = on_label_delete

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        body = QHBoxLayout()
        body.setSpacing(0)
        self.nav = QListWidget(self)
        self.nav.setObjectName("settingsNav")
        self.nav.setFixedWidth(170)
        self.nav.setFont(fonts.body_medium())
        self.stack = QStackedWidget(self)
        body.addWidget(self.nav)
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)

        builders = (self._general, self._appearance, self._labels, self._privacy)
        icon_names = ("settings", "eye", "tag", "eye_off")
        t = tokens.current()
        for name, icon_name, build in zip(self.PAGES, icon_names, builders, strict=True):
            item = QListWidgetItem(icons.icon(icon_name, t.text_secondary), self.tr(name))
            item.setSizeHint(QSize(160, 36))
            self.nav.addItem(item)
            page = QWidget()
            page.setObjectName("settingsPage")
            lay = QVBoxLayout(page)
            lay.setContentsMargins(20, 16, 20, 16)
            lay.setSpacing(8)
            title = QLabel(self.tr(name))
            title.setFont(fonts.title())
            lay.addWidget(title)
            build(lay)
            lay.addStretch(1)
            self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

        footer = QFrame(self)
        footer.setObjectName("dialogFooter")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(16, 10, 16, 10)
        restore = QPushButton(icons.icon("refresh", t.text_primary), self.tr("Restore defaults"))
        restore.clicked.connect(self._restore_defaults)
        cancel = QPushButton(self.tr("Cancel"))
        cancel.clicked.connect(self.reject)
        save = QPushButton(icons.icon("check", t.text_on_accent), self.tr("Save"))
        save.setObjectName("primaryBtn")
        save.setDefault(True)
        save.clicked.connect(self._save)
        fl.addWidget(restore)
        fl.addStretch(1)
        fl.addWidget(cancel)
        fl.addWidget(save)
        root.addWidget(footer)
        self._load_values()

    def select_page(self, name: str) -> None:
        if name in self.PAGES:
            self.nav.setCurrentRow(self.PAGES.index(name))

    # ------------------------------------------------------------- pages
    def _general(self, lay: QVBoxLayout) -> None:
        lay.addWidget(_section(self.tr("Open images with")))
        frame, gl = _group(self)
        self.open_photos = QRadioButton(self.tr("Windows Photos (recommended)"))
        self.open_default = QRadioButton(self.tr("Default image app"))
        self._open_group = QButtonGroup(self)
        for rb in (self.open_photos, self.open_default):
            self._open_group.addButton(rb)
            w = QWidget()
            wl = QHBoxLayout(w)
            wl.setContentsMargins(12, 8, 12, 8)
            wl.addWidget(rb)
            gl.addWidget(w)
        note = QLabel(
            self.tr(
                "Opens the first image of the folder; use ←/→ in Photos to read. "
                "Photos uses its own page order and keeps its own history."
            )
        )
        note.setObjectName("secondary")
        note.setFont(fonts.caption())
        note.setWordWrap(True)
        note.setContentsMargins(12, 0, 12, 10)
        gl.addWidget(note)
        lay.addWidget(frame)

        lay.addWidget(_section(self.tr("Library")))
        frame, gl = _group(self)
        self.auto_refresh = ToggleSwitch()
        self.list_thumbs = ToggleSwitch()
        gl.addWidget(
            _switch_row(
                self.tr("Auto-refresh"),
                self.tr("Rescan when the root folder changes on disk."),
                self.auto_refresh,
            )
        )
        gl.addWidget(
            _switch_row(
                self.tr("Cover thumbnails in List view"),
                self.tr("Shows a small cover next to each folder name."),
                self.list_thumbs,
                last=True,
            )
        )
        lay.addWidget(frame)

        lay.addWidget(_section(self.tr("Recent roots")))
        self.roots_list = QListWidget()
        self.roots_list.setMaximumHeight(120)
        self.roots_list.addItems(self.recent_roots)
        remove = QPushButton(
            icons.icon("close", tokens.current().text_primary), self.tr("Remove selected")
        )
        remove.clicked.connect(self._remove_root)
        lay.addWidget(self.roots_list)
        lay.addWidget(remove, 0, Qt.AlignmentFlag.AlignLeft)

    def _appearance(self, lay: QVBoxLayout) -> None:
        lay.addWidget(_section(self.tr("Accent color")))
        frame, gl = _group(self)
        win = windows_accent_color()
        self.accent_default = QRadioButton(self.tr("Fluent blue"))
        self.accent_windows = QRadioButton(
            self.tr("Windows accent color") + (f"  ({win})" if win else "")
        )
        self.accent_windows.setEnabled(win is not None)
        self.accent_custom = QRadioButton(self.tr("Custom"))
        self._accent_group = QButtonGroup(self)
        self.custom_btn = QPushButton(self.tr("Choose…"))
        self.custom_btn.clicked.connect(self._choose_accent)
        for rb in (self.accent_default, self.accent_windows, self.accent_custom):
            self._accent_group.addButton(rb)
            w = QWidget()
            wl = QHBoxLayout(w)
            wl.setContentsMargins(12, 8, 12, 8)
            wl.addWidget(rb)
            if rb is self.accent_custom:
                wl.addWidget(self.custom_btn)
            wl.addStretch(1)
            gl.addWidget(w)
        self._accent_group.buttonToggled.connect(lambda *_: self._update_preview())
        lay.addWidget(frame)

        lay.addWidget(_section(self.tr("Preview")))
        frame, gl = _group(self)
        self.preview_box = QWidget()
        pl = QHBoxLayout(self.preview_box)
        pl.setContentsMargins(12, 12, 12, 12)
        self.preview_btn = QPushButton(self.tr("Primary"))
        self.preview_row = QLabel(self.tr("  Selected row  "))
        self.preview_input = QLineEdit(self.tr("Focused input"))
        pl.addWidget(self.preview_btn)
        pl.addWidget(self.preview_row)
        pl.addWidget(self.preview_input)
        gl.addWidget(self.preview_box)
        lay.addWidget(frame)
        hint = QLabel(
            self.tr("Surfaces stay dark. Label colors are set per label in the Labels page.")
        )
        hint.setObjectName("secondary")
        hint.setFont(fonts.caption())
        lay.addWidget(hint)

    def _labels(self, lay: QVBoxLayout) -> None:
        hint = QLabel(self.tr("Changes on this page apply immediately."))
        hint.setObjectName("secondary")
        hint.setFont(fonts.caption())
        lay.addWidget(hint)
        self.labels_table = QTableWidget(0, 3)
        self.labels_table.setHorizontalHeaderLabels([self.tr("Label"), self.tr("Folders"), ""])
        self.labels_table.verticalHeader().hide()
        self.labels_table.setShowGrid(False)
        self.labels_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.labels_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.labels_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.labels_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.labels_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.labels_table.horizontalHeader().resizeSection(2, 300)
        self.labels_table.verticalHeader().setDefaultSectionSize(36)
        self.labels_table.setMinimumHeight(360)
        lay.addWidget(self.labels_table, 1)
        self.refresh_labels()

    def refresh_labels(self) -> None:
        table = self.labels_table
        labels = self.library.labels()
        usage = self.library.label_usage()
        table.setRowCount(len(labels))
        for i, label in enumerate(labels):
            item = QTableWidgetItem(
                _swatch_icon(self.library.chip_colors(label.name).dot), label.name
            )
            table.setItem(i, 0, item)
            count = QTableWidgetItem(str(usage.get(label.id, 0)))
            count.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(i, 1, count)
            actions = QWidget()
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(4)
            for text, cb in (
                (self.tr("Color…"), self._on_label_color),
                (self.tr("Rename…"), self._on_label_rename),
                (self.tr("Delete…"), self._on_label_delete),
            ):
                b = QPushButton(text)
                b.clicked.connect(lambda _=False, n=label.name, f=cb: (f(n), self.refresh_labels()))
                al.addWidget(b)
            table.setCellWidget(i, 2, actions)
        if not labels:
            table.setRowCount(0)

    def _privacy(self, lay: QVBoxLayout) -> None:
        info = QFrame()
        info.setObjectName("infoBox")
        il = QHBoxLayout(info)
        il.setContentsMargins(12, 10, 12, 10)
        icon = QLabel()
        icon.setPixmap(
            icons.pixmap("eye_off", tokens.current().accent, 20, self.devicePixelRatioF())
        )
        il.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        text = QLabel(
            self.tr(
                "App-level privacy only. FolderVault does not change Windows settings and does not "
                "encrypt files. Windows Photos and Explorer keep their own history."
            )
        )
        text.setWordWrap(True)
        il.addWidget(text, 1)
        lay.addWidget(info)

        lay.addWidget(_section(self.tr("App privacy")))
        frame, gl = _group(self)
        self.clear_on_exit = ToggleSwitch()
        self.no_hidden_cache = ToggleSwitch()
        self.stealth = ToggleSwitch()
        gl.addWidget(
            _switch_row(
                self.tr("Clear app history on exit"),
                self.tr(
                    "Forgets recent roots and deletes the thumbnail cache when FolderVault closes."
                ),
                self.clear_on_exit,
            )
        )
        gl.addWidget(
            _switch_row(
                self.tr("Don't cache thumbnails of hidden folders"),
                self.tr("Covers of hidden folders stay in memory only."),
                self.no_hidden_cache,
            )
        )
        gl.addWidget(
            _switch_row(
                self.tr("Stealth window title"),
                self.tr("Shows a generic title while the window is inactive or minimized."),
                self.stealth,
                last=True,
            )
        )
        lay.addWidget(frame)

        lay.addWidget(_section(self.tr("Immediate action")))
        row = QHBoxLayout()
        clear_now = QPushButton(
            icons.icon("refresh", tokens.current().text_primary), self.tr("Clear app history now")
        )
        clear_now.clicked.connect(self.clear_history_requested)
        self.clear_result = QLabel("")
        self.clear_result.setObjectName("secondary")
        row.addWidget(clear_now)
        row.addWidget(self.clear_result, 1)
        lay.addLayout(row)

    # ------------------------------------------------------------ values
    def _load_values(self) -> None:
        p = self.prefs
        (self.open_photos if p.open_with == "photos" else self.open_default).setChecked(True)
        self.auto_refresh.setChecked(p.auto_refresh)
        self.list_thumbs.setChecked(p.list_thumbnails)
        {
            "default": self.accent_default,
            "windows": self.accent_windows,
            "custom": self.accent_custom,
        }.get(p.accent_mode, self.accent_default).setChecked(True)
        if p.accent_mode == "windows" and not self.accent_windows.isEnabled():
            self.accent_default.setChecked(True)
        self.clear_on_exit.setChecked(p.privacy_clear_on_exit)
        self.no_hidden_cache.setChecked(p.privacy_no_hidden_thumb_cache)
        self.stealth.setChecked(p.privacy_stealth_title)
        self._update_preview()

    def _collect(self) -> Preferences:
        mode = (
            "custom"
            if self.accent_custom.isChecked()
            else "windows"
            if self.accent_windows.isChecked()
            else "default"
        )
        return replace(
            self.prefs,
            open_with="photos" if self.open_photos.isChecked() else "default",
            auto_refresh=self.auto_refresh.isChecked(),
            list_thumbnails=self.list_thumbs.isChecked(),
            accent_mode=mode,
            privacy_clear_on_exit=self.clear_on_exit.isChecked(),
            privacy_no_hidden_thumb_cache=self.no_hidden_cache.isChecked(),
            privacy_stealth_title=self.stealth.isChecked(),
        )

    def _choose_accent(self) -> None:
        color = QColorDialog.getColor(
            QColor(self.prefs.accent_custom), self, self.tr("Accent color")
        )
        if color.isValid():
            self.prefs.accent_custom = color.name(QColor.NameFormat.HexRgb).upper()
            self.accent_custom.setChecked(True)
            self._update_preview()

    def _update_preview(self) -> None:
        from ...core.colors import derive_accent

        base = (
            replace(self._collect()).accent_base()
            if hasattr(self, "open_photos")
            else self.prefs.accent_base()
        )
        a = derive_accent(base)
        t = tokens.current()
        self.preview_btn.setStyleSheet(
            f"QPushButton {{ background-color: {a.fill}; border: 1px solid {a.fill_hover}; color: {t.text_on_accent}; font-weight: 600; }}"
        )
        self.preview_row.setStyleSheet(
            f"QLabel {{ background-color: {a.selection}; border-left: 3px solid {a.accent}; padding: 6px; }}"
        )
        self.preview_input.setStyleSheet(f"QLineEdit {{ border: 1px solid {a.accent}; }}")
        self.custom_btn.setIcon(_swatch_icon(self.prefs.accent_custom))

    def _restore_defaults(self) -> None:
        self.prefs = Preferences()
        self._load_values()

    def _remove_root(self) -> None:
        for item in self.roots_list.selectedItems():
            self.recent_roots.remove(item.text())
            self.roots_list.takeItem(self.roots_list.row(item))

    def _save(self) -> None:
        self.prefs = self._collect()
        self.accept()

    def show_clear_result(self, text: str) -> None:
        self.clear_result.setText(text)
        self.recent_roots = self.recent_roots[:1] if self.recent_roots else []
        self.roots_list.clear()
        self.roots_list.addItems(self.recent_roots)
