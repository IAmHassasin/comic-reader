# 03 — Screens & Interactions

Visual tokens and components are defined in [02-design-system.md](02-design-system.md).
**(P)** = proposed and not yet confirmed. Everything else is Decided (see the decision log in
[06-design-review.md](06-design-review.md#decision-log)).

Screen list: S1 Main window (List) · S2 Album Cards · S3 Labels popup · S4 Open in Photos ·
S5 Settings (General / Appearance / Labels / Privacy) · S6 Metadata import · S7 Keyboard map.

The mockup's fullscreen viewer (`foldervault_fullscreen_photo_viewer/`) is **not built**.
Reading is delegated to Windows Photos (S4).

---

## S1. Main window

Reference: `foldervault_main_window_windows_11_fluent/code.html` (no PNG) and the shell parts of
the album and labels PNGs.

### Layout
```
┌ Native title bar: "FolderVault" (or the stealth title, see S5) ─────────────────────┐
├ Toolbar ────────────────────────────────────────────────────────────────────────────┤
│ [Open root] [⟳] [↑] │ [List|Album Cards] │ [🔍 Search name, label, title…  Ctrl+F]   │
│ [All levels] [★ Favorites] [☑ Image folders only] [☐ Show hidden] │ [Labels: all ▾] │
│                                                             [⤨ Random] [⚙ Settings] │
├ Context bar: Photos / all levels · Filtered by 2 labels (best, travel)    sort info  ┤
├──────────────────────────────────────────────────────┬──────────────────────────────┤
│ Content: List (S1a) or Album Cards (S2)             ║ Inspector (S1b), QSplitter    │
├──────────────────────────────────────────────────────┴──────────────────────────────┤
│ Status bar: totals | showing N                                 ● Ready   v0.x.y     │
└──────────────────────────────────────────────────────────────────────────────────────┘
```
- Native title bar. A frameless custom bar would cost Snap Layouts and native resize.
- The toolbar wraps into two rows below ~1200 px (two toolbars, or a flow layout).
- The mockup's `Privacy` button becomes **`Settings`** (gear) and opens S5. A small `accent` dot
  shows while stealth title or clear-on-exit is on (P).
- Mouse back/forward buttons (XButton1/2) navigate back/forward, like in Explorer.

### S1a. List mode (table, Explorer "Details" style)
| Col | Header | Content | Align | Sort |
|---|---|---|---|---|
| 0 | ★ | Star toggle (click toggles, selection unchanged) | center | favorites first |
| 1 | Folder | Icon (or 32 px cover if the option is on) + name relative to the current location. If a metadata `title` exists: the title, and the folder name in the tooltip | left | natural, case-insensitive |
| 2 | Images | Direct image count, `—` for 0 | right | numeric |
| 3 | Subfolders | Direct child folder count, `—` for 0 | right | numeric |
| 4 | Labels | Colored chips, overflow `+N` | left | by first label |
| 5 | Views | Times opened from the app, blank for 0 | right | numeric |

- Default sort: Folder ascending, natural (`Set 2` < `Set 10`, same as Explorer).
- Cover-thumbnail option: off by default.
- Column widths and order are user-resizable and movable, and persisted (Explorer behavior).
- Type-ahead: typing letters jumps to the next folder whose name starts with them.
- Multi-select: Ctrl/Shift-click, Ctrl+A.
- Hidden rows (when `Show hidden` is on) render at 50 % opacity with an eye-off icon,
  like hidden items in Explorer.
- Double-click / Enter:
  - Image folder → open in Photos (S4).
  - Group folder (0 images) → navigate into it.
  - Folder with images **and** subfolders → open in Photos. Ctrl+Enter or the context menu
    "Browse subfolders" navigates into it.
- Right-click / Shift+F10 / Menu key: context menu with Open in Photos, Browse subfolders,
  Open in Explorer, Favorite, Hide/Unhide, Edit labels, Copy path.

### S1b. Inspector
Top to bottom:
1. Preview of the cover. Clicking it opens that image in Photos.
2. Name (or metadata title) + ★ + image-count pill.
3. `size total • last scanned` line.
4. LABELS: chip editor (Enter to save, Esc to revert, Backspace on empty removes the last chip).
   Right-click a chip → *Change color…*. Suggestions = the top 3 most-used labels not on the folder.
5. Actions: `Open` (primary, opens in Photos) · `★ Favorite / Unfavorite` · `Hide / Unhide`.
6. METADATA (only when the folder has imported metadata): Series, Type, Language, then
   `extra` key/values. Read-only in the UI. The script is the source of truth.
7. DIRECTORY PROPERTIES: absolute path (elided in the middle, full path in the tooltip,
   click to copy), image formats, subfolder count, `Hidden in Windows: Yes` when applicable.

- 2+ folders selected: `N folders selected`, the combined image count, and bulk
  `Add label… / Remove label… / Favorite / Hide`.
- Nothing selected: the "Select a folder" placeholder.
- The mockup's `Security Flag: Public Vault` row isn't built.

### Hidden folders
| Source | How it's set | Unhide in app |
|---|---|---|
| App flag | `Hide` button / Ctrl+H | Yes |
| Windows *Hidden* attribute | Set by the user in Explorer (Properties → Hidden) | No. The `Hide` button is disabled with the tooltip "Hidden in Windows. Change it in Explorer". The app never changes file attributes |

Folders with both *Hidden* **and** *System* attributes (e.g. `$RECYCLE.BIN`) are never scanned.

### States
| State | Display |
|---|---|
| First run (no root) | Centered empty state: "Open a folder to start" + `Open root` primary button |
| Scanning | Rows appear progressively, status bar `Scanning 312 / 636…` + Cancel |
| Root missing / drive unplugged | Banner "Root not found: D:\Comics" + `Choose another` / `Retry` |
| No results for the filter | "No folders match" + `Clear filters` |
| Permission denied on a subfolder | Row with a warning icon and tooltip. The scan continues |
| Photos failed to launch | Status bar error + toast: "Couldn't open Windows Photos" + `Open with default app` |

---

## S2. Album Cards mode

Reference: `foldervault_album_preview_mode_stacked_covers/screen.png`. Visual spec: design system §5.6.

- Same model, filters, selection and inspector as List. Only the view changes.
- Card fields:
  - Title: metadata `title`, falling back to the folder name.
  - Badge (top-right): the folder name when a title exists (like `Set_003` in the mockup).
  - Path row: path, image count, total size.
  - Series / Type / Language: from imported metadata. **A row without a value is hidden**,
    never shown as `N/A`.
  - Tags: the folder's labels in their colors. Max 2 lines, then `…`.
  - Footer: folder modified time (left) and `Last opened <relative>` (right).
- The mockup's `Preview: 3-layer book stack` and `SELECTED` pill aren't built.
- Dates and times use `QLocale.system()` formats.

---

## S3. Labels filter popup

Reference: `foldervault_labels_filter_menu/screen.png`.

- Anchored under `Labels: all` / `Labels: 2 selected`. The button gets an `accent` border while
  the filter is active.
- Contents: search field (autofocus) → `☐ Match ALL` | `☐ (no label)` | `Clear` → list rows
  (checkbox, color dot, name, count) → footer `Space to toggle · Esc to close`.
- Semantics:
  - None checked → no label filter.
  - Match ALL off → OR, on → AND.
  - `(no label)` → folders without labels. It's OR'ed with the checked labels and disabled
    while Match ALL is on.
  - Counts are computed within the other active filters. Zero-count labels are listed dimmed.
- Right-click a row → *Change color…* / *Rename…* / *Delete label…* (delete asks for confirmation
  and removes the label from every folder).
- The filter applies live. Esc closes the popup and keeps the selection.
- Keys: ↑/↓, Space toggles, typing filters, Enter / Esc close.

---

## S4. Open in Windows Photos (replaces the built-in viewer)

| Item | Behavior |
|---|---|
| What opens | The folder's cover = the first image in natural order. In Photos the user presses ←/→ to move through the folder |
| Launch method | Setting `Open images with`: **Windows Photos** (default) or **Default app** (the user's file association) |
| Windows Photos | Launch the `ms-photos:viewer?fileName=<url-encoded absolute path>` URI. If that fails, fall back to the default app and show a toast once **(P, verify on Win10 and Win11)** |
| Default app | `os.startfile(path)` (ShellExecute "open") |
| Side effects in the app | `view_count += 1`, `last_opened_at = now` |
| Threading | The launch is async. The UI never waits for Photos |
| Specific image | Clicking the inspector preview opens that image (the cover) |

Known limitations, shown as a hint in S5 › General:
- Photos uses **its own** folder order. It normally matches Explorer's name sort, which can
  differ from the app's natural sort in edge cases.
- Photos and Windows may record the opened file in their own history (Photos recents,
  Windows Recent items). FolderVault can't prevent this.
- No resume-page, reading direction, spread or webtoon mode. That's up to Photos.

---

## S5. Settings dialog

Opened from the toolbar gear, or with Ctrl+, (P). It replaces the mockup's Privacy dialog and
reuses its look: native-title `QDialog`, section labels, switch rows, footer
`Restore defaults` · `Cancel` · `Save`. A left-side tab list: **General · Appearance · Labels · Privacy**.

### General
- Open images with: (•) Windows Photos  ( ) Default app.
- Auto-refresh when the root changes: switch, default on.
- Show cover thumbnails in List mode: switch, default off.
- Root history: the list of recent roots with remove buttons.

### Appearance
- Accent color: (•) Fluent blue `#60CDFF`  ( ) Windows accent color  ( ) Custom… (color picker).
  The live preview shows a button, a selected row and a focused input.
- Surfaces stay fixed (dark only).

### Labels
Table: color swatch · name · folder count · actions (Change color, Rename, Delete).
- Color picker: 7 palette swatches (02 §1.5) + `Custom…` (`QColorDialog`, any color).
  Chip fill, border and text are derived from the chosen color (02 §1.6).
- Rename merges into an existing label if the new name already exists (with a confirmation).

### Privacy (app-level only)
| Item | Behavior |
|---|---|
| Clear app history on exit | Clears recent roots, search history and the thumbnail disk cache when the app closes |
| Don't cache thumbnails of hidden folders | Hidden folders' covers stay in memory only |
| Stealth window title | Title and taskbar text become "Image Library" while the window is inactive or minimized |
| `Clear app history now` button | Same as the exit option, run now, with a result line ("Cleared 12 recent roots, 340 MB cache") |

Info note: "FolderVault doesn't change Windows settings and doesn't encrypt files. Windows
Photos and Explorer keep their own history."

The mockup's OS-level toggles, the immediate-operation buttons, the "Shield telemetry console"
and the vault lock are **not built** (decision log #3).

---

## S6. Metadata import (for external scripts)

Owner decision: the metadata stays empty until the owner's own script provides it. The app
gives the script a documented file format and two entry points.

### Entry points
- Menu **File › Import metadata…** (pick a `.json` file) → result dialog.
- CLI: `python -m foldervault import-meta <file.json> [--root <path>] [--dry-run]`
- CLI: `python -m foldervault export-meta <out.json> [--root <path>]` writes every known folder
  (path, name, image count, current metadata, labels). The script can use it as a template.

### File format (version 1)
```json
{
  "version": 1,
  "root": "D:/Comics",
  "items": [
    {
      "path": "Series A/Vol 01",
      "title": "Series A — Volume 1",
      "series": "Series A",
      "type": "Manga",
      "language": "Japanese",
      "labels": ["best", "ongoing"],
      "labels_mode": "merge",
      "extra": { "Artist": "Someone", "Year": "2021" }
    }
  ]
}
```
| Field | Rule |
|---|---|
| `path` | Absolute, or relative to `root` (the file's `root`, `--root`, or the current root). `/` or `\` |
| `title`, `series`, `type`, `language` | String sets the value · `null` clears it · key absent leaves it unchanged |
| `labels` | Optional. `labels_mode`: `merge` (default, add only) or `replace` |
| `extra` | Optional flat string→string map. It replaces the stored `extra` when present |
| Unknown keys | Ignored, and reported as warnings |

### Import behavior
- The import runs in one DB transaction. If the file is invalid (bad JSON, wrong version),
  nothing is applied.
- Items whose `path` isn't a known folder are **skipped and listed** in the report.
  They aren't created.
- Report: `matched N · updated N · unchanged N · not found N · warnings N`. The CLI exits with
  code 0 when it's OK and 1 on errors.
- `--dry-run` prints the report without writing anything.
- Safe while the app is running (SQLite WAL). The app reloads metadata on F5 or when the DB
  changes (P).
- The app **never writes** a sidecar file into the library.

---

## S7. Keyboard map (Windows / Explorer conventions)

Single-letter keys and Backspace are ignored while a text field has focus.

### Main window
| Key | Action | Windows convention it follows |
|---|---|---|
| Ctrl+O | Open root | Standard Open |
| F5, Ctrl+R | Refresh / rescan | Explorer refresh |
| Alt+↑ | Up one level | Explorer |
| Alt+←, Backspace, Mouse Back | Back | Explorer |
| Alt+→, Mouse Forward | Forward | Explorer |
| Ctrl+F, Ctrl+E, F3 | Focus search | Explorer search box |
| Esc (in search) | Clear the search, focus the list | Explorer |
| Enter, double-click | Open in Photos / enter a group folder | Explorer open |
| Ctrl+Enter | Browse subfolders | — |
| Ctrl+Shift+E | Open in Explorer | VS Code-style "reveal in Explorer" |
| F2 | Edit labels of the selection | Explorer F2 = rename / edit |
| Alt+Enter | Focus the inspector properties | Explorer Properties |
| Alt+P | Show / hide the inspector | Explorer preview pane |
| Ctrl+Shift+6 | List (Details) view | Explorer Details view |
| Ctrl+Shift+8 | Album Cards (Content) view | Explorer Content view |
| Ctrl+A | Select all | Standard |
| Ctrl+Shift+C | Copy path | Windows 11 "Copy as path" |
| Shift+F10, Menu key | Context menu | Standard |
| Ctrl+D | Toggle favorite | Browser "add to favorites". The app never deletes, so there's no clash with Explorer's Ctrl+D |
| Ctrl+H | Hide / unhide (app flag) | — |
| Ctrl+Shift+H | Toggle `Show hidden` | — |
| Ctrl+Shift+L | Open the Labels popup | — |
| Ctrl+, | Settings | Modern Windows apps |
| F11 | Full-screen window | Explorer F11 |
| F1 | Shortcut cheat-sheet dialog | Standard help |
| Random | No shortcut (toolbar only) | — |

### Labels popup
↑/↓ move · Space toggles · Enter / Esc close · typing filters.

### Dialogs
Enter = default button (Save) · Esc = Cancel · Ctrl+Tab / Ctrl+Shift+Tab switch Settings tabs.
