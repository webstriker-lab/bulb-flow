"""Unified AI Providers hub: Local Offline Models, API Keys (BYOK), and Subscriptions/CLI Bridges."""

from __future__ import annotations

import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
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

from ..ai_pipeline import AIPipeline, detect_available_local_tools
from ..constants import LLM_PROVIDERS, STT_PROVIDERS
from ..database import Database


class ProvidersPage(QWidget):
    """Configure Speech-to-Text and Polishing LLM across Local, API Keys, and Subscriptions."""

    config_changed = Signal()
    _test_result = Signal(bool, str)
    _probe_result = Signal(dict)

    def __init__(self, db: Database, pipeline: AIPipeline, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self.pipeline = pipeline
        self._key_inputs: dict[str, QLineEdit] = {}
        self._test_result.connect(self._on_test_result)
        self._probe_result.connect(self._on_probe_result)
        self._build_ui()
        self.probe_local_environment()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(42, 32, 42, 32)
        lay.setSpacing(20)

        # Header
        hdr = QHBoxLayout()
        title_col = QVBoxLayout()
        t = QLabel("AI Providers, API Keys & Local Models")
        t.setObjectName("PageTitle")
        sub = QLabel(
            "Zero paywalls, zero word limits. Mix and match local offline models, your own API keys, or existing AI subscriptions."
        )
        sub.setObjectName("SecondaryLabel")
        title_col.addWidget(t)
        title_col.addWidget(sub)
        hdr.addLayout(title_col, 1)

        self.test_btn = QPushButton("Test Active Pipeline")
        self.test_btn.setObjectName("AmberCTA")
        self.test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_btn.clicked.connect(self._run_connection_test)
        hdr.addWidget(self.test_btn)
        lay.addLayout(hdr)

        self.status_banner = QLabel("")
        self.status_banner.setObjectName("BadgeTeal")
        self.status_banner.setWordWrap(True)
        self.status_banner.setVisible(False)
        lay.addWidget(self.status_banner)

        # ================= SECTION 1: ACTIVE PIPELINE =================
        pipe_card = QFrame()
        pipe_card.setObjectName("RightCard")
        pl = QVBoxLayout(pipe_card)
        pl.setContentsMargins(20, 18, 20, 18)
        pl.setSpacing(14)

        pt = QLabel("Active Dictation Pipeline")
        pt.setObjectName("SectionTitle")
        pl.addWidget(pt)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        grid.addWidget(QLabel("Speech-to-Text Engine"), 0, 0)
        grid.addWidget(QLabel("Speech Model"), 0, 1)

        self.stt_combo = QComboBox()
        for p in STT_PROVIDERS:
            self.stt_combo.addItem(p["name"], p["id"])
        self.stt_model_combo = QComboBox()
        self.stt_model_combo.setEditable(True)

        grid.addWidget(self.stt_combo, 1, 0)
        grid.addWidget(self.stt_model_combo, 1, 1)

        grid.addWidget(QLabel("AI Polish & Style Engine"), 2, 0)
        grid.addWidget(QLabel("Polish / Transform Model"), 2, 1)

        self.llm_combo = QComboBox()
        for p in LLM_PROVIDERS:
            self.llm_combo.addItem(p["name"], p["id"])
        self.llm_model_combo = QComboBox()
        self.llm_model_combo.setEditable(True)

        grid.addWidget(self.llm_combo, 3, 0)
        grid.addWidget(self.llm_model_combo, 3, 1)

        grid.addWidget(QLabel("Spoken Language"), 4, 0)
        self.lang_combo = QComboBox()
        for code, label in [
            ("auto", "Auto-detect (100+ languages)"),
            ("en", "English"),
            ("es", "Spanish"),
            ("fr", "French"),
            ("de", "German"),
            ("hi", "Hindi"),
            ("ja", "Japanese"),
            ("zh", "Chinese"),
            ("pt", "Portuguese"),
        ]:
            self.lang_combo.addItem(label, code)
        grid.addWidget(self.lang_combo, 5, 0)

        self.pipe_desc = QLabel("")
        self.pipe_desc.setObjectName("SecondaryLabel")
        self.pipe_desc.setWordWrap(True)
        grid.addWidget(self.pipe_desc, 5, 1)

        pl.addLayout(grid)
        lay.addWidget(pipe_card)

        # ================= SECTION 2: LOCAL MODELS (100% FREE) =================
        local_card = QFrame()
        local_card.setObjectName("SurfaceCard")
        ll = QVBoxLayout(local_card)
        ll.setContentsMargins(20, 18, 20, 18)
        ll.setSpacing(12)

        l_top = QHBoxLayout()
        lt = QLabel("Local Models (100% Free & Offline)")
        lt.setObjectName("SectionTitle")
        l_top.addWidget(lt)
        l_top.addStretch()
        rescan_btn = QPushButton("Rescan Local Models")
        rescan_btn.setObjectName("SecondaryBtn")
        rescan_btn.clicked.connect(self.probe_local_environment)
        l_top.addWidget(rescan_btn)
        ll.addLayout(l_top)

        self.local_badges_lbl = QLabel("Scanning local Faster-Whisper, Ollama, llama.cpp & CLIs...")
        self.local_badges_lbl.setObjectName("SecondaryLabel")
        self.local_badges_lbl.setWordWrap(True)
        ll.addWidget(self.local_badges_lbl)

        lg = QGridLayout()
        lg.setHorizontalSpacing(14)
        lg.setVerticalSpacing(10)

        lg.addWidget(QLabel("Faster-Whisper Device"), 0, 0)
        self.whisper_dev = QComboBox()
        for v in ("auto", "cpu", "cuda"):
            self.whisper_dev.addItem(v)
        self.whisper_dev.setCurrentText(self.db.get_setting("whisper_device", "auto"))
        self.whisper_dev.currentTextChanged.connect(lambda v: self._save("whisper_device", v))
        lg.addWidget(self.whisper_dev, 0, 1)

        lg.addWidget(QLabel("Compute Precision"), 0, 2)
        self.whisper_comp = QComboBox()
        for v in ("int8", "float16", "float32"):
            self.whisper_comp.addItem(v)
        self.whisper_comp.setCurrentText(self.db.get_setting("whisper_compute_type", "int8"))
        self.whisper_comp.currentTextChanged.connect(lambda v: self._save("whisper_compute_type", v))
        lg.addWidget(self.whisper_comp, 0, 3)

        lg.addWidget(QLabel("Ollama Server URL"), 1, 0)
        self.ollama_url = QLineEdit(self.db.get_setting("ollama_url", "http://localhost:11434"))
        self.ollama_url.editingFinished.connect(lambda: self._save("ollama_url", self.ollama_url.text().strip()))
        lg.addWidget(self.ollama_url, 1, 1)

        lg.addWidget(QLabel("llama.cpp / LM Studio URL"), 1, 2)
        self.llama_url = QLineEdit(self.db.get_setting("llamacpp_url", "http://localhost:8080"))
        self.llama_url.editingFinished.connect(lambda: self._save("llamacpp_url", self.llama_url.text().strip()))
        lg.addWidget(self.llama_url, 1, 3)

        lg.addWidget(QLabel("Local Whisper HTTP URL"), 2, 0)
        self.local_whisper_url = QLineEdit(self.db.get_setting("local_whisper_url", "http://localhost:8000"))
        self.local_whisper_url.editingFinished.connect(
            lambda: self._save("local_whisper_url", self.local_whisper_url.text().strip())
        )
        lg.addWidget(self.local_whisper_url, 2, 1)

        ll.addLayout(lg)
        lay.addWidget(local_card)

        # ================= SECTION 3: API KEYS (BYOK) =================
        keys_card = QFrame()
        keys_card.setObjectName("SurfaceCard")
        kl = QVBoxLayout(keys_card)
        kl.setContentsMargins(20, 18, 20, 18)
        kl.setSpacing(12)

        kt = QLabel("API Keys (Stored Locally Only)")
        kt.setObjectName("SectionTitle")
        ksub = QLabel(
            "Keys are saved exclusively in your local SQLite database and sent only directly to the provider you choose."
        )
        ksub.setObjectName("SecondaryLabel")
        kl.addWidget(kt)
        kl.addWidget(ksub)

        kg = QGridLayout()
        kg.setHorizontalSpacing(12)
        kg.setVerticalSpacing(10)
        key_specs = [
            ("groq_api_key", "Groq API Key", "gsk_... (Free tier for Whisper-v3-Turbo & Llama 3.3)"),
            ("openai_api_key", "OpenAI API Key", "sk-... (gpt-4o-mini-transcribe, whisper-1, gpt-4o-mini)"),
            ("gemini_api_key", "Google Gemini API Key", "AIza... (Free tier native audio + text)"),
            ("anthropic_api_key", "Anthropic API Key", "sk-ant-... (Claude Haiku / Sonnet prose polish)"),
            ("deepgram_api_key", "Deepgram API Key", "Token for Nova-3 speech-to-text"),
            ("openrouter_api_key", "OpenRouter API Key", "sk-or-... (200+ free & frontier models)"),
        ]
        for row_idx, (setting_key, label, placeholder) in enumerate(key_specs):
            kg.addWidget(QLabel(label), row_idx, 0)
            inp = QLineEdit(self.db.get_setting(setting_key, ""))
            inp.setPlaceholderText(placeholder)
            inp.setEchoMode(QLineEdit.EchoMode.Password)
            inp.editingFinished.connect(lambda k=setting_key, box=inp: self._save(k, box.text().strip()))
            kg.addWidget(inp, row_idx, 1)
            self._key_inputs[setting_key] = inp

            eye = QPushButton("Show")
            eye.setObjectName("SecondaryBtn")
            eye.setFixedWidth(64)
            eye.clicked.connect(lambda _, box=inp, btn=eye: self._toggle_echo(box, btn))
            kg.addWidget(eye, row_idx, 2)

        kl.addLayout(kg)
        lay.addWidget(keys_card)

        # ================= SECTION 4: SUBSCRIPTIONS & PROXIES =================
        sub_card = QFrame()
        sub_card.setObjectName("SurfaceCard")
        sl = QVBoxLayout(sub_card)
        sl.setContentsMargins(20, 18, 20, 18)
        sl.setSpacing(12)

        st = QLabel("Subscriptions, CLI Bridges & Custom Proxies")
        st.setObjectName("SectionTitle")
        ssub = QLabel(
            "Already paying for Claude Pro/Max, ChatGPT Plus/Pro, Google AI, or a LiteLLM/Copilot proxy? "
            "Select a CLI bridge above or configure any OpenAI-compatible subscription proxy below."
        )
        ssub.setObjectName("SecondaryLabel")
        ssub.setWordWrap(True)
        sl.addWidget(st)
        sl.addWidget(ssub)

        self.cli_status_lbl = QLabel("")
        self.cli_status_lbl.setObjectName("BadgeLavender")
        sl.addWidget(self.cli_status_lbl)

        sg = QGridLayout()
        sg.setHorizontalSpacing(14)
        sg.setVerticalSpacing(10)

        sg.addWidget(QLabel("Custom Endpoint Base URL"), 0, 0)
        self.custom_url = QLineEdit(self.db.get_setting("custom_openai_url", "http://localhost:4000/v1"))
        self.custom_url.editingFinished.connect(lambda: self._save("custom_openai_url", self.custom_url.text().strip()))
        sg.addWidget(self.custom_url, 0, 1)

        sg.addWidget(QLabel("Custom Model Name"), 1, 0)
        self.custom_model = QLineEdit(self.db.get_setting("custom_openai_model", "gpt-4o-mini"))
        self.custom_model.editingFinished.connect(
            lambda: self._save("custom_openai_model", self.custom_model.text().strip())
        )
        sg.addWidget(self.custom_model, 1, 1)

        sg.addWidget(QLabel("Optional Bearer Token"), 2, 0)
        self.custom_key = QLineEdit(self.db.get_setting("custom_openai_key", ""))
        self.custom_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.custom_key.editingFinished.connect(lambda: self._save("custom_openai_key", self.custom_key.text().strip()))
        sg.addWidget(self.custom_key, 2, 1)

        sl.addLayout(sg)
        lay.addWidget(sub_card)
        lay.addStretch()

        scroll.setWidget(body)
        outer.addWidget(scroll)

        # Hydrate selections & wire signals
        self._load_pipeline_combos()
        self.stt_combo.currentIndexChanged.connect(self._on_stt_provider_changed)
        self.stt_model_combo.currentTextChanged.connect(lambda v: self._save("stt_model", v.strip()))
        self.llm_combo.currentIndexChanged.connect(self._on_llm_provider_changed)
        self.llm_model_combo.currentTextChanged.connect(lambda v: self._save("llm_model", v.strip()))
        self.lang_combo.currentIndexChanged.connect(
            lambda: self._save("language", self.lang_combo.currentData() or "auto")
        )

    def _load_pipeline_combos(self) -> None:
        cur_stt = self.db.get_setting("stt_provider", "local_faster_whisper")
        idx = self.stt_combo.findData(cur_stt)
        if idx >= 0:
            self.stt_combo.setCurrentIndex(idx)
        self._populate_stt_models(cur_stt, self.db.get_setting("stt_model", "base"))

        cur_llm = self.db.get_setting("llm_provider", "builtin_smart")
        idx2 = self.llm_combo.findData(cur_llm)
        if idx2 >= 0:
            self.llm_combo.setCurrentIndex(idx2)
        self._populate_llm_models(cur_llm, self.db.get_setting("llm_model", "rule-engine-v1"))

        cur_lang = self.db.get_setting("language", "auto")
        idx3 = self.lang_combo.findData(cur_lang)
        if idx3 >= 0:
            self.lang_combo.setCurrentIndex(idx3)
        self._update_desc()

    def _populate_stt_models(self, pid: str, selected: str = "") -> None:
        self.stt_model_combo.blockSignals(True)
        self.stt_model_combo.clear()
        spec = next((p for p in STT_PROVIDERS if p["id"] == pid), STT_PROVIDERS[0])
        for m in spec["models"]:
            self.stt_model_combo.addItem(m)
        target = selected or spec["default_model"]
        self.stt_model_combo.setCurrentText(target)
        self.stt_model_combo.blockSignals(False)

    def _populate_llm_models(self, pid: str, selected: str = "") -> None:
        self.llm_model_combo.blockSignals(True)
        self.llm_model_combo.clear()
        spec = next((p for p in LLM_PROVIDERS if p["id"] == pid), LLM_PROVIDERS[0])
        for m in spec["models"]:
            self.llm_model_combo.addItem(m)
        target = selected or spec["default_model"]
        self.llm_model_combo.setCurrentText(target)
        self.llm_model_combo.blockSignals(False)

    def _on_stt_provider_changed(self) -> None:
        pid = self.stt_combo.currentData()
        spec = next((p for p in STT_PROVIDERS if p["id"] == pid), STT_PROVIDERS[0])
        self._save("stt_provider", pid)
        self._populate_stt_models(pid, spec["default_model"])
        self._save("stt_model", spec["default_model"])
        self._update_desc()

    def _on_llm_provider_changed(self) -> None:
        pid = self.llm_combo.currentData()
        spec = next((p for p in LLM_PROVIDERS if p["id"] == pid), LLM_PROVIDERS[0])
        self._save("llm_provider", pid)
        self._populate_llm_models(pid, spec["default_model"])
        self._save("llm_model", spec["default_model"])
        self._update_desc()

    def _update_desc(self) -> None:
        stt_spec = next((p for p in STT_PROVIDERS if p["id"] == self.stt_combo.currentData()), STT_PROVIDERS[0])
        llm_spec = next((p for p in LLM_PROVIDERS if p["id"] == self.llm_combo.currentData()), LLM_PROVIDERS[0])
        self.pipe_desc.setText(f"STT: {stt_spec['desc']}\nPolish: {llm_spec['desc']}")

    def _save(self, key: str, value: str) -> None:
        self.db.set_setting(key, value)
        self.config_changed.emit()

    @staticmethod
    def _toggle_echo(box: QLineEdit, btn: QPushButton) -> None:
        if box.echoMode() == QLineEdit.EchoMode.Password:
            box.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setText("Hide")
        else:
            box.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setText("Show")

    def probe_local_environment(self) -> None:
        def _work() -> None:
            info = detect_available_local_tools()
            self._probe_result.emit(info)

        threading.Thread(target=_work, daemon=True).start()

    def _on_probe_result(self, info: dict) -> None:
        fw = "Installed & Ready" if info.get("faster_whisper") else "Not installed"
        ol_models = info.get("ollama_models") or []
        ol = f"Running ({len(ol_models)} models: {', '.join(ol_models[:4])})" if info.get("ollama_running") else "Not running"
        lc = "Detected on localhost" if info.get("llamacpp_running") else "Not running"
        self.local_badges_lbl.setText(f"Faster-Whisper: {fw}   ·   Ollama: {ol}   ·   llama.cpp / LM Studio: {lc}")

        clis = []
        clis.append(f"Claude CLI: {'Ready' if info.get('claude_cli') else 'Not found'}")
        clis.append(f"Codex CLI: {'Ready' if info.get('codex_cli') else 'Not found'}")
        clis.append(f"Gemini CLI: {'Ready' if info.get('gemini_cli') else 'Not found'}")
        self.cli_status_lbl.setText("   ·   ".join(clis))

        # If Ollama is currently selected and has discovered models, add them to dropdown
        if ol_models and self.llm_combo.currentData() == "ollama":
            cur = self.llm_model_combo.currentText()
            self.llm_model_combo.blockSignals(True)
            self.llm_model_combo.clear()
            for m in ol_models:
                self.llm_model_combo.addItem(m)
            self.llm_model_combo.setCurrentText(cur if cur in ol_models else ol_models[0])
            self.llm_model_combo.blockSignals(False)

    def _run_connection_test(self) -> None:
        # Flush any focused edits first
        for k, box in self._key_inputs.items():
            self.db.set_setting(k, box.text().strip())
        self.test_btn.setEnabled(False)
        self.test_btn.setText("Testing...")
        self.status_banner.setText("Testing active STT + LLM pipeline...")
        self.status_banner.setVisible(True)

        def _work() -> None:
            ok, msg = self.pipeline.test_connection()
            self._test_result.emit(ok, msg)

        threading.Thread(target=_work, daemon=True).start()

    def _on_test_result(self, ok: bool, msg: str) -> None:
        self.test_btn.setEnabled(True)
        self.test_btn.setText("Test Active Pipeline")
        self.status_banner.setObjectName("BadgeTeal" if ok else "BadgeLavender")
        self.status_banner.style().unpolish(self.status_banner)
        self.status_banner.style().polish(self.status_banner)
        self.status_banner.setText(("✓ " if ok else "⚠ ") + msg)
        self.status_banner.setVisible(True)
