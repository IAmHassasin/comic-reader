"""Domain records shared by the data layer, services and UI."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FolderMeta:
    """Script-provided metadata for a folder. All fields optional."""

    title: str | None = None
    series: str | None = None
    type: str | None = None
    language: str | None = None
    extra: dict[str, str] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not (self.title or self.series or self.type or self.language or self.extra)


@dataclass
class FolderRow:
    """One folder as shown in the library views."""

    id: int
    rel_path: str
    parent_rel_path: str | None
    image_count: int = 0
    subfolder_count: int = 0
    total_bytes: int = 0
    cover_name: str | None = None
    preview_names: tuple[str, ...] = ()
    format_stats: dict[str, int] = field(default_factory=dict)
    mtime: float | None = None
    win_hidden: bool = False
    is_hidden: bool = False
    is_favorite: bool = False
    view_count: int = 0
    last_opened_at: str | None = None
    labels: tuple[str, ...] = ()
    meta: FolderMeta | None = None

    @property
    def name(self) -> str:
        return self.rel_path.rsplit("/", 1)[-1] if self.rel_path else ""

    @property
    def effectively_hidden(self) -> bool:
        return self.is_hidden or self.win_hidden

    @property
    def display_title(self) -> str:
        if self.meta and self.meta.title:
            return self.meta.title
        return self.name


@dataclass(frozen=True)
class FolderScanResult:
    """What the scanner learned about one directory."""

    rel_path: str
    parent_rel_path: str | None
    image_count: int
    subfolder_count: int
    total_bytes: int
    cover_name: str | None
    preview_names: tuple[str, ...]
    format_stats: dict[str, int]
    mtime: float | None
    win_hidden: bool
    error: str | None = None


@dataclass(frozen=True)
class Label:
    id: int
    name: str
    color: str | None  # palette key, '#RRGGBB', or None for the default
