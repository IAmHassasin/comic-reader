# 04 — Architecture

Stack (Decided: follows the tech stack in the source spec, but the spec's sample code isn't
used): **Python 3.11 + PySide6 (6.12 installed) + SQLite (stdlib `sqlite3`)**. The detailed design
below is the author's proposal, built from scratch.

## 1. Principles

1. **Read-only toward the library.** The app never writes, renames, moves or changes the
   attributes of anything under the root. That includes sidecar files. All app state lives in
   `%LOCALAPPDATA%\FolderVault\`.
2. **No disk I/O on the UI thread.** Scanning, thumbnail decoding and metadata import run in
   workers. The UI consumes the results through signals.
3. **Model/View all the way.** One `QAbstractTableModel` feeds both List and Album Cards through
   one filter proxy. Views are painted by delegates, never by per-row widgets.
4. **Tokens, not hex.** UI code reads colors from `ui/theme/tokens.py`, and fonts from
   `ui/theme/fonts.py` (derived from the system font).
5. **No built-in reader.** Images open in Windows Photos (`services/opener.py`).

## 2. Project layout

As implemented (v0.1.0):
```
comic-reader/
├─ pyproject.toml              # deps, ruff, pytest, entry point
├─ scripts/ build.ps1 (lint + test + icon + PyInstaller), make_icon.py
├─ src/foldervault/
│  ├─ __init__.py              # __version__
│  ├─ __main__.py              # GUI entry; routes import-meta / export-meta to cli.py
│  ├─ app.py                   # logging, excepthook, QApplication, theme, DB, main window
│  ├─ config.py                # app data paths (FOLDERVAULT_DATA_DIR override for tests)
│  ├─ cli.py                   # metadata CLI (no Qt import)
│  ├─ core/                    # pure Python, no Qt
│  │  ├─ entities.py  natural_sort.py  image_types.py  labels.py
│  │  ├─ scanner.py  filtering.py  colors.py  metadata_io.py
│  ├─ data/
│  │  ├─ db.py                 # connection, PRAGMAs, migration runner (backs up DB first)
│  │  ├─ migrations.py         # ordered (version, SQL) list, kept in Python so PyInstaller needs no data files
│  │  └─ repository.py         # one Repository class: roots, folders, labels, meta, settings
│  ├─ services/
│  │  ├─ library.py            # root, background scan, DB writes, label cache, signals
│  │  ├─ thumbnails.py         # memory LRU + disk cache, QThreadPool
│  │  ├─ opener.py             # Windows Photos / default app / Explorer
│  │  ├─ metadata_import.py    # transactional import, export, root resolution (no Qt)
│  │  ├─ windows_accent.py  privacy.py
│  └─ ui/
│     ├─ theme/ tokens.py, fonts.py, qss.py (QSS + dark palette), icons.py (inline SVG)
│     ├─ main_window.py  models.py  views.py  delegates.py  painting.py
│     ├─ context.py  formatting.py  settings.py (Preferences)
│     ├─ widgets/ flow_layout, search_field, toggle_switch, chip_editor, color_picker,
│     │           labels_popup, inspector
│     └─ dialogs/ settings_dialog.py, shortcuts_dialog.py
├─ tests/   (pytest + pytest-qt, offscreen)
├─ docs/
└─ design/stitch/              # source mockups (reference only)
```
Implementation notes (differences from the original plan):
- Every scan is a full walk. On Windows `os.scandir` returns file sizes and mtimes without
  extra system calls, so the mtime-based incremental rescan was not needed (a scan of the test
  library is far below the 30 s target; a real 58k-image library has not been measured yet).
- `QFileSystemWatcher` watches only the root folder itself, so auto-refresh reacts to changes
  directly under the root. Changes deeper down need F5.
- The import-report dialog is a `QMessageBox` with a dry-run preview and the details text.
- The Qt style is Fusion, so the QSS renders the same everywhere. The font is still the system font.

## 3. Data model (SQLite)

Location: `%LOCALAPPDATA%\FolderVault\library.db`.

```sql
CREATE TABLE roots (
  id INTEGER PRIMARY KEY,
  path TEXT NOT NULL UNIQUE,          -- absolute, normalized
  last_scanned_at TEXT
);

