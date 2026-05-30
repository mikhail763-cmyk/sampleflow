"""Convert assets/icon.svg -> assets/icon.ico (multi-size Windows icon).

Uses PyQt6's built-in QSvgRenderer (no Cairo needed) + Pillow for ICO muxing.

Usage:
    python tools/make_icon.py
"""
from __future__ import annotations

import io
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SVG_PATH = os.path.join(ROOT, "assets", "icon.svg")
ICO_PATH = os.path.join(ROOT, "assets", "icon.ico")

SIZES = [16, 32, 48, 64, 128, 256]


def render_svg_frames() -> list:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtSvg import QSvgRenderer
    from PyQt6.QtGui import QImage, QPainter
    from PyQt6.QtCore import Qt, QRectF, QBuffer, QIODevice
    from PIL import Image

    app = QApplication.instance() or QApplication(sys.argv)

    renderer = QSvgRenderer(SVG_PATH)
    if not renderer.isValid():
        print(f"ERROR: cannot parse SVG: {SVG_PATH}")
        sys.exit(1)

    frames: list[Image.Image] = []
    for size in SIZES:
        img = QImage(size, size, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()

        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "PNG")
        pil = Image.open(io.BytesIO(bytes(buf.data()))).convert("RGBA")
        frames.append(pil)
        print(f"  rendered {size}x{size}")

    return frames


def save_ico(frames: list) -> None:
    from PIL import Image

    biggest: Image.Image = frames[-1]
    biggest.save(
        ICO_PATH,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=frames[:-1],
    )
    print(f"Saved: {ICO_PATH}")


if __name__ == "__main__":
    frames = render_svg_frames()
    save_ico(frames)
