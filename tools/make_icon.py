"""Generuje assets/icon.ico dla YouTrak.

Wymaga PySide6 (używane tylko do wygenerowania grafiki, nie jest zależnością
runtime aplikacji). Uruchom dowolnym interpreterem z zainstalowanym PySide6:

    pip install PySide6
    python tools/make_icon.py
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets"
OUT_ICO = OUT_DIR / "icon.ico"
OUT_PNG = OUT_DIR / "icon.png"

TOP_COLOR = "#2DD4BF"
BOTTOM_COLOR = "#0F3D3A"
SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]


def render(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    radius = size * 0.22
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), radius, radius)

    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor(TOP_COLOR))
    gradient.setColorAt(1.0, QColor(BOTTOM_COLOR))
    painter.fillPath(path, gradient)

    font = QFont("Segoe UI", weight=QFont.Weight.Black)
    font.setPixelSize(int(size * 0.64))
    painter.setFont(font)
    painter.setPen(QColor("#FFFFFF"))
    text_rect = QRectF(0, size * 0.03, size, size * 0.97)
    painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "Y")

    painter.end()
    return pixmap


def pixmap_to_png_bytes(pixmap: QPixmap) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, "PNG")
    return bytes(buffer.data())


def write_ico(sizes: list[int], path: Path) -> None:
    images = [(s, pixmap_to_png_bytes(render(s))) for s in sizes]

    header = struct.pack("<HHH", 0, 1, len(images))
    entries = b""
    data = b""
    offset = 6 + 16 * len(images)

    for size, png_bytes in images:
        dim = size if size < 256 else 0
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png_bytes), offset)
        data += png_bytes
        offset += len(png_bytes)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + entries + data)


def main() -> None:
    app = QApplication(sys.argv)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    write_ico(SIZES, OUT_ICO)
    render(512).save(str(OUT_PNG), "PNG")

    print(f"Zapisano: {OUT_ICO}")
    print(f"Zapisano: {OUT_PNG}")


if __name__ == "__main__":
    main()
