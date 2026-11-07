"""Generate the application style sheet from tokens. No font families: the system font is kept."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QPalette

from ... import config
from . import icons
from .tokens import Theme


def _asset(name: str, color: str) -> str:
    folder = config.data_dir() / "theme"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}_{color.lstrip('#')}.svg"
    if not path.exists():
        path.write_bytes(icons.svg(name, color))
    return Path(path).as_posix()


def build_palette(t: Theme) -> QPalette:
    """Dark palette so widgets/dialogs without QSS rules (e.g. QColorDialog) match."""
    pal = QPalette()
    roles = {
        QPalette.ColorRole.Window: t.surface_low,
        QPalette.ColorRole.WindowText: t.text_primary,
        QPalette.ColorRole.Base: t.surface_container,
        QPalette.ColorRole.AlternateBase: t.surface_row_alt,
        QPalette.ColorRole.Text: t.text_primary,
        QPalette.ColorRole.Button: t.surface_high,
        QPalette.ColorRole.ButtonText: t.text_primary,
        QPalette.ColorRole.Highlight: t.selection_row,
        QPalette.ColorRole.HighlightedText: t.text_on_accent,
        QPalette.ColorRole.ToolTipBase: t.surface_container,
        QPalette.ColorRole.ToolTipText: t.text_primary,
        QPalette.ColorRole.PlaceholderText: t.text_tertiary,
        QPalette.ColorRole.Link: t.accent,
        QPalette.ColorRole.Mid: t.line_default,
        QPalette.ColorRole.Dark: t.surface_lowest,
        QPalette.ColorRole.Light: t.line_strong,
    }
    for role, color in roles.items():
        pal.setColor(role, QColor(color))
    for role in (
        QPalette.ColorRole.Text,
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.ButtonText,
    ):
        pal.setColor(QPalette.ColorGroup.Disabled, role, QColor(t.text_tertiary))
    return pal


def build_qss(t: Theme) -> str:
    check = _asset("check", t.text_on_accent)
    chevron = _asset("chevron_down", t.text_secondary)
    return f"""
QMainWindow, QDialog {{ background-color: {t.surface_base}; color: {t.text_primary}; }}
QWidget {{ color: {t.text_primary}; }}
QWidget#appRoot, QWidget#centralArea {{ background-color: {t.surface_base}; }}

QToolTip {{
    background-color: {t.surface_container}; color: {t.text_primary};
    border: 1px solid {t.line_strong}; padding: 4px 6px;
}}

/* Toolbar --------------------------------------------------------------- */
QWidget#toolbar {{ background-color: {t.surface_low}; border-bottom: 1px solid {t.line_subtle}; }}
QWidget#toolbar QToolButton {{
    background: transparent; border: 1px solid transparent; border-radius: 4px;
    padding: 4px 8px; color: {t.text_tool}; min-height: 20px;
}}
QWidget#toolbar QToolButton:hover {{ background-color: {t.surface_high}; color: {t.text_primary}; }}
QWidget#toolbar QToolButton:pressed {{ background-color: {t.surface_highest}; }}
QWidget#toolbar QToolButton:checked {{
    background-color: {t.surface_highest}; color: {t.accent}; border: 1px solid {t.line_strong};
}}
QWidget#toolbar QToolButton:focus {{ border: 1px solid {t.accent}; }}
QToolButton#labelsButton[active="true"] {{ border: 1px solid {t.accent}; color: {t.accent}; }}
QToolButton::menu-indicator {{ image: none; width: 0; }}
QFrame#toolbarSeparator {{ background-color: {t.line_default}; }}

QWidget#contextBar {{ background-color: {t.surface_base}; border-bottom: 1px solid {t.line_subtle}; }}
QLabel#contextBarText {{ color: {t.text_secondary}; }}
QLabel#contextBarRight {{ color: {t.text_tertiary}; }}