CREATE TABLE folders (
  id INTEGER PRIMARY KEY,
  root_id INTEGER NOT NULL REFERENCES roots(id) ON DELETE CASCADE,
  rel_path TEXT NOT NULL,             -- relative to root, '/' separators, '' = root itself
  parent_rel_path TEXT,
  image_count INTEGER NOT NULL DEFAULT 0,
  subfolder_count INTEGER NOT NULL DEFAULT 0,
  total_bytes INTEGER NOT NULL DEFAULT 0,
  cover_name TEXT,
  format_stats TEXT,                  -- JSON {"jpg":198,"png":2}
  mtime REAL,
  win_hidden INTEGER NOT NULL DEFAULT 0, -- Windows Hidden attribute (read at scan, never written)
  is_hidden INTEGER NOT NULL DEFAULT 0,  -- app-level hide flag
  is_favorite INTEGER NOT NULL DEFAULT 0,
  view_count INTEGER NOT NULL DEFAULT 0,
  last_opened_at TEXT,
  missing INTEGER NOT NULL DEFAULT 0,
  UNIQUE (root_id, rel_path)
);

CREATE TABLE folder_meta (            -- filled only by metadata import
  folder_id INTEGER PRIMARY KEY REFERENCES folders(id) ON DELETE CASCADE,
  title TEXT, series TEXT, type TEXT, language TEXT,
  extra TEXT,                         -- JSON object string→string
  updated_at TEXT NOT NULL
);

CREATE TABLE labels (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE,
  color TEXT                          -- palette key ('amber') or '#RRGGBB'; NULL = hash default
);

CREATE TABLE folder_labels (
  folder_id INTEGER NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
  label_id  INTEGER NOT NULL REFERENCES labels(id) ON DELETE CASCADE,
  PRIMARY KEY (folder_id, label_id)
);

CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);  -- JSON values
CREATE TABLE schema_version (version INTEGER NOT NULL);
```
PRAGMAs: `journal_mode=WAL`, `foreign_keys=ON`, `synchronous=NORMAL`, `busy_timeout=3000`
(the CLI import may write while the GUI is open).

Effective hidden = `is_hidden OR win_hidden`.

### Label rules
Trim, collapse whitespace, case-insensitive uniqueness, max 40 chars, no `,`.
Rename into an existing name merges the two labels. Delete removes the label from every folder
after a confirmation.

### Folder identity (accepted limitation)
Folders are keyed by `(root, rel_path)`. A rename or move outside the app orphans the labels,
favorite and metadata. Rows not seen in a scan are marked `missing=1` and kept. "Re-link" (when
a new folder has the same image count and cover name) is P1. The owner's metadata script can
also re-apply metadata after a rename.

## 4. Scanning

- `os.scandir` recursive walk in a `QRunnable` on a dedicated single-thread `QThreadPool`.
  Emit batches of ~50 folders through a `QObject` signal bridge.
- Per folder: direct image count by extension, direct subfolder count, size sum, cover
  (natural sort, first), format stats, and `win_hidden` from
  `DirEntry.stat().st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN`.
- Skip: entries with both HIDDEN and SYSTEM attributes, reparse points / junctions (avoids loops),
  `$RECYCLE.BIN`, `System Volume Information`.
- Incremental rescan by folder `mtime` (it changes when direct children are added or removed, but
  not on in-place edits or attribute changes). F5 does a full rescan, which also picks up a
  changed Hidden attribute.
- Cancellable. Per-folder errors are logged and the walk continues.
- Auto-refresh: `QFileSystemWatcher` on the current root + a 2 s debounce → incremental rescan.

Image extensions: `.jpg .jpeg .jfif .png .gif .bmp .webp .tif .tiff`. Verified with
`QImageReader.supportedImageFormats()` on PySide6 6.12 (2026-11-07). At startup, intersect the
list with the formats Qt reports. `pdf`, `svg` and `ico` are reported by Qt but **excluded**,
because they aren't comic pages.

## 5. Model / filtering

- `FolderTableModel(QAbstractTableModel)` with custom roles (`FolderIdRole, LabelsRole,
  MetaRole, IsFavoriteRole, HiddenSourceRole, CoverKeyRole …`).
- `FolderFilterProxy(QSortFilterProxyModel)`: `filterAcceptsRow` → `core.filtering`.
  Natural-sort `lessThan`. Search matches the folder name, labels, and meta title/series
  (casefold, accent-insensitive with `unicodedata` NFKD (P)).
- "All levels" off → `parent_rel_path == current`. On → every descendant.
- Navigation history (back/forward stacks) lives in the main window controller.

## 6. Thumbnails

- Sizes: 32 px (list option), 160 px tall (album cover + 2 back layers), 360 px wide (inspector).
- `QImageReader` + `setScaledSize` + `setAutoTransform(True)` in workers → `QImage`. Convert to
  `QPixmap` on the UI thread only.
- Memory LRU (~200 MB). Disk cache at
  `%LOCALAPPDATA%\FolderVault\thumbs\<sha1(path|mtime|size|w)>.jpg`, except for hidden folders
  when the privacy option is on.
- The delegate paints a placeholder, requests the thumbnail, and emits `dataChanged` for that
  row when it arrives.

## 7. Opening images (`services/opener.py`)

```
open_in_photos(path)   -> QDesktopServices.openUrl(QUrl("ms-photos:viewer?fileName=" + quote(abs_path)))
open_default(path)     -> os.startfile(abs_path)
reveal_in_explorer(p)  -> subprocess.Popen(["explorer.exe", "/select,", abs_path])
```
- The configured mode decides `open_in_photos` vs `open_default`. If `openUrl` returns False,
  fall back to `open_default` and notify once.
- **To verify in Phase 4:** that the `ms-photos:` URI opens the file *with folder navigation*
  on both Windows 10 and 11. It's a widely used but undocumented protocol. If it's unreliable,
  the fallback is `os.startfile` (which uses Photos when Photos is the default image app).
- After a successful launch: `view_count += 1`, `last_opened_at = now()`.

## 8. Metadata import / export

- `core/metadata_io.py`: parses and validates schema v1 (03 §S6) into typed records and
  collects warnings. Pure Python.
- `services/metadata_import.py`: resolves paths to folder ids, then applies everything in a
  single transaction and returns an `ImportReport`. `--dry-run` rolls back.
- CLI (`python -m foldervault import-meta|export-meta …`) must not import PySide6, so it stays
  fast and works headless.
- The GUI reloads metadata after its own import. After an external CLI import it reloads on F5,
  or when the DB file mtime changes (P).

## 9. Colors

- `core/colors.py`: relative luminance, contrast ratio, blending, and chip derivation (02 §1.6),
  plus the accent derivation (02 §1.4). Unit-tested.
- Windows accent: read `HKCU\Software\Microsoft\Windows\DWM\AccentColor` (ABGR DWORD) through
  `winreg`. Fall back to `#60CDFF` if it's unavailable. Read-only.
- When the accent or a label color changes: regenerate the QSS, `app.setStyleSheet`, and repaint
  the views.

## 10. Settings (persisted in the `settings` table)

Last root, recent roots, window geometry/state, splitter sizes, column widths/order, view mode,
sort, quick filters, open-with mode, auto-refresh, list thumbnails, accent mode + color,
privacy options.

## 11. Error handling & logging

- `logging` to `%LOCALAPPDATA%\FolderVault\logs\app.log` (rotating 5×1 MB). With stealth mode
  on, paths are logged at DEBUG only (P).
- A corrupt image shows a placeholder. Delegates never raise.
- Back up the DB before running migrations.

## 12. Packaging

PyInstaller one-folder build. The version comes from `foldervault.__version__`.
