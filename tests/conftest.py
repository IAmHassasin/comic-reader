from __future__ import annotations

from pathlib import Path

import pytest

from foldervault import config
from foldervault.data.db import connect
from foldervault.data.repository import Repository


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data = tmp_path / "appdata"
    monkeypatch.setenv(config.DATA_DIR_ENV, str(data))
    return data


@pytest.fixture
def repo(tmp_path: Path) -> Repository:
    conn = connect(tmp_path / "test.db")
    yield Repository(conn)
    conn.close()


def make_tree(root: Path, spec: dict[str, int]) -> None:
    """Create folders with N tiny fake image files each. Keys are '/'-separated paths."""
    for rel, count in spec.items():
        folder = root / rel
        folder.mkdir(parents=True, exist_ok=True)
        for i in range(1, count + 1):
            (folder / f"{i}.jpg").write_bytes(b"\xff\xd8\xff\xd9")