/* Inputs ---------------------------------------------------------------- */
QLineEdit {{
    background-color: {t.surface_container}; border: 1px solid {t.line_default};
    border-radius: 4px; padding: 0 8px; min-height: 26px; color: {t.text_primary};
    selection-background-color: {t.accent_fill};
}}
QLineEdit:focus {{ border: 1px solid {t.accent}; background-color: #1E1F1F; }}
QLineEdit#chipInput, QLineEdit#chipInput:focus {{ border: none; background: transparent; min-height: 22px; padding: 0 2px; }}
QFrame#chipEditor {{
    background-color: {t.surface_container}; border: 1px solid {t.line_default}; border-radius: 4px;
}}
QFrame#chipEditor[focused="true"] {{ border: 1px solid {t.accent}; }}

QComboBox {{
    background-color: {t.surface_container}; border: 1px solid {t.line_default};
    border-radius: 4px; padding: 0 8px; min-height: 26px;
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox::down-arrow {{ image: url("{chevron}"); width: 12px; height: 12px; }}

/* Buttons --------------------------------------------------------------- */
QPushButton {{
    background-color: {t.surface_high}; border: 1px solid {t.line_default}; border-radius: 4px;
    padding: 0 14px; min-height: 26px; color: {t.text_primary};
}}
QPushButton:hover {{ background-color: #313233; border-color: {t.line_strong}; }}
QPushButton:pressed {{ background-color: #1E1F1F; }}
QPushButton:focus {{ border: 1px solid {t.accent}; }}
QPushButton:disabled {{ color: {t.text_tertiary}; background-color: {t.surface_low}; }}
QPushButton#primaryBtn {{
    background-color: {t.accent_fill}; border: 1px solid {t.accent_fill_hover};
    color: {t.text_on_accent}; font-weight: 600;
}}
QPushButton#primaryBtn:hover {{ background-color: {t.accent_fill_hover}; }}
QPushButton#primaryBtn:focus {{ border: 1px solid {t.text_primary}; }}
QPushButton#dangerBtn {{
    background-color: {t.danger_fill}; border: 1px solid {t.danger_border}; color: {t.danger_text};
}}
QPushButton#dangerBtn:hover {{ background-color: #722424; }}
QPushButton#linkBtn {{
    background: transparent; border: none; color: {t.accent}; padding: 0 4px; min-height: 18px;
}}
QPushButton#linkBtn:hover {{ text-decoration: underline; }}

/* Views ----------------------------------------------------------------- */
QTableView, QListView, QListWidget, QTableWidget {{
    background-color: {t.surface_base}; alternate-background-color: {t.surface_row_alt};
    border: none; gridline-color: {t.line_subtle}; color: {t.text_primary};
    selection-background-color: {t.selection_row}; selection-color: {t.text_on_accent};
    outline: 0;
}}
QTableView::item {{ padding: 0 6px; border: none; }}
QTableView::item:hover, QListWidget::item:hover {{ background-color: {t.surface_hover}; }}
QTableView::item:selected, QListWidget::item:selected {{ background-color: {t.selection_row}; }}
QTableView::item:selected:!active {{ background-color: {t.selection_row_inactive}; }}
QHeaderView {{ background-color: {t.surface_container}; }}
QHeaderView::section {{
    background-color: {t.surface_container}; color: {t.text_secondary};
    padding: 0 8px; border: none; border-bottom: 1px solid {t.line_default}; min-height: 24px;
    font-weight: 600;
}}
QHeaderView::section:hover {{ background-color: {t.surface_high}; }}
QTableCornerButton::section {{ background-color: {t.surface_container}; border: none; }}

