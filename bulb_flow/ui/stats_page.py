"""Voice Insights & Analytics page with custom QPainter 7-day activity chart."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from ..database import Database
from .home_page import format_word_count


class WeeklyBarChart(QWidget):
    """Minimalist 7-day dictation bar chart drawn with QPainter."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self._data: list[tuple[str, int]] = []

    def set_data(self, data: list[tuple[str, int]]) -> None:
        self._data = data
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        if not self._data:
            p.end()
            return

        max_val = max([v for _, v in self._data] + [10])
        n = len(self._data)
        slot_w = (w - 32) / max(1, n)
        bar_w = min(44.0, slot_w * 0.52)
        chart_bottom = h - 30.0
        chart_top = 24.0
        usable_h = max(20.0, chart_bottom - chart_top)

        for idx, (day, val) in enumerate(self._data):
            cx = 16.0 + idx * slot_w + slot_w / 2.0
            bh = max(6.0, (val / max_val) * usable_h) if val > 0 else 6.0
            bx = cx - bar_w / 2.0
            by = chart_bottom - bh

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#FFA946") if val > 0 else QColor("#E4E0D6"))
            p.drawRoundedRect(QRectF(bx, by, bar_w, bh), 6, 6)

            p.setPen(QColor("#8C8982"))
            p.setFont(QFont("Segoe UI", 9))
            p.drawText(QRectF(cx - 24, chart_bottom + 6, 48, 20), Qt.AlignmentFlag.AlignCenter, day)

            if val > 0:
                p.setPen(QColor("#57534E"))
                p.setFont(QFont("Segoe UI", 8.5, QFont.Weight.DemiBold))
                p.drawText(QRectF(cx - 28, by - 18, 56, 16), Qt.AlignmentFlag.AlignCenter, str(val))

        p.end()


class StatsPage(QWidget):
    """Analytics dashboard: words, WPM, streak, time saved, 7-day trend, and top apps."""

    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(42, 32, 42, 32)
        lay.setSpacing(20)

        t = QLabel("Voice Insights")
        t.setObjectName("PageTitle")
        sub = QLabel("All analytics are computed 100% locally from your SQLite dictation history.")
        sub.setObjectName("SecondaryLabel")
        lay.addWidget(t)
        lay.addWidget(sub)

        # KPI cards row
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)
        self.kpi_words = self._kpi_card("Total Words", "0")
        self.kpi_wpm = self._kpi_card("Average Speed", "0 wpm")
        self.kpi_streak = self._kpi_card("Day Streak", "0 days")
        self.kpi_saved = self._kpi_card("Time Saved vs Typing", "0 min")
        for card, _ in (self.kpi_words, self.kpi_wpm, self.kpi_streak, self.kpi_saved):
            kpi_row.addWidget(card, 1)
        lay.addLayout(kpi_row)

        # 7-day chart card
        chart_card = QFrame()
        chart_card.setObjectName("SurfaceCard")
        cl = QVBoxLayout(chart_card)
        cl.setContentsMargins(20, 18, 20, 18)
        cl.setSpacing(8)
        ct = QLabel("Words Dictated (Last 7 Days)")
        ct.setObjectName("SectionTitle")
        cl.addWidget(ct)
        self.chart = WeeklyBarChart()
        cl.addWidget(self.chart)
        lay.addWidget(chart_card)

        # Top apps card
        apps_card = QFrame()
        apps_card.setObjectName("RightCard")
        al = QVBoxLayout(apps_card)
        al.setContentsMargins(20, 18, 20, 18)
        al.setSpacing(10)
        at = QLabel("Top Applications")
        at.setObjectName("SectionTitle")
        al.addWidget(at)
        self.apps_lay = QVBoxLayout()
        self.apps_lay.setSpacing(8)
        al.addLayout(self.apps_lay)
        lay.addWidget(apps_card)
        lay.addStretch()

        scroll.setWidget(body)
        outer.addWidget(scroll)

    @staticmethod
    def _kpi_card(title: str, initial: str) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setObjectName("RightCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.setSpacing(6)
        val = QLabel(initial)
        val.setStyleSheet('font-family: "Georgia", serif; font-size: 26px; background: transparent;')
        lbl = QLabel(title)
        lbl.setObjectName("SecondaryLabel")
        cl.addWidget(val)
        cl.addWidget(lbl)
        return card, val

    def refresh(self) -> None:
        s = self.db.get_stats()
        self.kpi_words[1].setText(format_word_count(s["total_words"]))
        self.kpi_wpm[1].setText(f"{s['wpm']} wpm")
        self.kpi_streak[1].setText(f"{s['day_streak']} days")
        saved = s["saved_minutes"]
        self.kpi_saved[1].setText(f"{saved / 60:.1f} hrs" if saved >= 60 else f"{int(round(saved))} min")
        self.chart.set_data(s["daily_words"])

        while self.apps_lay.count():
            item = self.apps_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not s["top_apps"]:
            empty = QLabel("Dictate in any Windows app to see per-application stats here.")
            empty.setObjectName("SecondaryLabel")
            self.apps_lay.addWidget(empty)
            return

        for app in s["top_apps"]:
            row_w = QWidget()
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(0, 2, 0, 2)
            name = QLabel(app["app_name"])
            name.setStyleSheet("font-weight: 600; background: transparent;")
            cnt = QLabel(f"{app['words']} words · {app['cnt']} dictations")
            cnt.setObjectName("SecondaryLabel")
            rl.addWidget(name)
            rl.addStretch()
            rl.addWidget(cnt)
            self.apps_lay.addWidget(row_w)
