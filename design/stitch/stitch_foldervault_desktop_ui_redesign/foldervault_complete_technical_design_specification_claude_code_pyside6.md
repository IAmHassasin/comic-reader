# FolderVault — Comprehensive Technical Design & Implementation Specification
> **For Claude Code / PySide6 / Qt6 Architecture**
> Version: 1.4.2 | Design Language: Windows 11 Fluent Dark (Mica / Dark Slate)

---

## 1. Executive Summary & Design System Tokens

### 1.1 Palette & Surface Architecture (Dark Mode)
FolderVault follows the Windows 11 Fluent Design System, engineered specifically for Qt / PySide6 Desktop integration.

| Token | Hex Code | Usage in Qt / QSS |
|---|---|---|
| `surface-lowest` | `#0E0E0E` | Status bar, bottom docking, deep containers |
| `surface` / `window` | `#131313` | Main window background (`QMainWindow`, canvas canvas background) |
| `surface-low` | `#1B1C1C` | Side panel background, list alternate rows, card container background |
| `surface-container` | `#202121` | Toolbars, search input container, popup backgrounds |
| `surface-high` | `#2A2B2B` | Hover states, card surfaces, modal sub-panels |
| `surface-highest` | `#353636` | Pressed states, active borders, pill chip backgrounds |
| `outline` | `#3C3D3E` | Normal border lines, separator dividers (1px solid) |
| `outline-focus` | `#60CDFF` | Primary Accent Blue (Windows 11 Fluent Accent), selection rings |
| `text-primary` | `#F3F3F3` | Primary labels, headers, selected items |
| `text-secondary` | `#9E9E9E` | Subtitles, paths, timestamps, metadata keys |
| `text-tertiary` | `#6E6E6E` | Disabled text, subtle hints, bracket shortcuts |
| `accent-gold` | `#FFC83B` | Favorite Star (`★`), highlight markers |
| `accent-badge-cosplay` | `#388E3C` | Green tag pills (cosplay, convention) |
| `accent-badge-best` | `#D97706` | Amber tag pills (best, picks) |
| `accent-badge-travel` | `#0284C7` | Cyan/Sky tag pills (travel, outdoor) |
| `accent-badge-purple` | `#7C3AED` | Purple tag pills (landscape, art) |
| `accent-badge-rose` | `#E11D48` | Rose tag pills (favorites, portrait) |

### 1.2 Typography & Iconography Metrics
- **Font Family**: `Segoe UI Variable Text`, `Segoe UI`, `Inter`, system default sans-serif.
- **Font Sizes**:
  - Window Title & Top Breadcrumbs: `12px` / `13px` Regular
  - Header / Album Titles: `15px` SemiBold (`font-weight: 600`)
  - Body & Table Cells: `13px` Regular
  - Captions / Metadata / Badges: `11px` Regular
  - Micro Status & Shortcut Hints: `10px` Medium (`font-weight: 500`)
- **Corner Radii (`border-radius`)**:
  - Buttons & Inputs: `4px`
  - Dialog Cards & Stacked Covers: `6px`
  - Tag Chips (Pills): `10px` or `4px` (subtle rounded rect)
  - Windows & Dialogs: `8px`

---

## 2. Complete Qt Style Sheet (QSS / PySide6)

Save as `foldervault_theme.qss` and apply with `app.setStyleSheet(open("foldervault_theme.qss").read())`:

