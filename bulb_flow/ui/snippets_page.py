"""Voice Snippets / Text Expansions manager."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..database import Database


class SnippetsPage(QWidget):
    """Say a short trigger phrase -> Bulb Flow expands and pastes the full snippet."""

    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(42, 32, 42, 24)
        lay.setSpacing(16)

        t = QLabel("Snippets")
        t.setObjectName("PageTitle")
        sub = QLabel(
            "Create voice shortcuts for links, email templates, sign-offs, or code blocks. Say the trigger phrase to insert the expansion."
        )
        sub.setObjectName("SecondaryLabel")
        sub.setWordWrap(True)
        lay.addWidget(t)
        lay.addWidget(sub)

        add_card = QFrame()
        add_card.setObjectName("RightCard")
        al = QVBoxLayout(add_card)
        al.setContentsMargins(16, 14, 16, 14)
        al.setSpacing(10)

        top = QHBoxLayout()
        self.trigger_in = QLineEdit()
        self.trigger_in.setPlaceholderText("Spoken trigger phrase (e.g., 'my calendar')")
        add_btn = QPushButton("Save snippet")
        add_btn.setObjectName("AmberCTA")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._add_snippet)
        top.addWidget(self.trigger_in, 1)
        top.addWidget(add_btn)
        al.addLayout(top)

        self.expand_in = QTextEdit()
        self.expand_in.setPlaceholderText("Expanded text to paste when triggered...")
        self.expand_in.setFixedHeight(74)
        al.addWidget(self.expand_in)
        lay.addWidget(add_card)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.list_wrap = QWidget()
        self.list_lay = QVBoxLayout(self.list_wrap)
        self.list_lay.setContentsMargins(0, 4, 4, 12)
        self.list_lay.setSpacing(10)
        self.scroll.setWidget(self.list_wrap)
        lay.addWidget(self.scroll, 1)

    def _add_snippet(self) -> None:
        trig = self.trigger_in.text().strip()
        exp = self.expand_in.toPlainText().strip()
        if not trig or not exp:
            return
        self.db.upsert_snippet(trig, exp)
        self.trigger_in.clear()
        self.expand_in.clear()
        self.refresh()

    def refresh(self) -> None:
        while self.list_lay.count():
            item = self.list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for sn in self.db.list_snippets():
            card = QFrame()
            card.setObjectName("SurfaceCard")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 12, 14, 12)
            cl.setSpacing(6)

            hdr = QHBoxLayout()
            trig = QLabel(f'"{sn["trigger_phrase"]}"')
            trig.setObjectName("BadgeLavender")
            hdr.addWidget(trig)
            hdr.addStretch()
            used = QLabel(f"Used {sn['usage_count']}×")
            used.setObjectName("MutedLabel")
            hdr.addWidget(used)
            rm = QPushButton("Delete")
            rm.setObjectName("GhostBtn")
            rm.clicked.connect(lambda _, sid=sn["id"]: (self.db.delete_snippet(sid), self.refresh()))
            hdr.addWidget(rm)
            cl.addLayout(hdr)

            body = QLabel(sn["expansion_text"])
            body.setWordWrap(True)
            body.setObjectName("SecondaryLabel")
            cl.addWidget(body)
            self.list_lay.addWidget(card)

        self.list_lay.addStretch()
