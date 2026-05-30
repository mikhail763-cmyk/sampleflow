from __future__ import annotations

import math

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import (
    QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap,
)


def make_icon(size: int = 256) -> QIcon:
    """Generate the SampleFlow vinyl+waveform icon via QPainter."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    cx = cy = size // 2
    margin = max(2, size // 64)

    # vinyl disc
    p.setBrush(QBrush(QColor("#1A1A1A")))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)

    # grooves — concentric rings
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor("#252525"), max(1, size // 128)))
    r_inner = int(size * 0.22)
    r_outer = int(size * 0.46)
    n_grooves = 10
    for i in range(n_grooves):
        r = r_inner + (r_outer - r_inner) * i // max(1, n_grooves - 1)
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

    # sine waveform across the disc
    pts = 80
    amp = int(size * 0.065)
    x0 = int(size * 0.10)
    x1 = int(size * 0.90)
    path = QPainterPath()
    for i in range(pts):
        t = i / (pts - 1)
        x = x0 + t * (x1 - x0)
        y = cy + amp * math.sin(t * math.pi * 5)
        if i == 0:
            path.moveTo(QPointF(x, y))
        else:
            path.lineTo(QPointF(x, y))
    wave_pen = QPen(
        QColor("#00ADB5"),
        max(2, size // 52),
        Qt.PenStyle.SolidLine,
        Qt.PenCapStyle.RoundCap,
        Qt.PenJoinStyle.RoundJoin,
    )
    p.setPen(wave_pen)
    p.drawPath(path)

    # center label circle (covers middle of waveform)
    label_r = int(size * 0.19)
    p.setBrush(QBrush(QColor("#00ADB5")))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(cx - label_r, cy - label_r, label_r * 2, label_r * 2)

    # center hole
    hole_r = max(2, int(size * 0.034))
    p.setBrush(QBrush(QColor("#1A1A1A")))
    p.drawEllipse(cx - hole_r, cy - hole_r, hole_r * 2, hole_r * 2)

    p.end()

    icon = QIcon()
    for s in (16, 32, 48, 64, 128, 256):
        icon.addPixmap(
            pix.scaled(
                s, s,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
    return icon
