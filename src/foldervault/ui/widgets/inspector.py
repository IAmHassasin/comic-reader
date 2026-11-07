"""Right-side detail panel (docs/03 §S1b)."""

from __future__ import annotations

from collections import Counter

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...core.entities import FolderRow
from ..context import UiContext
from ..formatting import format_count, human_size, relative_time
from ..painting import fit_rect
from ..theme import fonts, icons, tokens
from .chip_editor import ChipEditor

PREVIEW_W, PREVIEW_H = 320, 240


class _PreviewLabel(QLabel):
    clicked = Signal()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


def _section(text: str, parent: QWidget) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName("sectionLabel")
    label.setFont(fonts.micro_upper())
    return label


class Inspector(QFrame):
    open_requested = Signal(int)
    favorite_requested = Signal(list, bool)
    hide_requested = Signal(list, bool)
    labels_edited = Signal(int, list)
    bulk_add_requested = Signal(list)
    bulk_remove_requested = Signal(list)
    color_requested = Signal(str)
    status_message = Signal(str)

    def __init__(self, ctx: UiContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.setObjectName("inspector")
        self.setMinimumWidth(280)
        self._rows: list[FolderRow] = []

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        body = QWidget()
        body.setObjectName("inspectorBody")
        body.setStyleSheet("")  # inherits #inspector background through the frame
        scroll.setWidget(body)
        scroll.viewport().setAutoFillBackground(False)
        body.setAutoFillBackground(False)
        lay = QVBoxLayout(body)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
        self._layout = lay

        self.preview = _PreviewLabel(body)
        self.preview.setObjectName("previewBox")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(PREVIEW_H)
        self.preview.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.preview.setToolTip(self.tr("Open in Photos"))
        self.preview.clicked.connect(self._open)
        lay.addWidget(self.preview)

        head = QHBoxLayout()
        self.title = QLabel(body)
        self.title.setFont(fonts.heading())
        self.title.setWordWrap(True)
        self.title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.star = QLabel(body)
        self.count_pill = QLabel(body)
        self.count_pill.setObjectName("countPill")
        self.count_pill.setFont(fonts.caption_bold())
        head.addWidget(self.title, 1)
        head.addWidget(self.star)
        head.addWidget(self.count_pill, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(head)
        self.meta_line = QLabel(body)
        self.meta_line.setObjectName("secondary")
        self.meta_line.setFont(fonts.caption())
        self.meta_line.setWordWrap(True)
        lay.addWidget(self.meta_line)

        lay.addSpacing(4)
        label_head = QHBoxLayout()
        label_head.addWidget(_section(self.tr("Labels"), body))
        label_head.addStretch(1)
        hint = QLabel(self.tr("Enter to add"), body)
        hint.setObjectName("tertiary")
        hint.setFont(fonts.micro())
        label_head.addWidget(hint)
        lay.addLayout(label_head)
        self.chips = ChipEditor(ctx.library.chip_colors, body)
        self.chips.labels_edited.connect(self._on_labels_edited)
        self.chips.color_requested.connect(self.color_requested)
        self.chips.invalid_input.connect(self.status_message)
        lay.addWidget(self.chips)
        self.suggestions = QWidget(body)
        sl = QHBoxLayout(self.suggestions)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(4)
        self._suggestion_layout = sl
        lay.addWidget(self.suggestions)

        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        t = tokens.current()
        self.open_btn = QPushButton(icons.icon("image", t.text_on_accent), self.tr("Open"), body)
        self.open_btn.setObjectName("primaryBtn")
        self.open_btn.setToolTip(self.tr("Open in Windows Photos (Enter)"))
        self.open_btn.clicked.connect(self._open)
        self.fav_btn = QPushButton(body)
        self.fav_btn.clicked.connect(self._toggle_favorite)
        self.hide_btn = QPushButton(body)
        self.hide_btn.clicked.connect(self._toggle_hidden)
        for b in (self.open_btn, self.fav_btn, self.hide_btn):
            buttons.addWidget(b, 1)
        lay.addLayout(buttons)

        self.bulk = QWidget(body)
        bl = QHBoxLayout(self.bulk)
        bl.setContentsMargins(0, 0, 0, 0)
        add_btn = QPushButton(icons.icon("tag", t.text_primary), self.tr("Add label…"), self.bulk)
        rem_btn = QPushButton(
            icons.icon("close", t.text_primary), self.tr("Remove label…"), self.bulk
        )
        add_btn.clicked.connect(lambda: self.bulk_add_requested.emit(self._ids()))
        rem_btn.clicked.connect(lambda: self.bulk_remove_requested.emit(self._ids()))
        bl.addWidget(add_btn)
        bl.addWidget(rem_btn)
        lay.addWidget(self.bulk)

        self.meta_card = self._card(body)
        self.meta_grid: QGridLayout = self.meta_card.layout()  # type: ignore[assignment]
        lay.addWidget(self.meta_card)
        self.props_card = self._card(body)
        self.props_grid: QGridLayout = self.props_card.layout()  # type: ignore[assignment]
        lay.addWidget(self.props_card)
        lay.addStretch(1)

        self.placeholder = QLabel(self.tr("Select a folder"), self)
        self.placeholder.setObjectName("emptyText")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self.placeholder)
        self._content = scroll
        ctx.thumbnails.ready.connect(self._on_thumb)
        self.set_rows([])

    @staticmethod
    def _card(parent: QWidget) -> QFrame:
        card = QFrame(parent)
        card.setObjectName("propertyCard")
        grid = QGridLayout(card)
        grid.setContentsMargins(10, 8, 10, 10)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(1, 1)
        return card

    # ------------------------------------------------------------- state
    def _ids(self) -> list[int]:
        return [r.id for r in self._rows]

    def current(self) -> FolderRow | None:
        return self._rows[0] if len(self._rows) == 1 else None

    def set_rows(self, rows: list[FolderRow]) -> None:
        self._rows = rows
        has = bool(rows)
        self._content.setVisible(has)
        self.placeholder.setVisible(not has)
        if not has:
            return
        single = len(rows) == 1
        t = tokens.current()
        self.preview.setVisible(single)
        self.chips.setVisible(single)
        self.suggestions.setVisible(single)
        self.bulk.setVisible(not single)
        self.meta_card.setVisible(False)
        self.props_card.setVisible(single)
        any_fav = all(r.is_favorite for r in rows)
        self.fav_btn.setText(self.tr("Unfavorite") if any_fav else self.tr("Favorite"))
        self.fav_btn.setIcon(icons.icon("star_filled" if any_fav else "star", t.favorite_on))
        win_hidden = any(r.win_hidden and not r.is_hidden for r in rows)
        all_hidden = all(r.is_hidden for r in rows)
        self.hide_btn.setText(self.tr("Unhide") if all_hidden else self.tr("Hide"))
        self.hide_btn.setIcon(icons.icon("eye" if all_hidden else "eye_off", t.text_primary))
        self.hide_btn.setEnabled(not (single and win_hidden))
        self.hide_btn.setToolTip(
            self.tr("Hidden in Windows. Change it in Explorer (Properties → Hidden).")
            if single and win_hidden
            else self.tr("Hide / unhide in FolderVault (Ctrl+H)")
        )
        if single:
            self._show_single(rows[0])
        else:
            total = sum(r.image_count for r in rows)
            self.title.setText(self.tr("{0} folders selected").format(len(rows)))
            self.star.clear()
            self.count_pill.setText(self.tr("{0} images").format(format_count(total)))
            self.meta_line.setText(
                human_size(sum(r.total_bytes for r in rows)) + " " + self.tr("total")
            )
            self.open_btn.setEnabled(False)

    def _show_single(self, row: FolderRow) -> None:
        t = tokens.current()
        self.title.setText(row.display_title)
        self.star.setPixmap(
            icons.pixmap("star_filled", t.favorite_on, 16, self.devicePixelRatioF())
            if row.is_favorite
            else QPixmap()
        )
        self.count_pill.setText(self.tr("{0} images").format(format_count(row.image_count)))
        parts = []
        if row.total_bytes:
            parts.append(human_size(row.total_bytes) + " " + self.tr("total"))
        if row.last_opened_at:
            parts.append(self.tr("Opened {0}").format(relative_time(row.last_opened_at)))
        self.meta_line.setText("  •  ".join(parts))
        self.open_btn.setEnabled(row.image_count > 0)
        if self.chips.labels() != list(row.labels) or not self.chips.input.hasFocus():
            self.chips.set_labels(list(row.labels))
        self.chips.set_known_labels([lbl.name for lbl in self.ctx.library.labels()])
        self._update_suggestions(row)
        self._update_preview()
        self._fill_meta(row)
        self._fill_props(row)

    def refresh_colors(self) -> None:
        self.chips.refresh_colors()
        if self.current():
            self._update_suggestions(self.current())

    def _update_suggestions(self, row: FolderRow) -> None:
        while self._suggestion_layout.count():
            item = self._suggestion_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        usage = self.ctx.library.label_usage()
        have = {n.casefold() for n in row.labels}
        ranked = sorted(
            (lbl for lbl in self.ctx.library.labels() if lbl.name.casefold() not in have),
            key=lambda lbl: (-usage.get(lbl.id, 0), lbl.name.casefold()),
        )[:3]
        if not ranked:
            self.suggestions.setVisible(False)
            return
        self.suggestions.setVisible(True)
        caption = QLabel(self.tr("Suggestions:"), self.suggestions)
        caption.setObjectName("tertiary")
        caption.setFont(fonts.caption())
        self._suggestion_layout.addWidget(caption)
        for lbl in ranked:
            btn = QPushButton("+ " + lbl.name, self.suggestions)
            btn.setObjectName("linkBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, n=lbl.name: self.chips.add_from_text(n))
            self._suggestion_layout.addWidget(btn)
        self._suggestion_layout.addStretch(1)

    def _preview_size(self) -> QSize:
        dpr = self.devicePixelRatioF()
        return QSize(round(PREVIEW_W * dpr), round(PREVIEW_H * dpr))

    def _update_preview(self) -> None:
        row = self.current()
        if row is None:
            return
        t = tokens.current()
        if not row.cover_name:
            self.preview.setPixmap(QPixmap())
            self.preview.setText(self.tr("No images in this folder"))
            return
        pm = self.ctx.thumbnail(row, self._preview_size())
        if pm is None:
            failed = self.ctx.thumbnails.is_failed(
                self.ctx.image_path(row) or "", self._preview_size()
            )
            self.preview.setPixmap(QPixmap())
            self.preview.setText(self.tr("Cannot read cover image") if failed else "")
            if failed:
                self.preview.setPixmap(
                    icons.pixmap("warning", t.warning, 24, self.devicePixelRatioF())
                )
            return
        box = self.preview.contentsRect().adjusted(1, 1, -1, -1)
        pm = QPixmap(pm)
        pm.setDevicePixelRatio(self.devicePixelRatioF())
        target = fit_rect(pm, box)
        self.preview.setPixmap(
            pm.scaled(
                target.size() * self.devicePixelRatioF(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _on_thumb(self, key: str) -> None:
        row = self.current()
        if row and key.startswith((self.ctx.image_path(row) or "\0") + "|"):
            self._update_preview()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_preview()

    @staticmethod
    def _clear_grid(grid: QGridLayout) -> None:
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_pair(
        self, grid: QGridLayout, key: str, value: str, row: int, tooltip: str = ""
    ) -> None:
        k = QLabel(key)
        k.setObjectName("secondary")
        k.setFont(fonts.caption())
        # Zero-width spaces let long paths wrap at separators instead of widening the panel.
        v = QLabel(value.replace("\\", "\\​").replace("/", "/​"))
        v.setFont(fonts.caption_bold())
        v.setWordWrap(True)
        v.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        if tooltip:
            v.setToolTip(tooltip)
        grid.addWidget(k, row, 0, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(v, row, 1)

    def _fill_meta(self, row: FolderRow) -> None:
        self._clear_grid(self.meta_grid)
        meta = row.meta
        if meta is None:
            self.meta_card.setVisible(False)
            return
        self.meta_card.setVisible(True)
        self.meta_grid.addWidget(_section(self.tr("Metadata"), self.meta_card), 0, 0, 1, 2)
        r = 1
        for key, value in (
            ("Title", meta.title),
            ("Series", meta.series),
            ("Type", meta.type),
            ("Language", meta.language),
        ):
            if value:
                self._add_pair(self.meta_grid, key, value, r)
                r += 1
        for key, value in meta.extra.items():
            self._add_pair(self.meta_grid, key, value, r)
            r += 1

    def _fill_props(self, row: FolderRow) -> None:
        self._clear_grid(self.props_grid)
        self.props_grid.addWidget(
            _section(self.tr("Directory properties"), self.props_card), 0, 0, 1, 2
        )
        path = self.ctx.library.abs_path(row.rel_path)
        self._add_pair(self.props_grid, self.tr("Path"), path, 1, self.tr("Ctrl+Shift+C to copy"))
        formats = Counter(row.format_stats)
        fmt = ", ".join(f"{k} ({v})" for k, v in formats.most_common()) or "—"
        self._add_pair(self.props_grid, self.tr("Image formats"), fmt, 2)
        self._add_pair(self.props_grid, self.tr("Subfolders"), str(row.subfolder_count), 3)
        r = 4
        if row.win_hidden:
            self._add_pair(self.props_grid, self.tr("Hidden in Windows"), self.tr("Yes"), r)
            r += 1
        if row.is_hidden:
            self._add_pair(self.props_grid, self.tr("Hidden in app"), self.tr("Yes"), r)
            r += 1
        self._add_pair(self.props_grid, self.tr("Views"), str(row.view_count), r)

    # ----------------------------------------------------------- actions
    def _open(self) -> None:
        row = self.current()
        if row and row.image_count:
            self.open_requested.emit(row.id)

    def _toggle_favorite(self) -> None:
        if self._rows:
            self.favorite_requested.emit(self._ids(), not all(r.is_favorite for r in self._rows))

    def _toggle_hidden(self) -> None:
        if self._rows:
            self.hide_requested.emit(self._ids(), not all(r.is_hidden for r in self._rows))

    def _on_labels_edited(self, labels: list) -> None:
        row = self.current()
        if row is not None:
            self.labels_edited.emit(row.id, labels)

    def focus_labels(self) -> None:
        if self.current():
            self.chips.focus_input()
