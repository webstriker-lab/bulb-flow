"""Notetaker / Meeting Recorder page with live recording, transcription, and AI summaries."""

from __future__ import annotations

import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..ai_pipeline import AIPipeline
from ..database import Database
from ..icons import icon_record


class MeetingsPage(QWidget):
    """Record meetings, transcribe with local/API STT, and generate AI summaries & action items."""

    record_meeting_toggle = Signal()
    _summary_ready = Signal(str, str)

    def __init__(self, db: Database, pipeline: AIPipeline, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self.pipeline = pipeline
        self._current_id: str | None = None
        self._summary_ready.connect(self._on_summary_ready)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(36, 28, 36, 24)
        lay.setSpacing(20)

        # Left meeting list
        left = QVBoxLayout()
        left.setSpacing(10)
        hdr = QHBoxLayout()
        t = QLabel("Notetaker")
        t.setObjectName("PageTitle")
        new_btn = QPushButton("+ Meeting")
        new_btn.setObjectName("SecondaryBtn")
        new_btn.clicked.connect(self._new_meeting)
        hdr.addWidget(t)
        hdr.addStretch()
        hdr.addWidget(new_btn)
        left.addLayout(hdr)

        sub = QLabel("Record meetings & generate AI summaries with your local or cloud models.")
        sub.setObjectName("SecondaryLabel")
        sub.setWordWrap(True)
        left.addWidget(sub)

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

        # Right meeting workspace
        card = QFrame()
        card.setObjectName("SurfaceCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 18, 20, 18)
        cl.setSpacing(12)

        top = QHBoxLayout()
        self.title_in = QLineEdit()
        self.title_in.setPlaceholderText("Meeting title (e.g., Weekly Product Sync)")
        self.title_in.setStyleSheet("font-size: 16px; font-weight: 600;")
        top.addWidget(self.title_in, 1)

        self.rec_btn = QPushButton(" Record Audio")
        self.rec_btn.setObjectName("RecordBtn")
        self.rec_btn.setIcon(icon_record(15, "#FFFFEB"))
        self.rec_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rec_btn.clicked.connect(self.record_meeting_toggle.emit)
        top.addWidget(self.rec_btn)

        self.sum_btn = QPushButton("Generate AI Summary")
        self.sum_btn.setObjectName("AmberCTA")
        self.sum_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sum_btn.clicked.connect(self._summarize)
        top.addWidget(self.sum_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("SecondaryBtn")
        save_btn.clicked.connect(self._save)
        top.addWidget(save_btn)
        cl.addLayout(top)

        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("MutedLabel")
        cl.addWidget(self.status_lbl)

        self.tabs = QTabWidget()
        self.transcript_box = QTextEdit()
        self.transcript_box.setPlaceholderText("Click 'Record Audio' or paste a meeting transcript here...")
        self.summary_box = QTextEdit()
        self.summary_box.setPlaceholderText("AI-generated meeting summary will appear here...")
        self.actions_box = QTextEdit()
        self.actions_box.setPlaceholderText("Extracted action items & next steps will appear here...")

        self.tabs.addTab(self.transcript_box, "Transcript")
        self.tabs.addTab(self.summary_box, "AI Summary")
        self.tabs.addTab(self.actions_box, "Action Items")
        cl.addWidget(self.tabs, 1)

        lay.addWidget(card, 1)

    def set_recording_state(self, recording: bool) -> None:
        self.rec_btn.setProperty("recording", "true" if recording else "false")
        self.rec_btn.style().unpolish(self.rec_btn)
        self.rec_btn.style().polish(self.rec_btn)
        self.rec_btn.setText(" Stop & Transcribe" if recording else " Record Audio")
        if recording:
            self.status_lbl.setText("Recording meeting audio...")

    def append_transcript(self, text: str) -> None:
        if not text:
            return
        cur = self.transcript_box.toPlainText()
        sep = "\n\n" if cur.strip() else ""
        self.transcript_box.setPlainText(cur + sep + text)
        self.status_lbl.setText("Transcript updated. Click 'Generate AI Summary' anytime.")
        self._save()

    def _new_meeting(self) -> None:
        self._current_id = None
        self.title_in.clear()
        self.transcript_box.clear()
        self.summary_box.clear()
        self.actions_box.clear()
        self.status_lbl.setText("")

    def _save(self) -> None:
        title = self.title_in.text().strip() or "Untitled Meeting"
        self._current_id = self.db.save_meeting(
            title=title,
            transcript=self.transcript_box.toPlainText(),
            summary=self.summary_box.toPlainText(),
            action_items=self.actions_box.toPlainText(),
            meeting_id=self._current_id,
        )
        self.refresh(select_id=self._current_id)

    def _summarize(self) -> None:
        transcript = self.transcript_box.toPlainText().strip()
        if not transcript:
            self.status_lbl.setText("Record or paste a transcript before summarizing.")
            return
        title = self.title_in.text().strip() or "Meeting"
        self.sum_btn.setEnabled(False)
        self.status_lbl.setText("Generating summary and action items...")

        def _work() -> None:
            try:
                summary, actions = self.pipeline.summarize_meeting(transcript, title=title)
            except Exception as exc:
                summary, actions = f"Summary failed: {exc}", ""
            self._summary_ready.emit(summary, actions)

        threading.Thread(target=_work, daemon=True).start()

    def _on_summary_ready(self, summary: str, actions: str) -> None:
        self.sum_btn.setEnabled(True)
        self.summary_box.setPlainText(summary)
        self.actions_box.setPlainText(actions)
        self.tabs.setCurrentIndex(1)
        self.status_lbl.setText("Summary ready.")
        self._save()

    def refresh(self, select_id: str | None = None) -> None:
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        selected_row = -1
        for idx, m in enumerate(self.db.list_meetings()):
            item = QListWidgetItem(f"{m['title']}\n{m['created_at'][:16].replace('T', ' ')}")
            item.setData(Qt.ItemDataRole.UserRole, m)
            self.list_widget.addItem(item)
            if select_id and m["id"] == select_id:
                selected_row = idx
        self.list_widget.blockSignals(False)
        if selected_row >= 0:
            self.list_widget.setCurrentRow(selected_row)

    def _on_select(self, current: QListWidgetItem | None, _prev) -> None:
        if not current:
            return
        m = current.data(Qt.ItemDataRole.UserRole)
        self._current_id = m["id"]
        self.title_in.setText(m["title"])
        self.transcript_box.setPlainText(m["transcript"])
        self.summary_box.setPlainText(m["summary"])
        self.actions_box.setPlainText(m["action_items"])
