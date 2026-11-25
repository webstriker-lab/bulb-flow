"""Crisp custom QPainter vector icons for Bulb Flow (original artwork, dark/light aware)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def _make_icon(size: int, color: str, draw_fn) -> QIcon:
    dpr = 2
    px = QPixmap(size * dpr, size * dpr)
    px.setDevicePixelRatio(dpr)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    c = QColor(color)
    pen = QPen(c, 1.65, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    draw_fn(p, size, c)
    p.end()
    return QIcon(px)


def icon_brand(size: int = 24, color: str = "#1C1917") -> QIcon:
    """Original Bulb Flow mark: glowing bulb silhouette with soundwave filament bars."""
    def draw(p: QPainter, s: int, c: QColor) -> None:
        # 5 crisp vertical waveform bars forming a subtle bulb contour
        bars = [
            (0.18, 0.38, 0.62),
            (0.34, 0.22, 0.72),
            (0.50, 0.14, 0.78),
            (0.66, 0.22, 0.72),
            (0.82, 0.38, 0.62),
        ]
        pen = QPen(c, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        for x, y1, y2 in bars:
            p.drawLine(QPointF(s * x, s * y1), QPointF(s * x, s * y2))
        # Warm amber bulb base dot/accent
        p.setPen(QPen(QColor("#F59E0B"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(s * 0.38, s * 0.88), QPointF(s * 0.62, s * 0.88))

    return _make_icon(size, color, draw)


def icon_sidebar(size: int = 18, color: str = "#262320") -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        p.drawRoundedRect(QRectF(2.5, 3.0, s - 5.0, s - 6.0), 2.5, 2.5)
        p.drawLine(QPointF(s * 0.38, 3.0), QPointF(s * 0.38, s - 3.0))

    return _make_icon(size, color, draw)


def icon_user(size: int = 18, color: str = "#262320") -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        p.drawEllipse(QRectF(2.2, 2.2, s - 4.4, s - 4.4))
        p.drawEllipse(QRectF(s * 0.35, s * 0.27, s * 0.30, s * 0.30))
        path = QPainterPath()
        path.moveTo(s * 0.27, s * 0.79)
        path.quadTo(s * 0.50, s * 0.58, s * 0.73, s * 0.79)
        p.drawPath(path)

    return _make_icon(size, color, draw)


def icon_home(size: int = 18, color: str = "#262320") -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        g = 2.5
        w = (s - 6.0 - g) / 2.0
        for row in range(2):
            for col in range(2):
                p.drawRoundedRect(QRectF(3.0 + col * (w + g), 3.0 + row * (w + g), w, w), 1.6, 1.6)

    return _make_icon(size, color, draw)


def icon_record(size: int = 18, color: str = "#262320") -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        p.drawEllipse(QRectF(2.5, 2.5, s - 5.0, s - 5.0))
        p.setBrush(c)
        p.drawEllipse(QRectF(s * 0.36, s * 0.36, s * 0.28, s * 0.28))

    return _make_icon(size, color, draw)


def icon_stats(size: int = 18, color: str = "#262320") -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        p.drawLine(QPointF(3.0, s - 3.0), QPointF(s - 3.0, s - 3.0))
        p.drawRoundedRect(QRectF(4.0, s * 0.48, 3.0, s - 3.0 - s * 0.48), 1.0, 1.0)
        p.drawRoundedRect(QRectF(8.5, s * 0.22, 3.0, s - 3.0 - s * 0.22), 1.0, 1.0)
        p.drawRoundedRect(QRectF(13.0, s * 0.36, 3.0, s - 3.0 - s * 0.36), 1.0, 1.0)

    return _make_icon(size, color, draw)


def icon_dictionary(size: int = 18, color: str = "#262320") -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        p.drawRoundedRect(QRectF(3.5, 2.5, s - 7.0, s - 5.0), 2.0, 2.0)
        p.drawLine(QPointF(6.5, 6.8), QPointF(s - 6.5, 6.8))
        p.drawLine(QPointF(6.5, 10.2), QPointF(s - 6.5, 10.2))
        p.drawLine(QPointF(6.5, 13.5), QPointF(s - 8.5, 13.5))

    return _make_icon(size, color, draw)


def icon_snippets(size: int = 18, color: str = "#262320") -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        p.drawEllipse(QRectF(2.8, 3.2, 4.4, 4.4))
        p.drawEllipse(QRectF(2.8, s - 7.6, 4.4, 4.4))
        p.drawLine(QPointF(6.8, 6.2), QPointF(s - 3.0, s - 4.0))
        p.drawLine(QPointF(6.8, s - 6.2), QPointF(s - 3.0, 4.0))

    return _make_icon(size, color, draw)


def icon_style(size: int = 18, color: str = "#262320") -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        # Big T
        p.drawLine(QPointF(2.8, 4.2), QPointF(10.8, 4.2))
        p.drawLine(QPointF(6.8, 4.2), QPointF(6.8, 14.5))
        # Small t
        p.drawLine(QPointF(11.0, 8.8), QPointF(15.6, 8.8))
        p.drawLine(QPointF(13.3, 6.8), QPointF(13.3, 14.5))

    return _make_icon(size, color, draw)


def icon_transforms(size: int = 18, color: str = "#262320") -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        # Magic wand diagonal + sparkle
        p.drawLine(QPointF(3.5, s - 3.5), QPointF(s - 4.5, 4.5))
        p.drawLine(QPointF(4.5, 5.0), QPointF(4.5, 8.0))
        p.drawLine(QPointF(3.0, 6.5), QPointF(6.0, 6.5))
        p.drawLine(QPointF(12.5, 11.5), QPointF(12.5, 14.5))
        p.drawLine(QPointF(11.0, 13.0), QPointF(14.0, 13.0))

    return _make_icon(size, color, draw)


def icon_notes(size: int = 18, color: str = "#262320") -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        p.drawRoundedRect(QRectF(3.0, 3.0, s - 6.0, s - 6.0), 2.2, 2.2)
        p.drawLine(QPointF(6.0, 7.2), QPointF(s - 6.0, 7.2))
        p.drawLine(QPointF(6.0, 10.8), QPointF(s - 7.5, 10.8))

    return _make_icon(size, color, draw)


def icon_providers(size: int = 18, color: str = "#262320") -> QIcon:
    """CPU / AI Models icon."""
    def draw(p: QPainter, s: int, c: QColor) -> None:
        p.drawRoundedRect(QRectF(5.0, 5.0, s - 10.0, s - 10.0), 2.0, 2.0)
        for pos in (7.0, 11.0):
            p.drawLine(QPointF(pos, 2.5), QPointF(pos, 5.0))
            p.drawLine(QPointF(pos, s - 5.0), QPointF(pos, s - 2.5))
            p.drawLine(QPointF(2.5, pos), QPointF(5.0, pos))
            p.drawLine(QPointF(s - 5.0, pos), QPointF(s - 2.5, pos))

    return _make_icon(size, color, draw)


def icon_key(size: int = 18, color: str = "#262320") -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        p.drawEllipse(QRectF(2.8, 5.5, 6.2, 6.2))
        p.drawLine(QPointF(9.0, 8.6), QPointF(s - 2.5, 8.6))
        p.drawLine(QPointF(s - 5.2, 8.6), QPointF(s - 5.2, 11.4))
        p.drawLine(QPointF(s - 2.8, 8.6), QPointF(s - 2.8, 11.0))

    return _make_icon(size, color, draw)


def icon_settings(size: int = 18, color: str = "#262320", dot_color: str | None = None) -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        p.drawEllipse(QRectF(6.2, 6.2, s - 12.4, s - 12.4))
        p.drawEllipse(QRectF(3.4, 3.4, s - 6.8, s - 6.8))
        if dot_color:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(dot_color))
            p.drawEllipse(QRectF(s - 5.5, 1.5, 4.5, 4.5))

    return _make_icon(size, color, draw)


def icon_help(size: int = 18, color: str = "#262320") -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        p.drawEllipse(QRectF(2.5, 2.5, s - 5.0, s - 5.0))
        path = QPainterPath()
        path.moveTo(6.8, 7.2)
        path.cubicTo(6.8, 5.0, 11.2, 5.0, 11.2, 7.4)
        path.cubicTo(11.2, 9.0, 9.0, 9.2, 9.0, 10.8)
        p.drawPath(path)
        p.setBrush(c)
        p.drawEllipse(QRectF(8.3, 12.6, 1.4, 1.4))

    return _make_icon(size, color, draw)


def icon_moon(size: int = 17, color: str = "#262320") -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        path = QPainterPath()
        path.moveTo(11.8, 3.2)
        path.cubicTo(6.2, 3.8, 4.0, 9.8, 7.6, 13.4)
        path.cubicTo(10.4, 16.0, 14.2, 14.4, 15.0, 12.2)
        path.cubicTo(11.4, 12.8, 9.0, 8.8, 11.8, 3.2)
        p.drawPath(path)

    return _make_icon(size, color, draw)


def icon_sun(size: int = 17, color: str = "#F5F4F0") -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        p.drawEllipse(QRectF(5.5, 5.5, s - 11.0, s - 11.0))
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0), (-0.7, -0.7), (0.7, 0.7), (-0.7, 0.7), (0.7, -0.7)):
            cx, cy = s / 2.0, s / 2.0
            p.drawLine(QPointF(cx + dx * 5.2, cy + dy * 5.2), QPointF(cx + dx * 6.8, cy + dy * 6.8))

    return _make_icon(size, color, draw)


def icon_bell(size: int = 17, color: str = "#262320") -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        path = QPainterPath()
        path.moveTo(4.2, 12.8)
        path.lineTo(12.8, 12.8)
        path.lineTo(11.8, 11.0)
        path.lineTo(11.8, 7.5)
        path.cubicTo(11.8, 4.2, 5.2, 4.2, 5.2, 7.5)
        path.lineTo(5.2, 11.0)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(7.4, 14.5), QPointF(9.6, 14.5))

    return _make_icon(size, color, draw)


def icon_search(size: int = 17, color: str = "#8C8982") -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        p.drawEllipse(QRectF(3.0, 3.0, 8.8, 8.8))
        p.drawLine(QPointF(10.6, 10.6), QPointF(14.5, 14.5))

    return _make_icon(size, color, draw)


def icon_mic(size: int = 18, color: str = "#1C1917") -> QIcon:
    def draw(p: QPainter, s: int, c: QColor) -> None:
        p.drawRoundedRect(QRectF(6.5, 2.5, 5.0, 8.5), 2.5, 2.5)
        path = QPainterPath()
        path.moveTo(4.2, 9.0)
        path.cubicTo(4.2, 14.0, 13.8, 14.0, 13.8, 9.0)
        p.drawPath(path)
        p.drawLine(QPointF(9.0, 13.2), QPointF(9.0, 15.8))
        p.drawLine(QPointF(6.5, 15.8), QPointF(11.5, 15.8))

    return _make_icon(size, color, draw)
