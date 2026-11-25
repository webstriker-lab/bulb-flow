"""Home dashboard matching capture/window.png proportions, colors, and calm layout."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..database import Database
from ..icons import icon_mic, icon_search


def format_word_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1000:
        return f"{n / 1000:.1f}K"
    return str(n)


class HeroBannerWidget(QWidget):
    """Dark obsidian-to-warm-amber procedural glow banner (original artwork matching hero geometry)."""

    start_clicked = Signal()
    dismiss_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(130)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 18, 16, 18)
        layout.setSpacing(12)

        text_col = QVBoxLayout()
        text_col.setSpacing(6)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title = QLabel('Make Bulb Flow sound like <i style="font-style:italic;">you</i>')
        title.setStyleSheet(
            'color: #FFFFEB; font-family: "Georgia", "Times New Roman", serif; '
            "font-size: 23px; font-weight: 400; background: transparent;"
        )
        sub = QLabel("Set up writing styles, API keys, or local offline models.")
        sub.setStyleSheet("color: #DDD9CE; font-size: 13px; background: transparent;")
        text_col.addWidget(title)
        text_col.addWidget(sub)
        layout.addLayout(text_col, 1)

        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(0)

        dismiss_row = QHBoxLayout()
        dismiss_row.addStretch()
        dismiss_btn = QPushButton("×")
        dismiss_btn.setFixedSize(24, 24)
        dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dismiss_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #EAE6DC; border: none; font-size: 16px; border-radius: 12px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.16); }"
        )
        dismiss_btn.clicked.connect(self.dismiss_clicked.emit)
        dismiss_row.addWidget(dismiss_btn)
        right_col.addLayout(dismiss_row)
        right_col.addStretch()

        cta_row = QHBoxLayout()
        cta_row.addStretch()
        start_btn = QPushButton("Start now")
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.setStyleSheet(
            "QPushButton { background: #F5F3EC; color: #1C1917; border: none; border-radius: 8px; "
            "padding: 8px 18px; font-size: 12.5px; font-weight: 600; }"
            "QPushButton:hover { background: #FFFFFF; }"
        )
        start_btn.clicked.connect(self.start_clicked.emit)
        cta_row.addWidget(start_btn)
        cta_row.addSpacing(8)
        right_col.addLayout(cta_row)
        right_col.addSpacing(6)

        layout.addLayout(right_col)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height())

        # Base dark obsidian horizontal gradient
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor("#090807"))
        grad.setColorAt(0.50, QColor("#120D08"))
        grad.setColorAt(0.76, QColor("#4A2B0C"))
        grad.setColorAt(1.0, QColor("#251608"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(rect, 14, 14)

        # Warm glowing bulb bokeh orbs on the right side (original abstract art)
        glow1 = QRadialGradient(QPointF(self.width() * 0.72, self.height() * 0.48), 115)
        glow1.setColorAt(0.0, QColor(255, 175, 72, 165))
        glow1.setColorAt(0.45, QColor(196, 108, 32, 85))
        glow1.setColorAt(1.0, QColor(196, 108, 32, 0))
        p.setBrush(QBrush(glow1))
        p.drawRoundedRect(rect, 14, 14)

        glow2 = QRadialGradient(QPointF(self.width() * 0.86, self.height() * 0.35), 95)
        glow2.setColorAt(0.0, QColor(255, 224, 140, 120))
        glow2.setColorAt(0.5, QColor(230, 130, 48, 55))
        glow2.setColorAt(1.0, QColor(230, 130, 48, 0))
        p.setBrush(QBrush(glow2))
        p.drawRoundedRect(rect, 14, 14)

        # Subtle stylized soundwave filament arcs inside the warm glow
        p.setPen(QPen(QColor(255, 245, 214, 48), 1.4))
        cx = self.width() * 0.73
        cy = self.height() * 0.50
        for r in (22, 36, 52):
            p.drawEllipse(QPointF(cx, cy), r, r)

        p.end()


class NotetakerMiniPreview(QWidget):
    """Stylized miniature meeting-notes preview drawn with QPainter (original UI graphic)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(96)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()

        # Mini white note card
        card = QRectF(4, 6, w - 58, h - 12)
        p.setPen(QPen(QColor("#E0DDD4"), 1.0))
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(card, 10, 10)

        p.setPen(QColor("#262320"))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.drawText(QRectF(14, 13, 130, 16), Qt.AlignmentFlag.AlignLeft, "Product Sync")

        # Tabs strip
        p.setPen(QColor("#8C8982"))
        p.setFont(QFont("Segoe UI", 6.5))
        p.drawText(QRectF(14, 29, 140, 14), Qt.AlignmentFlag.AlignLeft, "My thoughts   ·   Transcript   ·   Summary")

        # Abstract transcript lines
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#E6E3DA"))
        p.drawRoundedRect(QRectF(14, 48, 92, 5), 2.5, 2.5)
        p.drawRoundedRect(QRectF(14, 58, 126, 5), 2.5, 2.5)
        p.drawRoundedRect(QRectF(14, 68, 78, 5), 2.5, 2.5)

        # Two overlapping stylized speaker tiles on the right
        tile1 = QRectF(w - 94, 24, 44, 52)
        g1 = QLinearGradient(tile1.topLeft(), tile1.bottomRight())
        g1.setColorAt(0, QColor("#FDE6C4"))
        g1.setColorAt(1, QColor("#E2A45B"))
        p.setPen(QPen(QColor("#FFFFFF"), 1.5))
        p.setBrush(QBrush(g1))
        p.drawRoundedRect(tile1, 8, 8)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#6E4720"))
        p.drawEllipse(QPointF(tile1.center().x(), tile1.top() + 19), 7, 7)
        p.drawRoundedRect(QRectF(tile1.center().x() - 10, tile1.top() + 29, 20, 13), 6, 6)

        tile2 = QRectF(w - 46, 24, 44, 52)
        g2 = QLinearGradient(tile2.topLeft(), tile2.bottomRight())
        g2.setColorAt(0, QColor("#E2D4FA"))
        g2.setColorAt(1, QColor("#9C76D6"))
        p.setPen(QPen(QColor("#FFFFFF"), 1.5))
        p.setBrush(QBrush(g2))
        p.drawRoundedRect(tile2, 8, 8)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#3E2469"))
        p.drawEllipse(QPointF(tile2.center().x(), tile2.top() + 19), 7, 7)
        p.drawRoundedRect(QRectF(tile2.center().x() - 10, tile2.top() + 29, 20, 13), 6, 6)

        p.end()


