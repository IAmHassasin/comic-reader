"""User preferences stored in the settings table."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields

from ..core.colors import is_hex_color
from ..data.repository import Repository
from ..services.windows_accent import windows_accent_color
from .theme.tokens import DEFAULT_ACCENT

PREFIX = "pref."


@dataclass
class Preferences:
    open_with: str = "photos"  # "photos" | "default"
    auto_refresh: bool = True
    list_thumbnails: bool = False
    accent_mode: str = "default"  # "default" | "windows" | "custom"
    accent_custom: str = DEFAULT_ACCENT
    privacy_clear_on_exit: bool = False
    privacy_no_hidden_thumb_cache: bool = False
    privacy_stealth_title: bool = False

    @classmethod
    def load(cls, repo: Repository) -> Preferences:
        prefs = cls()
        for f in fields(cls):
            value = repo.get_setting(PREFIX + f.name, None)
            if value is not None and isinstance(value, type(getattr(prefs, f.name))):
                setattr(prefs, f.name, value)
        if prefs.open_with not in ("photos", "default"):
            prefs.open_with = "photos"
        if prefs.accent_mode not in ("default", "windows", "custom"):
            prefs.accent_mode = "default"
        if not is_hex_color(prefs.accent_custom):
            prefs.accent_custom = DEFAULT_ACCENT
        return prefs

    def save(self, repo: Repository) -> None:
        for key, value in asdict(self).items():
            repo.set_setting(PREFIX + key, value)

    def accent_base(self) -> str:
        if self.accent_mode == "windows":
            return windows_accent_color() or DEFAULT_ACCENT
        if self.accent_mode == "custom":
            return self.accent_custom
        return DEFAULT_ACCENT
