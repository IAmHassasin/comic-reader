"""Read the Windows accent color (read-only)."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def windows_accent_color() -> str | None:
    """Return '#RRGGBB' or None when unavailable."""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM") as key:
            value, _ = winreg.QueryValueEx(key, "AccentColor")
    except (ImportError, OSError):
        log.debug("Windows accent color not available")
        return None
    value = int(value) & 0xFFFFFFFF  # ABGR
    r, g, b = value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF
    return f"#{r:02X}{g:02X}{b:02X}"
