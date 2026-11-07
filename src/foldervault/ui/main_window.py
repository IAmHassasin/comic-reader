"""Main window: toolbar, context bar, List/Album views, inspector, status bar."""

from __future__ import annotations

import base64
import html
import logging
import random
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import (
    QByteArray,
    QEvent,
    QFileSystemWatcher,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QObject,
    QPoint,
    QSize,
    Qt,
    QTimer,
    QUrl,
)
from PySide6.QtGui import (
    QDesktopServices,
    QKeySequence,
    QMouseEvent,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import __version__, config
from ..core.filtering import FilterState, label_counts
from ..core.labels import InvalidLabelError, normalize_label, split_label_input
from ..core.metadata_io import MetadataFileError, load_metadata_file, write_export_file
from ..data.repository import Repository
from ..services import opener, privacy
from ..services.library import LibraryService, debounce
from ..services.thumbnails import ThumbnailService
from .context import UiContext
from .delegates import (
    ROW_HEIGHT,
    ROW_HEIGHT_THUMBS,
    AlbumCardDelegate,
    LabelsDelegate,
    NameDelegate,
    StarDelegate,
)
from .dialogs.settings_dialog import SettingsDialog
from .dialogs.shortcuts_dialog import ShortcutsDialog
from .formatting import format_count
from .models import COL_LABELS, COL_NAME, COL_STAR, HEADERS, FolderFilterProxy, FolderTableModel
from .settings import Preferences
from .theme import fonts, icons, tokens
from .theme.qss import build_palette, build_qss
from .theme.tokens import build_theme
from .views import CardList, FolderTable
from .widgets.color_picker import LabelColorDialog
from .widgets.flow_layout import FlowLayout
from .widgets.inspector import Inspector
from .widgets.labels_popup import LabelsPopup
from .widgets.search_field import SearchField

log = logging.getLogger(__name__)

PAGE_EMPTY, PAGE_TABLE, PAGE_CARDS, PAGE_NO_RESULTS = range(4)


def _b64(data: QByteArray) -> str:
    return base64.b64encode(bytes(data.data())).decode("ascii")


def _unb64(value: str | None) -> QByteArray | None:
    if not value:
        return None
    try:
        return QByteArray(base64.b64decode(value))
    except ValueError:
        return None


class MainWindow(QMainWindow):
    def __init__(self, repo: Repository) -> None:
        super().__init__()
        self.repo = repo
        self.prefs = Preferences.load(repo)
        self.thumbnails = ThumbnailService(self)
        self.library = LibraryService(repo, self)
        self.ctx = UiContext(
            self.library,
            self.thumbnails,
            list_thumbnails=self.prefs.list_thumbnails,
            cache_hidden_thumbnails=not self.prefs.privacy_no_hidden_thumb_cache,
        )
        self.location = ""
        self._back: list[str] = []
        self._forward: list[str] = []
        self._tool_icons: list[tuple[QToolButton | QPushButton, str, str | None]] = []
        self._fallback_notified = False
        self._view_mode = "list"
        self.setWindowTitle(config.APP_NAME)
        self.resize(1380, 860)
        self.setMinimumSize(900, 560)

        self.model = FolderTableModel(self)
        self.proxy = FolderFilterProxy(self)
        self.proxy.setSourceModel(self.model)

        self._build_ui()
        self._build_shortcuts()
        self._connect()
        self._restore_state()
        QApplication.instance().installEventFilter(self)

        self._repaint_timer = debounce(self, 40, self._repaint_views)
        self.thumbnails.ready.connect(lambda _key: self._repaint_timer.start())
        self.watcher = QFileSystemWatcher(self)
        self._rescan_timer = debounce(self, 2000, self._auto_rescan)
        self.watcher.directoryChanged.connect(lambda _p: self._rescan_timer.start())

        last_root = repo.get_setting("last_root")
        if last_root:
            QTimer.singleShot(0, lambda: self.open_root(last_root))
        else:
            self._update_pages()

    # ================================================================ UI
    def _tool(
        self,
        text: str,
        icon_name: str,
        tip: str,
        checkable: bool = False,
        active_icon: bool = True,
        text_beside: bool = True,
    ) -> QToolButton:
        btn = QToolButton()
        btn.setText(text)
        btn.setToolTip(tip)
        btn.setAccessibleName(text or tip)
        btn.setCheckable(checkable)
        btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        btn.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            if text and text_beside
            else Qt.ToolButtonStyle.ToolButtonIconOnly
        )
        btn.setIconSize(QSize(16, 16))
        self._tool_icons.append((btn, icon_name, "accent" if checkable and active_icon else None))
        return btn

    def _separator(self) -> QFrame:
        sep = QFrame()
        sep.setObjectName("toolbarSeparator")
        sep.setFixedSize(1, 22)
        return sep

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("appRoot")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.setCentralWidget(root)

        # ---------------------------------------------------------- toolbar
        toolbar = QWidget(root)
        toolbar.setObjectName("toolbar")
        toolbar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        flow = FlowLayout(toolbar, margin=6, h_spacing=4, v_spacing=4)
        self.open_btn = self._tool(
            self.tr("Open root"), "folder", self.tr("Open a root folder (Ctrl+O)")
        )
        self.open_btn.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.recent_menu = QMenu(self.open_btn)
        self.recent_menu.aboutToShow.connect(self._fill_recent_menu)
        self.open_btn.setMenu(self.recent_menu)
        self.refresh_btn = self._tool("", "refresh", self.tr("Refresh (F5)"))
        self.up_btn = self._tool("", "arrow_up", self.tr("Up one level (Alt+Up)"))
        self.list_btn = self._tool(
            self.tr("List"), "list", self.tr("List view (Ctrl+Shift+6)"), checkable=True
        )
        self.cards_btn = self._tool(
            self.tr("Album Cards"),
            "cards",
            self.tr("Album Cards view (Ctrl+Shift+8)"),
            checkable=True,
        )
        self.search = SearchField()
        self.search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.levels_btn = self._tool(
            self.tr("All levels"),
            "folder_stack",
            self.tr("Show every subfolder level"),
            checkable=True,
        )
        self.fav_btn = self._tool(
            self.tr("Favorites"), "star", self.tr("Favorites only"), checkable=True
        )
        self.images_only_btn = self._tool(
            self.tr("Image folders only"),
            "image",
            self.tr("Hide folders without images"),
            checkable=True,
        )
        self.hidden_btn = self._tool(
            self.tr("Show hidden"),
            "eye_off",
            self.tr("Show hidden folders (Ctrl+Shift+H)"),
            checkable=True,
        )
        self.labels_btn = self._tool(
            self.tr("Labels: all"), "tag", self.tr("Filter by labels (Ctrl+Shift+L)")
        )
        self.labels_btn.setObjectName("labelsButton")
        self.random_btn = self._tool(
            self.tr("Random"), "shuffle", self.tr("Open a random folder from the list")
        )
        self.settings_btn = self._tool(
            self.tr("Settings"), "settings", self.tr("Settings (Ctrl+,)")
        )
        self.more_btn = self._tool("", "more", self.tr("More"))
        self.more_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.more_btn.setMenu(self._build_more_menu())
        for w in (
            self.open_btn,
            self.refresh_btn,
            self.up_btn,
            self._separator(),
            self.list_btn,
            self.cards_btn,
            self._separator(),
            self.search,
            self.levels_btn,
            self.fav_btn,
            self.images_only_btn,
            self.hidden_btn,
            self._separator(),
            self.labels_btn,
            self.random_btn,
            self.settings_btn,
            self.more_btn,
        ):
            flow.addWidget(w)
        outer.addWidget(toolbar)

        # ------------------------------------------------------ context bar
        ctx_bar = QWidget(root)
        ctx_bar.setObjectName("contextBar")
        ctx_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        cl = QHBoxLayout(ctx_bar)
        cl.setContentsMargins(10, 4, 10, 4)
        self.breadcrumb = QLabel(ctx_bar)
        self.breadcrumb.setObjectName("contextBarText")
        self.breadcrumb.setFont(fonts.caption())
        self.breadcrumb.setTextFormat(Qt.TextFormat.RichText)
        self.breadcrumb.linkActivated.connect(self._on_breadcrumb)
        self.context_right = QLabel(ctx_bar)
        self.context_right.setObjectName("contextBarRight")
        self.context_right.setFont(fonts.caption())
        cl.addWidget(self.breadcrumb, 1)
        cl.addWidget(self.context_right)
        outer.addWidget(ctx_bar)

        # ----------------------------------------------------------- banner
        self.banner = QFrame(root)
        self.banner.setObjectName("banner")
        bl = QHBoxLayout(self.banner)
        bl.setContentsMargins(12, 6, 12, 6)
        self.banner_icon = QLabel()
        self.banner_text = QLabel()
        choose = QPushButton(self.tr("Choose another"))
        choose.clicked.connect(self.choose_root)
        retry = QPushButton(self.tr("Retry"))
        retry.clicked.connect(lambda: self.library.root and self.open_root(str(self.library.root)))
        bl.addWidget(self.banner_icon)
        bl.addWidget(self.banner_text, 1)
        bl.addWidget(choose)
        bl.addWidget(retry)
        self.banner.hide()
        outer.addWidget(self.banner)

        # ------------------------------------------------------- main area
        self.splitter = QSplitter(Qt.Orientation.Horizontal, root)
        self.splitter.setHandleWidth(1)
        self.stack = QStackedWidget(self.splitter)
        self.stack.addWidget(self._build_empty_page())

        self.table = FolderTable()
        self.table.setModel(self.proxy)
        self.table.configure_columns()
        self.star_delegate = StarDelegate(self.table)
        self.table.setItemDelegateForColumn(COL_STAR, self.star_delegate)
        self.table.setItemDelegateForColumn(COL_NAME, NameDelegate(self.ctx, self.table))
        self.table.setItemDelegateForColumn(COL_LABELS, LabelsDelegate(self.ctx, self.table))
        self.table.sortByColumn(COL_NAME, Qt.SortOrder.AscendingOrder)
        self.stack.addWidget(self.table)

        self.cards = CardList()
        self.cards.setModel(self.proxy)
        self.cards.setModelColumn(COL_NAME)
        self.card_delegate = AlbumCardDelegate(self.ctx, self.cards)
        self.cards.setItemDelegate(self.card_delegate)
        self.cards.setSelectionModel(self.table.selectionModel())
        self.stack.addWidget(self.cards)
        self.stack.addWidget(self._build_no_results_page())

        self.inspector = Inspector(self.ctx, self.splitter)
        self.splitter.addWidget(self.stack)
        self.splitter.addWidget(self.inspector)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setCollapsible(0, False)
        self.splitter.setSizes([1000, 340])
        outer.addWidget(self.splitter, 1)

        # ------------------------------------------------------ status bar
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)
        self.status_totals = QLabel()
        self.status_totals.setFont(fonts.caption())
        sb.addWidget(self.status_totals, 1)
        self.status_state = QLabel()
        self.status_state.setFont(fonts.caption())
        self.cancel_btn = QPushButton(self.tr("Cancel"))
        self.cancel_btn.setObjectName("linkBtn")
        self.cancel_btn.hide()
        self.cancel_btn.clicked.connect(self.library.cancel_scan)
        version = QLabel(f"v{__version__}")
        version.setFont(fonts.caption())
        sb.addPermanentWidget(self.status_state)
        sb.addPermanentWidget(self.cancel_btn)
        sb.addPermanentWidget(version)

        self.labels_popup = LabelsPopup(self)
        self._apply_icons()
        self._set_ready()

    def _build_more_menu(self) -> QMenu:
        menu = QMenu(self)
        t = tokens.current()
        menu.addAction(
            icons.icon("import", t.text_primary), self.tr("Import metadata…"), self.import_metadata
        )
        menu.addAction(
            icons.icon("export", t.text_primary), self.tr("Export metadata…"), self.export_metadata
        )
        menu.addSeparator()
        menu.addAction(
            icons.icon("keyboard", t.text_primary),
            self.tr("Keyboard shortcuts\tF1"),
            self.show_shortcuts,
        )
        menu.addAction(
            icons.icon("folder", t.text_primary),
            self.tr("Open app data folder"),
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(config.data_dir()))),
        )
        menu.addAction(self.tr("About FolderVault"), self.show_about)
        return menu

    def _build_empty_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addStretch(1)
        icon = QLabel()
        icon.setPixmap(
            icons.pixmap("folder", tokens.current().accent, 48, self.devicePixelRatioF())
        )
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel(self.tr("Open a folder to start"))
        title.setObjectName("emptyTitle")
        title.setFont(fonts.title())
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text = QLabel(
            self.tr(
                "Choose the root folder of your comic library. FolderVault never changes files in it."
            )
        )
        text.setObjectName("emptyText")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setWordWrap(True)
        btn = QPushButton(self.tr("Open root"))
        btn.setObjectName("primaryBtn")
        btn.clicked.connect(self.choose_root)
        for w in (icon, title, text):
            lay.addWidget(w)
        lay.addSpacing(8)
        lay.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)
        lay.addStretch(2)
        return page

    def _build_no_results_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addStretch(1)
        self.no_results_title = QLabel(self.tr("No folders match"))
        self.no_results_title.setObjectName("emptyTitle")
        self.no_results_title.setFont(fonts.heading())
        self.no_results_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        clear = QPushButton(self.tr("Clear filters"))
        clear.setObjectName("linkBtn")
        clear.clicked.connect(self.clear_filters)
        lay.addWidget(self.no_results_title)
        lay.addWidget(clear, 0, Qt.AlignmentFlag.AlignCenter)
        lay.addStretch(2)
        return page

    def _apply_icons(self) -> None:
        t = tokens.current()
        for btn, name, active in self._tool_icons:
            btn.setIcon(icons.icon(name, t.text_tool, t.accent if active else None))

    # ========================================================= shortcuts
    def _build_shortcuts(self) -> None:
        def sc(keys: str | QKeySequence.StandardKey, fn: Callable[[], None]) -> None:
            seq = QKeySequence(keys)
            shortcut = QShortcut(seq, self)
            shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
            shortcut.activated.connect(fn)

        sc("Ctrl+O", self.choose_root)
        sc("F5", self.refresh)
        sc("Ctrl+R", self.refresh)
        sc("Alt+Up", self.go_up)
        sc("Alt+Left", self.go_back)
        sc("Backspace", self.go_back)
        sc("Alt+Right", self.go_forward)
        for keys in ("Ctrl+F", "Ctrl+E", "F3"):
            sc(keys, self.focus_search)
        sc("Ctrl+Return", self.browse_selected)
        sc("Ctrl+Enter", self.browse_selected)
        sc("Ctrl+Shift+E", self.reveal_selected)
        sc("F2", self.inspector.focus_labels)
        sc("Alt+Return", self.focus_properties)
        sc("Alt+P", self.toggle_inspector)
        sc("Ctrl+Shift+6", lambda: self.set_view_mode("list"))
        sc("Ctrl+Shift+8", lambda: self.set_view_mode("cards"))
        sc("Ctrl+Shift+C", self.copy_paths)
        sc("Ctrl+D", self.toggle_favorite_selected)
        sc("Ctrl+H", self.toggle_hidden_selected)
        sc("Ctrl+Shift+H", self.hidden_btn.click)
        sc("Ctrl+Shift+L", self.show_labels_popup)
        sc("Ctrl+,", self.show_settings)
        sc("F11", self.toggle_fullscreen)
        sc("F1", self.show_shortcuts)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and isinstance(event, QMouseEvent)
            and self.isActiveWindow()
        ):
            if event.button() == Qt.MouseButton.BackButton:
                self.go_back()
                return True
            if event.button() == Qt.MouseButton.ForwardButton:
                self.go_forward()
                return True
        return super().eventFilter(obj, event)

    # =========================================================== signals
    def _connect(self) -> None:
        lib = self.library
        lib.rows_reset.connect(self._on_rows_reset)
        lib.rows_changed.connect(self._on_rows_changed)
        lib.rows_removed.connect(self._on_rows_removed)
        lib.labels_changed.connect(self._on_labels_changed)
        lib.scan_started.connect(self._on_scan_started)
        lib.scan_progress.connect(self._on_scan_progress)
        lib.scan_finished.connect(self._on_scan_finished)
        lib.root_changed.connect(self._on_root_changed)
        lib.root_missing.connect(self._on_root_missing)

        self.open_btn.clicked.connect(self.choose_root)
        self.refresh_btn.clicked.connect(self.refresh)
        self.up_btn.clicked.connect(self.go_up)
        self.list_btn.clicked.connect(lambda: self.set_view_mode("list"))
        self.cards_btn.clicked.connect(lambda: self.set_view_mode("cards"))
        self.search.search_changed.connect(lambda _t: self._update_filter())
        self.search.escape_pressed.connect(self._focus_view)
        self.search.returnPressed.connect(self._focus_view)
        for btn in (self.levels_btn, self.fav_btn, self.images_only_btn, self.hidden_btn):
            btn.toggled.connect(lambda _c: self._update_filter())
        self.labels_btn.clicked.connect(self.show_labels_popup)
        self.random_btn.clicked.connect(self.open_random)
        self.settings_btn.clicked.connect(self.show_settings)

        self.labels_popup.filter_changed.connect(self._on_label_filter)
        self.labels_popup.color_requested.connect(self.change_label_color)
        self.labels_popup.rename_requested.connect(self.rename_label)
        self.labels_popup.delete_requested.connect(self.delete_label)

        self.star_delegate.toggled.connect(lambda fid, v: self.library.set_favorite([fid], v))
        self.card_delegate.favorite_clicked.connect(
            lambda fid, v: self.library.set_favorite([fid], v)
        )
        for view in (self.table, self.cards):
            view.activated.connect(self._on_activated)
            view.customContextMenuRequested.connect(lambda pos, v=view: self._context_menu(v, pos))
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.proxy.rowsInserted.connect(lambda *_: self._after_proxy_change())
        self.proxy.rowsRemoved.connect(lambda *_: self._after_proxy_change())
        self.proxy.modelReset.connect(self._after_proxy_change)
        self.proxy.layoutChanged.connect(self._update_context_right)

        insp = self.inspector
        insp.open_requested.connect(self.open_folder_by_id)
        insp.favorite_requested.connect(self.library.set_favorite)
        insp.hide_requested.connect(self.library.set_hidden)
        insp.labels_edited.connect(self.library.set_labels)
        insp.bulk_add_requested.connect(self.bulk_add_labels)
        insp.bulk_remove_requested.connect(self.bulk_remove_labels)
        insp.color_requested.connect(self.change_label_color)
        insp.status_message.connect(lambda m: self.statusBar().showMessage(m, 5000))

    # ============================================================ state
    def _restore_state(self) -> None:
        geo = _unb64(self.repo.get_setting("window_geometry"))
        if geo:
            self.restoreGeometry(geo)
        header = _unb64(self.repo.get_setting("header_state"))
        if header:
            self.table.horizontalHeader().restoreState(header)
        sizes = self.repo.get_setting("splitter_sizes")
        if isinstance(sizes, list) and len(sizes) == 2:
            self.splitter.setSizes([int(s) for s in sizes])
        self.inspector.setVisible(self.repo.get_setting("inspector_visible", True))
        f = self.repo.get_setting("filters", {}) or {}
        for btn, key, default in (
            (self.levels_btn, "all_levels", True),
            (self.fav_btn, "favorites", False),
            (self.images_only_btn, "images_only", False),
            (self.hidden_btn, "show_hidden", False),
        ):
            btn.blockSignals(True)
            btn.setChecked(bool(f.get(key, default)))
            btn.blockSignals(False)
        self.set_view_mode(self.repo.get_setting("view_mode", "list"), save=False)
        self._apply_row_height()
        self._update_filter()

    def _save_state(self) -> None:
        self.repo.set_setting("window_geometry", _b64(self.saveGeometry()))
        self.repo.set_setting("header_state", _b64(self.table.horizontalHeader().saveState()))
        self.repo.set_setting("splitter_sizes", self.splitter.sizes())
        self.repo.set_setting("inspector_visible", self.inspector.isVisible())
        self.repo.set_setting(
            "filters",
            {
                "all_levels": self.levels_btn.isChecked(),
                "favorites": self.fav_btn.isChecked(),
                "images_only": self.images_only_btn.isChecked(),
                "show_hidden": self.hidden_btn.isChecked(),
            },
        )

    def _apply_row_height(self) -> None:
        self.table.set_row_height(ROW_HEIGHT_THUMBS if self.ctx.list_thumbnails else ROW_HEIGHT)

    # ========================================================== library
    def choose_root(self) -> None:
        start = str(self.library.root) if self.library.root else str(Path.home())
        path = QFileDialog.getExistingDirectory(self, self.tr("Open root folder"), start)
        if path:
            self.open_root(path)

    def open_root(self, path: str) -> None:
        self.location = ""
        self._back.clear()
        self._forward.clear()
        self.library.open_root(path)
        self._watch_root()
        self._update_filter()

    def _watch_root(self) -> None:
        if self.watcher.directories():
            self.watcher.removePaths(self.watcher.directories())
        if self.library.root and self.library.root.is_dir() and self.prefs.auto_refresh:
            self.watcher.addPath(str(self.library.root))

    def _auto_rescan(self) -> None:
        if self.prefs.auto_refresh and not self.library.scanning:
            self.library.start_scan()

    def refresh(self) -> None:
        if self.library.root is None:
            self.choose_root()
            return
        if not self.library.root.is_dir():
            self.open_root(str(self.library.root))
            return
        self.thumbnails.clear_memory()
        self.library.start_scan()

    def _fill_recent_menu(self) -> None:
        self.recent_menu.clear()
        recent = self.repo.get_setting("recent_roots", []) or []
        if not recent:
            act = self.recent_menu.addAction(self.tr("No recent roots"))
            act.setEnabled(False)
            return
        for path in recent:
            self.recent_menu.addAction(path, lambda p=path: self.open_root(p))

    def _on_root_changed(self, root: str) -> None:
        self.banner.hide()
        self.model.set_location(self.location)
        self._update_breadcrumb()
        self._update_pages()

    def _on_root_missing(self, root: str) -> None:
        self.banner_icon.setPixmap(
            icons.pixmap("warning", tokens.current().warning, 16, self.devicePixelRatioF())
        )
        self.banner_text.setText(self.tr("Root not found: {0}").format(root))
        self.banner.show()
        self._update_pages()

    def _on_rows_reset(self, rows: list) -> None:
        selected = self._selected_ids()
        self.model.reset_rows(rows)
        self._restore_selection(selected)
        self._refresh_after_rows()

    def _on_rows_changed(self, rows: list) -> None:
        self.model.upsert_rows(rows)
        changed = {r.id for r in rows}
        if changed & set(self._selected_ids()):
            self._on_selection_changed()
        self._refresh_after_rows()

    def _on_rows_removed(self, ids: list) -> None:
        self.model.remove_ids(ids)
        self._refresh_after_rows()

    def _refresh_after_rows(self) -> None:
        self._update_status()
        self._update_pages()
        if self.labels_popup.isVisible():
            self._fill_labels_popup()

    def _on_labels_changed(self) -> None:
        self.model.refresh_all()
        self.inspector.refresh_colors()
        self._repaint_views()
        self._update_labels_button()

    # ------------------------------------------------------------ scan
    def _set_ready(self) -> None:
        self.status_state.setText(
            f"<span style='color:{tokens.current().success}'>●</span> " + self.tr("Ready")
        )

    def _on_scan_started(self) -> None:
        self.status_state.setText(self.tr("Scanning…"))
        self.cancel_btn.show()

    def _on_scan_progress(self, count: int) -> None:
        self.status_state.setText(self.tr("Scanning {0} folders…").format(format_count(count)))

    def _on_scan_finished(self, cancelled: bool, errors: int) -> None:
        self.cancel_btn.hide()
        self._set_ready()
        if cancelled:
            self.statusBar().showMessage(self.tr("Scan cancelled"), 4000)
        elif errors:
            self.statusBar().showMessage(
                self.tr("Scan finished with {0} unreadable folders (see log)").format(errors), 8000
            )
        self._update_status()
        self._on_selection_changed()

    # ========================================================= filtering
    def _filter_state(self) -> FilterState:
        current = self.proxy.state
        return replace(
            current,
            location=self.location,
            all_levels=self.levels_btn.isChecked(),
            search=self.search.text(),
            favorites_only=self.fav_btn.isChecked(),
            image_folders_only=self.images_only_btn.isChecked(),
            show_hidden=self.hidden_btn.isChecked(),
        )

    def _update_filter(self) -> None:
        self.proxy.set_state(self._filter_state())
        self._update_breadcrumb()
        self._update_labels_button()
        self._after_proxy_change()

    def _on_label_filter(self, selected: frozenset, match_all: bool, no_label: bool) -> None:
        self.proxy.set_state(
            replace(self.proxy.state, labels=selected, match_all=match_all, no_label=no_label)
        )
        self._update_labels_button()
        self._update_breadcrumb()
        self._after_proxy_change()
        self._fill_labels_popup()

    def clear_filters(self) -> None:
        self.search.clear()
        for btn in (self.fav_btn, self.images_only_btn):
            btn.setChecked(False)
        self.proxy.set_state(
            replace(
                self._filter_state(), search="", labels=frozenset(), match_all=False, no_label=False
            )
        )
        self._update_labels_button()
        self._update_breadcrumb()
        self._after_proxy_change()

    def _after_proxy_change(self) -> None:
        self._update_pages()
        self._update_status()
        self._update_context_right()

    def _update_labels_button(self) -> None:
        state = self.proxy.state
        n = len(state.labels) + (1 if state.no_label else 0)
        self.labels_btn.setText(
            self.tr("Labels: all") if n == 0 else self.tr("Labels: {0} selected").format(n)
        )
        self.labels_btn.setProperty("active", n > 0)
        self.labels_btn.style().unpolish(self.labels_btn)
        self.labels_btn.style().polish(self.labels_btn)

    def show_labels_popup(self) -> None:
        self._fill_labels_popup()
        self.labels_popup.popup_below(self.labels_btn)

    def _fill_labels_popup(self) -> None:
        counts, unlabeled = label_counts(self.model.all_rows(), self.proxy.state)
        s = self.proxy.state
        self.labels_popup.set_data(
            self.library.labels(),
            self.library.chip_colors,
            counts,
            unlabeled,
            s.labels,
            s.match_all,
            s.no_label,
        )

    # ========================================================== navigation
    def _navigate(self, location: str, record: bool = True) -> None:
        if location == self.location:
            return
        if record:
            self._back.append(self.location)
            self._forward.clear()
        self.location = location
        self.model.set_location(location)
        self._update_filter()

    def go_up(self) -> None:
        if self.location:
            self._navigate(self.location.rsplit("/", 1)[0] if "/" in self.location else "")

    def go_back(self) -> None:
        if self._back:
            self._forward.append(self.location)
            self._navigate(self._back.pop(), record=False)

    def go_forward(self) -> None:
        if self._forward:
            self._back.append(self.location)
            self._navigate(self._forward.pop(), record=False)

    def _on_breadcrumb(self, link: str) -> None:
        if link.startswith("nav:"):
            self._navigate(link[4:])

    def _update_breadcrumb(self) -> None:
        if self.library.root is None:
            self.breadcrumb.setText(self.tr("No root folder"))
            self.up_btn.setEnabled(False)
            return
        t = tokens.current()
        link_style = f"color:{t.text_primary}; text-decoration:none; font-weight:600;"
        parts = [f"<a href='nav:' style='{link_style}'>{html.escape(self.library.root_name())}</a>"]
        acc = ""
        for seg in [s for s in self.location.split("/") if s]:
            acc = f"{acc}/{seg}" if acc else seg
            parts.append(
                f"<a href='nav:{html.escape(acc, quote=True)}' style='{link_style}'>{html.escape(seg)}</a>"
            )
        text = " / ".join(parts)
        text += " · " + (
            self.tr("all levels") if self.levels_btn.isChecked() else self.tr("this level")
        )
        labels = sorted(self.proxy.state.labels)
        if labels or self.proxy.state.no_label:
            names = [html.escape(n) for n in labels] + (
                [self.tr("(no label)")] if self.proxy.state.no_label else []
            )
            mode = self.tr("all of") if self.proxy.state.match_all else self.tr("any of")
            text += (
                f" · <span style='color:{t.accent}'>"
                + self.tr("Filtered by {0}: {1}").format(mode, ", ".join(names))
                + "</span>"
            )
        self.breadcrumb.setText(text)
        self.up_btn.setEnabled(bool(self.location))

    def _update_context_right(self) -> None:
        col = self.table.horizontalHeader().sortIndicatorSection()
        order = self.table.horizontalHeader().sortIndicatorOrder()
        name = HEADERS[col] if 0 <= col < len(HEADERS) else HEADERS[COL_NAME]
        direction = (
            self.tr("ascending") if order == Qt.SortOrder.AscendingOrder else self.tr("descending")
        )
        view = (
            self.tr("Album Cards") if self.stack.currentWidget() is self.cards else self.tr("List")
        )
        self.context_right.setText(
            self.tr("{0} · sorted by {1} ({2})").format(view, name, direction)
        )

    # ============================================================== pages
    def _update_pages(self) -> None:
        if self.library.root is None:
            self.stack.setCurrentIndex(PAGE_EMPTY)
            return
        if self.proxy.rowCount() == 0 and self.model.rowCount() > 0:
            self.stack.setCurrentIndex(PAGE_NO_RESULTS)
            return
        self.stack.setCurrentWidget(self.cards if self._view_mode == "cards" else self.table)

    def set_view_mode(self, mode: str, save: bool = True) -> None:
        mode = "cards" if mode == "cards" else "list"
        self._view_mode = mode
        self.list_btn.setChecked(mode == "list")
        self.cards_btn.setChecked(mode == "cards")
        self._update_pages()
        self._update_context_right()
        if save:
            self.repo.set_setting("view_mode", mode)
        current = self.table.currentIndex()
        if current.isValid():
            view = self.cards if mode == "cards" else self.table
            view.scrollTo(current)

    def _active_view(self):
        return self.cards if self._view_mode == "cards" else self.table

    def _focus_view(self) -> None:
        view = self._active_view()
        view.setFocus()
        if not view.currentIndex().isValid() and self.proxy.rowCount():
            view.setCurrentIndex(self.proxy.index(0, COL_NAME))

    def _repaint_views(self) -> None:
        self.table.viewport().update()
        self.cards.viewport().update()

    # ============================================================ status
    def _update_status(self) -> None:
        rows = [r for r in self.model.all_rows() if r.rel_path]
        with_images = sum(1 for r in rows if r.image_count)
        images = sum(r.image_count for r in rows)
        favorites = sum(1 for r in rows if r.is_favorite)
        hidden = sum(1 for r in rows if r.effectively_hidden)
        self.status_totals.setText(
            self.tr(
                "{0} folders · {1} with images · {2} images · {3} favorites · {4} hidden  |  showing {5}"
            ).format(
                format_count(len(rows)),
                format_count(with_images),
                format_count(images),
                format_count(favorites),
                format_count(hidden),
                format_count(self.proxy.rowCount()),
            )
        )

    # ========================================================= selection
    def _selected_ids(self) -> list[int]:
        sm = self.table.selectionModel()
        ids = []
        for index in sm.selectedRows(COL_NAME):
            row = self.proxy.row_at(index.row())
            if row is not None:
                ids.append(row.id)
        return ids

    def _selected_rows(self) -> list:
        return [
            self.proxy.row_at(i.row()) for i in self.table.selectionModel().selectedRows(COL_NAME)
        ]

    def _restore_selection(self, ids: list[int]) -> None:
        sm = self.table.selectionModel()
        selection = QItemSelection()
        first: QModelIndex | None = None
        for fid in ids:
            src = self.model.index_of(fid)
            idx = self.proxy.mapFromSource(src)
            if idx.isValid():
                selection.select(idx.siblingAtColumn(0), idx.siblingAtColumn(len(HEADERS) - 1))
                first = first or idx
        if first is not None:
            sm.select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)
            sm.setCurrentIndex(first, QItemSelectionModel.SelectionFlag.NoUpdate)

    def _on_selection_changed(self, *_args) -> None:
        self.inspector.set_rows([r for r in self._selected_rows() if r is not None])

    # ============================================================ actions
    def _on_activated(self, index: QModelIndex) -> None:
        row = self.proxy.row_at(index.row())
        if row is None:
            return
        if row.image_count:
            self.open_folder(row)
        elif row.subfolder_count:
            self._browse(row)

    def browse_selected(self) -> None:
        rows = self._selected_rows()
        if len(rows) == 1 and rows[0].subfolder_count:
            self._browse(rows[0])

    def _browse(self, row) -> None:
        self.levels_btn.setChecked(False)
        self._navigate(row.rel_path)

    def open_folder_by_id(self, folder_id: int) -> None:
        row = self.model.row_by_id(folder_id)
        if row:
            self.open_folder(row)

    def open_folder(self, row) -> None:
        path = self.ctx.image_path(row)
        if not path:
            return
        mode = opener.OpenMode(self.prefs.open_with)
        result = opener.open_image(path, mode)
        if result is opener.OpenResult.FAILED:
            QMessageBox.warning(
                self,
                self.tr("Couldn't open image"),
                self.tr("Windows couldn't open:\n{0}").format(path),
            )
            return
        if result is opener.OpenResult.FALLBACK and not self._fallback_notified:
            self._fallback_notified = True
            self.statusBar().showMessage(
                self.tr("Couldn't open Windows Photos; used the default app instead"), 8000
            )
        self.library.record_open(row.id)

    def open_random(self) -> None:
        candidates = [r for r in self.proxy.visible_rows() if r.image_count]
        if not candidates:
            self.statusBar().showMessage(self.tr("No image folders in the current list"), 4000)
            return
        row = random.choice(candidates)  # noqa: S311 - not security related
        self._restore_selection([row.id])
        self._active_view().scrollTo(self.proxy.mapFromSource(self.model.index_of(row.id)))
        self.open_folder(row)

    def reveal_selected(self) -> None:
        rows = self._selected_rows()
        if rows:
            row = rows[0]
            target = self.ctx.image_path(row) or self.library.abs_path(row.rel_path)
            if not opener.reveal_in_explorer(target):
                self.statusBar().showMessage(self.tr("Couldn't start Explorer"), 5000)

    def copy_paths(self) -> None:
        rows = self._selected_rows()
        if rows:
            QApplication.clipboard().setText(
                "\n".join(self.library.abs_path(r.rel_path) for r in rows)
            )
            self.statusBar().showMessage(self.tr("Copied {0} path(s)").format(len(rows)), 3000)

    def toggle_favorite_selected(self) -> None:
        rows = self._selected_rows()
        if rows:
            self.library.set_favorite([r.id for r in rows], not all(r.is_favorite for r in rows))

    def toggle_hidden_selected(self) -> None:
        rows = [r for r in self._selected_rows() if not (r.win_hidden and not r.is_hidden)]
        if rows:
            self.library.set_hidden([r.id for r in rows], not all(r.is_hidden for r in rows))
        elif self._selected_rows():
            self.statusBar().showMessage(self.tr("Hidden in Windows. Change it in Explorer."), 5000)

    def focus_search(self) -> None:
        self.search.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.search.selectAll()

    def focus_properties(self) -> None:
        if not self.inspector.isVisible():
            self.inspector.show()
        self.inspector.setFocus()

    def toggle_inspector(self) -> None:
        self.inspector.setVisible(not self.inspector.isVisible())

    def toggle_fullscreen(self) -> None:
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def _context_menu(self, view, pos: QPoint) -> None:
        index = view.indexAt(pos)
        if not index.isValid():
            return
        if not view.selectionModel().isSelected(index):
            self._restore_selection([self.proxy.row_at(index.row()).id])
        rows = self._selected_rows()
        if not rows:
            return
        t = tokens.current()
        menu = QMenu(self)
        single = rows[0] if len(rows) == 1 else None
        act = menu.addAction(
            icons.icon("image", t.text_primary),
            self.tr("Open in Photos\tEnter"),
            lambda: self.open_folder(single),
        )
        act.setEnabled(bool(single and single.image_count))
        act = menu.addAction(
            icons.icon("folder_stack", t.text_primary),
            self.tr("Browse subfolders\tCtrl+Enter"),
            lambda: self._browse(single),
        )
        act.setEnabled(bool(single and single.subfolder_count))
        menu.addAction(
            icons.icon("external", t.text_primary),
            self.tr("Open in Explorer\tCtrl+Shift+E"),
            self.reveal_selected,
        )
        menu.addSeparator()
        fav = all(r.is_favorite for r in rows)
        menu.addAction(
            icons.icon("star_filled" if fav else "star", t.favorite_on),
            self.tr("Unfavorite\tCtrl+D") if fav else self.tr("Favorite\tCtrl+D"),
            self.toggle_favorite_selected,
        )
        hid = all(r.is_hidden for r in rows)
        act = menu.addAction(
            icons.icon("eye" if hid else "eye_off", t.text_primary),
            self.tr("Unhide\tCtrl+H") if hid else self.tr("Hide\tCtrl+H"),
            self.toggle_hidden_selected,
        )
        act.setEnabled(any(not (r.win_hidden and not r.is_hidden) for r in rows))
        if single:
            menu.addAction(
                icons.icon("tag", t.text_primary),
                self.tr("Edit labels\tF2"),
                self.inspector.focus_labels,
            )
        else:
            menu.addAction(
                icons.icon("tag", t.text_primary),
                self.tr("Add label…"),
                lambda: self.bulk_add_labels([r.id for r in rows]),
            )
            menu.addAction(
                self.tr("Remove label…"), lambda: self.bulk_remove_labels([r.id for r in rows])
            )
        menu.addSeparator()
        menu.addAction(self.tr("Copy path\tCtrl+Shift+C"), self.copy_paths)
        menu.exec(view.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------ labels
    def bulk_add_labels(self, ids: list) -> None:
        text, ok = QInputDialog.getText(
            self, self.tr("Add labels"), self.tr("Labels (comma separated):")
        )
        if not ok or not text.strip():
            return
        try:
            names = split_label_input(text)
        except InvalidLabelError as exc:
            QMessageBox.warning(self, self.tr("Invalid label"), str(exc))
            return
        self.library.add_labels(ids, names)

    def bulk_remove_labels(self, ids: list) -> None:
        names = sorted(
            {n for fid in ids if (r := self.model.row_by_id(fid)) for n in r.labels},
            key=str.casefold,
        )
        if not names:
            self.statusBar().showMessage(self.tr("The selected folders have no labels"), 4000)
            return
        name, ok = QInputDialog.getItem(
            self, self.tr("Remove label"), self.tr("Label:"), names, 0, False
        )
        if ok and name:
            self.library.remove_labels(ids, [name])

    def change_label_color(self, name: str) -> None:
        label = next(
            (lbl for lbl in self.library.labels() if lbl.name.casefold() == name.casefold()), None
        )
        if label is None:
            return
        dialog = LabelColorDialog(label.name, label.color, self)
        if dialog.exec():
            self.library.set_label_color(label.name, dialog.chosen())
            if self.labels_popup.isVisible():
                self._fill_labels_popup()

    def rename_label(self, name: str) -> None:
        new, ok = QInputDialog.getText(
            self, self.tr("Rename label"), self.tr("New name:"), text=name
        )
        if not ok or not new.strip() or new.strip() == name:
            return
        try:
            new = normalize_label(new)
        except InvalidLabelError as exc:
            QMessageBox.warning(self, self.tr("Invalid label"), str(exc))
            return
        if new.casefold() != name.casefold() and self.library.label_exists(new):
            answer = QMessageBox.question(
                self,
                self.tr("Merge labels"),
                self.tr("A label named “{0}” already exists. Merge “{1}” into it?").format(
                    new, name
                ),
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.library.rename_label(name, new)
        self._clear_label_from_filter(name)

    def delete_label(self, name: str) -> None:
        answer = QMessageBox.question(
            self,
            self.tr("Delete label"),
            self.tr("Delete “{0}” and remove it from every folder? This can't be undone.").format(
                name
            ),
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.library.delete_label(name)
            self._clear_label_from_filter(name)

    def _clear_label_from_filter(self, name: str) -> None:
        s = self.proxy.state
        if name.casefold() in s.labels:
            self.proxy.set_state(replace(s, labels=s.labels - {name.casefold()}))
            self._update_labels_button()
            self._update_breadcrumb()
        if self.labels_popup.isVisible():
            self._fill_labels_popup()

    # ---------------------------------------------------------- metadata
    def import_metadata(self) -> None:
        if self.library.root is None:
            QMessageBox.information(
                self, self.tr("Import metadata"), self.tr("Open a root folder first.")
            )
            return
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Import metadata"), "", self.tr("JSON files (*.json)")
        )
        if not path:
            return
        try:
            data = load_metadata_file(Path(path))
            preview = self.library.import_metadata(data, dry_run=True)
        except MetadataFileError as exc:
            QMessageBox.warning(
                self, self.tr("Import metadata"), self.tr("The file is not valid:\n{0}").format(exc)
            )
            return
        if data.root and Path(data.root).resolve() != self.library.root.resolve():
            note = self.tr(
                "\n\nNote: the file's root ({0}) differs from the open root; paths are matched against the open root."
            ).format(data.root)
        else:
            note = ""
        box = QMessageBox(self)
        box.setWindowTitle(self.tr("Import metadata"))
        box.setText(
            self.tr("Preview: {0}\n\nApply these changes?").format(preview.summary()) + note
        )
        details = [f"not found: {p}" for p in preview.not_found] + [
            f"warning: {w}" for w in preview.warnings
        ]
        if details:
            box.setDetailedText("\n".join(details))
        box.setStandardButtons(QMessageBox.StandardButton.Apply | QMessageBox.StandardButton.Cancel)
        if box.exec() != QMessageBox.StandardButton.Apply:
            return
        report = self.library.import_metadata(data)
        self.statusBar().showMessage(
            self.tr("Metadata imported: {0}").format(report.summary()), 10000
        )

    def export_metadata(self) -> None:
        if self.library.root is None:
            QMessageBox.information(
                self, self.tr("Export metadata"), self.tr("Open a root folder first.")
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Export metadata"),
            "foldervault-metadata.json",
            self.tr("JSON files (*.json)"),
        )
        if not path:
            return
        items = self.library.export_metadata_items()
        try:
            write_export_file(Path(path), str(self.library.root), items)
        except OSError as exc:
            QMessageBox.warning(self, self.tr("Export metadata"), str(exc))
            return
        self.statusBar().showMessage(self.tr("Exported {0} folders").format(len(items)), 6000)

    # ---------------------------------------------------------- settings
    def show_settings(self, page: str = "General") -> None:
        dialog = SettingsDialog(
            self.prefs,
            self.library,
            self.repo.get_setting("recent_roots", []) or [],
            self.change_label_color,
            self.rename_label,
            self.delete_label,
            self,
        )
        dialog.select_page(page if isinstance(page, str) else "General")
        dialog.clear_history_requested.connect(
            lambda: dialog.show_clear_result(self.clear_history_now())
        )
        if not dialog.exec():
            return
        self.repo.set_setting("recent_roots", dialog.recent_roots)
        old = self.prefs
        self.prefs = dialog.prefs
        self.prefs.save(self.repo)
        self.ctx.list_thumbnails = self.prefs.list_thumbnails
        self.ctx.cache_hidden_thumbnails = not self.prefs.privacy_no_hidden_thumb_cache
        self._apply_row_height()
        if old.accent_base() != self.prefs.accent_base():
            self.apply_theme()
        self._watch_root()
        self._update_title()
        self._repaint_views()

    def clear_history_now(self) -> str:
        keep = str(self.library.root) if self.library.root else None
        return privacy.clear_app_history(self.repo, self.thumbnails, keep).summary()

    def apply_theme(self) -> None:
        theme = build_theme(self.prefs.accent_base())
        tokens.set_current(theme)
        icons.clear_cache()
        QApplication.instance().setPalette(build_palette(theme))
        QApplication.instance().setStyleSheet(build_qss(theme))
        self._apply_icons()
        self._set_ready()
        self._update_breadcrumb()
        self.model.refresh_all()
        self._repaint_views()

    def show_shortcuts(self) -> None:
        ShortcutsDialog(self).exec()

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            self.tr("About FolderVault"),
            self.tr(
                "<b>FolderVault</b> {0}<br>Comic library manager.<br><br>"
                "Reading opens in Windows Photos. FolderVault never changes files in your library.<br>"
                "App data: {1}"
            ).format(__version__, html.escape(str(config.data_dir()))),
        )

    # ------------------------------------------------------- window events
    def _update_title(self) -> None:
        stealth = self.prefs.privacy_stealth_title and (
            not self.isActiveWindow() or self.isMinimized()
        )
        self.setWindowTitle(config.STEALTH_TITLE if stealth else config.APP_NAME)

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802
        if event.type() in (QEvent.Type.ActivationChange, QEvent.Type.WindowStateChange):
            self._update_title()
        super().changeEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._save_state()
        QApplication.instance().removeEventFilter(self)
        self.library.shutdown()
        if self.prefs.privacy_clear_on_exit:
            privacy.clear_app_history(self.repo, self.thumbnails, keep_root=None)
        self.thumbnails.shutdown()
        super().closeEvent(event)
