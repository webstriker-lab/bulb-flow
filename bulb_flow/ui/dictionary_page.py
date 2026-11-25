"""Personal Dictionary & Auto-Replace vocabulary manager."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..database import Database


class DictionaryPage(QWidget):
    """Teach Bulb Flow custom names, technical jargon, acronyms, and spoken auto-replacements."""

    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(42, 32, 42, 24)
        lay.setSpacing(16)

        t = QLabel("Dictionary")
        t.setObjectName("PageTitle")
        sub = QLabel(
            "Add custom names, acronyms, and spellings. Words here are passed as hints to Whisper/Gemini and auto-corrected after transcription."
        )
        sub.setObjectName("SecondaryLabel")
        sub.setWordWrap(True)
        lay.addWidget(t)
        lay.addWidget(sub)

        # Add bar
        add_card = QFrame()
        add_card.setObjectName("RightCard")
        al = QHBoxLayout(add_card)
        al.setContentsMargins(16, 14, 16, 14)
        al.setSpacing(10)

        self.phrase_in = QLineEdit()
        self.phrase_in.setPlaceholderText("Spoken phrase or term (e.g., 'bulb flow' or 'PySide')")
        self.repl_in = QLineEdit()
        self.repl_in.setPlaceholderText("Preferred spelling (optional, e.g., 'Bulb Flow')")
        add_btn = QPushButton("Add word")
        add_btn.setObjectName("AmberCTA")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._add_word)

        al.addWidget(self.phrase_in, 1)
        al.addWidget(self.repl_in, 1)
        al.addWidget(add_btn)
        lay.addWidget(add_card)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.list_wrap = QWidget()
        self.list_lay = QVBoxLayout(self.list_wrap)
        self.list_lay.setContentsMargins(0, 4, 4, 12)
        self.list_lay.setSpacing(8)
        self.scroll.setWidget(self.list_wrap)
        lay.addWidget(self.scroll, 1)

    def _add_word(self) -> None:
        phrase = self.phrase_in.text().strip()
        if not phrase:
            return
        self.db.upsert_dictionary(phrase, self.repl_in.text().strip() or phrase)
        self.phrase_in.clear()
        self.repl_in.clear()
        self.refresh()

    def refresh(self) -> None:
        while self.list_lay.count():
            item = self.list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        entries = self.db.list_dictionary()
        for e in entries:
            card = QFrame()
            card.setObjectName("SurfaceCard")
            row = QHBoxLayout(card)
            row.setContentsMargins(16, 10, 14, 10)
            row.setSpacing(12)

            star = QPushButton("★" if e["starred"] else "☆")
            star.setObjectName("GhostBtn")
            star.setFixedWidth(30)
            star.clicked.connect(lambda _, eid=e["id"]: (self.db.toggle_dictionary_star(eid), self.refresh()))
            row.addWidget(star)

            phrase_lbl = QLabel(e["phrase"])
            phrase_lbl.setStyleSheet("font-weight: 600; background: transparent;")
            row.addWidget(phrase_lbl)

            if e["replacement"] and e["replacement"] != e["phrase"]:
                arrow = QLabel(f"→  {e['replacement']}")
                arrow.setObjectName("BadgeLavender")
                row.addWidget(arrow)

            row.addStretch()
            used = QLabel(f"Used {e['frequency_used']}×")
            used.setObjectName("MutedLabel")
            row.addWidget(used)

            rm = QPushButton("Remove")
            rm.setObjectName("GhostBtn")
            rm.clicked.connect(lambda _, eid=e["id"]: (self.db.delete_dictionary(eid), self.refresh()))
            row.addWidget(rm)
            self.list_lay.addWidget(card)

        self.list_lay.addStretch()
