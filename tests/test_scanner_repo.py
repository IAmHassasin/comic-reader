from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from foldervault.core.image_types import CANDIDATE_EXTENSIONS
from foldervault.core.metadata_io import MetadataFileError, load_metadata_file, parse_metadata
from foldervault.core.scanner import scan_tree
from foldervault.data.repository import Repository
from foldervault.services.metadata_import import apply_metadata, export_items, to_rel_path

from .conftest import make_tree


def scan(root: Path) -> dict[str, object]:
    return {r.rel_path: r for r in scan_tree(root, CANDIDATE_EXTENSIONS)}


def test_scanner_counts_and_cover(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    make_tree(root, {"Group/Part 1": 3, "Group/Part 2": 12, "Set 1": 0})
    (root / "Set 1" / "notes.txt").write_text("x")
    (root / "Ünïcode name").mkdir()
    (root / "Ünïcode name" / "10.png").write_bytes(b"x")
    (root / "Ünïcode name" / "2.png").write_bytes(b"x")
    results = scan(root)
    assert results["Group"].image_count == 0 and results["Group"].subfolder_count == 2
    assert results["Group/Part 2"].image_count == 12
    assert results["Group/Part 2"].cover_name == "1.jpg"
    assert results["Group/Part 2"].preview_names == ("1.jpg", "2.jpg", "3.jpg")
    assert results["Group/Part 2"].parent_rel_path == "Group"
    assert results["Set 1"].image_count == 0
    assert results["Ünïcode name"].cover_name == "2.png"
    assert results["Ünïcode name"].format_stats == {"PNG": 2}
    assert results[""].subfolder_count == 3


@pytest.mark.skipif(sys.platform != "win32", reason="Windows attributes")
def test_scanner_reads_windows_hidden_attribute(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    make_tree(root, {"Visible": 1, "Secret": 1})
    subprocess.run(["attrib", "+h", str(root / "Secret")], check=True)
    results = scan(root)
    assert results["Secret"].win_hidden is True
    assert results["Visible"].win_hidden is False


def test_scanner_cancel(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    make_tree(root, {f"S{i}": 1 for i in range(20)})
    out = list(scan_tree(root, CANDIDATE_EXTENSIONS, should_cancel=lambda: True))
    assert out == []


def _seed(repo: Repository, tmp_path: Path) -> tuple[int, Path]:
    root = tmp_path / "lib"
    make_tree(root, {"A/1": 2, "A/2": 2, "B": 1})
    root_id = repo.get_or_create_root(str(root))
    repo.upsert_scan_results(root_id, list(scan_tree(root, CANDIDATE_EXTENSIONS)))
    return root_id, root


def test_repository_flags_labels_and_missing(repo: Repository, tmp_path: Path) -> None:
    root_id, root = _seed(repo, tmp_path)
    ids = repo.folder_ids_by_path(root_id)
    repo.set_favorite([ids["A/1"]], True)
    repo.set_folder_labels(ids["A/1"], ["best", "travel"])
    repo.add_labels([ids["B"]], ["Best"])
    rows = {r.rel_path: r for r in repo.load_rows(root_id)}
    assert rows["A/1"].is_favorite and rows["A/1"].labels == ("best", "travel")
    assert rows["B"].labels == ("best",)

    repo.rename_label("travel", "best")  # merge
    assert [lbl.name for lbl in repo.all_labels()] == ["best"]

    assert repo.mark_missing_except(root_id, {"", "A", "A/1", "A/2"}) == 1
    assert "B" not in {r.rel_path for r in repo.load_rows(root_id)}
    # Re-appearing folder keeps its labels.
    repo.upsert_scan_results(root_id, list(scan_tree(root, CANDIDATE_EXTENSIONS)))
    assert {r.rel_path: r for r in repo.load_rows(root_id)}["B"].labels == ("best",)


def test_metadata_import_semantics(repo: Repository, tmp_path: Path) -> None:
    root_id, root = _seed(repo, tmp_path)
    first = parse_metadata(
        {
            "version": 1,
            "items": [
                {
                    "path": "A/1",
                    "title": "T1",
                    "series": "S",
                    "labels": ["new"],
                    "extra": {"k": "v"},
                },
                {"path": str(root / "B"), "type": "Manga", "bogus": 1},
                {"path": "nope"},
            ],
        }
    )
    report = apply_metadata(repo, root_id, str(root), first)
    assert (report.matched, report.updated, report.not_found) == (2, 2, ["nope"])
    assert any("bogus" in w for w in report.warnings)

    second = parse_metadata(
        {
            "version": 1,
            "items": [{"path": "A/1", "series": None, "labels": ["x"], "labels_mode": "replace"}],
        }
    )
    apply_metadata(repo, root_id, str(root), second)
    row = {r.rel_path: r for r in repo.load_rows(root_id)}["A/1"]
    assert row.meta.title == "T1" and row.meta.series is None and row.meta.extra == {"k": "v"}
    assert row.labels == ("x",)

    # Re-applying identical data reports unchanged; dry-run writes nothing.
    assert apply_metadata(repo, root_id, str(root), second).unchanged == 1
    dry = parse_metadata({"version": 1, "items": [{"path": "A/2", "title": "Dry"}]})
    assert apply_metadata(repo, root_id, str(root), dry, dry_run=True).updated == 1
    assert {r.rel_path: r for r in repo.load_rows(root_id)}["A/2"].meta is None

    exported = {i["path"]: i for i in export_items(repo, root_id)}
    assert exported["A/1"]["title"] == "T1"


def test_metadata_file_validation(tmp_path: Path) -> None:
    with pytest.raises(MetadataFileError):
        parse_metadata({"version": 2, "items": []})
    with pytest.raises(MetadataFileError):
        parse_metadata({"version": 1, "items": [{"title": "no path"}]})
    with pytest.raises(MetadataFileError):
        parse_metadata({"version": 1, "items": [{"path": "a", "title": 3}]})
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(MetadataFileError):
        load_metadata_file(bad)


def test_to_rel_path(tmp_path: Path) -> None:
    root = str(tmp_path / "lib")
    assert to_rel_path("A\\1", root) == "A/1"
    assert to_rel_path(str(tmp_path / "lib" / "A" / "1"), root) == "A/1"
    assert to_rel_path(str(tmp_path / "elsewhere"), root) is None


def test_cli_round_trip(tmp_path: Path, repo: Repository) -> None:
    from foldervault import cli, config
    from foldervault.data.db import connect

    conn = connect(config.db_path())
    app_repo = Repository(conn)
    root_id, root = _seed(app_repo, tmp_path)
    app_repo.set_setting("last_root", str(root))
    conn.close()

    out = tmp_path / "export.json"
    assert cli.run(["export-meta", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    payload["items"][0]["title"] = "From script"
    out.write_text(json.dumps(payload), encoding="utf-8")
    assert cli.run(["import-meta", str(out), "--dry-run"]) == 0
    assert cli.run(["import-meta", str(out)]) == 0
    assert cli.run(["import-meta", str(tmp_path / "missing.json")]) == 1


def test_export_keys_round_trip_without_warnings(repo: Repository, tmp_path: Path) -> None:
    root_id, root = _seed(repo, tmp_path)
    data = parse_metadata({"version": 1, "items": export_items(repo, root_id)})
    report = apply_metadata(repo, root_id, str(root), data)
    assert report.warnings == [] and report.updated == 0


def test_import_rolls_back_on_non_sqlite_error(
    repo: Repository, tmp_path: Path, monkeypatch
) -> None:
    root_id, root = _seed(repo, tmp_path)
    data = parse_metadata(
        {"version": 1, "items": [{"path": "A/1", "title": "T"}, {"path": "B", "labels": ["x"]}]}
    )

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(repo, "add_labels", boom)
    with pytest.raises(RuntimeError):
        apply_metadata(repo, root_id, str(root), data)
    repo.set_setting("any", 1)  # a later commit must not persist the half-applied import
    assert {r.rel_path: r for r in repo.load_rows(root_id)}["A/1"].meta is None


def test_load_rows_by_ids_includes_labels_and_meta(repo: Repository, tmp_path: Path) -> None:
    root_id, root = _seed(repo, tmp_path)
    ids = repo.folder_ids_for_paths(root_id, ["A/1", "B", "nope"])
    assert len(ids) == 2
    repo.add_labels(ids, ["best"])
    rows = repo.load_rows(root_id, ids)
    assert sorted(r.rel_path for r in rows) == ["A/1", "B"]
    assert all(r.labels == ("best",) for r in rows)
