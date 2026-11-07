# 01 — Product Overview

## 1. Purpose

FolderVault is a **comic library manager** for Windows. It helps one user browse, filter and
tag a large local library of comic / CG folders. Each folder is one "set" (a chapter, a volume,
a CG set). The target scale is **~636 folders / ~58,500 images** under one root, and the app
must stay responsive at that size.

FolderVault **doesn't include its own reader**. Reading is delegated to **Windows Photos**
(Decided 2026-11-07). The owner already reads this way, and Photos supports ←/→ navigation
through the images in a folder.

Core loop: **pick a root → browse/filter folders → inspect one → open it in Photos → tag it.**

## 2. Target user

- A power user on Windows 10/11 with a mouse and keyboard and a dark theme.
- Expects Windows Explorer conventions (shortcuts, font, list behavior).
- Some of the content is private.

## 3. Glossary

| Term | Meaning |
|---|---|
| Root | The top-level directory the user opens (`Open root`). |
| Folder / Set | Any directory under the root. An **image folder** directly contains ≥1 image. A **group folder** only has subfolders (shown with `—` images and a subfolder count). |
| All levels | A flat view of every descendant folder of the current location, not just its direct children. |
| Cover | The image that represents a folder: the first image in natural A→Z order (`2.jpg` < `10.jpg`, same as Explorer). |
| Label | A free-text tag that the user attaches to a folder. Labels belong to **folders**, not images. Each label has a color the user can change. |
| Favorite (★) | A boolean flag on a **folder**. |
| Hidden | A folder that's hidden **in the app** (app flag), **or** has the Windows *Hidden* attribute set in Explorer. Both are excluded unless `Show hidden` is on. |
| Metadata | Optional fields per folder (title, series, type, language, extra key/values) that an **external script** fills through the import file. The app never guesses them. |
| Views | How many times the folder was opened in Photos from the app. |
| Inspector | The right-side detail panel for the selected folder. |

## 4. Feature list

Priority: **P0** = MVP, **P1** = next, **P2** = later. Status is Decided unless marked **(P)**.

### Library & browsing
| # | Feature | Priority |
|---|---|---|
| L1 | Open root folder, remember last root + recent roots | P0 |
| L2 | Background scan: image count, subfolder count, cover, total size, Windows hidden attribute | P0 |
| L3 | List mode (table, like Explorer's Details view) | P0 |
| L4 | Album Cards mode (stacked covers + metadata card) | P1 |
| L5 | Navigation: Up, breadcrumb, `All levels` toggle | P0 |
| L6 | Refresh (F5) and auto-refresh (root watcher) | P0 / P1 |
| L7 | Sort by any column, natural sort | P0 |
| L8 | Random: pick a random image folder from the visible rows, select it and open it in Photos **(P)** | P1 |
| L9 | Status bar totals | P0 |

### Search & filter
| # | Feature | Priority |
|---|---|---|
| F1 | Search by folder name, label or metadata title/series (Ctrl+F / Ctrl+E / F3), debounced | P0 |
| F2 | Quick filters: Favorites, Image folders only, Show hidden | P0 |
| F3 | Labels popup: multi-select, Match ALL / ANY, `(no label)`, Clear, counts | P0 |

### Organization
| # | Feature | Priority |
|---|---|---|
| O1 | Toggle folder favorite | P0 |
| O2 | Edit labels with a chip editor (Enter to save), suggestions | P0 |
| O3 | Hide / unhide in the app (DB flag). Respect folders hidden in Explorer (read-only) | P0 |
| O4 | **Custom label colors**: palette swatches or any color through a color picker | P0 |
| O5 | **Custom accent color** (default Fluent blue, or "use Windows accent color") | P1 |
| O6 | Bulk label / favorite / hide on a multi-row selection | P1 |

### Reading (through Windows Photos)
| # | Feature | Priority |
|---|---|---|
| R1 | `Open` → open the folder's cover (first image) in Windows Photos | P0 |
| R2 | Count views and store `last opened` on every open | P0 |
| R3 | Setting: open with **Windows Photos** (default) or the **default image app** | P1 |
| R4 | Open a specific image from the inspector preview (click) | P1 |

Not available because the app has no reader: resume the last page, RTL / double-page / webtoon
modes, and in-app EXIF. These are Photos' responsibility.

### Metadata (script-fed)
| # | Feature | Priority |
|---|---|---|
| M1 | Store per-folder metadata (title, series, type, language, extra) | P1 |
| M2 | Import metadata from a JSON file (menu + CLI) written by an external script | P1 |
| M3 | Export the folder list (paths + current metadata) as JSON, so a script knows what to fill | P1 |

### Privacy (app-level only)
| # | Feature | Priority |
|---|---|---|
| P1 | Clear the app's history (recent roots, search history, thumbnail cache), now or on exit | P0 |
| P2 | Stealth window title | P1 |
| P3 | Don't write thumbnails of hidden folders to the disk cache | P1 |

OS-level privacy items from the mockup (Quick Access, Jump Lists, search index, thumbcache,
restart Explorer, telemetry console) are **dropped**. The app lock is **dropped**.

## 5. Out of scope (Decided)

- A built-in reader / viewer (see §1).
- Archive formats (CBZ/ZIP/RAR/7z). Folders only.
- Editing, renaming, moving, or changing the attributes of anything inside the library.
- Encryption, app lock, OS-level privacy changes.
- Cloud sync, multi-user, light theme.

## 6. Non-functional requirements (P)

| Area | Target |
|---|---|
| Startup with a cached library of 636 folders | UI interactive in < 1.5 s |
| Full cold scan of 58k images on SSD | < 30 s, UI never blocks, progress shown |
| Search / filter response | < 100 ms after a 150 ms debounce |
| Scrolling the list or album cards | Smooth, no synchronous disk I/O on the UI thread |
| `Open` → Photos window appears | Limited by Photos itself. The app returns immediately (async launch) |
| Memory | Bounded thumbnail cache (LRU) |
| Platform | Windows 10 22H2+ / Windows 11, 100–200 % display scaling |
