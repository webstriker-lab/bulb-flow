"""Scratchpad Voice Notes page with direct voice dictation."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..database import Database
from ..icons import icon_mic


class NotesPage(QWidget):
    """Voice-first scratchpad notes with pin, search, and direct dictation insertion."""

    dictate_into_note = Signal()

    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self._current_id: str | None = None
        self._pinned = False
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(36, 28, 36, 24)
        lay.setSpacing(20)

        # Left notes list
        left = QVBoxLayout()
        left.setSpacing(10)
        top = QHBoxLayout()
        t = QLabel("Notes")
        t.setObjectName("PageTitle")
        new_btn = QPushButton("+ New")
        new_btn.setObjectName("AmberCTA")
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.clicked.connect(self._new_note)
        top.addWidget(t)
        top.addStretch()
        top.addWidget(new_btn)
        left.addLayout(top)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search notes...")
        self.search.textChanged.connect(self.refresh)
        left.addWidget(self.search)

        self.list_widget = QListWidget()
        self.list_widget.setFixedWidth(260)
        self.list_widget.setStyleSheet(
            "QListWidget { background: transparent; border: none; outline: none; }"
            "QListWidget::item { padding: 10px 12px; border-radius: 10px; margin-bottom: 4px; }"
            "QListWidget::item:selected { background: #EEEBE3; color: #1C1917; font-weight: 600; }"
        )
        self.list_widget.currentItemChanged.connect(self._on_select)
        left.addWidget(self.list_widget, 1)
        lay.addLayout(left)

        # Right note editor
        editor_card = QFrame()
        editor_card.setObjectName("SurfaceCard")
        el = QVBoxLayout(editor_card)
        el.setContentsMargins(20, 18, 20, 18)
        el.setSpacing(12)

        erow = QHBoxLayout()
        self.title_in = QLineEdit()
        self.title_in.setPlaceholderText("Note title...")
        self.title_in.setStyleSheet("font-size: 16px; font-weight: 600;")
        erow.addWidget(self.title_in, 1)

        self.dict_btn = QPushButton(" Dictate")
        self.dict_btn.setObjectName("RecordBtn")
        self.dict_btn.setIcon(icon_mic(15, "#FFFFEB"))
        self.dict_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dict_btn.clicked.connect(self.dictate_into_note.emit)
        erow.addWidget(self.dict_btn)

        self.pin_btn = QPushButton("Pin")
        self.pin_btn.setObjectName("SecondaryBtn")
        self.pin_btn.clicked.connect(self._toggle_pin)
        erow.addWidget(self.pin_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("AmberCTA")
        save_btn.clicked.connect(self._save_current)
        erow.addWidget(save_btn)

        del_btn = QPushButton("Delete")
        del_btn.setObjectName("GhostBtn")
        del_btn.clicked.connect(self._delete_current)
        erow.addWidget(del_btn)
        el.addLayout(erow)

        self.body_in = QTextEdit()
        self.body_in.setPlaceholderText("Start typing or click Dictate to capture your thoughts with voice...")
        el.addWidget(self.body_in, 1)

        lay.addWidget(editor_card, 1)

    def append_dictated_text(self, text: str) -> None:
        if not text:
            return
        existing = self.body_in.toPlainText()
        sep = "\n\n" if existing.strip() else ""
        self.body_in.setPlainText(existing + sep + text)
        self._save_current()

    def _new_note(self) -> None:
        self._current_id = None
        self._pinned = False
        self.title_in.clear()
        self.body_in.clear()
        self.pin_btn.setText("Pin")
        self.title_in.setFocus()

    def _toggle_pin(self) -> None:
        self._pinned = not self._pinned
        self.pin_btn.setText("Pinned ★" if self._pinned else "Pin")
        if self._current_id:
            self._save_current()

    def _save_current(self) -> None:
        title = self.title_in.text().strip() or "Quick Voice Note"
        content = self.body_in.toPlainText()
        self._current_id = self.db.save_note(title, content, note_id=self._current_id, pinned=self._pinned)
        self.refresh(select_id=self._current_id)

    def _delete_current(self) -> None:
        if self._current_id:
            self.db.delete_note(self._current_id)
        self._new_note()
        self.refresh()

    def refresh(self, select_id: str | None = None) -> None:
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        notes = self.db.list_notes(search=self.search.text())
        selected_row = -1
        for idx, n in enumerate(notes):
            prefix = "★ " if n["pinned"] else ""
            item = QListWidgetItem(f"{prefix}{n['title']}\n{n['updated_at'][:16].replace('T', ' ')}")
            item.setData(Qt.ItemDataRole.UserRole, n)
            self.list_widget.addItem(item)
            if select_id and n["id"] == select_id:
                selected_row = idx
        self.list_widget.blockSignals(False)
        if selected_row >= 0:
            self.list_widget.setCurrentRow(selected_row)

    def _on_select(self, current: QListWidgetItem | None, _prev) -> None:
        if not current:
            return
        n = current.data(Qt.ItemDataRole.UserRole)
        self._current_id = n["id"]
        self._pinned = bool(n["pinned"])
        self.title_in.setText(n["title"])
        self.body_in.setPlainText(n["content"])
        self.pin_btn.setText("Pinned ★" if self._pinned else "Pin")
