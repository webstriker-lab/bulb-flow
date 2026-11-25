"""AI Transforms & Custom Prompt Studio."""

from __future__ import annotations

import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
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

from ..ai_pipeline import AIPipeline
from ..database import Database


class TransformsPage(QWidget):
    """Run one-click AI transforms on dictated text and author custom prompt recipes."""

    _result_ready = Signal(str)

    def __init__(self, db: Database, pipeline: AIPipeline, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self.pipeline = pipeline
        self._result_ready.connect(self._on_result)
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
        lay.setSpacing(18)

        t = QLabel("AI Transforms")
        t.setObjectName("PageTitle")
        sub = QLabel(
            "Apply reusable AI prompts to clean up, summarize, translate, or rewrite text using your active local or cloud LLM."
        )
        sub.setObjectName("SecondaryLabel")
        sub.setWordWrap(True)
        lay.addWidget(t)
        lay.addWidget(sub)

        # Sandbox card
        sb = QFrame()
        sb.setObjectName("RightCard")
        sbl = QVBoxLayout(sb)
        sbl.setContentsMargins(18, 16, 18, 16)
        sbl.setSpacing(10)

        st = QLabel("Transform Sandbox")
        st.setObjectName("SectionTitle")
        sbl.addWidget(st)

        io_row = QHBoxLayout()
        io_row.setSpacing(12)
        self.in_box = QTextEdit()
        self.in_box.setPlaceholderText("Paste or dictate raw text here, then click any transform below...")
        self.in_box.setFixedHeight(110)

        self.out_box = QTextEdit()
        self.out_box.setPlaceholderText("Transformed output will appear here...")
        self.out_box.setReadOnly(True)
        self.out_box.setFixedHeight(110)

        io_row.addWidget(self.in_box, 1)
        io_row.addWidget(self.out_box, 1)
        sbl.addLayout(io_row)

        out_actions = QHBoxLayout()
        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("MutedLabel")
        out_actions.addWidget(self.status_lbl)
        out_actions.addStretch()
        copy_btn = QPushButton("Copy Output")
        copy_btn.setObjectName("SecondaryBtn")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.out_box.toPlainText()))
        out_actions.addWidget(copy_btn)
        sbl.addLayout(out_actions)
        lay.addWidget(sb)

        # Recipe list
        self.list_lay = QVBoxLayout()
        self.list_lay.setSpacing(10)
        lay.addLayout(self.list_lay)

        # Add custom transform
        add_card = QFrame()
        add_card.setObjectName("SurfaceCard")
        al = QVBoxLayout(add_card)
        al.setContentsMargins(16, 14, 16, 14)
        al.setSpacing(8)
        al.addWidget(QLabel("Create Custom Transform"))
        r1 = QHBoxLayout()
        self.new_name = QLineEdit()
        self.new_name.setPlaceholderText("Transform name (e.g., 'Slack Update')")
        add_btn = QPushButton("Add Transform")
        add_btn.setObjectName("AmberCTA")
        add_btn.clicked.connect(self._add_transform)
        r1.addWidget(self.new_name, 1)
        r1.addWidget(add_btn)
        al.addLayout(r1)

        self.new_prompt = QTextEdit()
        self.new_prompt.setPlaceholderText("System instruction for the LLM...")
        self.new_prompt.setFixedHeight(66)
        al.addWidget(self.new_prompt)
        lay.addWidget(add_card)
        lay.addStretch()

        scroll.setWidget(body)
        outer.addWidget(scroll)

    def _add_transform(self) -> None:
        name = self.new_name.text().strip()
        prompt = self.new_prompt.toPlainText().strip()
        if not name or not prompt:
            return
        self.db.upsert_transform(name, prompt)
        self.new_name.clear()
        self.new_prompt.clear()
        self.refresh()

    def refresh(self) -> None:
        while self.list_lay.count():
            item = self.list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for tr in self.db.list_transforms():
            card = QFrame()
            card.setObjectName("SurfaceCard")
            row = QHBoxLayout(card)
            row.setContentsMargins(16, 12, 14, 12)
            row.setSpacing(12)

            info = QVBoxLayout()
            n = QLabel(tr["name"])
            n.setStyleSheet("font-weight: 600; background: transparent;")
            p = QLabel(tr["system_prompt"])
            p.setObjectName("SecondaryLabel")
            p.setWordWrap(True)
            info.addWidget(n)
            info.addWidget(p)
            row.addLayout(info, 1)

            run_btn = QPushButton("Run")
            run_btn.setObjectName("AmberCTA")
            run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            run_btn.clicked.connect(lambda _, sp=tr["system_prompt"], nm=tr["name"]: self._run(nm, sp))
            row.addWidget(run_btn)

            rm = QPushButton("Delete")
            rm.setObjectName("GhostBtn")
            rm.clicked.connect(lambda _, tid=tr["id"]: (self.db.delete_transform(tid), self.refresh()))
            row.addWidget(rm)
            self.list_lay.addWidget(card)

    def _run(self, name: str, system_prompt: str) -> None:
        src = self.in_box.toPlainText().strip()
        if not src:
            self.status_lbl.setText("Enter or paste some text in the input box first.")
            return
        self.status_lbl.setText(f"Running '{name}'...")

        def _work() -> None:
            try:
                out = self.pipeline.run_transform(src, system_prompt)
            except Exception as exc:
                out = f"Error: {exc}"
            self._result_ready.emit(out)

        threading.Thread(target=_work, daemon=True).start()

    def _on_result(self, text: str) -> None:
        self.out_box.setPlainText(text)
        self.status_lbl.setText("Done.")
