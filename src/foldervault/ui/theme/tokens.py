"""Color tokens. The only place hex colors may appear in UI code."""

from __future__ import annotations

from dataclasses import dataclass

from ...core.colors import derive_accent

DEFAULT_ACCENT = "#60CDFF"


@dataclass(frozen=True)
class Theme:
    # Surfaces
    surface_lowest: str = "#0E0E0E"
    surface_base: str = "#131313"
    surface_row_alt: str = "#171818"
    surface_low: str = "#1B1C1C"
    surface_container: str = "#202121"
    surface_high: str = "#2A2B2B"
    surface_highest: str = "#353636"
    surface_hover: str = "#1C1D1D"
    preview_box: str = "#1A1A1A"
    # Lines
    line_subtle: str = "#232424"
    line_default: str = "#3C3D3E"
    line_strong: str = "#4D4E4F"
    # Text
    text_primary: str = "#F3F3F3"
    text_secondary: str = "#9E9E9E"
    text_tertiary: str = "#737373"
    text_on_accent: str = "#FFFFFF"
    text_tool: str = "#CCCCCC"
    # State
    favorite_on: str = "#FFC83B"
    favorite_off: str = "#4A4A4A"
    danger: str = "#E05D5D"
    danger_fill: str = "#5A1E1E"
    danger_border: str = "#822828"
    danger_text: str = "#FFB3B3"
    warning: str = "#FFB900"
    success: str = "#4CC38A"
    # Accent (derived from the user's accent base color)
    accent: str = DEFAULT_ACCENT
    accent_fill: str = "#0078D4"
    accent_fill_hover: str = "#1084D9"
    selection_row: str = "#1A4B75"
    selection_row_inactive: str = "#24384A"


def build_theme(accent_base: str = DEFAULT_ACCENT) -> Theme:
    if accent_base.upper() == DEFAULT_ACCENT:
        return Theme()  # hand-tuned defaults
    derived = derive_accent(accent_base)
    return Theme(
        accent=derived.accent,
        accent_fill=derived.fill,
        accent_fill_hover=derived.fill_hover,
        selection_row=derived.selection,
        selection_row_inactive=derived.selection_inactive,
    )


_current = Theme()


def current() -> Theme:
    return _current


def set_current(theme: Theme) -> None:
    global _current
    _current = theme
