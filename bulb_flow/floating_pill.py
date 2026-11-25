"""Always-on-top floating dictation pill docked at bottom-center (Wispr Flow status bar style)."""

from __future__ import annotations

import math
from collections import deque

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

from .constants import (
    PILL_ACTIVE_HEIGHT,
    PILL_ACTIVE_WIDTH,
    PILL_DOCK_MARGIN_BOTTOM,
    PILL_REST_HEIGHT,
    PILL_REST_WIDTH,
)


class FloatingDictationPill(QWidget):
    """Subtle bottom-docked resting bar that expands into a live waveform pill while dictating."""

    clicked_toggle = Signal()

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._state = "resting"  # resting | listening | processing | done | error
        self._status_text = ""
        self._levels: deque[float] = deque([0.12] * 14, maxlen=14)
        self._phase = 0.0
        self._hovered = False

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(33)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.start()

        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(self.set_resting)

        self.set_resting()

    def _position_bottom_center(self, w: int, h: int) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - w) // 2
        y = geo.y() + geo.height() - h - PILL_DOCK_MARGIN_BOTTOM
        self.setGeometry(x, y, w, h)

    def set_resting(self) -> None:
        self._state = "resting"
        self._status_text = ""
        self._position_bottom_center(PILL_REST_WIDTH + 16, PILL_REST_HEIGHT + 12)
        self.update()

    def set_listening(self, mode_label: str = "Listening...") -> None:
        self._reset_timer.stop()
        self._state = "listening"
        self._status_text = mode_label
        self._position_bottom_center(PILL_ACTIVE_WIDTH, PILL_ACTIVE_HEIGHT)
        self.update()

    def set_processing(self, label: str = "Polishing...") -> None:
        self._reset_timer.stop()
        self._state = "processing"
        self._status_text = label
        self._position_bottom_center(PILL_ACTIVE_WIDTH, PILL_ACTIVE_HEIGHT)
        self.update()

    def set_done(self, preview: str) -> None:
        self._state = "done"
        trimmed = preview.strip().replace("\n", " ")
        self._status_text = (trimmed[:34] + "...") if len(trimmed) > 34 else (trimmed or "Pasted!")
        self._position_bottom_center(320, PILL_ACTIVE_HEIGHT)
        self.update()
        self._reset_timer.start(2200)

    def set_error(self, message: str) -> None:
        self._state = "error"
        self._status_text = message[:40]
        self._position_bottom_center(320, PILL_ACTIVE_HEIGHT)
        self.update()
        self._reset_timer.start(3000)

    def push_audio_level(self, level: float) -> None:
        self._levels.append(max(0.08, min(1.0, level)))

    def _tick(self) -> None:
        if self._state in ("listening", "processing"):
            self._phase += 0.22
            self.update()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked_toggle.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()

        if self._state == "resting":
            bar_w = PILL_REST_WIDTH + (12 if self._hovered else 0)
            bar_h = PILL_REST_HEIGHT + (2 if self._hovered else 0)
            rx = (w - bar_w) / 2.0
            ry = (h - bar_h) / 2.0
            p.setPen(QPen(QColor(255, 255, 255, 45), 1.0))
            p.setBrush(QColor(26, 26, 25, 195 if self._hovered else 140))
            p.drawRoundedRect(QRectF(rx, ry, bar_w, bar_h), bar_h / 2.0, bar_h / 2.0)
            p.end()
            return

        # Active obsidian pill (#1F1F1F)
        p.setPen(QPen(QColor("#3A3936"), 1.2))
        p.setBrush(QColor("#1F1F1F"))
        p.drawRoundedRect(QRectF(1.5, 1.5, w - 3.0, h - 3.0), (h - 3.0) / 2.0, (h - 3.0) / 2.0)

        # Left indicator dot
        dot_color = {
            "listening": QColor("#FFA946"),
            "processing": QColor("#C29BE1"),
            "done": QColor("#68BDB0"),
            "error": QColor("#F87171"),
        }.get(self._state, QColor("#FFA946"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(dot_color)
        p.drawEllipse(QRectF(16, (h - 10) / 2.0, 10, 10))

        if self._state == "listening":
            # Animated 14-bar audio waveform
            start_x = 36.0
            bar_spacing = 5.5
            max_bar_h = 22.0
            levels = list(self._levels)
            for i, lvl in enumerate(levels):
                wave = 0.22 * abs(math.sin(self._phase + i * 0.55))
                bh = max(4.0, min(max_bar_h, (lvl + wave) * max_bar_h))
                bx = start_x + i * bar_spacing
                by = (h - bh) / 2.0
                p.setBrush(QColor("#FFFFEB"))
                p.drawRoundedRect(QRectF(bx, by, 3.0, bh), 1.5, 1.5)

            p.setPen(QColor("#D6D3CB"))
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            p.drawText(QRectF(122, 0, w - 134, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, self._status_text)

        elif self._state == "processing":
            # Pulsing dots
            for i in range(3):
                pulse = 0.5 + 0.5 * math.sin(self._phase * 1.6 - i * 0.9)
                r = 2.6 + pulse * 1.6
                p.setBrush(QColor(239, 229, 252, int(130 + 125 * pulse)))
                p.drawEllipse(QPoint(44 + i * 11, h // 2), int(r), int(r))
            p.setPen(QColor("#FCFCFB"))
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            p.drawText(QRectF(80, 0, w - 94, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._status_text)

        else:
            p.setPen(QColor("#FCFCFB"))
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
            p.drawText(QRectF(36, 0, w - 50, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._status_text)

        p.end()