QScrollBar:vertical {{ background: {t.surface_base}; width: 10px; margin: 0; }}
QScrollBar:horizontal {{ background: {t.surface_base}; height: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #3A3B3C; min-height: 24px; border-radius: 4px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #3A3B3C; min-width: 24px; border-radius: 4px; margin: 2px; }}
QScrollBar::handle:hover {{ background: #5A5B5C; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

QSplitter::handle {{ background-color: {t.line_default}; }}
QSplitter::handle:hover {{ background-color: {t.line_strong}; }}

/* Panels ---------------------------------------------------------------- */
QFrame#inspector, QFrame#inspector QScrollArea, QWidget#inspectorBody {{ background-color: {t.surface_low}; }}
QFrame#inspector QLabel#sectionLabel, QLabel#sectionLabel {{ color: {t.text_secondary}; }}
QLabel#previewBox {{
    background-color: {t.preview_box}; border: 1px solid #333333; border-radius: 4px;
    color: {t.text_tertiary};
}}
QLabel#secondary {{ color: {t.text_secondary}; }}
QLabel#tertiary {{ color: {t.text_tertiary}; }}
QLabel#countPill {{
    color: {t.accent}; border: 1px solid {t.accent}; border-radius: 9px; padding: 1px 8px;
}}
QFrame#propertyCard {{
    background-color: {t.surface_base}; border: 1px solid {t.line_subtle}; border-radius: 6px;
}}
QLabel#emptyTitle {{ color: {t.text_primary}; }}
QLabel#emptyText {{ color: {t.text_secondary}; }}
QFrame#banner {{ background-color: #3A2A10; border-bottom: 1px solid {t.warning}; }}

/* Popup / menus ------------------------------------------------------- */
QFrame#popup {{
    background-color: {t.surface_container}; border: 1px solid {t.line_strong}; border-radius: 6px;
}}
QFrame#popupFooter {{ background-color: {t.surface_low}; border-top: 1px solid {t.line_subtle}; }}
QFrame#popup QListWidget {{ background-color: {t.surface_container}; }}
QMenu {{
    background-color: {t.surface_container}; border: 1px solid {t.line_strong}; padding: 4px;
}}
QMenu::item {{ padding: 5px 24px 5px 10px; border-radius: 4px; }}
QMenu::item:selected {{ background-color: {t.surface_high}; }}
QMenu::item:disabled {{ color: {t.text_tertiary}; }}
QMenu::separator {{ height: 1px; background: {t.line_default}; margin: 4px 6px; }}

/* Check / radio ------------------------------------------------------ */
QCheckBox, QRadioButton {{ spacing: 8px; color: #E0E0E0; }}
QCheckBox:disabled, QRadioButton:disabled {{ color: {t.text_tertiary}; }}
QCheckBox::indicator {{
    width: 14px; height: 14px; border-radius: 3px; border: 1px solid #4C4D4E;
    background-color: {t.surface_container};
}}
QCheckBox::indicator:hover {{ border-color: {t.accent}; }}
QCheckBox::indicator:checked {{
    background-color: {t.accent_fill}; border-color: {t.accent}; image: url("{check}");
}}
QCheckBox:focus {{ color: {t.text_primary}; }}
QRadioButton::indicator {{
    width: 14px; height: 14px; border-radius: 8px; border: 1px solid #4C4D4E;
    background-color: {t.surface_container};
}}
QRadioButton::indicator:checked {{ border: 4px solid {t.accent_fill}; background-color: {t.text_on_accent}; }}

/* Status bar -------------------------------------------------------- */
QStatusBar {{ background-color: {t.surface_lowest}; color: {t.text_secondary}; border-top: 1px solid {t.line_subtle}; }}
QStatusBar QLabel {{ color: {t.text_secondary}; }}
QStatusBar::item {{ border: none; }}

/* Settings dialog --------------------------------------------------- */
QListWidget#settingsNav {{ background-color: {t.surface_container}; border-right: 1px solid {t.line_subtle}; }}
QListWidget#settingsNav::item {{ padding: 8px 12px; }}
QListWidget#settingsNav::item:selected {{ background-color: {t.surface_high}; color: {t.accent}; }}
QWidget#settingsPage {{ background-color: {t.surface_low}; }}
QFrame#settingsGroup {{
    background-color: {t.surface_base}; border: 1px solid {t.line_subtle}; border-radius: 6px;
}}
QFrame#settingsRow {{ border-bottom: 1px solid {t.line_subtle}; }}
QFrame#dialogFooter {{ background-color: {t.surface_low}; border-top: 1px solid {t.line_subtle}; }}
QFrame#infoBox {{
    background-color: {t.surface_base}; border: 1px solid {t.line_default}; border-radius: 6px;
}}
QPlainTextEdit {{
    background-color: {t.surface_lowest}; border: 1px solid {t.line_default}; border-radius: 4px;
    color: {t.text_secondary};
}}
"""
