# 06 — Pre-Implementation Design Review

Date: 2026-11-07 · Scope: every file in `design/stitch/stitch_foldervault_desktop_ui_redesign/`.
Method: read both spec documents in full, inspected all 5 PNGs and extracted the text of all
5 HTML mockups. Nothing was built or run. These are document findings, not test results.

> **Status 2026-11-07:** the owner has answered every blocking question. See the
> [decision log](#decision-log) at the end. The tables below are kept as the original review
> record. Where a decision overrides a "Proposed resolution", the decision log wins.

Severity: **Blocker** = must be decided before the affected phase starts · **High** = will cause
rework or user harm if ignored · **Medium** = inconsistency or gap that needs a decision ·
**Low** = cosmetic or cleanup.

---

## A. Design-system conflicts

| ID | Sev | Conflict | Sources | Proposed resolution |
|---|---|---|---|---|
| A-01 | High | Two different surface scales: canvas `#131313` vs `#202020`, panels `#1B1C1C` vs `#2C2C2C` | spec §1.1 + HTML Tailwind + DESIGN.md front-matter vs DESIGN.md prose | Use `#131313` (matches the mockups) → 02 §1.1 |
| A-02 | Medium | Selected row: `#1B354D` / `#1F384C` (spec QSS) vs `#1A4B75` (DESIGN.md) | spec §2 vs DESIGN.md | `#1A4B75` (matches the labels PNG) |
| A-03 | Medium | Favorite gold: `#FFC83B` vs `#FFD700` / `#FCE100` | spec vs DESIGN.md | `#FFC83B` |
| A-04 | High | Tag style: saturated solid fills vs tinted fill + rim | spec §1.1 vs DESIGN.md and PNGs | Tinted + rim (02 §1.5) |
| A-05 | Medium | Label→color mapping contradicts: `cosplay` is green (spec) vs cyan (DESIGN.md). `travel` is sky (spec) vs sage (DESIGN.md) | spec vs DESIGN.md | Hash-based + per-label override. Seed the defaults to match the PNGs |
| A-06 | Medium | Font: Segoe UI Variable (spec) vs Inter (DESIGN.md, mockups). Inter isn't installed on Windows | spec vs DESIGN.md | Segoe UI Variable. Bundle Inter only if exact mockup fidelity is required |
| A-07 | Low | Body size 13 px (spec) vs 12 px (DESIGN.md body-md). Control height 26 px vs typical 28 px | spec vs DESIGN.md | 13 px body, 28 px controls |
| A-08 | Low | Radius scale: DESIGN.md `DEFAULT 0.25rem` vs HTML Tailwind `DEFAULT 0.125rem`, `full 0.75rem` (not full) | DESIGN.md vs HTML | 4 / 6 / 8 px (02 §3) |
| A-09 | Low | Chips are 10 px pills (spec) vs 4 px rects (DESIGN.md, PNGs) | spec vs DESIGN.md | 4 px |
| A-10 | Medium | Stacked covers: spec text says rotate −2°/−4° and offset (−6,−3)/(−12,−6). The spec's own code offsets **right/down** with no rotation. The PNG shows a left offset with no rotation | spec text vs spec code vs PNG | Left offset, no rotation (02 §5.6) |
| A-11 | Medium | The Privacy button is red-filled (labels PNG), blue-filled (privacy PNG) and amber-outlined (album PNG) | PNGs | Neutral + status dot |
| A-12 | Low | Design annotations rendered as UI: `QDialog · Qt 6` badge, `Preview: 3-layer book stack`, `SELECTED` pill, `Layout: High Density` | PNGs | Don't ship the first two. `SELECTED` is redundant with the selection styling |
| A-13 | Low | "Mica / Acrylic" claimed in the spec header. QSS can't produce it | spec | Flat opaque. Mica is out of scope |

## B. Privacy & security feature risks

The Privacy dialog (spec §Screen 5, privacy PNG) is the **highest-risk part** of the design.
Several items are technically infeasible as written. Others change **system-wide** Windows state
irreversibly, which contradicts the dialog's own promise: "All changes are non-destructive and can
be restored at any time." Per org policy, security-sensitive and system-modifying work needs
human review before implementation.

| ID | Sev | Item | Problem | Recommendation |
|---|---|---|---|---|
| B-01 | Blocker | "Prevent folders from appearing in Explorer Quick Access" | Windows has no per-folder suppression. The only options are the global `ShowFrequent` / `ShowRecent` toggles (which affect every app) or removing entries after the fact | Don't implement it as described. At most, the app avoids *creating* entries (no `SHAddToRecentDocs`) and offers a link to Explorer's own setting |
| B-02 | Blocker | "Clear Jump List & Run History" | Deleting `AutomaticDestinations` / `RunMRU` wipes the history of **all** apps and can't be undone. That's destructive to user data outside the app | Remove it. The app's own Jump List can be left empty instead |
| B-03 | High | "Hide from Explorer search indexing (exclusion attribute)" | Means writing `FILE_ATTRIBUTE_NOT_CONTENT_INDEXED` onto the user's folders. That's a write into the library (it breaks the "read-only toward the library" principle) and needs per-file application and tracking to revert | Defer. If it's ever needed, record every change in the DB so it can be reverted, and get explicit opt-in per root |
| B-04 | Blocker | "Scrub thumbcache_*.db for hidden sets" | Entries can't be selectively removed. The files are locked by Explorer and shared by the whole system. Deleting them needs Explorer stopped and erases **all** thumbnails | Remove it |
| B-05 | High | "Restart Windows Explorer" | Kills `explorer.exe`, so the user loses open Explorer windows and the taskbar flickers | Remove it, or keep it only as a manual action with a confirmation dialog and no automation |
| B-06 | High | "Lock Vault after 15 min… biometric PIN or passphrase" | There's no auth design: where the secret is stored, what is locked, the recovery path, Windows Hello integration. Without encryption a "lock" is only a UI curtain: the files stay readable in Explorer | Defer to P2 with a security design. If built: a PIN hashed with a KDF (scrypt or argon2), stored in app data, an honest copy ("hides the app window, does not protect files") |
| B-07 | High | "Shield telemetry console" showing `Initializing … shell filter hook`, `Explorer telemetry suppressed`, `Active Hook` | No shell hook exists or should exist. These messages would be false claims of protection | Remove it. If a log is kept, it shows only actions the app really performed |
| B-08 | High | Naming: "FolderVault", "Vault", "Security Flag: Public Vault", "Privacy shield" | Implies encryption or protection the app doesn't provide | Keep the name if wanted, but the UI copy must state plainly that files aren't encrypted. Drop "Security Flag" |
| B-09 | Medium | "Auto-clear session history on exit" | Fine, as long as it's scoped to app data | Keep (03 §S5) |
| B-10 | Medium | "Stealth mode titlebar" | Fine. Note that the taskbar thumbnail and Alt+Tab preview still show the content | Keep, document the limitation. Optionally blank the window content when it's inactive |

## C. Functional gaps & ambiguities

| ID | Sev | Topic | Issue | Proposed resolution |
|---|---|---|---|---|
| C-01 | Blocker | Persistence | The spec never says where labels, favorites, hidden flags and views are stored | SQLite in `%LOCALAPPDATA%` (04 §3) |
| C-02 | High | Folder identity | Rename or move outside the app orphans labels and favorites | Path key + "missing" rows + re-link (04 §3). Accept the limitation for MVP |
| C-03 | High | Hide mechanism | Undefined. The main-window mockup lists `.vault_private_archive` (dot-prefixed), which hints at renaming folders | App-level DB flag only. Never rename or change file attributes |
| C-04 | High | Product identity | The repo is named `comic-reader`, while the design is a "photo manager" (EXIF camera and lens panel, "Photo Album" type). The reference `image.png_2` is a comic/CG gallery layout | Confirm the product focus. It drives C-05, C-06 and C-07 |
| C-05 | High | Album card metadata (Series, Type, Language, long titles) | There's no source: plain folders don't have these fields. The spec's "Language: English / Multi (Exif metadata intact)" isn't a real derivation | MVP: hide the empty rows. Later: read an optional sidecar (`ComicInfo.xml`, `info.json`, …) or add manual fields. **Decision needed** |
| C-06 | High | Comic-reading features | None are specified: RTL reading direction, double-page spread, continuous vertical scroll (webtoon), resume last page. Only "Fit width" hints at it | Resume = P1. The rest P2, pending C-04 |
| C-07 | Medium | Archives | Comics are often `.cbz`/`.zip`/`.rar`. The design is folders only | Out of MVP. Confirm |
| C-08 | Medium | Shortcut conflicts | Open root `Ctrl+O` (spec) vs `Alt+O` (mockup). Space = open viewer (spec) vs "rapid carousel preview" (mockup) vs Next (viewer). `I` = toggle HUD (spec) vs `I` info + `H` hide overlays (mockup) | Unified map in 03 §S6 |
| C-09 | Medium | `Open` button | "Open in Explorer" (spec) vs "Open" (PNG) | `Open` = viewer, Explorer through the menu or Ctrl+E |
| C-10 | Medium | Redundant label UI | Chip editor plus `Add label…` / `Remove label…` buttons | Buttons only for multi-selection bulk edits |
| C-11 | Medium | `(no label)` + `Match ALL` | AND with "no label" is always empty, and the semantics aren't stated | 03 §S3 |
| C-12 | Medium | "favorites" label vs ★ favorite | The labels PNG has a `favorites` label next to the ★ favorite flag, which confuses users | Reserve the word or warn when it's created. Seed data shouldn't include it |
| C-13 | Medium | Random | Behavior undefined (select? open the viewer? which pool?) | Pick from the visible filtered rows (image folders only), select it and open the viewer |
| C-14 | Medium | Views column | "Views / Activity telemetry" isn't defined | The number of times the folder was opened in the viewer |
| C-15 | Medium | Cover thumbnail in the list | The spec says the Folder column shows a cover thumbnail. Both the PNG and the HTML show an icon | An option, default off |
| C-16 | Medium | Missing screens and states | No PNG for the main window or the viewer. No first-run, scanning, error, no-results, or root-missing states. No settings screen besides Privacy | Defined in 03. Design them during implementation |
| C-17 | Medium | Auto-refresh | The labels PNG shows "Auto-refresh: On" with no spec | Root watcher + debounce + F5 (04 §4) |
| C-18 | Low | Locale | Vietnamese dates (`7 Thg 11, 2026`) inside an English UI | `QLocale` system format everywhere. UI strings through `tr()` |
| C-19 | Low | Custom title bar in the mockups | Frameless costs Snap Layouts and needs native hit-testing | Native title bar for MVP |
| C-20 | Low | Accessibility | The spec's QSS has `outline: none` on every widget. There are no focus states for delegates, and tertiary text is < 4.5:1 | 02 §6. Visible focus required |
| C-21 | Low | Multi-root | Breadcrumb "Photos" implies one root. Multiple roots aren't discussed | Single active root + a recent-roots list |
| C-22 | Low | Version number | The spec says v1.4.2, but the repo has no commits | Start at 0.1.0 |

## D. Spec code-template defects

The PySide6 sample in spec §4 is a layout sketch. **Don't use it as a base.**

| ID | Issue |
|---|---|
| D-01 | `option.State_Selected` raises `AttributeError` in PySide6. Use `QStyle.StateFlag.State_Selected` |
| D-02 | The `StackedCoverDelegate` is set on a `QTableView` with no model, so nothing renders. Fake text is hard-coded in `paint` (`"D:/Archive/Photos/Set_…"`, `"best ⚲"`) |
| D-03 | `sizeHint` is a fixed `QSize(800, 155)` that ignores the viewport width |
| D-04 | Emoji in toolbar actions and buttons. Inline `setStyleSheet` with hex colors bypasses the theme |
| D-05 | `QFont("Segoe UI", 11, QFont.Bold)` uses points while the QSS uses px, so sizes mismatch |
| D-06 | QSS problems listed in 02 §6 (`outline:none`, `::placeholder`, per-cell border) |

## E. Repository / source hygiene

| ID | Sev | Issue | Recommendation |
|---|---|---|---|
| E-01 | Medium | `image.png_2` (reference) contains third-party cover art and explicit adult-content tag names | Keep it out of a public repo (add it to `.gitignore` or store it outside the repo) |
| E-02 | Low | The HTML mockups load the Tailwind CDN and Google Fonts. Opening them needs internet | Reference only. Don't ship them |
| E-03 | Low | Folder names `image.png_1/`, `image.png_2/` aren't descriptive | Rename to `current_app_screenshot/` and `reference_album_layout/` (optional) |
| E-04 | Medium | Dev environment: `python` isn't on PATH. `py` resolves to 3.14.2 | Pin Python 3.12 in a venv (05 §1). Verify PySide6 support before using 3.14 |

---

## Decision log

Owner answers from 2026-11-07. The docs have been updated to match.

| # | Question | Decision | Effect on the docs |
|---|---|---|---|
| 1 | Product focus (C-04) | **Comic reader** (library manager). Reading is done in **Windows Photos** | The built-in viewer was removed. 03 §S4 "Open in Photos". C-06 closed (Photos' job) |
| 2 | Album card metadata source (C-05) | **Empty for now.** The owner will write a script, and the app supports script import | 03 §S6 JSON import/export + CLI. 04 `folder_meta` table. Empty rows are hidden |
| 3 | OS-level privacy items (B-01…B-07) | **All dropped**, including the app lock | 03 §S5: app-level privacy only, inside Settings |
| 4 | Hide mechanism (C-03) | The owner can hide folders in Explorer manually. Resolution: **app flag + honor the Windows Hidden attribute (read-only)** | 03 §S1 "Hidden folders". 04 `win_hidden` column |
| 5 | Archives (C-07) | **No** | 01 §5 |
| 6 | Consolidated tokens (A-01…A-13) | **Accepted.** Additionally: **colors are customizable in the app** (label colors and accent) | 02 §1.4, §1.5, §1.6, §5.9a. 03 §S5 Appearance / Labels |
| 7 | Font (A-06) | **Same as Windows Explorer** (system UI font, Segoe UI 9 pt) | 02 §2: no hard-coded family, sizes relative to the system font |
| — | Shortcuts (C-08) | **Follow Windows / Explorer habits** | 03 §S7 rewritten |
| — | Spec gaps (C-xx) | The author resolves them | Resolutions applied in 01, 03 and 04 |
| — | Spec sample code (D-xx) | **Ignore it.** Build from scratch with the same tech stack | 05 §2 |
| — | Dev environment (E-04) | The author sets it up | Done: `.venv` with Python 3.11.9 + PySide6 6.12.0 (05 §1) |
| — | `image.png_2` (E-01) | **Delete it** | Deleted |

## Remaining open points (non-blocking)

| ID | Sev | Item | When |
|---|---|---|---|
| R-01 | Medium | Verify that the `ms-photos:viewer?fileName=` URI opens with folder navigation on Win10 and Win11. The fallback is `os.startfile` | Phase 4 |
| R-02 | Low | Photos' folder order may differ from the app's natural sort in edge cases (Photos controls it) | Phase 4, document only |
| R-03 | Low | Opening files through Photos/the shell may add entries to Windows / Photos history. The app can't prevent this. It's disclosed in Settings › Privacy | Phase 7 |
| R-04 | Low | A rename/move outside the app orphans labels and metadata (C-02). "Re-link" is P1, or the owner's script re-imports | After MVP |
| R-05 | Low | Raise `requires-python` above 3.13 once PySide6 support for 3.14 is confirmed | Any time |

## Verified vs unverified

- **Verified (by reading):** every finding above cites content present in the source files.
- **Not verified:** no code was run. PySide6 support for Python 3.14, the plugin availability
  (WebP/TIFF) in the PySide6 wheels, and the performance targets in 01 §6 must be checked
  during Phase 1–2.
- **Platform facts (B-01…B-05):** based on documented Windows behavior. Re-check them if
  OS-level privacy is ever scheduled.
