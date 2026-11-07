---
name: Fluent Slate Desktop
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#393939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1b1c1c'
  surface-container: '#202020'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353535'
  on-surface: '#e5e2e1'
  on-surface-variant: '#bdc8cf'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#303030'
  outline: '#889299'
  outline-variant: '#3e484e'
  surface-tint: '#74d1ff'
  primary: '#b4e4ff'
  on-primary: '#003548'
  primary-container: '#60cdff'
  on-primary-container: '#005572'
  inverse-primary: '#006687'
  secondary: '#fff9ef'
  on-secondary: '#3a3000'
  secondary-container: '#ffdb3c'
  on-secondary-container: '#725f00'
  tertiary: '#bae3ff'
  on-tertiary: '#00344b'
  tertiary-container: '#72cbff'
  on-tertiary-container: '#005577'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#c1e8ff'
  primary-fixed-dim: '#74d1ff'
  on-primary-fixed: '#001e2b'
  on-primary-fixed-variant: '#004d67'
  secondary-fixed: '#ffe16d'
  secondary-fixed-dim: '#e9c400'
  on-secondary-fixed: '#221b00'
  on-secondary-fixed-variant: '#544600'
  tertiary-fixed: '#c6e7ff'
  tertiary-fixed-dim: '#81cfff'
  on-tertiary-fixed: '#001e2d'
  on-tertiary-fixed-variant: '#004c6b'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353535'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 26px
  headline-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 22px
  headline-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
  body-lg:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
  body-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  body-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 14px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
  label-xs:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: '600'
    lineHeight: 12px
    letterSpacing: 0.4px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 0.5rem
  margin: 0.5rem
  space-xs: 0.125rem
  space-sm: 0.25rem
  space-md: 0.5rem
  space-lg: 0.75rem
  space-xl: 1rem
---

## Brand & Style

This design system defines a desktop-first, high-density utility experience built around Windows 11 Fluent Design principles and tailored for modern Qt / PySide6 architectures. It targets power users, digital archivists, and media organizers managing tens of thousands of directories, media files, and taxonomy structures.

The core visual signature balances dark slate neutral layers (`#202020` canvas with `#2C2C2C` containers) against crisp micro-borders and vibrant precision accents. The mood is disciplined, fast, and silent—prioritizing spatial compression, instant visual scannability, clear hierarchical tables, and keyboard ergonomics over gratuitous empty space.

Key aesthetic pillars:
- **Fluent Subtlety**: Flat-opaque fallbacks compatible with native QSS stylesheets alongside semi-translucent hover coats that simulate acrylic surfaces.
- **Precision Utility**: Tight tabular line heights, micro-inline tag chips, and persistent keyboard accelerators (`(Ctrl+F)`, `Enter to save`).
- **High-Scannability Contrast**: High-contrast foregrounds (`#FFFFFF` text primary, `#9E9E9E` meta-secondary) with unmistakable state highlights: Fluent Blue (`#60CDFF` / `#0078D4`) for focus/selection and Warm Gold (`#FFD700`) for priority stars.

## Colors

The color palette is engineered around dark-mode ergonomics to eliminate eye fatigue during high-volume cataloging while meeting strict WCAG AA contrast thresholds against low-luminance slate backgrounds.

### Core Canvas & Surface Hierarchy
- **Canvas Base (`#202020`)**: Deep slate window background used for root application canvases and split-pane gutters.
- **Surface Elevation 1 (`#262626`)**: Alternate table striping and docked utility bars.
- **Surface Elevation 2 (`#2C2C2C`)**: Primary pane surfaces, side detail inspectors, card backgrounds, and button rests.
- **Surface Elevation 3 (`#323232`)**: Interactive control hover fills and active popovers.
- **Borders & Separators (`#383838`)**: Crisp structural dividers, table row outlines, and input bounding strokes.
- **Subtle Stroke (`#444444`)**: Hover state outlines and splitter handles.

### Accents & Semantic Roles
- **Primary Fluent Accent (`#60CDFF` on dark, `#0078D4` for high-fill highlights)**: System-level active states, focused row highlights, primary buttons, and selected tabs.
- **Selected Row Fill (`#1A4B75`)**: Deep translucent blue wash applied across full tabular row selections with crisp `#60CDFF` high-contrast indicator bars.
- **Favorite / Warm Gold (`#FFD700` / `#FCE100`)**: Favorited folder stars and star-toggle actions. Star glyphs unselected render as muted `#555555`.
- **System Destructive / Warning (`#E05D5D` / `#FFB900`)**: Privacy mode banners, removal actions, and destructive confirmations.

### Tag Badge Palette (Muted Badges with Clear Contrast)
Badges use low-saturation, dark background fills (15–20% opacity) combined with matching 1px solid rims and high-readability text:
- **Ochre / Amber ("best", "featured")**: Background `#382A18`, Border `#94682E`, Text `#FFD285`.
- **Sage / Emerald ("travel", "outdoor")**: Background `#1B3224`, Border `#3E7756`, Text `#82E0AA`.
- **Cyan / Teal ("cosplay", "work")**: Background `#162E3B`, Border `#2B6B8B`, Text `#7CE3FF`.
- **Amethyst / Violet ("personal", "archive")**: Background `#2C1E38`, Border `#6D458C`, Text `#DDB8FF`.

## Typography

