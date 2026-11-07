# FolderVault — Documentation Index

FolderVault is a Windows desktop **comic library manager** (Python + PySide6 / Qt 6). It is used
to browse, filter and label large libraries of comic / CG image folders. Reading happens in
**Windows Photos**. The app has no built-in viewer.

Status (2026-11-07): owner decisions recorded ([06 decision log](06-design-review.md#decision-log)),
dev environment set up ([05 §1](05-implementation-guide.md#1-environment-set-up-2026-11-07)).
The next step is Phase 1.

Source material: the Google Stitch export in [`design/stitch/`](../design/stitch/stitch_foldervault_desktop_ui_redesign/)
(HTML mockups, PNG screenshots, a tech spec and a design-system file). These docs consolidate
that material, resolve its internal contradictions, and flag what is still undecided.

| Doc | Purpose |
|---|---|
| [01-product-overview.md](01-product-overview.md) | What the app does, scope, glossary, feature list (MVP vs later) |
| [02-design-system.md](02-design-system.md) | The single source of truth for colors, type, spacing, radii, components |
| [03-screens-and-interactions.md](03-screens-and-interactions.md) | Per-screen spec, states, and the unified keyboard map |
| [04-architecture.md](04-architecture.md) | Code structure, data model, storage, threading, caching |
| [05-implementation-guide.md](05-implementation-guide.md) | Environment (installed), conventions, phased plan, definition of done |
| [06-design-review.md](06-design-review.md) | Pre-implementation review: issues and risks, plus the **decision log** |

## Status legend used in all docs

- **Decided**: stated consistently by the source material, or confirmed by the owner.
- **Proposed**: a resolution written by the doc author to fix a contradiction or gap.
  It needs owner confirmation before it is treated as a requirement.
- **Open**: there's no basis for a decision yet. See [06-design-review.md](06-design-review.md).

## Source files map

| Source | Content | Has PNG? |
|---|---|---|
| `foldervault_main_window_windows_11_fluent/` | Main window, list (table) mode | No (HTML only) |
| `foldervault_album_preview_mode_stacked_covers/` | Album card mode with stacked covers | Yes |
| `foldervault_labels_filter_menu/` | Labels multi-select popup | Yes |
| `foldervault_fullscreen_photo_viewer/` | Fullscreen viewer: **not built** (replaced by Windows Photos) | No (HTML only) |
| `foldervault_privacy_settings_dialog/` | Privacy dialog. Only its **look** is reused, for the Settings dialog | Yes |
| `image.png_1/` | Screenshot of the **current** (pre-redesign) app | Yes |

`image.png_2/` (external album-layout reference) was deleted on 2026-11-07 at the owner's request.
| `foldervault_complete_technical_design_specification_claude_code_pyside6.md` | Tech spec v1.4.2 (tokens, QSS, screens, code template) | n/a |
| `fluent_slate_desktop/DESIGN.md` | Design system "Fluent Slate Desktop" | n/a |

The HTML mockups use the Tailwind CDN and Google Fonts. They are **visual references only**.
Don't port their markup.