```css
/* ==========================================================================
   FolderVault — Windows 11 Fluent Dark Theme (PySide6 / PyQt6)
   ========================================================================== */

QMainWindow, QDialog {
    background-color: #131313;
    color: #F3F3F3;
    font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
    font-size: 13px;
}

QWidget {
    color: #F3F3F3;
    outline: none;
}

/* ToolBar & Header Dock */
QToolBar {
    background-color: #1B1C1C;
    border-bottom: 1px solid #2D2E2E;
    spacing: 6px;
    padding: 3px 8px;
}

QToolBar QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px 8px;
    color: #CCCCCC;
    font-size: 12px;
}

QToolBar QToolButton:hover {
    background-color: #2A2B2B;
    color: #FFFFFF;
}

QToolBar QToolButton:pressed, QToolBar QToolButton:checked {
    background-color: #353636;
    color: #60CDFF;
    border: 1px solid #454646;
}

/* Search Bar & Text Inputs */
QLineEdit {
    background-color: #202121;
    border: 1px solid #3C3D3E;
    border-radius: 4px;
    padding: 4px 10px;
    color: #F3F3F3;
    selection-background-color: #0078D4;
}

QLineEdit:focus {
    border: 1px solid #60CDFF;
    background-color: #1E1F1F;
}

QLineEdit::placeholder {
    color: #7A7A7A;
}

/* Table View & List View */
QTableView, QListView {
    background-color: #131313;
    alternate-background-color: #161717;
    border: none;
    gridline-color: #202121;
    color: #E0E0E0;
    selection-background-color: #1F384C;
    selection-color: #FFFFFF;
}

QTableView::item {
    padding: 6px;
    border-bottom: 1px solid #1A1B1B;
}

QTableView::item:selected {
    background-color: #1B354D;
    border-left: 3px solid #60CDFF;
}

QTableView::item:hover:!selected {
    background-color: #1C1D1D;
}

QHeaderView::section {
    background-color: #181919;
    color: #8C8C8C;
    padding: 4px 8px;
    border: none;
    border-right: 1px solid #232424;
    border-bottom: 1px solid #2D2E2E;
    font-size: 11px;
    font-weight: 600;
}

/* ScrollBars */
QScrollBar:vertical {
    background: #131313;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #3A3B3C;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #5A5B5C;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Buttons */
QPushButton {
    background-color: #262727;
    border: 1px solid #38393A;
    border-radius: 4px;
    padding: 5px 14px;
    color: #F3F3F3;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #313233;
    border-color: #4C4D4E;
}

QPushButton:pressed {
    background-color: #1E1F1F;
}

QPushButton#primaryBtn {
    background-color: #0078D4;
    border: 1px solid #2893E6;
    color: #FFFFFF;
    font-weight: 600;
}

QPushButton#primaryBtn:hover {
    background-color: #1084D9;
}

QPushButton#dangerBtn {
    background-color: #5A1E1E;
    border: 1px solid #822828;
    color: #FFB3B3;
}

QPushButton#dangerBtn:hover {
    background-color: #722424;
}

/* Status Bar */
QStatusBar {
    background-color: #0E0E0E;
    color: #7E7E7E;
    border-top: 1px solid #202121;
    font-size: 11px;
}

/* CheckBox & Toggle */
QCheckBox {
    spacing: 8px;
    color: #E0E0E0;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #4C4D4E;
    background-color: #202121;
}

QCheckBox::indicator:checked {
    background-color: #0078D4;
    border-color: #60CDFF;
}

/* Right Inspector Panel */
QFrame#inspectorPanel {
    background-color: #161717;
    border-left: 1px solid #242525;
}
```

---

## 3. Core Screens & Architectural Breakdown

### Screen 1: Main Window & Table View (`FolderVault - Main Window`)
- **Key Purpose**: High-density management of 600+ folders containing 58,000+ photos.
- **Components**:
  - `QToolBar`: Open Root (`Ctrl+O`), Refresh (`F5`), Breadcrumb `Photos > all levels`, Search QLineEdit (`Ctrl+F`), View modes (`List` vs `Album Cards`), Quick filters (`★ Favorites`, `Image folders only`, `Show hidden`), `Labels: all ▾`, `Random`, `Privacy` (red badge).
  - `QTableView` (or custom `QTreeView` with flat layout):
    - Col 0: `★` (Folder Favorite toggle flag).
    - Col 1: `Folder & Cover` (Shows folder icon for category nodes, or scaled thumbnail of 1st A–Z image).
    - Col 2: `Images` (Direct count of images).
    - Col 3: `Subfolders` (Count of child folders).
    - Col 4: `Labels` (Colored badge pills: `best`, `travel`, `cosplay`).
    - Col 5: `Views` / Activity telemetry.
  - `InspectorPanel` (Right Sidebar):
    - Live large preview image of the selected folder's cover photo.
    - Title, image count, last scanned metadata.
    - Quick Label Input: Comma-separated tokenized chip editor.
    - Action Buttons: `Open in Explorer`, `★ Favorite / Unfavorite (Folder Level)`, `Hide Folder`.
    - Directory Properties: Absolute path, MIME format distribution, subfolder index stats.

---

### Screen 2: Album Preview Mode (Stacked 3D Covers) (`SCREEN_2`)
- **Visual Reference**: High-fidelity layered book/magazine cover card.
- **Delegate Logic (`QStyledItemDelegate` or custom `QWidget` inside `QListView`)**:
  - **Cover Stack Visual**:
    - Back layer 2: Offset `(-12px, -6px)`, rotated `-4deg`, dimmed brightness (60%).
    - Back layer 1: Offset `(-6px, -3px)`, rotated `-2deg`, dimmed brightness (80%).
    - Main cover: Scaled to `140px × 190px` (or `120px × 160px`), sharp border `1px solid rgba(255,255,255,0.12)`, radius `4px`, shadow `0 8px 16px rgba(0,0,0,0.6)`.
    - Counter badge on cover corner: `1 / 200` (Index of cover / Total images in set).
  - **Metadata Card Section**:
    - Top: Folder name + `★` toggle icon + Series Tag (`Set_003`).
    - Path display: `D:/Archive/Photos/Set_003 (200 photos) — 428 MB total`.
    - Two-column spec table:
      - `Series`: Travel & Scenic Landscapes
      - `Type`: Photo Album (200 photos) · **Favorite**
      - `Language`: English / Multi (Exif metadata intact)
      - `Tags`: `[best ⚲]`, `[travel ⚲]`, `[landscape ⚲]`, `[mountain ⚲]`, `[sunset ⚲]`, `[...]`
    - Footer row: Scan timestamp (`21:21 7 Thg 11, 2026`) and Last opened status.

