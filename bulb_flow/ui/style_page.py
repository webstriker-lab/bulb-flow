"""Writing Styles & Auto-Cleanup per App Category (mirrors Wispr Flow Style page)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..constants import APP_CATEGORIES, CLEANUP_LEVELS, TONE_OPTIONS
from ..database import Database


class StylePage(QWidget):
    """Per-app writing styles (Formal, Casual, very casual, Excited!) + Auto Cleanup."""

    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self._active_cat = APP_CATEGORIES[0]["id"]
        self._cat_btns: dict[str, QPushButton] = {}
        self._tone_cards: dict[str, QFrame] = {}
        self._cleanup_btns: dict[str, QPushButton] = {}
        self._build_ui()
        self._select_category(self._active_cat)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(42, 32, 42, 32)
        lay.setSpacing(20)

        t = QLabel("Writing Style")
        t.setObjectName("PageTitle")
        sub = QLabel(
            "Bulb Flow automatically detects your active Windows app and applies the right tone and cleanup level."
        )
        sub.setObjectName("SecondaryLabel")
        lay.addWidget(t)
        lay.addWidget(sub)

        # Category tabs row
        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)
        for cat in APP_CATEGORIES:
            btn = QPushButton(cat["label"].replace("&", "&&"))
            btn.setObjectName("SecondaryBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, cid=cat["id"]: self._select_category(cid))
            self._cat_btns[cat["id"]] = btn
            tab_row.addWidget(btn)
        tab_row.addStretch()
        lay.addLayout(tab_row)

        self.apps_lbl = QLabel("")
        self.apps_lbl.setObjectName("MutedLabel")
        lay.addWidget(self.apps_lbl)

        # 2x2 Tone Cards Grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        self._tone_samples: dict[str, QLabel] = {}
        for idx, tone in enumerate(TONE_OPTIONS):
            card = QFrame()
            card.setObjectName("SurfaceCard")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(18, 16, 18, 16)
            cl.setSpacing(8)

            top = QHBoxLayout()
            title_lbl = QLabel(tone["title"])
            title_lbl.setStyleSheet('font-family: "Georgia", serif; font-size: 19px; font-weight: 500; background: transparent;')
            sub_lbl = QLabel(tone["subtitle"])
            sub_lbl.setObjectName("MutedLabel")
            top.addWidget(title_lbl)
            top.addStretch()
            top.addWidget(sub_lbl)
            cl.addLayout(top)

            sample_lbl = QLabel("")
            sample_lbl.setObjectName("SecondaryLabel")
            sample_lbl.setWordWrap(True)
            sample_lbl.setMinimumHeight(64)
            cl.addWidget(sample_lbl)
            self._tone_samples[tone["id"]] = sample_lbl

            card.mousePressEvent = lambda e, tid=tone["id"]: self._set_tone(tid)  # type: ignore[method-assign]
            self._tone_cards[tone["id"]] = card
            grid.addWidget(card, idx // 2, idx % 2)

        lay.addLayout(grid)

        # Auto Cleanup Level Card
        clean_card = QFrame()
        clean_card.setObjectName("RightCard")
        cl2 = QVBoxLayout(clean_card)
        cl2.setContentsMargins(20, 18, 20, 18)
        cl2.setSpacing(12)

        ct = QLabel("Auto Cleanup")
        ct.setObjectName("SectionTitle")
        cl2.addWidget(ct)

        clean_row = QHBoxLayout()
        clean_row.setSpacing(10)
        for cid, label, desc in CLEANUP_LEVELS:
            btn = QPushButton(f"{label}\n{desc}")
            btn.setObjectName("SecondaryBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(56)
            btn.clicked.connect(lambda _, lv=cid: self._set_cleanup(lv))
            self._cleanup_btns[cid] = btn
            clean_row.addWidget(btn, 1)
        cl2.addLayout(clean_row)

        # Optional custom prompt per category
        cl2.addWidget(QLabel("Custom Style Instruction (optional)"))
        self.custom_prompt = QLineEdit()
        self.custom_prompt.setPlaceholderText("e.g., Always use British spelling, or keep Slack replies under 2 sentences...")
        self.custom_prompt.editingFinished.connect(self._save_custom_prompt)
        cl2.addWidget(self.custom_prompt)

        lay.addWidget(clean_card)
        lay.addStretch()

        scroll.setWidget(body)
        outer.addWidget(scroll)

    def _select_category(self, cat_id: str) -> None:
        self._active_cat = cat_id
        cat = next(c for c in APP_CATEGORIES if c["id"] == cat_id)
        self.apps_lbl.setText("Matches apps: " + ", ".join(cat["apps"]))

        for cid, btn in self._cat_btns.items():
            if cid == cat_id:
                btn.setObjectName("LavenderPill")
            else:
                btn.setObjectName("SecondaryBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        for tone in TONE_OPTIONS:
            self._tone_samples[tone["id"]].setText(tone["sample"].get(cat_id, tone["sample"]["other"]))

        styles = self.db.get_styles()
        cur = styles.get(cat_id, {"tone": cat["default_tone"], "cleanup_level": cat["default_cleanup"], "custom_prompt": ""})
        self.custom_prompt.setText(cur.get("custom_prompt", ""))
        self._highlight_selection(cur["tone"], cur["cleanup_level"])

    def _highlight_selection(self, tone_id: str, cleanup_id: str) -> None:
        for tid, card in self._tone_cards.items():
            if tid == tone_id:
                card.setStyleSheet("QFrame#SurfaceCard { border: 2px solid #571B83; border-radius: 12px; }")
            else:
                card.setStyleSheet("")
        for lv, btn in self._cleanup_btns.items():
            if lv == cleanup_id:
                btn.setObjectName("AmberCTA")
            else:
                btn.setObjectName("SecondaryBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _set_tone(self, tone_id: str) -> None:
        styles = self.db.get_styles()
        cur = styles.get(self._active_cat, {"cleanup_level": "medium", "custom_prompt": ""})
        self.db.set_style(self._active_cat, tone_id, cur.get("cleanup_level", "medium"), cur.get("custom_prompt", ""))
        self._highlight_selection(tone_id, cur.get("cleanup_level", "medium"))

    def _set_cleanup(self, cleanup_id: str) -> None:
        styles = self.db.get_styles()
        cur = styles.get(self._active_cat, {"tone": "formal", "custom_prompt": ""})
        self.db.set_style(self._active_cat, cur.get("tone", "formal"), cleanup_id, cur.get("custom_prompt", ""))
        self._highlight_selection(cur.get("tone", "formal"), cleanup_id)

    def _save_custom_prompt(self) -> None:
        styles = self.db.get_styles()
        cur = styles.get(self._active_cat, {"tone": "formal", "cleanup_level": "medium"})
        self.db.set_style(
            self._active_cat,
            cur.get("tone", "formal"),
            cur.get("cleanup_level", "medium"),
            self.custom_prompt.text().strip(),
        )
