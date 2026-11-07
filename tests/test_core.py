from __future__ import annotations

import pytest

from foldervault.core import colors
from foldervault.core.entities import FolderMeta, FolderRow
from foldervault.core.filtering import FilterState, accepts, label_counts
from foldervault.core.image_types import restrict_to_readable
from foldervault.core.labels import InvalidLabelError, normalize_label, split_label_input
from foldervault.core.natural_sort import fold_text, natural_key


def test_natural_sort_orders_numbers_numerically() -> None:
    names = ["Set 10", "set 2", "Set 1", "a.jpg", "10.jpg", "2.jpg"]
    assert sorted(names, key=natural_key) == [
        "2.jpg",
        "10.jpg",
        "a.jpg",
        "Set 1",
        "set 2",
        "Set 10",
    ]


def test_fold_text_is_case_and_accent_insensitive() -> None:
    assert fold_text("Café ÜBER") == fold_text("cafe uber")


def test_restrict_to_readable() -> None:
    exts = restrict_to_readable(["jpeg", "png", "pdf"])
    assert {".jpg", ".jpeg", ".jfif", ".png"} == set(exts)


def test_label_normalization() -> None:
    assert normalize_label("  best   picks ") == "best picks"
    with pytest.raises(InvalidLabelError):
        normalize_label("   ")
    with pytest.raises(InvalidLabelError):
        normalize_label("x" * 41)
    assert split_label_input("best, Best ,travel,, ") == ["best", "travel"]


def _row(rel: str, labels=(), **kw) -> FolderRow:
    parent = rel.rsplit("/", 1)[0] if "/" in rel else ""
    return FolderRow(id=hash(rel), rel_path=rel, parent_rel_path=parent, labels=tuple(labels), **kw)


ROWS = [
    _row("A", image_count=0, subfolder_count=2),
    _row("A/1", ["best", "travel"], image_count=5, is_favorite=True),
    _row("A/2", ["best"], image_count=5),
    _row("B", [], image_count=3),
    _row("C", ["travel"], image_count=3, is_hidden=True),
    _row("D", [], image_count=3, win_hidden=True),
    _row("E", [], image_count=1, meta=FolderMeta(title="Dragon Story")),
]


def visible(state: FilterState) -> list[str]:
    return [r.rel_path for r in ROWS if accepts(r, state)]


def test_location_and_levels() -> None:
    assert visible(FilterState(all_levels=False)) == ["A", "B", "E"]
    assert visible(FilterState(all_levels=True)) == ["A", "A/1", "A/2", "B", "E"]
    assert visible(FilterState(location="A", all_levels=False)) == ["A/1", "A/2"]


def test_hidden_covers_app_flag_and_windows_attribute() -> None:
    assert "C" not in visible(FilterState())
    assert "D" not in visible(FilterState())
    assert {"C", "D"} <= set(visible(FilterState(show_hidden=True)))


def test_quick_filters_and_search() -> None:
    assert visible(FilterState(favorites_only=True)) == ["A/1"]
    assert "A" not in visible(FilterState(image_folders_only=True))
    assert visible(FilterState(search="dragon")) == ["E"]
    assert visible(FilterState(search="TRAVEL")) == ["A/1"]


def test_label_and_or_no_label() -> None:
    both = frozenset({"best", "travel"})
    assert visible(FilterState(labels=both)) == ["A/1", "A/2"]
    assert visible(FilterState(labels=both, match_all=True)) == ["A/1"]
    assert visible(FilterState(no_label=True)) == ["A", "B", "E"]
    assert visible(FilterState(labels=frozenset({"travel"}), no_label=True)) == [
        "A",
        "A/1",
        "B",
        "E",
    ]
    # AND with "(no label)" is ignored rather than producing nonsense.
    assert visible(FilterState(labels=frozenset({"best"}), no_label=True, match_all=True)) == [
        "A/1",
        "A/2",
    ]


def test_label_counts_ignore_label_filter() -> None:
    counts, unlabeled = label_counts(ROWS, FilterState(labels=frozenset({"travel"})))
    assert counts["best"] == 2 and counts["travel"] == 1
    assert unlabeled == 3


def test_chip_colors_contrast_for_extreme_inputs() -> None:
    for base in ["#000000", "#FFFFFF", "#FF0000", "#00FF00", "#0000FF", "#808080", "#123456"]:
        chip = colors.derive_chip_colors(base)
        assert colors.contrast_ratio(chip.text, chip.fill) >= colors.MIN_TEXT_CONTRAST, base


def test_accent_fill_contrast() -> None:
    for base in ["#60CDFF", "#FFFF00", "#FFFFFF", "#0078D4", "#E81123"]:
        accent = colors.derive_accent(base)
        assert colors.contrast_ratio("#FFFFFF", accent.fill) >= colors.MIN_TEXT_CONTRAST, base


def test_chip_color_resolution() -> None:
    assert colors.chip_colors("best", None) == colors.PALETTE["amber"]
    assert colors.chip_colors("x", "violet") == colors.PALETTE["violet"]
    assert colors.chip_colors("x", "#ff7a00").dot == "#FF7A00"
    assert colors.default_palette_key("anything") in colors.PALETTE


def test_search_matches_folder_name_not_parent_path() -> None:
    rows = [_row("Parent"), _row("Parent/Child")]
    state = FilterState(search="parent")
    assert [r.rel_path for r in rows if accepts(r, state)] == ["Parent"]
