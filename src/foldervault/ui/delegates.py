"""Item delegates for the List (table) and Album Cards views."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QModelIndex, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QIcon, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

from ..core.entities import FolderRow
from .context import UiContext
from .formatting import format_timestamp, human_size, relative_time
from .models import RowRole
from .painting import fit_rect, paint_chips
from .theme import fonts, icons, tokens

ROW_HEIGHT = 28
ROW_HEIGHT_THUMBS = 44


def _paint_item_background(
    painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
) -> None:
    """Let the style paint hover/selection backgrounds (QSS ::item rules), without content."""
    opt = QStyleOptionViewItem(option)
    opt.text = ""
    opt.icon = QIcon()
    opt.features &= ~QStyleOptionViewItem.ViewItemFeature.HasDecoration
    widget = option.widget
    style = widget.style() if widget else QApplication.style()
    style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, widget)


def _row(index: QModelIndex) -> FolderRow | None:
    return index.data(RowRole)


class StarDelegate(QStyledItemDelegate):
    """Favorite star; clicking toggles. Also paints the 3px selection accent bar."""

    toggled = Signal(int, bool)  # folder id, new value

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        _paint_item_background(painter, option, index)
        row = _row(index)
        if row is None:
            return
        t = tokens.current()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(
                QRect(option.rect.left(), option.rect.top(), 3, option.rect.height()),
                QColor(t.accent),
            )
        name, color = (
            ("star_filled", t.favorite_on) if row.is_favorite else ("star", t.favorite_off)
        )
        if not row.is_favorite and option.state & QStyle.StateFlag.State_MouseOver:
            color = t.text_secondary
        size = 14
        dpr = painter.device().devicePixelRatioF() if painter.device() else 1.0
        pm = icons.pixmap(name, color, size, dpr)
        r = option.rect
        painter.drawPixmap(r.x() + (r.width() - size) // 2, r.y() + (r.height() - size) // 2, pm)

    def editorEvent(
        self, event: QEvent, model, option: QStyleOptionViewItem, index: QModelIndex
    ) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent):
            if event.button() == Qt.MouseButton.LeftButton and option.rect.contains(
                event.position().toPoint()
            ):
                row = _row(index)
                if row is not None:
                    self.toggled.emit(row.id, not row.is_favorite)
                return True
        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick):
            return True  # do not change selection when clicking the star
        return super().editorEvent(event, model, option, index)


class NameDelegate(QStyledItemDelegate):
    def __init__(self, ctx: UiContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ctx = ctx

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        _paint_item_background(painter, option, index)
        row = _row(index)
        if row is None:
            return
        t = tokens.current()
        painter.save()
        if row.effectively_hidden:
            painter.setOpacity(0.5)
        r = option.rect.adjusted(6, 0, -6, 0)
        dpr = painter.device().devicePixelRatioF() if painter.device() else 1.0
        x = r.x()
        if self.ctx.list_thumbnails:
            box = QRect(x, r.y() + (r.height() - 36) // 2, 36, 36)
            thumb = self.ctx.thumbnail(row, QSize(round(36 * dpr), round(36 * dpr)))
            if thumb is not None:
                thumb.setDevicePixelRatio(dpr)
                painter.drawPixmap(fit_rect(thumb, box), thumb)
            else:
                self._draw_folder_icon(painter, row, box, dpr)
            x += 44
        else:
            self._draw_folder_icon(
                painter, row, QRect(x, r.y() + (r.height() - 16) // 2, 16, 16), dpr
            )
            x += 24
        text_rect = QRect(x, r.y(), r.right() - x, r.height())
        if row.effectively_hidden:
            painter.drawPixmap(
                text_rect.right() - 14,
                r.y() + (r.height() - 14) // 2,
                icons.pixmap("eye_off", t.text_secondary, 14, dpr),
            )
            text_rect.setRight(text_rect.right() - 20)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        color = t.text_primary if (row.image_count or selected) else t.text_secondary
        painter.setPen(QColor(color))
        painter.setFont(fonts.body())
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        fm = QFontMetrics(painter.font())
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            fm.elidedText(text, Qt.TextElideMode.ElideMiddle, text_rect.width()),
        )
        painter.restore()

    @staticmethod
    def _draw_folder_icon(painter: QPainter, row: FolderRow, box: QRect, dpr: float) -> None:
        t = tokens.current()
        name = "folder" if row.image_count else "folder_stack"
        color = t.accent if row.image_count else t.text_secondary
        size = min(box.width(), box.height(), 16)
        painter.drawPixmap(
            box.x() + (box.width() - size) // 2,
            box.y() + (box.height() - size) // 2,
            icons.pixmap(name, color, size, dpr),
        )


class LabelsDelegate(QStyledItemDelegate):
    def __init__(self, ctx: UiContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ctx = ctx

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        _paint_item_background(painter, option, index)
        row = _row(index)
        if row is None or not row.labels:
            return
        painter.save()
        if row.effectively_hidden:
            painter.setOpacity(0.5)
        paint_chips(
            painter,
            option.rect.adjusted(6, 2, -6, -2),
            row.labels,
            self.ctx.library.chip_colors,
            fonts.micro(),
        )
        painter.restore()


# --------------------------------------------------------------------- cards
CARD_HEIGHT = 228
COVER_W, COVER_H = 108, 144


class AlbumCardDelegate(QStyledItemDelegate):
    """Paints a whole album card (docs/02 §5.6) for a QListView row."""

    favorite_clicked = Signal(int, bool)

    def __init__(self, ctx: UiContext, view: QAbstractItemView) -> None:
        super().__init__(view)
        self.ctx = ctx
        self.view = view

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:  # noqa: N802
        return QSize(max(400, self.view.viewport().width() - 2), CARD_HEIGHT)

    def _card_rect(self, rect: QRect) -> QRect:
        return rect.adjusted(12, 6, -12, -6)

    def _star_rect(self, card: QRect) -> QRect:
        return QRect(card.x() + 10, card.y() + 8, 16, 16)

    def editorEvent(
        self, event: QEvent, model, option: QStyleOptionViewItem, index: QModelIndex
    ) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent):
            if (
                self._star_rect(self._card_rect(option.rect))
                .adjusted(-4, -4, 4, 4)
                .contains(event.position().toPoint())
            ):
                row = _row(index)
                if row is not None:
                    self.favorite_clicked.emit(row.id, not row.is_favorite)
                return True
        return super().editorEvent(event, model, option, index)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:  # noqa: C901, PLR0915
        row = _row(index)
        if row is None:
            return
        t = tokens.current()
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        dpr = painter.device().devicePixelRatioF() if painter.device() else 1.0
        card = self._card_rect(option.rect)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if row.effectively_hidden:
            painter.setOpacity(0.55)
        # Card body
        border = (
            QColor(t.accent) if selected else QColor(t.line_strong if hovered else t.line_default)
        )
        painter.setPen(QPen(border, 1))
        painter.setBrush(QColor(t.surface_low))
        painter.drawRoundedRect(card.adjusted(0, 0, -1, -1), 6, 6)

        # Header
        header = QRect(card.x() + 1, card.y() + 1, card.width() - 2, 30)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(t.selection_row if selected else t.surface_high))
        painter.drawRoundedRect(header, 5, 5)
        painter.drawRect(header.adjusted(0, 10, 0, 0))
        star = self._star_rect(card)
        painter.drawPixmap(
            star,
            icons.pixmap(
                "star_filled" if row.is_favorite else "star",
                t.favorite_on if row.is_favorite else t.text_secondary,
                16,
                dpr,
            ),
        )
        badge_text = row.name if row.meta and row.meta.title else ""
        badge_w = 0
        painter.setFont(fonts.caption())
        fm_cap = QFontMetrics(fonts.caption())
        if badge_text:
            badge_w = min(fm_cap.horizontalAdvance(badge_text) + 14, card.width() // 3)
            badge = QRect(header.right() - badge_w - 8, header.y() + 6, badge_w, 18)
            painter.setPen(QColor(t.line_strong))
            painter.setBrush(QColor(t.surface_base))
            painter.drawRoundedRect(badge, 4, 4)
            painter.setPen(QColor(t.text_secondary))
            painter.drawText(
                badge,
                Qt.AlignmentFlag.AlignCenter,
                fm_cap.elidedText(badge_text, Qt.TextElideMode.ElideMiddle, badge_w - 8),
            )
        title_rect = QRect(
            star.right() + 10,
            header.y(),
            header.right() - star.right() - 26 - badge_w,
            header.height(),
        )
        painter.setFont(fonts.heading())
        painter.setPen(QColor(t.text_primary))
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            QFontMetrics(fonts.heading()).elidedText(
                row.display_title, Qt.TextElideMode.ElideRight, title_rect.width()
            ),
        )

        # Path row
        path_row = QRect(card.x() + 10, header.bottom() + 2, card.width() - 20, 22)
        painter.drawPixmap(
            path_row.x(), path_row.y() + 4, icons.pixmap("folder", t.text_secondary, 14, dpr)
        )
        size_text = f"{human_size(row.total_bytes)} total" if row.total_bytes else ""
        painter.setFont(fonts.caption())
        size_w = fm_cap.horizontalAdvance(size_text) + 4
        painter.setPen(QColor(t.text_secondary))
        painter.drawText(
            path_row.adjusted(0, 0, 0, 0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
            size_text,
        )
        path_text = f"{self.ctx.library.abs_path(row.rel_path)}  ({row.image_count:,} images)"
        path_rect = path_row.adjusted(20, 0, -size_w - 8, 0)
        painter.drawText(
            path_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            fm_cap.elidedText(path_text, Qt.TextElideMode.ElideMiddle, path_rect.width()),
        )
        painter.setPen(QColor(t.line_subtle))
        painter.drawLine(
            card.x() + 1, path_row.bottom() + 2, card.right() - 1, path_row.bottom() + 2
        )

        # Cover stack
        body_top = path_row.bottom() + 10
        cover = QRect(card.x() + 30, body_top, COVER_W, COVER_H)
        thumb_size = QSize(round(COVER_W * dpr), round(COVER_H * dpr))
        backs = [
            (row.preview_names[2] if len(row.preview_names) > 2 else None, 12, 0.6),
            (row.preview_names[1] if len(row.preview_names) > 1 else None, 6, 0.8),
        ]
        for name, offset, brightness in backs:
            back = cover.translated(-offset, -offset // 2)
            pm = self.ctx.thumbnail(row, thumb_size, name) if name else None
            self._paint_cover(painter, back, pm, dpr, t, brightness)
        cover_pm = self.ctx.thumbnail(row, thumb_size) if row.cover_name else None
        self._paint_cover(painter, cover, cover_pm, dpr, t, 1.0, placeholder=True)
        if row.image_count:
            badge_text = f"1/{row.image_count}"
            bw = fm_cap.horizontalAdvance(badge_text) + 10
            badge = QRect(cover.right() - bw - 4, cover.bottom() - 22, bw, 18)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 180))
            painter.drawRoundedRect(badge, 4, 4)
            painter.setPen(QColor(t.text_primary))
            painter.setFont(fonts.micro())
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, badge_text)

        # Fields
        fx = cover.right() + 24
        key_w = 84
        fy = body_top + 2
        line_h = 20
        painter.setFont(fonts.body())
        fm_body = QFontMetrics(fonts.body())
        value_w = card.right() - 12 - fx - key_w
        meta = row.meta
        fields = []
        if meta:
            fields = [
                (k, v)
                for k, v in (
                    ("Series", meta.series),
                    ("Type", meta.type),
                    ("Language", meta.language),
                )
                if v
            ]
        for key, value in fields:
            painter.setPen(QColor(t.text_secondary))
            painter.drawText(QRect(fx, fy, key_w, line_h), Qt.AlignmentFlag.AlignVCenter, key)
            painter.setPen(QColor(t.text_primary))
            painter.drawText(
                QRect(fx + key_w, fy, value_w, line_h),
                Qt.AlignmentFlag.AlignVCenter,
                fm_body.elidedText(value, Qt.TextElideMode.ElideRight, value_w),
            )
            fy += line_h
        painter.setPen(QColor(t.text_secondary))
        painter.drawText(QRect(fx, fy, key_w, line_h), Qt.AlignmentFlag.AlignVCenter, "Labels")
        if row.labels:
            paint_chips(
                painter,
                QRect(fx + key_w, fy + 1, value_w, 44),
                row.labels,
                self.ctx.library.chip_colors,
                fonts.micro(),
                max_lines=2,
            )
        else:
            painter.setPen(QColor(t.text_tertiary))
            painter.drawText(
                QRect(fx + key_w, fy, value_w, line_h), Qt.AlignmentFlag.AlignVCenter, "No labels"
            )

        # Footer
        footer = QRect(fx, card.bottom() - 26, card.right() - 12 - fx, 20)
        painter.setFont(fonts.caption())
        painter.setPen(QColor(t.text_secondary))
        painter.drawText(
            footer,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            format_timestamp(row.mtime),
        )
        opened = relative_time(row.last_opened_at)
        if opened:
            painter.drawText(
                footer,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                f"Last opened {opened}",
            )
        elif row.subfolder_count:
            painter.drawText(
                footer,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                f"{row.subfolder_count} subfolders",
            )
        painter.restore()

    @staticmethod
    def _paint_cover(
        painter: QPainter,
        box: QRect,
        pm,
        dpr: float,
        t: tokens.Theme,
        brightness: float,
        placeholder: bool = False,
    ) -> None:
        painter.save()
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        painter.setBrush(QColor(t.surface_highest if not placeholder else t.preview_box))
        painter.drawRoundedRect(box, 4, 4)
        if pm is not None:
            pm.setDevicePixelRatio(dpr)
            painter.drawPixmap(fit_rect(pm, box.adjusted(1, 1, -1, -1)), pm)
        elif placeholder:
            painter.drawPixmap(
                box.center().x() - 12,
                box.center().y() - 12,
                icons.pixmap("image", t.text_tertiary, 24, dpr),
            )
        if brightness < 1.0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, int(255 * (1 - brightness))))
            painter.drawRoundedRect(box, 4, 4)
        painter.restore()
