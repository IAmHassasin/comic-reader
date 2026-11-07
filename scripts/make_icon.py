"""Generate the application icon (.ico + .png) from the project's own folder glyph.

Usage: python scripts/make_icon.py <output_dir>
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

from foldervault.ui.theme import icons

BACKGROUND = "#0078D4"
GLYPH = "#FFFFFF"


def render(size: int) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(BACKGROUND))
    radius = size * 0.22
    p.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)
    renderer = QSvgRenderer(QByteArray(icons.svg("folder", GLYPH)))
    margin = size * 0.16
    renderer.render(p, QRectF(margin, margin, size - 2 * margin, size - 2 * margin))
    p.end()
    return img


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "build")
    out.mkdir(parents=True, exist_ok=True)
    QGuiApplication(sys.argv[:1])
    big = render(256)
    if not big.save(str(out / "app.ico"), "ICO"):
        print("error: could not write app.ico", file=sys.stderr)
        return 1
    big.save(str(out / "app.png"), "PNG")
    print(f"icon written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
