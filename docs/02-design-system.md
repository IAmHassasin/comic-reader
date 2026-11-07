# 02 — Design System ("Fluent Slate", consolidated)

This file is the **single source of truth** for visual tokens. The two source files
(`technical_design_specification.md` §1–2 and `fluent_slate_desktop/DESIGN.md`) disagree on
several values. Every value below is either taken from where they agree, or picked to match
the PNG mockups. The owner accepted this consolidated set on 2026-11-07 (decision log #6). The few
remaining **(P)** marks are implementation formulas that can still be tuned.
The full list of conflicts is in [06-design-review.md](06-design-review.md#a-design-system-conflicts).

Implementation rule: tokens live in one Python module (`ui/theme/tokens.py`) and the QSS is
**generated** from them. Don't hard-code hex values in widgets or delegates.

---

## 1. Color tokens (dark only)

### 1.1 Surfaces
| Token | Hex | Use |
|---|---|---|
| `surface.lowest` | `#0E0E0E` | Status bar, deepest containers |
| `surface.base` | `#131313` | Main window / table background |
| `surface.row-alt` | `#171818` | Alternate table row, between the two sources' `#161717` and `#242424` |
| `surface.low` | `#1B1C1C` | Toolbar, inspector background, card body |
| `surface.container` | `#202121` | Inputs, popups, header cells |
| `surface.high` | `#2A2B2B` | Hover fill, buttons at rest, card header |
| `surface.highest` | `#353636` | Pressed / checked fill, chip background |

> The DESIGN.md prose describes a lighter `#202020 / #262626 / #2C2C2C` scale. The mockups,
> the HTML Tailwind config and the tech spec all use the `#131313` scale, so that scale wins.

### 1.2 Lines
| Token | Hex | Use |
|---|---|---|
| `line.subtle` | `#232424` | Row separators, gridlines |
| `line.default` | `#3C3D3E` | Input and button borders, dividers |
| `line.strong` | `#4D4E4F` | Hover borders, popup borders, splitter handle on hover |

### 1.3 Text
| Token | Hex | Use |
|---|---|---|
| `text.primary` | `#F3F3F3` | Names, headings, values |
| `text.secondary` | `#9E9E9E` | Metadata, paths, header cells |
| `text.tertiary` | `#737373` | Placeholders, shortcut hints, disabled |
| `text.on-accent` | `#FFFFFF` | Text on a filled accent button |

Contrast check (WCAG AA ≥ 4.5:1 on `#131313`): primary ≈ 17:1, secondary ≈ 7:1,
tertiary ≈ 3.9:1, so **tertiary only works for non-essential hints** (≥ 3:1 large/UI).

### 1.4 Accent & state
**The accent is user-customizable** (Settings › Appearance): Fluent blue (default), the
Windows accent color, or any custom color. The user picks **one** base color, and the
`accent*` and `selection.*` tokens below are derived from it at runtime. The values in the table
are the defaults for `#60CDFF`. Derivation **(P)**:
`accent` = base. `accent.fill` = base darkened until white text reaches ≥ 4.5:1.
`accent.fill-hover` = `accent.fill` lightened 6 %. `selection.row` = base blended 30 % over `surface.base`.
`selection.row-inactive` = base blended 15 %. The QSS is regenerated when the accent changes.

| Token | Hex | Use |
|---|---|---|
| `accent` | `#60CDFF` | Focus ring, selection bar, active toggle, links |
| `accent.fill` | `#0078D4` | Primary button fill, checked checkbox |
| `accent.fill-hover` | `#1084D9` | Primary button hover |
| `selection.row` | `#1A4B75` | Selected row fill, matching the labels-filter PNG |
| `selection.row-inactive` | `#24384A` | Selected row while the view isn't focused |
| `favorite.on` | `#FFC83B` | Active star, picked over `#FFD700` |
| `favorite.off` | `#4A4A4A` | Inactive star |
| `danger` | `#E05D5D` | Destructive text and icons |
| `danger.fill` | `#5A1E1E` / border `#822828` / text `#FFB3B3` | Danger button |
| `warning` | `#FFB900` | Warning banners |
| `success` | `#4CC38A` | "Ready" dot, OK log lines |

### 1.5 Label (tag) palette
Chips use a **tinted fill + 1 px rim + light text** (the DESIGN.md style, as in the album and
labels PNGs). The saturated solid fills in the tech spec §1.1 are dropped.

| Key | Fill | Border | Text | Dot (filter list) |
|---|---|---|---|---|
| `amber` | `#382A18` | `#94682E` | `#FFD285` | `#F5B83D` |
| `green` | `#1B3224` | `#3E7756` | `#82E0AA` | `#3DD68C` |
| `cyan` | `#162E3B` | `#2B6B8B` | `#7CE3FF` | `#3CC8F0` |
| `violet` | `#2C1E38` | `#6D458C` | `#DDB8FF` | `#B57BFF` |
| `rose` | `#3A1A22` | `#8C3A4C` | `#FFB3C1` | `#F2667E` |
| `blue` | `#16263F` | `#2F5A99` | `#9CC3FF` | `#4A90E2` |
| `slate` | `#262728` | `#4A4C4E` | `#C8CACC` | `#8A8F94` |

Label → color assignment (Decided: **user-customizable**):
- A new label gets a palette key from a stable hash of its lowercase name.
- The user can change it any time (chip right-click, Labels popup right-click, Settings › Labels).
  The user can pick one of the 7 palette keys or **any custom color** (`QColorDialog`).
- Stored per label in the DB as either a palette key (`amber`) or a hex (`#FF7A00`).

### 1.6 Deriving chip colors from a custom color (P)
Given the base color `C` (the user's pick):
| Part | Formula |
|---|---|
| Dot | `C` |
| Fill | `C` alpha-blended 18 % over `surface.base` |
| Border | `C` alpha-blended 55 % over `surface.base` |
| Text | `C` mixed toward white in 10 % steps until contrast vs Fill ≥ 4.5:1 |

Implement this once in `ui/theme/colors.py` with a unit test that checks contrast ≥ 4.5:1 for a
set of extreme inputs (black, white, pure red/green/blue, mid-grey). The 7 palette rows above
are hand-tuned and are used as-is.

---

## 2. Typography

Font (Decided): **the same font as Windows Explorer**, which is the Windows system UI font.
Qt on Windows already uses it as the default application font: **Segoe UI 9 pt** on the dev
machine (checked 2026-11-07 with PySide6 6.12). So:
- **Don't hard-code a family.** Take `QApplication.font()` as the base and derive every style
  from it by size and weight only. If the user changes the system font or text size, the app
  follows, like Explorer.
- Inter (from the mockups) isn't used or bundled.
- Sizes are in **pt, relative to the base** (9 pt ≈ 12 px at 100 % scaling). Never mix pt and px.

| Token | Size (pt) / weight | ≈ px @100 % | Use |
|---|---|---|---|
| `title` | base + 5 / 600 | 19 | Dialog titles |
| `heading` | base + 2 / 600 | 15 | Album card title, inspector folder name |
| `subheading` | base / 600 | 12 | Section headers inside dialogs |
| `body` | base / 400 | 12 | Table cells, inputs, buttons (same as Explorer's Details view) |
| `caption` | base − 1 / 400 | 11 | Metadata, status bar, header cells (600) |
| `micro` | base − 1.5 / 600 | 10 | Keycaps, chips, uppercase section labels |

Rules:
- Use tabular figures for numeric columns. Segoe UI's digits are already tabular.
- Right-align the numeric columns `Images`, `Subfolders`, `Views`. The current app centers them.
- Shortcut hints are `micro` text in `text.tertiary`, inside a keycap
  (`surface.container` fill, `line.default` border, radius 3).
- Don't put `font-family` in QSS. Derive `QFont` objects from `QApplication.font()` in
  `ui/theme/fonts.py`, and have delegates use those objects.

## 3. Spacing, sizing, radii

Base unit **4 px**. Scale: `2, 4, 8, 12, 16, 24`.

| Element | Value |
|---|---|
| Toolbar height | 40 px (buttons 28 px) |
| Input / button height | 28 px (the sources say 26). 28 leaves room for Segoe UI 9 pt at 125–150 % scaling |
| Table row height (List mode) | 28 px (cover thumbnail off), 44 px (cover thumbnail on) |
| Table header height | 26 px |
| Album card height | ~ 210 px (cover 120×160 + padding) |
| Inspector width | 320 px default, 280–480 resizable (QSplitter) |
| Status bar height | 24 px |
| Radius: chips, keycaps | 4 px (pills at 10 px are not used) |
| Radius: buttons, inputs, image previews | 4 px |
| Radius: cards, popups | 6 px |
| Radius: dialogs | 8 px |
| Panels docked to the window edge | 0 px |

Elevation is **tonal only** (no blurred shadows in QSS). Popups use `surface.container` +
`line.strong` border. If a shadow is really needed, `QGraphicsDropShadowEffect` is allowed on
popups only, never on list items.

## 4. Iconography

- Use **one** icon family: Fluent UI System Icons (MIT) or Material Symbols Outlined (Apache 2.0),
  bundled as SVG and recolored at runtime. The mockups use Material Symbols.
- Don't use emoji as icons (the spec's code template uses 📁 🔄 🛡️). They render
  inconsistently across fonts and DPI.
- Icon sizes: 16 px in the toolbar and table, 20 px for empty-state glyphs.

## 5. Components

### 5.1 Buttons
| Variant | Rest | Hover | Pressed / checked |
|---|---|---|---|
| Default | `surface.high` fill, `line.default` border, `text.primary` | `#313233`, `line.strong` | `#1E1F1F` |
| Primary (`objectName=primaryBtn`) | `accent.fill`, border `#2893E6`, white 600 | `accent.fill-hover` | darker 8 % |
| Danger (`dangerBtn`) | `danger.fill` tokens | `#722424` | — |
| Toolbar tool | transparent, no border, `#CCCCCC` | `surface.high`, white | `surface.highest` fill, `accent` text |
| Toggle (checkable tool) | as tool | as tool | checked: `accent` text + 2 px bottom indicator (the "All levels" tab style) |

### 5.2 Inputs
- `QLineEdit`: `surface.container` fill, `line.default` border, radius 4, padding 0 8.
  Focus: 1 px `accent` border, no glow.
- Placeholder color: set through `QPalette.PlaceholderText`.
  `QLineEdit::placeholder` **isn't valid QSS** (that's an error in the spec).
- Search field: leading search icon (`QLineEdit.addAction`, LeadingPosition) and a trailing
  `Ctrl+F` keycap hint that hides while the field has text.

### 5.3 Checkbox & switch
- `QCheckBox` indicator 16 px, radius 3, checked = `accent.fill` with a white check (SVG).
- **Switch** (used in Privacy): Qt has no native switch. Build a small custom `ToggleSwitch(QAbstractButton)`,
  40×20, track `#3C3D3E` off / `accent.fill` on, knob animated with `QPropertyAnimation`.
  Support keyboard (Space) and focus ring.

### 5.4 Label chip
- Height 18, padding 0 6, radius 4, `micro` text (10/500). Colors from §1.5.
- In the table: drawn by a delegate. Overflow collapses to `+N`.
- In the chip editor: chip + `×` remove button. Backspace on an empty input removes the last chip.

### 5.5 Table (List mode)
- Header: `surface.container`, `caption` 11/600, `text.secondary`, bottom border `line.default`,
  no vertical dividers.
- Rows: `surface.base` / `surface.row-alt`, hover `#1C1D1D`, selected `selection.row` +
  **3 px `accent` bar on the left edge of the row**. The bar is drawn in the delegate of
  column 0, because QSS `::item:selected { border-left }` would draw it on every cell.
- Group (no-image) folders: name in `text.secondary` and a stacked-folder icon. Images = `—`.
- Empty numeric cell: `—` in `text.tertiary`.

### 5.6 Album card (Album Cards mode)
Layout from the album PNG:
```
┌───────────────────────────────────────────────────────────────┐
│ ★  Title                                    [SELECTED] [Set_003]│  header: surface.high
│ 📂 D:/…/Set_003 (200 photos)                         428 MB total│  path row: caption
├───────────────────────────────────────────────────────────────┤
│ ┌┐┌┐┌──────┐   Series     …                                    │
│ ││││ cover │   Type       …                                    │
│ ││││ 120×  │   Language   …                                    │
│ └┘└┘│ 160 │   Tags       [best] [travel] [landscape] [...]     │
│     └1/200┘                                                    │
│ 21:21 · 7 Nov 2026                     Last opened yesterday … │
└───────────────────────────────────────────────────────────────┘
```
- Cover stack: two back layers offset **left** by −6 px and −12 px (and up by 3/6 px),
  brightness 80 % and 60 %, **no rotation**. The spec mentions rotation of
  −2°/−4°, but neither the PNG nor the spec's own code rotates.
  The back layers use the 2nd and 3rd images when they exist, otherwise flat `surface.highest`.
- Cover: 1 px `rgba(255,255,255,0.12)` border, radius 4, page badge `1/200` bottom-right
  (`#000000B3` fill, `micro` text).
- Selected card: 1 px `accent` border + `selection.row` tint on the header.
- Paint the whole card in a `QStyledItemDelegate` with cached pixmaps. Don't put an
  `indexWidget` per row.

### 5.7 Inspector panel
- Background `surface.low`, left border `line.default`, padding 12.
- Preview: aspect-fit in a `#1A1A1A` box with a `#333333` 1 px border, radius 4. An empty folder
  shows a centered folder glyph + "No images".
- Header: name (`heading`) + star, image-count pill (accent outline).
- Meta line: size total • last scanned.
- `LABELS` section label (`micro`, uppercase) + chip editor + suggestions row.
- Actions: `Open` (primary), `Favorite/Unfavorite`, `Hide/Unhide`.
- `DIRECTORY PROPERTIES` key/value grid: absolute path (elided in the middle, full path in the
  tooltip, click to copy), format breakdown, subfolder count.

### 5.8 Popup (labels filter)
- 360 px wide, max 420 px tall, `surface.container`, 1 px `line.strong`, radius 6.
- Implement as a `QFrame` with `Qt.Popup` (closes on an outside click and on Esc).
- Row height 38: checkbox, color dot (8 px), label, right-aligned count keycap.

### 5.9 Dialog
- `QDialog` with the native title bar. Body `surface.low`, section labels `micro` uppercase.
- Footer: tertiary action left (e.g. Restore defaults), Cancel + primary right.
- The `QDialog · Qt 6` badge in the Privacy mockup title is a design annotation. **Don't ship it.**
- The Settings dialog (03 §S5) reuses the Privacy mockup's look: switch rows with a title and
  a caption line, and section labels. A left tab list sits on `surface.container`.

### 5.9a Color picker row
- Swatch row: 7 palette circles (20 px) + a `Custom…` circle with a `+` icon. The selected
  swatch gets a 2 px `text.primary` ring.
- `Custom…` opens `QColorDialog` (no alpha). It shows a live preview of the chip
  (fill / border / text) derived per §1.6.

### 5.10 Status bar
- `surface.lowest`, top border `line.subtle`, `caption` `text.secondary`.
- Left: `636 folders · 624 with images · 58,531 images · 2 favorites · 0 hidden | showing 636`.
- Right: state dot + `Ready` / `Scanning 312/636…` / `Error`, then the version.

## 6. QSS corrections to the spec template

| Spec line | Problem | Fix |
|---|---|---|
| `QWidget { outline: none; }` | Removes every focus indicator, so keyboard users can't see where they are | Remove it. Style `:focus` per widget instead |
| `QLineEdit::placeholder` | Not a QSS sub-control, so it's silently ignored | `QPalette.PlaceholderText` |
| `QTableView::item:selected { border-left: 3px … }` | Draws on every cell | Paint in the delegate (§5.5) |
| `font-family` on `QMainWindow` | Doesn't reach popups and dialogs reliably, and overrides the system font | Keep the system font. Derive styles from `QApplication.font()` |
| `open("foldervault_theme.qss")` | Relative to the CWD, and no encoding | Load from the package resources with `encoding="utf-8"` |
| `option.State_Selected` (PySide6) | Not valid in PySide6 | `QStyle.StateFlag.State_Selected` |
| "Mica / Acrylic" | QSS can't do Mica | Flat opaque surfaces. Real Mica needs the `DwmSetWindowAttribute` API and isn't in scope |