class HomePage(QWidget):
    """Main dashboard view with hero banner, dictation history, and right stats rail."""

    navigate = Signal(str)
    toggle_dictation = Signal()

    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self._is_recording = False
        self._build_ui()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(42, 34, 34, 24)
        root.setSpacing(28)

        # ================= LEFT / CENTER MAIN COLUMN =================
        center = QVBoxLayout()
        center.setSpacing(18)

        self.greeting_lbl = QLabel(f"Welcome back, {self.db.get_setting('user_name', 'Friend')}")
        self.greeting_lbl.setObjectName("PageTitle")
        center.addWidget(self.greeting_lbl)

        # Dark Hero Banner
        self.hero = HeroBannerWidget()
        self.hero.start_clicked.connect(lambda: self.navigate.emit("style"))
        self.hero.dismiss_clicked.connect(self._dismiss_hero)
        self.hero.setVisible(self.db.get_bool("show_hero_banner", True))
        center.addWidget(self.hero)

        # Action / Search bar row (clean minimal bar with right-aligned search icon)
        bar_row = QHBoxLayout()
        bar_row.setSpacing(10)

        self.dictate_btn = QPushButton(" Dictate now")
        self.dictate_btn.setObjectName("RecordBtn")
        self.dictate_btn.setIcon(icon_mic(15, "#FFFFEB"))
        self.dictate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dictate_btn.clicked.connect(self.toggle_dictation.emit)
        bar_row.addWidget(self.dictate_btn)

        self.hotkey_hint = QLabel("")
        self.hotkey_hint.setObjectName("MutedLabel")
        bar_row.addWidget(self.hotkey_hint)

        bar_row.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search dictations...")
        self.search_input.setFixedWidth(220)
        self.search_input.setVisible(False)
        self.search_input.textChanged.connect(self.refresh_history)
        bar_row.addWidget(self.search_input)

        self.search_btn = QPushButton()
        self.search_btn.setObjectName("IconBtn")
        self.search_btn.setIcon(icon_search(17, "#8C8982"))
        self.search_btn.setFixedSize(32, 32)
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn.setToolTip("Search transcripts")
        self.search_btn.clicked.connect(self._toggle_search)
        bar_row.addWidget(self.search_btn)

        center.addLayout(bar_row)

        # Live status banner (visible while recording / transcribing / error)
        self.live_status = QLabel("")
        self.live_status.setObjectName("BadgeLavender")
        self.live_status.setVisible(False)
        center.addWidget(self.live_status)

        # Scrollable History Feed
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.history_container = QWidget()
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(0, 4, 4, 16)
        self.history_layout.setSpacing(10)
        self.scroll.setWidget(self.history_container)
        center.addWidget(self.scroll, 1)

        root.addLayout(center, 1)

        # ================= RIGHT STATS & CARDS RAIL =================
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFixedWidth(292)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        right_wrap = QWidget()
        right_col = QVBoxLayout(right_wrap)
        right_col.setContentsMargins(0, 6, 4, 12)
        right_col.setSpacing(16)

        # --- Card 1: Stats + Unlimited Open-Source Status ---
        card1 = QFrame()
        card1.setObjectName("RightCard")
        c1_lay = QVBoxLayout(card1)
        c1_lay.setContentsMargins(20, 20, 20, 20)
        c1_lay.setSpacing(12)

        self.stat_words_val, row_w = self._make_stat_row("0", "total words")
        self.stat_wpm_val, row_wpm = self._make_stat_row("0", "wpm")
        self.stat_streak_val, row_str = self._make_stat_row("0", "day streak")
        c1_lay.addLayout(row_w)
        c1_lay.addLayout(row_wpm)
        c1_lay.addLayout(row_str)

        c1_lay.addSpacing(4)
        div = QFrame()
        div.setObjectName("Divider")
        c1_lay.addWidget(div)
        c1_lay.addSpacing(4)

        unlim_row = QHBoxLayout()
        unlim_row.setSpacing(6)
        inf_lbl = QLabel("∞")
        inf_lbl.setStyleSheet("color: #571B83; font-size: 20px; font-weight: 700; background: transparent;")
        unlim_txt = QLabel("unlimited words")
        unlim_txt.setStyleSheet("font-size: 14px; font-weight: 600; background: transparent;")
        unlim_row.addWidget(inf_lbl)
        unlim_row.addWidget(unlim_txt)
        unlim_row.addStretch()
        c1_lay.addLayout(unlim_row)

        self.provider_summary_lbl = QLabel(
            "Free & open source — zero weekly caps. Powered by your API keys, subscriptions, or local models."
        )
        self.provider_summary_lbl.setObjectName("SecondaryLabel")
        self.provider_summary_lbl.setWordWrap(True)
        c1_lay.addWidget(self.provider_summary_lbl)

        c1_lay.addSpacing(4)
        cfg_btn = QPushButton("Configure AI Providers")
        cfg_btn.setObjectName("AmberCTA")
        cfg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cfg_btn.clicked.connect(lambda: self.navigate.emit("providers"))
        c1_lay.addWidget(cfg_btn)

        # Divider inside card1 bottom -> Voice / Engine card feel (matching stacked cards)
        right_col.addWidget(card1)

        # --- Card 2: Local & Cloud Ready ---
        self.card2 = QFrame()
        self.card2.setObjectName("RightCard")
        c2_lay = QVBoxLayout(self.card2)
        c2_lay.setContentsMargins(20, 16, 16, 20)
        c2_lay.setSpacing(8)

        c2_top = QHBoxLayout()
        c2_title = QLabel("Voice Engine Ready!")
        c2_title.setStyleSheet("font-size: 14.5px; font-weight: 600; background: transparent;")
        c2_top.addWidget(c2_title)
        c2_top.addStretch()
        c2_close = QPushButton("×")
        c2_close.setObjectName("GhostBtn")
        c2_close.setFixedSize(22, 22)
        c2_close.clicked.connect(self._dismiss_card2)
        c2_top.addWidget(c2_close)
        c2_lay.addLayout(c2_top)

        c2_sub = QLabel("View your speaking speed, top apps, and time saved with Bulb Flow.")
        c2_sub.setObjectName("SecondaryLabel")
        c2_sub.setWordWrap(True)
        c2_lay.addWidget(c2_sub)

        c2_lay.addSpacing(4)
        report_btn = QPushButton("View voice insights")
        report_btn.setObjectName("AmberCTA")
        report_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        report_btn.clicked.connect(lambda: self.navigate.emit("stats"))
        c2_lay.addWidget(report_btn)

        self.card2.setVisible(self.db.get_bool("show_voice_card", True))
        right_col.addWidget(self.card2)

        # --- Card 3: Try Notetaker ---
        card3 = QFrame()
        card3.setObjectName("RightCard")
        card3.setCursor(Qt.CursorShape.PointingHandCursor)
        c3_lay = QVBoxLayout(card3)
        c3_lay.setContentsMargins(16, 16, 16, 16)
        c3_lay.setSpacing(10)

        c3_lay.addWidget(NotetakerMiniPreview())
        nt_row = QHBoxLayout()
        nt_lbl = QLabel("Try Notetaker")
        nt_lbl.setStyleSheet("font-size: 14px; font-weight: 600; background: transparent;")
        nt_row.addWidget(nt_lbl)
        nt_row.addStretch()
        nt_open = QPushButton("Open →")
        nt_open.setObjectName("GhostBtn")
        nt_open.clicked.connect(lambda: self.navigate.emit("meetings"))
        nt_row.addWidget(nt_open)
        c3_lay.addLayout(nt_row)
        card3.mousePressEvent = lambda e: self.navigate.emit("meetings")  # type: ignore[method-assign]

        right_col.addWidget(card3)
        right_col.addStretch()

        right_scroll.setWidget(right_wrap)
        root.addWidget(right_scroll)

        self.refresh_all()

    @staticmethod
    def _make_stat_row(value: str, label: str) -> tuple[QLabel, QHBoxLayout]:
        row = QHBoxLayout()
        row.setSpacing(8)
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(
            'font-family: "Georgia", "Times New Roman", serif; font-size: 25px; font-weight: 400; background: transparent;'
        )
        txt_lbl = QLabel(label)
        txt_lbl.setObjectName("SecondaryLabel")
        txt_lbl.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)
        row.addWidget(val_lbl)
        row.addWidget(txt_lbl)
        row.addStretch()
        return val_lbl, row

    def _dismiss_hero(self) -> None:
        self.hero.setVisible(False)
        self.db.set_setting("show_hero_banner", False)

    def _dismiss_card2(self) -> None:
        self.card2.setVisible(False)
        self.db.set_setting("show_voice_card", False)

    def _toggle_search(self) -> None:
        vis = not self.search_input.isVisible()
        self.search_input.setVisible(vis)
        if vis:
            self.search_input.setFocus()
        else:
            self.search_input.clear()

    def set_recording_state(self, recording: bool, status: str = "") -> None:
        self._is_recording = recording
        self.dictate_btn.setProperty("recording", "true" if recording else "false")
        self.dictate_btn.style().unpolish(self.dictate_btn)
        self.dictate_btn.style().polish(self.dictate_btn)
        self.dictate_btn.setText(" Stop recording" if recording else " Dictate now")
        if status:
            self.live_status.setText(status)
            self.live_status.setVisible(True)
        else:
            self.live_status.setVisible(False)

    def refresh_all(self) -> None:
        self.greeting_lbl.setText(f"Welcome back, {self.db.get_setting('user_name', 'Friend')}")
        ptt = self.db.get_setting("ptt_hotkey", "ctrl+win").replace("+", " + ").title()
        stt = self.db.get_setting("stt_provider", "local_faster_whisper").replace("_", " ").title()
        llm = self.db.get_setting("llm_provider", "builtin_smart").replace("_", " ").title()
        self.hotkey_hint.setText(f"Hold {ptt} anywhere  ·  {stt}")
        self.provider_summary_lbl.setText(
            f"Active stack: {stt} + {llm}. Switch freely between local models, API keys, or subscriptions."
        )

        stats = self.db.get_stats()
        self.stat_words_val.setText(format_word_count(stats["total_words"]))
        self.stat_wpm_val.setText(str(stats["wpm"]))
        self.stat_streak_val.setText(str(stats["day_streak"]))

        self.refresh_history()

    def refresh_history(self) -> None:
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        query = self.search_input.text() if self.search_input.isVisible() else ""
        rows = self.db.list_history(search=query, limit=60)

        if not rows:
            # Clean, calm empty state keeping visual breathing room like capture/window.png
            empty = QFrame()
            empty.setObjectName("SoftCard")
            el = QVBoxLayout(empty)
            el.setContentsMargins(24, 24, 24, 24)
            el.setSpacing(8)
            h = QLabel("Ready to dictate anywhere on Windows")
            h.setObjectName("SectionTitle")
            ptt = self.db.get_setting("ptt_hotkey", "ctrl+win").replace("+", " + ").title()
            hf = self.db.get_setting("hands_free_hotkey", "ctrl+win+space").replace("+", " + ").title()
            b = QLabel(
                f"Hold {ptt} to speak and auto-paste into any focused app, press {hf} for hands-free mode, "
                "or click 'Dictate now' above. Your recent transcripts will appear here."
            )
            b.setObjectName("SecondaryLabel")
            b.setWordWrap(True)
            el.addWidget(h)
            el.addWidget(b)
            self.history_layout.addWidget(empty)
            self.history_layout.addStretch()
            return

        for row in rows:
            self.history_layout.addWidget(self._build_history_item(row))
        self.history_layout.addStretch()

    def _build_history_item(self, row: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("SurfaceCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 12, 14, 12)
        lay.setSpacing(6)

        meta = QHBoxLayout()
        ts = row.get("timestamp", "")
        short_ts = ts[11:16] if len(ts) >= 16 else ts
        day_ts = ts[:10] if len(ts) >= 10 else ""
        time_lbl = QLabel(f"{day_ts}  {short_ts}")
        time_lbl.setObjectName("MutedLabel")
        meta.addWidget(time_lbl)

        app_badge = QLabel(row.get("app_name", "Bulb Flow"))
        app_badge.setObjectName("BadgeTeal")
        meta.addWidget(app_badge)

        style_badge = QLabel(row.get("style_used", "formal"))
        style_badge.setObjectName("BadgeLavender")
        meta.addWidget(style_badge)

        lat = row.get("e2e_latency_ms", 0)
        if lat:
            lat_lbl = QLabel(f"{int(lat)} ms · {row.get('num_words', 0)} words")
            lat_lbl.setObjectName("MutedLabel")
            meta.addWidget(lat_lbl)

        meta.addStretch()

        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("GhostBtn")
        copy_btn.clicked.connect(lambda _, txt=row["formatted_text"]: QApplication.clipboard().setText(txt))
        meta.addWidget(copy_btn)

        del_btn = QPushButton("Delete")
        del_btn.setObjectName("GhostBtn")
        del_btn.clicked.connect(lambda _, eid=row["id"]: self._delete_entry(eid))
        meta.addWidget(del_btn)
        lay.addLayout(meta)

        text_lbl = QLabel(row.get("formatted_text", ""))
        text_lbl.setWordWrap(True)
        text_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text_lbl.setStyleSheet("font-size: 13.5px; line-height: 1.45; background: transparent;")
        lay.addWidget(text_lbl)

        if row.get("asr_text") and row["asr_text"].strip() != row.get("formatted_text", "").strip():
            raw_lbl = QLabel(f"Raw: {row['asr_text']}")
            raw_lbl.setObjectName("MutedLabel")
            raw_lbl.setWordWrap(True)
            lay.addWidget(raw_lbl)

        return card

    def _delete_entry(self, entry_id: str) -> None:
        self.db.delete_history(entry_id)
        self.refresh_all()
