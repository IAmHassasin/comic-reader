"""Color math: contrast, blending, label chip and accent derivation (docs/02 §1.4-1.6)."""

from __future__ import annotations

import re
import zlib
from dataclasses import dataclass

SURFACE_BASE = "#131313"
WHITE = "#FFFFFF"
MIN_TEXT_CONTRAST = 4.5

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class ChipColors:
    fill: str
    border: str
    text: str
    dot: str


# Hand-tuned palette (docs/02 §1.5).
PALETTE: dict[str, ChipColors] = {
    "amber": ChipColors("#382A18", "#94682E", "#FFD285", "#F5B83D"),
    "green": ChipColors("#1B3224", "#3E7756", "#82E0AA", "#3DD68C"),
    "cyan": ChipColors("#162E3B", "#2B6B8B", "#7CE3FF", "#3CC8F0"),
    "violet": ChipColors("#2C1E38", "#6D458C", "#DDB8FF", "#B57BFF"),
    "rose": ChipColors("#3A1A22", "#8C3A4C", "#FFB3C1", "#F2667E"),
    "blue": ChipColors("#16263F", "#2F5A99", "#9CC3FF", "#4A90E2"),
    "slate": ChipColors("#262728", "#4A4C4E", "#C8CACC", "#8A8F94"),
}
PALETTE_KEYS: tuple[str, ...] = tuple(PALETTE)

# Defaults that match the mockups; other labels get a hash-derived key.
SEEDED_LABEL_COLORS = {
    "best": "amber",
    "travel": "cyan",
    "cosplay": "green",
    "landscape": "violet",
    "archived": "slate",
    "work": "blue",
}


def is_hex_color(value: str) -> bool:
    return bool(_HEX_RE.match(value))


def _to_rgb(hex_color: str) -> tuple[int, int, int]:
    if not is_hex_color(hex_color):
        raise ValueError(f"Invalid color: {hex_color!r}")
    return int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)


def _to_hex(rgb: tuple[float, float, float]) -> str:
    r, g, b = (max(0, min(255, round(c))) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def blend(top: str, bottom: str, alpha: float) -> str:
    """Alpha-blend ``top`` over ``bottom`` (alpha in 0..1)."""
    t, b = _to_rgb(top), _to_rgb(bottom)
    return _to_hex(tuple(tc * alpha + bc * (1 - alpha) for tc, bc in zip(t, b, strict=True)))


def relative_luminance(hex_color: str) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = _to_rgb(hex_color)
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(a: str, b: str) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def default_palette_key(label_name: str) -> str:
    key = label_name.casefold()
    if key in SEEDED_LABEL_COLORS:
        return SEEDED_LABEL_COLORS[key]
    return PALETTE_KEYS[zlib.crc32(key.encode("utf-8")) % len(PALETTE_KEYS)]


def derive_chip_colors(base: str, surface: str = SURFACE_BASE) -> ChipColors:
    fill = blend(base, surface, 0.18)
    border = blend(base, surface, 0.55)
    text = base
    step = 0
    while contrast_ratio(text, fill) < MIN_TEXT_CONTRAST and step < 10:
        step += 1
        text = blend(WHITE, base, step / 10)
    return ChipColors(fill=fill, border=border, text=text, dot=base)


def chip_colors(label_name: str, color: str | None) -> ChipColors:
    """Resolve the stored label color (palette key, hex, or None) to chip colors."""
    if color and color in PALETTE:
        return PALETTE[color]
    if color and is_hex_color(color):
        return derive_chip_colors(color.upper())
    return PALETTE[default_palette_key(label_name)]


@dataclass(frozen=True)
class AccentColors:
    accent: str
    fill: str
    fill_hover: str
    selection: str
    selection_inactive: str


def derive_accent(base: str, surface: str = SURFACE_BASE) -> AccentColors:
    base = base.upper()
    fill = base
    step = 0
    while contrast_ratio(WHITE, fill) < MIN_TEXT_CONTRAST and step < 20:
        step += 1
        fill = blend("#000000", base, step * 0.05)
    return AccentColors(
        accent=base,
        fill=fill,
        fill_hover=blend(WHITE, fill, 0.06),
        selection=blend(base, surface, 0.30),
        selection_inactive=blend(base, surface, 0.15),
    )
