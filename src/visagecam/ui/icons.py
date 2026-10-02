# Copyright (c) 2026 Skain. Todos los derechos reservados.

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

_CACHE: dict[tuple[str, str, int], QIcon] = {}


def _path_for(name: str) -> tuple[QPainterPath, bool]:
    p = QPainterPath()
    fill = False
    if name == "camera":
        p.addRoundedRect(QRectF(3, 7, 18, 12), 3, 3)
        p.addEllipse(QPointF(12, 13), 3.6, 3.6)
        p.moveTo(8, 7)
        p.lineTo(9.5, 4.5)
        p.lineTo(14.5, 4.5)
        p.lineTo(16, 7)
    elif name == "mask":
        p.moveTo(3.5, 6)
        p.cubicTo(3.5, 4.5, 6, 4, 12, 4)
        p.cubicTo(18, 4, 20.5, 4.5, 20.5, 6)
        p.cubicTo(20.5, 14, 17, 20, 12, 20)
        p.cubicTo(7, 20, 3.5, 14, 3.5, 6)
        p.addEllipse(QPointF(8.6, 10), 1.9, 1.3)
        p.addEllipse(QPointF(15.4, 10), 1.9, 1.3)
        p.moveTo(9, 15.2)
        p.quadTo(12, 17.2, 15, 15.2)
    elif name == "hat":
        p.moveTo(12, 3.5)
        p.lineTo(5.5, 19.5)
        p.lineTo(18.5, 19.5)
        p.closeSubpath()
        p.moveTo(8.6, 13)
        p.lineTo(15.4, 13)
        p.addEllipse(QPointF(12, 3.2), 1.3, 1.3)
    elif name == "sparkle":
        p.moveTo(12, 3)
        p.quadTo(12.6, 10.4, 20, 11)
        p.quadTo(12.6, 11.6, 12, 19)
        p.quadTo(11.4, 11.6, 4, 11)
        p.quadTo(11.4, 10.4, 12, 3)
        p.moveTo(19, 16)
        p.lineTo(19, 21)
        p.moveTo(16.5, 18.5)
        p.lineTo(21.5, 18.5)
    elif name == "image":
        p.addRoundedRect(QRectF(3.5, 4.5, 17, 15), 3, 3)
        p.addEllipse(QPointF(9, 10), 1.8, 1.8)
        p.moveTo(4, 17.5)
        p.lineTo(9.5, 13)
        p.lineTo(13, 16)
        p.lineTo(16, 13.5)
        p.lineTo(20, 17)
    elif name == "plug":
        p.moveTo(9, 3)
        p.lineTo(9, 8)
        p.moveTo(15, 3)
        p.lineTo(15, 8)
        p.addRoundedRect(QRectF(6, 8, 12, 6), 2, 2)
        p.moveTo(12, 14)
        p.lineTo(12, 17)
        p.quadTo(12, 20, 9, 20)
    elif name == "sliders":
        for y, x in ((7, 9), (12, 15), (17, 8)):
            p.moveTo(4, y)
            p.lineTo(20, y)
            p.addEllipse(QPointF(x, y), 2.2, 2.2)
    elif name == "plus":
        p.moveTo(12, 5)
        p.lineTo(12, 19)
        p.moveTo(5, 12)
        p.lineTo(19, 12)
    elif name == "trash":
        p.moveTo(4.5, 7)
        p.lineTo(19.5, 7)
        p.moveTo(9, 7)
        p.lineTo(9, 4.5)
        p.lineTo(15, 4.5)
        p.lineTo(15, 7)
        p.moveTo(6.5, 7)
        p.lineTo(7.5, 19.5)
        p.lineTo(16.5, 19.5)
        p.lineTo(17.5, 7)
    elif name == "upload":
        p.moveTo(12, 16)
        p.lineTo(12, 5)
        p.moveTo(7.5, 9)
        p.lineTo(12, 4.5)
        p.lineTo(16.5, 9)
        p.moveTo(4.5, 15)
        p.lineTo(4.5, 19.5)
        p.lineTo(19.5, 19.5)
        p.lineTo(19.5, 15)
    elif name == "eye":
        p.moveTo(2.5, 12)
        p.quadTo(12, 3, 21.5, 12)
        p.quadTo(12, 21, 2.5, 12)
        p.addEllipse(QPointF(12, 12), 3, 3)
    elif name == "mouth":
        p.moveTo(3.5, 12)
        p.quadTo(12, 6.5, 20.5, 12)
        p.quadTo(12, 19.5, 3.5, 12)
        p.moveTo(3.5, 12)
        p.lineTo(20.5, 12)
    elif name == "ears":
        p.addEllipse(QPointF(12, 12), 8.5, 8.5)
        p.moveTo(3.5, 12)
        p.lineTo(3.5, 15)
        p.moveTo(20.5, 12)
        p.lineTo(20.5, 15)
        p.addRoundedRect(QRectF(1.5, 11, 3.5, 6), 1.5, 1.5)
        p.addRoundedRect(QRectF(19, 11, 3.5, 6), 1.5, 1.5)
    elif name == "free":
        for a in range(4):
            ang = a * math.pi / 2
            p.moveTo(12 + 2 * math.cos(ang), 12 + 2 * math.sin(ang))
            p.lineTo(12 + 8 * math.cos(ang), 12 + 8 * math.sin(ang))
        p.addEllipse(QPointF(12, 12), 1.6, 1.6)
    elif name == "check":
        p.moveTo(5, 12.5)
        p.lineTo(10, 17.5)
        p.lineTo(19, 7)
    elif name == "face":
        p.addEllipse(QPointF(12, 12), 8.5, 8.5)
        p.addEllipse(QPointF(9, 10.5), 0.9, 0.9)
        p.addEllipse(QPointF(15, 10.5), 0.9, 0.9)
        p.moveTo(8.5, 15)
        p.quadTo(12, 18, 15.5, 15)
    elif name == "refresh":
        p.arcMoveTo(QRectF(5, 5, 14, 14), 40)
        p.arcTo(QRectF(5, 5, 14, 14), 40, 280)
        p.moveTo(17.5, 3.5)
        p.lineTo(18.5, 8)
        p.lineTo(14, 8.5)
    elif name == "paste":
        p.addRoundedRect(QRectF(5, 5, 14, 16), 2, 2)
        p.addRoundedRect(QRectF(9, 3, 6, 4), 1.5, 1.5)
    elif name == "link":
        p.addRoundedRect(QRectF(3, 9, 10, 6), 3, 3)
        p.addRoundedRect(QRectF(11, 9, 10, 6), 3, 3)
    elif name == "play":
        p.moveTo(8, 5.5)
        p.lineTo(19, 12)
        p.lineTo(8, 18.5)
        p.closeSubpath()
        fill = True
    return p, fill


def icon(name: str, color: str = "#eceff6", size: int = 24) -> QIcon:
    key = (name, color, size)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    scale = 3
    pixmap = QPixmap(size * scale, size * scale)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.scale(size * scale / 24.0, size * scale / 24.0)
    path, fill = _path_for(name)
    pen = QPen(QColor(color), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(QColor(color) if fill else Qt.NoBrush)
    painter.drawPath(path)
    painter.end()
    pixmap.setDevicePixelRatio(1.0)
    result = QIcon(pixmap.scaled(size * 2, size * 2, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    _CACHE[key] = result
    return result
