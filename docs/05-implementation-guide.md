# 05 — Implementation Guide

## 1. Environment (set up 2026-11-07)

| Item | Value |
|---|---|
| Interpreter | Python **3.11.9** (existing install, `py -3.11`). No system-wide install was added |
| Virtual env | `.venv/` in the repo root (git-ignored) |
| Installed | PySide6 **6.12.0** (Qt 6.12.0), pytest 9.2, pytest-qt, ruff 0.17.4, pyinstaller |
| Package | `src/foldervault` installed in editable mode (`pip install -e ".[dev]"`) |
| Checked | PySide6 imports, a `QApplication` starts, the default font is Segoe UI 9 pt, and `QImageReader` supports jpg/png/gif/bmp/webp/tiff |

Why 3.11 and not 3.14: `py` defaults to 3.14, but `pyproject.toml` pins `>=3.11,<3.14` to stay
on versions PySide6 has long supported. Revisit the upper bound once you've confirmed PySide6
supports 3.14.

Daily use (PowerShell):
```powershell
.\.venv\Scripts\Activate.ps1
python -m foldervault          # currently a placeholder window ("environment OK")
pytest
ruff check . ; ruff format .
```

Recreate from scratch:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## 2. Conventions

- Code, comments, identifiers, logs and UI strings are in **English** (org rule). Wrap UI
  strings in `self.tr()` so a Vietnamese translation can be added later.
- `ruff` lint + format. Type hints on public functions.
- `core/` and `cli.py` must not import Qt.
- No hex colors outside `ui/theme/tokens.py`, and no font families anywhere (use the system font).
- No emoji icons. Use SVG from one icon set.
- Don't use the spec's sample code (owner decision). Build from these docs.
- Commit per vertical slice. Every commit leaves the app runnable.

## 3. Phased plan

**Status 2026-11-07:** phases 1–8 are implemented in v0.1.0 and the build produces
`dist\FolderVault\FolderVault.exe`. Still open: R-01 (manual check that the `ms-photos:` launch
gives ←/→ navigation in Photos on Win10 and Win11) and a performance measurement on a real
58k-image library. See the root `README.md` for the run, test and build commands.

| Phase | Scope | Exit criteria |
|---|---|---|
| **0. Decisions** | ✅ Done 2026-11-07 (06 decision log) | — |
| **1. Skeleton** | `app.py`, theme (tokens → QSS, system-font styles, accent derivation), main window shell, toolbar, status bar, empty state, settings persistence | Launches with the dark theme. Geometry is restored. `core/colors.py` contrast tests pass |
| **2. Library core** | DB + migrations, scanner (worker, cancel, incremental, Windows hidden attribute), model + proxy, List mode, Up/Back/Forward/breadcrumb/All levels, natural sort | A synthetic library of 636 folders / 58k images scans without UI freeze. Tests for the scanner, natural sort and filtering pass |
| **3. Organize** | Favorites, labels (chip editor, chips delegate, **custom colors**), hide/unhide, search, quick filters, labels popup, inspector, keyboard map (03 §S7) | Filter combinations are unit-tested. Labels and colors persist across restarts |
| **4. Open in Photos** | `services/opener.py`, view counting, context menu, Explorer reveal. Verify the `ms-photos:` URI on Win10 and Win11 | `Open` launches Photos with ←/→ navigation through the folder. The fallback works |
| **5. Album Cards** | Card delegate, stacked covers, thumbnail pipeline (memory + disk cache), metadata rows | Smooth scroll through 636 cards. Empty metadata rows are hidden |
| **6. Metadata import** | `metadata_io`, import service, CLI `import-meta` / `export-meta`, File › Import, report dialog | Round-trip test: export → edit → import. Dry-run writes nothing. Unknown paths are reported |
| **7. Settings** | General / Appearance (accent: default / Windows / custom) / Labels manager / Privacy (app-level) | Every setting persists and applies live |
| **8. Packaging** | PyInstaller one-folder build, icon, version | Runs on a machine without Python |

## 4. Testing strategy

- **Unit**: natural sort, label normalization/merge, filter predicate (AND/OR/no-label ×
  favorites × hidden(app/windows) × search incl. meta title), color derivation and contrast,
  metadata schema validation (null vs absent, labels merge/replace, bad version, unknown
  paths), scanner on a temp tree (empty folders, junction loop, permission error, unicode
  names, a Hidden-attribute folder set through `attrib +h` in the test fixture), repository
  CRUD + migrations.
- **Widget (pytest-qt)**: model/proxy counts, labels popup, chip editor, color picker, keyboard
  shortcuts in 03 §S7.
- **Opener**: mock `QDesktopServices.openUrl` / `os.startfile`. Check the fallback and the view
  counting. Test the real Photos launch manually.
- **Performance**: a generator script for 636 folders × ~92 tiny images. Measure the scan time
  and the first paint.
- **Visual**: compare against the PNGs in `design/stitch/` at 100 % and 150 % scaling.

## 5. Definition of done (per feature)

- Matches [02](02-design-system.md) tokens and the [03](03-screens-and-interactions.md) behavior,
  including empty, loading and error states.
- Keyboard-operable, and the focus is visible.
- No UI-thread disk I/O.
- Tests added and passing. `ruff check` is clean.
- Never writes inside the library root.