---

### Screen 3: Labels Multi-Select Filter Menu (`SCREEN_4`)
- **Popup Architecture**: Anchored beneath `Labels: all ▾` button.
- **Internal Widgets**:
  1. `QLineEdit`: Quick instant filter for label names (`Search labels...`).
  2. Logic controls:
     - `Match ALL` checkbox (Switch between boolean `AND` vs `OR` filtering).
     - `(no label)` checkbox (Filters for untagged folders to assist categorization).
     - `Clear` button.
  3. Scrollable List of Labels:
     - Checkbox + Colored category dot indicator (`●`).
     - Label string (e.g. `best`, `travel`, `cosplay`, `archived`, `work`).
     - Right-aligned counter badge (`84`, `42`, `118`, etc.).
  4. Footer shortcut guide: `[Space] to toggle` · `[Esc] to close`.

---

### Screen 4: Distraction-Free Fullscreen Photo Viewer (`SCREEN_7`)
- **Interaction Model**: Opens on double-click or pressing `Enter`/`Space` on a photo.
- **Canvas Features**:
  - Full black canvas (`#080808` or `#000000`).
  - Smooth pan, drag, and zoom (`Ctrl + Wheel` or `+`/`-`).
- **HUD Overlays (Toggleable via `I` key)**:
  - **Top Navigation Bar**:
    - `[Esc] Back` button.
    - Breadcrumbs: `Photos / Set 003` · Current position: `3 / 200`.
    - Folder Tags: `[best]`, `[travel]`.
    - Zoom Presets: `Fit window [F]`, `Fit width [W]` (essential for tall webtoons/art), `100% [1]`.
    - Right-side Action: **★ Folder Favorited** (Folder level only, strictly keeping folder context).
  - **Floating EXIF Info Panel (Right)**:
    - Dimensions: `6000 × 4000` (24 MP).
    - File Size: `18.4 MB`.
    - Camera Model: `Sony A7R V` · Lens: `35mm f/1.4 GM`.
    - Settings: `1/250s, ISO 100`.
    - Absolute file location.
  - **Bottom Filmstrip Carousel**:
    - Horizontal thumbnails of nearby files (`1, 2, 3 [Active], 4, 5...`).
    - Quick rotate controls: `↺ 90°`, `↻ 90°`.
    - Shortcut guide in bottom status: `← / →: Prev/Next`, `Space: Next`, `F: Fit Window`, `W: Fit Width`, `I: Toggle Info`, `Esc: Exit`.

---

### Screen 5: Privacy & Explorer Protection Dialog (`SCREEN_6`)
- **Modal QDialog Architecture**: Non-destructive Windows Explorer integration shield.
- **Header Notice**:
  - Shield Icon + Assurance: *"Non-destructive local protection. All changes can be restored at any time. Keeps sensitive photo folders discreet and hidden from Windows Explorer telemetry, Jump Lists, and Quick Access."*
- **7 Core Privacy Toggles (`QCheckBox` or custom sliding Switch)**:
  1. `Prevent folders from appearing in Explorer Quick Access`: Disables automatic recent folder pin additions and Frequent Folders feed.
  2. `Clear Windows Explorer Jump List & Run History`: Cleans recent traces of vault paths from taskbar right-click popups.
  3. `Hide .vault_private_archive & tagged folders from Explorer search indexing`: Applies Windows Search exclusion attribute directly to cataloged subdirectories.
  4. `Auto-clear session history on app exit`: Removes temporary caches, filter queries, and MRU records immediately upon closing FolderVault.
  5. `Scrub thumbnail cache for hidden sets (thumbcache_*.db)`: Requests system cache invalidation so cached thumbnail art is erased.
  6. `Enable stealth mode titlebar`: Renames window header to a generic utility name when minimized or inactive.
  7. `Lock Vault after 15 minutes of inactivity`: Requires quick biometric PIN or passphrase re-verification after idle timeout.
- **Immediate Action Buttons**:
  - `Clear History Now` (MRU & Search Traces)
  - `Unpin All from Quick Access` (Releases Explorer pins)
  - `Restart Windows Explorer` (Forces `explorer.exe` shell refresh safely)
