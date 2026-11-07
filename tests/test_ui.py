"""GUI smoke tests (offscreen). They exercise the real widgets, models and services."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QColor, QImage

from foldervault import config
from foldervault.data.db import connect
from foldervault.data.repository import Repository
from foldervault.services import opener
from foldervault.ui.models import COL_NAME
from foldervault.ui.theme import tokens
from foldervault.ui.theme.qss import build_palette, build_qss


def _png(path: Path, color: str, w: int = 60, h: int = 90) -> None:
    img = QImage(w, h, QImage.Format.Format_RGB32)
    img.fill(QColor(color))
    path.parent.mkdir(parents=True, exist_ok=True)
    assert img.save(str(path), "PNG")


@pytest.fixture
def library(tmp_path: Path) -> Path:
    root = tmp_path / "Comics"
    for i in (1, 2, 10):
        for page in (1, 2, 3):
            _png(root / f"Set {i}" / f"{page}.png", "#884422")
    _png(root / "Group" / "Part 1" / "1.png", "#224488")
    (root / "Group" / "Part 2").mkdir(parents=True)
    (root / "Empty").mkdir()
    return root


@pytest.fixture
def window(qtbot, qapp):
    tokens.set_current(tokens.build_theme())
    qapp.setPalette(build_palette(tokens.current()))
    qapp.setStyleSheet(build_qss(tokens.current()))
    conn = connect(config.db_path())
    from foldervault.ui.main_window import MainWindow

    win = MainWindow(Repository(conn))
    qtbot.addWidget(win)
    win.show()
    yield win
    win.close()
    conn.close()


def _wait_scan(qtbot, win) -> None:
    qtbot.waitUntil(lambda: not win.library.scanning and win.model.rowCount() > 0, timeout=10000)


def _names(win) -> list[str]:
    return [win.proxy.data(win.proxy.index(i, COL_NAME)) for i in range(win.proxy.rowCount())]


def test_first_run_shows_empty_state(window) -> None:
    assert window.stack.currentIndex() == 0


def test_open_scan_filter_and_organize(qtbot, window, library, monkeypatch) -> None:
    win = window
    win.open_root(str(library))
    _wait_scan(qtbot, win)

    # All levels on by default; natural sort; root itself is not a row.
    assert _names(win) == [
        "Empty",
        "Group",
        "Group/Part 1",
        "Group/Part 2",
        "Set 1",
        "Set 2",
        "Set 10",
    ]
    win.images_only_btn.setChecked(True)
    assert _names(win) == ["Group/Part 1", "Set 1", "Set 2", "Set 10"]

    # Select "Set 10", favorite + label via the inspector API.
    win._restore_selection([win.model.all_rows()[0].id])  # any row first
    set10 = next(r for r in win.model.all_rows() if r.rel_path == "Set 10")
    win._restore_selection([set10.id])
    assert win.inspector.current().rel_path == "Set 10"
    win.library.set_favorite([set10.id], True)
    win.inspector.chips.add_from_text("best, travel")
    row = win.model.row_by_id(set10.id)
    assert row.is_favorite and row.labels == ("best", "travel")

    # Label filter (AND) and favorites.
    win._on_label_filter(frozenset({"best", "travel"}), True, False)
    assert _names(win) == ["Set 10"]
    win.clear_filters()
    win.fav_btn.setChecked(True)
    assert _names(win) == ["Set 10"]
    win.fav_btn.setChecked(False)

    # Hide in app; hidden rows disappear unless "Show hidden".
    win.library.set_hidden([set10.id], True)
    assert "Set 10" not in _names(win)
    win.hidden_btn.setChecked(True)
    assert "Set 10" in _names(win)

    # Open in Photos (mocked launcher) counts a view.
    calls: list[str] = []
    monkeypatch.setattr(opener, "_startfile", lambda target: calls.append(target))
    win.open_folder(win.model.row_by_id(set10.id))
    assert (
        calls and calls[0].startswith("ms-photos:viewer?fileName=") and calls[0].endswith("1.png")
    )
    assert win.model.row_by_id(set10.id).view_count == 1

    # Fallback when the Photos protocol fails.
    def failing(target: str) -> None:
        if target.startswith("ms-photos:"):
            raise OSError("no handler")
        calls.append(target)

    monkeypatch.setattr(opener, "_startfile", failing)
    win.open_folder(win.model.row_by_id(set10.id))
    assert calls[-1].endswith("1.png") and not calls[-1].startswith("ms-photos:")


def test_navigation_views_and_dialogs(qtbot, window, library) -> None:
    win = window
    win.open_root(str(library))
    _wait_scan(qtbot, win)
    group = next(r for r in win.model.all_rows() if r.rel_path == "Group")
    win._browse(group)
    assert win.location == "Group" and _names(win) == ["Part 1", "Part 2"]
    win.go_back()
    assert win.location == ""
    win.go_forward()
    assert win.location == "Group"
    win.go_up()
    assert win.location == ""

    win.set_view_mode("cards")
    assert win.stack.currentWidget() is win.cards
    win.cards.grab()  # paints every visible card delegate
    win.set_view_mode("list")
    win.table.grab()

    win.show_labels_popup()
    assert win.labels_popup.isVisible()
    win.labels_popup.close()

    from foldervault.ui.dialogs.settings_dialog import SettingsDialog

    dlg = SettingsDialog(
        win.prefs, win.library, [], lambda n: None, lambda n: None, lambda n: None, win
    )
    dlg.accent_custom.setChecked(True)
    dlg._update_preview()
    dlg.close()

    # Search, then no-results page.
    win.search.setText("zzz-not-there")
    win.search.search_changed.emit("zzz-not-there")
    assert win.proxy.rowCount() == 0
    assert win.stack.currentIndex() == 3


def test_accent_change_rebuilds_theme(qtbot, window) -> None:
    window.prefs.accent_mode = "custom"
    window.prefs.accent_custom = "#FF7A00"
    window.apply_theme()
    assert tokens.current().accent == "#FF7A00"


def test_switching_to_missing_root_does_not_receive_stale_batches(
    qtbot, window, library, tmp_path
) -> None:
    win = window
    win.open_root(str(library))  # scan starts
    missing = tmp_path / "Unplugged"
    win.open_root(str(missing))  # cancels the scan; root does not exist
    qtbot.wait(1500)
    assert win.model.rowCount() == 0
    assert not win.library.scanning
    assert win.repo.load_rows(win.library.root_id) == []
    assert win.banner.isVisible()
