"""Settings & Help page: Hotkeys, Microphone, Auto-Paste, Floating Pill, Privacy & Export."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..audio import list_input_devices
from ..constants import HANDS_FREE_PRESETS, HOTKEY_PRESETS
from ..database import Database


class SettingsPage(QWidget):
    """Global hotkeys, microphone selection, behavior toggles, and local data export."""

    settings_changed = Signal()

    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(42, 32, 42, 32)
        lay.setSpacing(20)

        t = QLabel("Settings & Shortcuts")
        t.setObjectName("PageTitle")
        sub = QLabel("Customize global Windows hotkeys, audio input, floating dictation pill, and privacy.")
        sub.setObjectName("SecondaryLabel")
        lay.addWidget(t)
        lay.addWidget(sub)

        # Shortcuts & Audio card
        card1 = QFrame()
        card1.setObjectName("RightCard")
        g = QGridLayout(card1)
        g.setContentsMargins(20, 18, 20, 18)
        g.setHorizontalSpacing(16)
        g.setVerticalSpacing(12)

        g.addWidget(QLabel("Your Display Name"), 0, 0)
        self.name_in = QLineEdit(self.db.get_setting("user_name", "Friend"))
        self.name_in.editingFinished.connect(lambda: self._save("user_name", self.name_in.text().strip() or "Friend"))
        g.addWidget(self.name_in, 0, 1)

        g.addWidget(QLabel("Push-to-Talk Hotkey (Hold)"), 1, 0)
        self.ptt_combo = QComboBox()
        for cid, label in HOTKEY_PRESETS:
            self.ptt_combo.addItem(label, cid)
        idx = self.ptt_combo.findData(self.db.get_setting("ptt_hotkey", "ctrl+win"))
        if idx >= 0:
            self.ptt_combo.setCurrentIndex(idx)
        self.ptt_combo.currentIndexChanged.connect(lambda: self._save("ptt_hotkey", self.ptt_combo.currentData()))
        g.addWidget(self.ptt_combo, 1, 1)

        g.addWidget(QLabel("Hands-Free Toggle Hotkey"), 2, 0)
        self.hf_combo = QComboBox()
        for cid, label in HANDS_FREE_PRESETS:
            self.hf_combo.addItem(label, cid)
        idx2 = self.hf_combo.findData(self.db.get_setting("hands_free_hotkey", "ctrl+win+space"))
        if idx2 >= 0:
            self.hf_combo.setCurrentIndex(idx2)
        self.hf_combo.currentIndexChanged.connect(lambda: self._save("hands_free_hotkey", self.hf_combo.currentData()))
        g.addWidget(self.hf_combo, 2, 1)

        g.addWidget(QLabel("Microphone Input Device"), 3, 0)
        self.mic_combo = QComboBox()
        self._populate_mics()
        self.mic_combo.currentIndexChanged.connect(
            lambda: self._save("mic_device_id", str(self.mic_combo.currentData()))
        )
        g.addWidget(self.mic_combo, 3, 1)
        lay.addWidget(card1)

        # Behavior toggles
        card2 = QFrame()
        card2.setObjectName("SurfaceCard")
        bl = QVBoxLayout(card2)
        bl.setContentsMargins(20, 18, 20, 18)
        bl.setSpacing(10)
        bt = QLabel("Dictation Behavior")
        bt.setObjectName("SectionTitle")
        bl.addWidget(bt)

        self.auto_paste_cb = QCheckBox("Automatically paste transcript into the active window (Ctrl+V)")
        self.auto_paste_cb.setChecked(self.db.get_bool("auto_paste", True))
        self.auto_paste_cb.toggled.connect(lambda v: self._save("auto_paste", v))
        bl.addWidget(self.auto_paste_cb)

        self.restore_cb = QCheckBox("Preserve & restore my previous clipboard contents after pasting")
        self.restore_cb.setChecked(self.db.get_bool("restore_clipboard", True))
        self.restore_cb.toggled.connect(lambda v: self._save("restore_clipboard", v))
        bl.addWidget(self.restore_cb)

        self.pill_cb = QCheckBox("Show always-on-top floating dictation pill at bottom of screen")
        self.pill_cb.setChecked(self.db.get_bool("show_floating_pill", True))
        self.pill_cb.toggled.connect(lambda v: self._save("show_floating_pill", v))
        bl.addWidget(self.pill_cb)

        self.sound_cb = QCheckBox("Play subtle start/stop audio feedback tones")
        self.sound_cb.setChecked(self.db.get_bool("sound_feedback", True))
        self.sound_cb.toggled.connect(lambda v: self._save("sound_feedback", v))
        bl.addWidget(self.sound_cb)
        lay.addWidget(card2)

        # Privacy & Data
        card3 = QFrame()
        card3.setObjectName("SurfaceCard")
        dl = QVBoxLayout(card3)
        dl.setContentsMargins(20, 18, 20, 18)
        dl.setSpacing(10)
        dt_lbl = QLabel("Privacy, Data & Open Source")
        dt_lbl.setObjectName("SectionTitle")
        dl.addWidget(dt_lbl)
        dsub = QLabel(
            f"Local SQLite database: {self.db.db_path}\n"
            "Bulb Flow never sends telemetry and never locks features behind a subscription."
        )
        dsub.setObjectName("SecondaryLabel")
        dsub.setWordWrap(True)
        dl.addWidget(dsub)

        btn_row = QHBoxLayout()
        export_btn = QPushButton("Export All Data (JSON)")
        export_btn.setObjectName("SecondaryBtn")
        export_btn.clicked.connect(self._export_data)
        btn_row.addWidget(export_btn)

        clear_btn = QPushButton("Clear Dictation History")
        clear_btn.setObjectName("SecondaryBtn")
        clear_btn.clicked.connect(self._clear_history)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        dl.addLayout(btn_row)
        lay.addWidget(card3)

        lay.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)

    def _populate_mics(self) -> None:
        self.mic_combo.clear()
        saved = self.db.get_setting("mic_device_id", "-1")
        for dev_id, name in list_input_devices():
            self.mic_combo.addItem(name, dev_id)
        idx = self.mic_combo.findData(int(saved) if saved.lstrip("-").isdigit() else -1)
        if idx >= 0:
            self.mic_combo.setCurrentIndex(idx)

    def _save(self, key: str, value) -> None:
        self.db.set_setting(key, value)
        self.settings_changed.emit()

    def _export_data(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Bulb Flow Backup", "bulb_flow_backup.json", "JSON (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.db.export_json())
        QMessageBox.information(self, "Export Complete", f"Saved backup to:\n{path}")

    def _clear_history(self) -> None:
        res = QMessageBox.question(
            self,
            "Clear Dictation History",
            "Delete all saved dictation transcripts? Dictionary, snippets, notes, and settings will be kept.",
        )
        if res == QMessageBox.StandardButton.Yes:
            self.db.clear_history()
            self.settings_changed.emit()