- **Shield Telemetry Console**:
  - Terminal-styled mini log displaying real-time hook status, active suppression counts, and indexing verification logs.

---

## 4. PySide6 Implementation Code Template

You can copy and run this boilerplate directly in Python 3.10+ / PySide6 to test the layout and delegates:

```python
import sys
from PySide6.QtCore import Qt, QSize, QRect
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QToolBar,
    QLineEdit,
    QPushButton,
    QLabel,
    QTableView,
    QHeaderView,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QFrame,
    QDialog,
)


class StackedCoverDelegate(QStyledItemDelegate):
    """Custom delegate for 3D Layered Album Cover effect"""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        rect = option.rect
        # Draw background selection
        if option.state & option.State_Selected:
            painter.fillRect(rect, QColor("#1B354D"))
            painter.setPen(QColor("#60CDFF"))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
        else:
            painter.fillRect(rect, QColor("#161717") if index.row() % 2 == 0 else QColor("#131313"))

        cover_w, cover_h = 100, 130
        x = rect.x() + 20
        y = rect.y() + 10

        # 1. Back Layer 2 (dimmed, rotated simulation)
        painter.setBrush(QColor("#222324"))
        painter.setPen(QColor("#333435"))
        painter.drawRoundedRect(QRect(x + 12, y + 2, cover_w, cover_h), 4, 4)

        # 2. Back Layer 1
        painter.setBrush(QColor("#2B2C2D"))
        painter.drawRoundedRect(QRect(x + 6, y + 4, cover_w, cover_h), 4, 4)

        # 3. Main Cover Front
        painter.setBrush(QColor("#1E293B"))
        painter.setPen(QColor("#475569"))
        painter.drawRoundedRect(QRect(x, y + 6, cover_w, cover_h), 4, 4)

        # Draw text & tags
        text_x = x + cover_w + 30
        painter.setPen(QColor("#F3F3F3"))
        font = QFont("Segoe UI", 11, QFont.Bold)
        painter.setFont(font)

        title = index.data(Qt.DisplayRole) or f"Set {index.row() + 1:03d} — Archive Collection"
        painter.drawText(text_x, y + 25, title)

        painter.setPen(QColor("#8C8C8C"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(
            text_x, y + 48, f"D:/Archive/Photos/Set_{index.row() + 1:03d} (200 photos) · 428 MB"
        )

        # Sample Label Pills
        painter.setBrush(QColor("#D97706"))  # amber badge
        painter.setPen(Qt.NoPen)
        tag_rect = QRect(text_x, y + 65, 54, 20)
        painter.drawRoundedRect(tag_rect, 10, 10)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(tag_rect, Qt.AlignCenter, "best ⚲")

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(800, 155)


class FolderVaultMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FolderVault — Fluent Photo Manager")
        self.resize(1380, 860)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left Content Area
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Toolbar
        toolbar = QToolBar()
        left_layout.addWidget(toolbar)
        toolbar.addAction("📁 Open root (Alt+O)")
        toolbar.addAction("🔄")
        toolbar.addSeparator()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search name or label... (Ctrl+F)")
        self.search_box.setFixedWidth(280)
        toolbar.addWidget(self.search_box)

        toolbar.addAction("★ Favorites")
        toolbar.addAction("Labels: all ▾")
        toolbar.addAction("🛡️ Privacy")

        # Table / List View
        self.table = QTableView()
        self.table.setItemDelegate(StackedCoverDelegate(self.table))
        left_layout.addWidget(self.table)

        main_layout.addWidget(left_widget, 7)

        # Right Inspector Panel
        inspector = QFrame()
        inspector.setObjectName("inspectorPanel")
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.setContentsMargins(16, 16, 16, 16)

        title_lbl = QLabel("Set 003 ★")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFF;")
        inspector_layout.addWidget(title_lbl)

        meta_lbl = QLabel("200 images · 428 MB total\nLast scanned: Yesterday 18:42")
        meta_lbl.setStyleSheet("color: #8C8C8C; font-size: 11px;")
        inspector_layout.addWidget(meta_lbl)

        inspector_layout.addSpacing(16)
        btn_open = QPushButton("📂 Open in Explorer")
        btn_open.setObjectName("primaryBtn")
        btn_fav = QPushButton("★ Unfavorite Folder")
        btn_hide = QPushButton("👁️ Hide Folder")

        inspector_layout.addWidget(btn_open)
        inspector_layout.addWidget(btn_fav)
        inspector_layout.addWidget(btn_hide)
        inspector_layout.addStretch()

        main_layout.addWidget(inspector, 3)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FolderVaultMainWindow()
    window.show()
    sys.exit(app.exec())
```
