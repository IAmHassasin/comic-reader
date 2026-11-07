"""Folder filter predicate shared by the UI proxy model and tests."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field, replace

from .entities import FolderRow
from .natural_sort import fold_text


@dataclass(frozen=True)
class FilterState:
    location: str = ""  # rel_path of the current folder; '' = root
    all_levels: bool = True
    search: str = ""
    favorites_only: bool = False
    image_folders_only: bool = False
    show_hidden: bool = False
    labels: frozenset[str] = field(default_factory=frozenset)  # casefolded names
    match_all: bool = False
    no_label: bool = False

    @property
    def label_filter_active(self) -> bool:
        return bool(self.labels) or self.no_label

    def without_labels(self) -> FilterState:
        return replace(self, labels=frozenset(), no_label=False)


def in_location(row: FolderRow, location: str, all_levels: bool) -> bool:
    if not row.rel_path:
        return False  # the root itself is the location, never a row
    if all_levels:
        return location == "" or row.rel_path.startswith(location + "/")
    return (row.parent_rel_path or "") == location and row.rel_path != location


def _matches_search(row: FolderRow, folded_query: str) -> bool:
    haystack = [row.name, *row.labels]  # folder name, not the whole path (docs/01 F1)
    if row.meta:
        haystack.extend(v for v in (row.meta.title, row.meta.series) if v)
    return any(folded_query in fold_text(text) for text in haystack)


def _matches_labels(row: FolderRow, state: FilterState) -> bool:
    if not state.label_filter_active:
        return True
    row_labels = {label.casefold() for label in row.labels}
    if state.match_all:
        # "(no label)" cannot be combined with AND; the UI disables it, ignore here too.
        return bool(state.labels) and state.labels <= row_labels
    if state.no_label and not row_labels:
        return True
    return bool(state.labels & row_labels)


def accepts(row: FolderRow, state: FilterState) -> bool:
    if not in_location(row, state.location, state.all_levels):
        return False
    if not state.show_hidden and row.effectively_hidden:
        return False
    if state.favorites_only and not row.is_favorite:
        return False
    if state.image_folders_only and row.image_count == 0:
        return False
    query = fold_text(state.search.strip())
    if query and not _matches_search(row, query):
        return False
    return _matches_labels(row, state)


def label_counts(rows: Iterable[FolderRow], state: FilterState) -> tuple[Counter[str], int]:
    """Count folders per label (casefolded) among rows passing all non-label filters.

    Returns (counts, number_of_rows_without_labels).
    """
    base = state.without_labels()
    counts: Counter[str] = Counter()
    unlabeled = 0
    for row in rows:
        if not accepts(row, base):
            continue
        if not row.labels:
            unlabeled += 1
        counts.update({label.casefold() for label in row.labels})
    return counts, unlabeled