Typography prioritizes extreme glyph clarity at low sizes (10px–13px) to maximize on-screen file metrics and dense hierarchy trees. On Windows desktop environments, fall back seamlessly to `Segoe UI Variable Text`, `Segoe UI`, or native system sans-serif fonts.

Rules for typography application:
- **Numerical Alignment**: Subfolder counts, file tallies, and numerical metadata must use tabular lining (`tnum` / fixed column metrics) to ensure neat right-aligned data grids.
- **Header Rows**: Table headers render at `11px`, Medium (500 weight), uppercase-neutral (`#9E9E9E`), preventing headers from competing with primary directory strings.
- **Item Primary Labels**: Folder titles and file names render at `12px` or `13px`, Regular (400) or Medium (500), crisp white (`#FFFFFF`) against slate backgrounds.
- **Keyboard Accelerators & Shortcuts**: In-place keys (such as `Ctrl+F` or `Enter to save`) render at `label-xs` or `body-sm` using secondary slate tinting (`#808080`) to provide instant user guidance without cluttering actionable UI.

## Elevation & Depth

Visual hierarchy does not use deep blurred drop shadows, which look foreign and perform poorly in desktop frameworks like Qt. Instead, depth is achieved purely through **tonal stacking** and **crisp micro-outlines**:

1. **Base Layer (0dp)**: Window background `#202020`.
2. **Elevated Panels (1dp)**: Main file list canvas and right inspector panel `#262626` / `#2C2C2C`, bounded by `#383838` borders.
3. **Hover & Active Highlights**: Surfaces achieve interactive prominence via inner luminescence:
   - Button resting: `#2C2C2C` with `#383838` perimeter outline.
   - Button hover: `#383838` with `#484848` outline.
   - Selected table row: Solid fill `#1A4B75` with a vertical 3px accent bar `#60CDFF` pinned to the left edge of the column.
4. **Floating Overlays & Context Menus**: Popups, context menus, and tooltips take surface `#2C2C2C` with a 1px solid border of `#4D4D4D` and a sharp, ultra-tight shadow (`0px 4px 12px rgba(0, 0, 0, 0.45)`).

## Shapes

In alignment with Windows 11 Fluent specifications, the shape system employs subtle, restrained rounding across all interactive elements:
- **Buttons and Inputs**: 4px radius (`0.25rem`). Gives an intentional modern contour without sacrificing pixel density.
- **Chips & Badges**: 4px radius for compact rectangular tags, or fully curved 10px pill shapes strictly when visually isolating micro-labels within data tables.
- **Panels & Splitter Panes**: 0px radius (sharp) where edges dock to the outer application window shell, maintaining seamless desktop window anchoring.
- **Image Preview Cards**: 4px radius with an inner 1px border (`rgba(255, 255, 255, 0.08)`) to preserve clean separation from dark container fills.

## Components

### Buttons & Action Bars
- **Default Buttons**: Background `#2C2C2C`, border 1px solid `#383838`, text `#FFFFFF`, border-radius 4px, height 26px, padding 0 10px. Hover background `#363636`, active `#242424`.
- **Primary / Accent Buttons**: Background `#0078D4`, border 1px solid `#60CDFF`, text `#FFFFFF`, font-weight 600. Hover background `#1084D9`.
- **Toolbar Icon Buttons**: Height 24px, width 24px, transparent background, border: none. Hover background `#383838`, radius 4px.

### Inputs & Global Search Bar
- **Search Field**: Background `#1E1E1E`, border 1px solid `#383838`, radius 4px, height 26px, padding 0 8px, text `#FFFFFF`, placeholder `#737373`.
- **Focus State**: 1px solid `#60CDFF` with no fuzzy glow ring; crisp and high-contrast.
- **Embedded Shortcut Indicator**: Right-aligned uneditable text indicator (`Ctrl+F`) styled in `#737373` at 10px.

### Tabular Data Grid (`QTableView`)
- **Header Cells**: Height 24px, background `#202020`, bottom border 1px solid `#383838`, text color `#9E9E9E`, text-align left, font-size 11px, weight 500.
- **Grid Lines**: Horizontal line 1px solid `#2B2B2B`; no vertical dividers between content columns.
- **Row States**:
  - Rest: Alternating `#202020` and `#242424`.
  - Hover: `#2C2C2C`.
  - Selected: `#1A4B75`, text `#FFFFFF`, with 3px solid `#60CDFF` marker on the star column.
- **Favorite Column**: Star icons rendered centered; inactive star `#404040`, active star `#FFD700`.

### Tag Chips & Badges
- **Dimensions**: Height 18px, padding 0 6px, border-radius 4px, font-size 10px, font-weight 500.
- **Display**: Inline-flex with 4px gap, cleanly vertically centered in table cells and detail panels.
- **Color Themes**: Soft tinted fill with 1px border match (e.g., Gold tag: `#382A18` fill, `#94682E` border, `#FFD285` text; Sage tag: `#1B3224` fill, `#3E7756` border, `#82E0AA` text).

### Inspector Sidebar & Image Previews
- **Detail Pane**: Fixed background `#262626`, left border 1px solid `#383838`, padding 12px.
- **Preview Canvas**: Aspect-ratio preserving viewport, background `#1A1A1A`, border 1px solid `#333333`, rounded 4px. Empty preview shows center-aligned muted directory placeholder with count caption.
- **Property Field Rows**: Label at top (`#8A8A8A`, 11px), followed by editable inline multi-tag field or text control.