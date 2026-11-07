"""Command-line metadata import/export. Must not import Qt."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config
from .core.metadata_io import MetadataFileError, load_metadata_file, write_export_file
from .data.db import connect
from .data.repository import Repository
from .services.metadata_import import apply_metadata, export_items, resolve_root

COMMANDS = ("import-meta", "export-meta")


def _ensure_console() -> None:
    """In the windowed (no-console) build, attach to the parent console for output."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    try:
        import ctypes

        if ctypes.windll.kernel32.AttachConsole(-1):  # ATTACH_PARENT_PROCESS
            sys.stdout = open("CONOUT$", "w", encoding="utf-8")  # noqa: SIM115
            sys.stderr = sys.stdout
    except (AttributeError, OSError):
        pass


def _out(message: str, err: bool = False) -> None:
    stream = sys.stderr if err else sys.stdout
    if stream is not None:
        print(message, file=stream)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="foldervault")
    sub = parser.add_subparsers(dest="command", required=True)

    imp = sub.add_parser("import-meta", help="Import folder metadata from a JSON file")
    imp.add_argument("file", type=Path)
    imp.add_argument("--root", help="Library root (default: file 'root', then last opened root)")
    imp.add_argument("--dry-run", action="store_true", help="Report without writing")

    exp = sub.add_parser("export-meta", help="Export known folders and metadata to JSON")
    exp.add_argument("file", type=Path)
    exp.add_argument("--root", help="Library root (default: last opened root)")
    return parser


def run(argv: list[str]) -> int:
    _ensure_console()
    args = build_parser().parse_args(argv)
    conn = connect(config.db_path())
    try:
        repo = Repository(conn)
        if args.command == "import-meta":
            return _import(repo, args)
        return _export(repo, args)
    finally:
        conn.close()


def _import(repo: Repository, args: argparse.Namespace) -> int:
    try:
        data = load_metadata_file(args.file)
    except MetadataFileError as exc:
        _out(f"error: {exc}", err=True)
        return 1
    root = resolve_root(repo, args.root, data.root)
    if root is None:
        _out("error: no root given and no root opened before; use --root", err=True)
        return 1
    root_id = repo.find_root(str(root))
    if root_id is None:
        _out(f"error: root has never been scanned in FolderVault: {root}", err=True)
        return 1
    report = apply_metadata(repo, root_id, str(root), data, dry_run=args.dry_run)
    _out(report.summary())
    for path in report.not_found:
        _out(f"not found: {path}")
    for warning in report.warnings:
        _out(f"warning: {warning}")
    return 0


def _export(repo: Repository, args: argparse.Namespace) -> int:
    root = resolve_root(repo, args.root, None)
    if root is None:
        _out("error: no root given and no root opened before; use --root", err=True)
        return 1
    root_id = repo.find_root(str(root))
    if root_id is None:
        _out(f"error: root has never been scanned in FolderVault: {root}", err=True)
        return 1
    items = export_items(repo, root_id)
    try:
        write_export_file(args.file, str(root), items)
    except OSError as exc:
        _out(f"error: cannot write {args.file}: {exc}", err=True)
        return 1
    _out(f"exported {len(items)} folders to {args.file}")
    return 0
