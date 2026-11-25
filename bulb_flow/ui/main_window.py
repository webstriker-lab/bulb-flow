"""Main frameless window shell for Bulb Flow matching capture/window.png layout & ergonomics."""

from __future__ import annotations

import threading
import time

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import QAction, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ..ai_pipeline import AIPipeline
from ..audio import AudioRecorder, play_feedback_tone
from ..constants import (
    DICTATION_DEBOUNCE_MS,
    HUB_DEFAULT_HEIGHT,
    HUB_DEFAULT_WIDTH,
    HUB_MIN_HEIGHT,
    HUB_MIN_WIDTH,
    SIDEBAR_COLLAPSED_WIDTH,
    SIDEBAR_EXPANDED_WIDTH,
    TOPBAR_HEIGHT,
)
from ..database import Database
from ..floating_pill import FloatingDictationPill
from ..icons import (
    icon_bell,
    icon_brand,
    icon_dictionary,
    icon_help,
    icon_home,
    icon_key,
    icon_moon,
    icon_notes,
    icon_providers,
    icon_record,
    icon_settings,
    icon_sidebar,
    icon_snippets,
    icon_stats,
    icon_style,
    icon_sun,
    icon_transforms,
    icon_user,
)
from ..theme import build_stylesheet, get_palette
from ..win_integration import (
    GlobalHotkeyMonitor,
    detect_app_category,
    get_foreground_app_info,
    paste_text_into_active_window,
)
from .dictionary_page import DictionaryPage
from .home_page import HomePage
from .meetings_page import MeetingsPage
from .notes_page import NotesPage
from .providers_page import ProvidersPage
from .settings_page import SettingsPage
from .snippets_page import SnippetsPage
from .stats_page import StatsPage
from .style_page import StylePage
from .transforms_page import TransformsPage


class DraggableTopBar(QFrame):
    """Custom frameless title bar matching capture/window.png."""

    def __init__(self, window: QMainWindow) -> None:
        super().__init__(window)
        self._window = window
        self._drag_pos: QPoint | None = None
        self.setObjectName("TopBar")
        self.setFixedHeight(TOPBAR_HEIGHT)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            if not self._window.isMaximized():
                self._window.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()
        super().mouseDoubleClickEvent(event)


class BulbFlowMainWindow(QMainWindow):
    """Primary desktop hub window orchestrating dictation, hotkeys, floating pill, and all views."""

    _sig_start_dictation = Signal(str)
    _sig_stop_dictation = Signal()
    _sig_audio_level = Signal(float)
    _sig_dictation_done = Signal(dict, str)
    _sig_dictation_error = Signal(str)

    def __init__(self, screenshot_mode: bool = False) -> None:
        super().__init__()
        self._screenshot_mode = screenshot_mode
        self.db = Database()
        self.pipeline = AIPipeline(self.db)
        self._theme = self.db.get_setting("theme", "light")
        self._sidebar_expanded = self.db.get_bool("sidebar_expanded", False)
        self._active_page = "home"
        self._dictation_target = "global"  # global | note | meeting
        self._target_app_info = ("Bulb Flow", "")
        self._nav_buttons: dict[str, tuple[QPushButton, str, callable]] = {}

        # Frameless sleek modern window (like Wispr Flow's custom chrome)
        flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        if screenshot_mode:
            flags |= Qt.WindowType.WindowDoesNotAcceptFocus
        self.setWindowFlags(flags)
        if screenshot_mode:
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.setWindowTitle("Bulb Flow")
        self.setWindowIcon(icon_brand(32, "#1C1917"))
        self.resize(HUB_DEFAULT_WIDTH, HUB_DEFAULT_HEIGHT)
        self.setMinimumSize(HUB_MIN_WIDTH, HUB_MIN_HEIGHT)

        # Core audio & floating pill (disabled during headless screenshot capture)
        self.recorder = AudioRecorder(
            device_id=int(self.db.get_setting("mic_device_id", "-1") or "-1"),
            on_level=self._sig_audio_level.emit,
        )
        self.pill: FloatingDictationPill | None = None
        self.hotkey_monitor: GlobalHotkeyMonitor | None = None
        self.tray: QSystemTrayIcon | None = None

        self._sig_start_dictation.connect(self._begin_dictation)
        self._sig_stop_dictation.connect(self._finish_dictation)
        self._sig_audio_level.connect(self._on_audio_level)
        self._sig_dictation_done.connect(self._on_dictation_done)
        self._sig_dictation_error.connect(self._on_dictation_error)

        self._build_ui()
        self._apply_theme()

        if not screenshot_mode:
            self._setup_background_services()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("RootFrame")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 8, 8)
        outer.setSpacing(0)

        # ==================== TOP BAR ====================
        self.topbar = DraggableTopBar(self)
        tb = QHBoxLayout(self.topbar)
        tb.setContentsMargins(14, 0, 6, 0)
        tb.setSpacing(6)

        self.sidebar_toggle_btn = QPushButton()
        self.sidebar_toggle_btn.setObjectName("IconBtn")
        self.sidebar_toggle_btn.setFixedSize(30, 30)
        self.sidebar_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_toggle_btn.setToolTip("Toggle sidebar")
        self.sidebar_toggle_btn.clicked.connect(self._toggle_sidebar)
        tb.addWidget(self.sidebar_toggle_btn)

        self.profile_btn = QPushButton()
        self.profile_btn.setObjectName("IconBtn")
        self.profile_btn.setFixedSize(30, 30)
        self.profile_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.profile_btn.setToolTip("Profile & AI Stack")
        self.profile_btn.clicked.connect(lambda: self.navigate("providers"))
        tb.addWidget(self.profile_btn)

        tb.addStretch()

        self.badge_btn = QPushButton("∞ Free && Open Source")
        self.badge_btn.setObjectName("LavenderPill")
        self.badge_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.badge_btn.setToolTip("Configure Local Models, API Keys & Subscriptions")
        self.badge_btn.clicked.connect(lambda: self.navigate("providers"))
        tb.addWidget(self.badge_btn)

        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("IconBtn")
        self.theme_btn.setFixedSize(30, 30)
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.setToolTip("Toggle dark / light mode")
        self.theme_btn.clicked.connect(self._toggle_theme)
        tb.addWidget(self.theme_btn)

        self.bell_btn = QPushButton()
        self.bell_btn.setObjectName("IconBtn")
        self.bell_btn.setFixedSize(30, 30)
        self.bell_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bell_btn.setToolTip("Status & Quick Help")
        self.bell_btn.clicked.connect(self._show_quick_status)
        tb.addWidget(self.bell_btn)

        tb.addSpacing(4)

        min_btn = QPushButton("—")
        min_btn.setObjectName("WinCtrlBtn")
        min_btn.clicked.connect(self.showMinimized)
        tb.addWidget(min_btn)

        max_btn = QPushButton("□")
        max_btn.setObjectName("WinCtrlBtn")
        max_btn.clicked.connect(lambda: self.showNormal() if self.isMaximized() else self.showMaximized())
        tb.addWidget(max_btn)

        close_btn = QPushButton("×")
        close_btn.setObjectName("WinCloseBtn")
        close_btn.clicked.connect(self.close)
        tb.addWidget(close_btn)

        outer.addWidget(self.topbar)

        # ==================== BODY: SIDEBAR + CANVAS ====================
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        sb_lay = QVBoxLayout(self.sidebar)
        sb_lay.setContentsMargins(10, 12, 10, 12)
        sb_lay.setSpacing(6)

        # Brand mark at top of sidebar
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(6, 2, 4, 14)
        brand_row.setSpacing(10)
        self.brand_icon_lbl = QLabel()
        self.brand_icon_lbl.setFixedSize(24, 24)
        self.brand_text_lbl = QLabel("Bulb Flow")
        self.brand_text_lbl.setStyleSheet("font-size: 15px; font-weight: 700; background: transparent;")
        brand_row.addWidget(self.brand_icon_lbl)
        brand_row.addWidget(self.brand_text_lbl)
        brand_row.addStretch()
        sb_lay.addLayout(brand_row)

        primary_items = [
            ("home", "Home", icon_home),
            ("meetings", "Notetaker", icon_record),
            ("stats", "Insights", icon_stats),
            ("dictionary", "Dictionary", icon_dictionary),
            ("snippets", "Snippets", icon_snippets),
            ("style", "Style", icon_style),
            ("transforms", "Transforms", icon_transforms),
            ("notes", "Notes", icon_notes),
        ]
        for pid, label, icon_fn in primary_items:
            btn = self._create_nav_button(pid, label, icon_fn)
            sb_lay.addWidget(btn)

        sb_lay.addStretch()

        footer_items = [
            ("providers", "AI Providers", icon_providers),
            ("keys", "API Keys", icon_key),
            ("settings", "Settings", lambda sz, c: icon_settings(sz, c, dot_color="#E5484D")),
            ("help", "Help", icon_help),
        ]
        for pid, label, icon_fn in footer_items:
            btn = self._create_nav_button(pid, label, icon_fn)
            sb_lay.addWidget(btn)

        body.addWidget(self.sidebar)

        # Rounded Main Canvas
        self.canvas = QFrame()
        self.canvas.setObjectName("MainCanvas")
        canvas_lay = QVBoxLayout(self.canvas)
        canvas_lay.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        self.home_page = HomePage(self.db)
        self.meetings_page = MeetingsPage(self.db, self.pipeline)
        self.stats_page = StatsPage(self.db)
        self.dictionary_page = DictionaryPage(self.db)
        self.snippets_page = SnippetsPage(self.db)
        self.style_page = StylePage(self.db)
        self.transforms_page = TransformsPage(self.db, self.pipeline)
        self.notes_page = NotesPage(self.db)
        self.providers_page = ProvidersPage(self.db, self.pipeline)
        self.settings_page = SettingsPage(self.db)

        self._pages = {
            "home": self.home_page,
            "meetings": self.meetings_page,
            "stats": self.stats_page,
            "dictionary": self.dictionary_page,
            "snippets": self.snippets_page,
            "style": self.style_page,
            "transforms": self.transforms_page,
            "notes": self.notes_page,
            "providers": self.providers_page,
            "keys": self.providers_page,
            "settings": self.settings_page,
        }
        for w in [
            self.home_page,
            self.meetings_page,
            self.stats_page,
            self.dictionary_page,
            self.snippets_page,
            self.style_page,
            self.transforms_page,
            self.notes_page,
            self.providers_page,
            self.settings_page,
        ]:
            self.stack.addWidget(w)

        canvas_lay.addWidget(self.stack)
        body.addWidget(self.canvas, 1)
        outer.addLayout(body, 1)

        # Connect page signals
        self.home_page.navigate.connect(self.navigate)
        self.home_page.toggle_dictation.connect(lambda: self._toggle_dictation_button("global"))
        self.notes_page.dictate_into_note.connect(lambda: self._toggle_dictation_button("note"))
        self.meetings_page.record_meeting_toggle.connect(lambda: self._toggle_dictation_button("meeting"))
        self.providers_page.config_changed.connect(self._on_config_changed)
        self.settings_page.settings_changed.connect(self._on_config_changed)

        self._apply_sidebar_width()
        self.navigate("home")

    def _create_nav_button(self, page_id: str, label: str, icon_fn) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName("NavBtn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setIconSize(QSize(18, 18))
        btn.setFixedHeight(36)
        btn.setToolTip(label)
        if page_id == "help":
            btn.clicked.connect(self._show_help_dialog)
        else:
            btn.clicked.connect(lambda _, pid=page_id: self.navigate(pid))
        self._nav_buttons[page_id] = (btn, label, icon_fn)
        return btn

    def _apply_sidebar_width(self) -> None:
        w = SIDEBAR_EXPANDED_WIDTH if self._sidebar_expanded else SIDEBAR_COLLAPSED_WIDTH
        self.sidebar.setFixedWidth(w)
        self.brand_text_lbl.setVisible(self._sidebar_expanded)
        for pid, (btn, label, _fn) in self._nav_buttons.items():
            btn.setText(f"  {label}" if self._sidebar_expanded else "")

    def _toggle_sidebar(self) -> None:
        self._sidebar_expanded = not self._sidebar_expanded
        self.db.set_setting("sidebar_expanded", self._sidebar_expanded)
        self._apply_sidebar_width()

    def _toggle_theme(self) -> None:
        self._theme = "dark" if self._theme == "light" else "light"
        self.db.set_setting("theme", self._theme)
        self._apply_theme()

    def _apply_theme(self) -> None:
        p = get_palette(self._theme)
        self.setStyleSheet(build_stylesheet(p))
        ic = p["icon_color"]

        self.sidebar_toggle_btn.setIcon(icon_sidebar(18, ic))
        self.profile_btn.setIcon(icon_user(18, ic))
        self.theme_btn.setIcon(icon_sun(17, ic) if self._theme == "dark" else icon_moon(17, ic))
        self.bell_btn.setIcon(icon_bell(17, ic))
        self.brand_icon_lbl.setPixmap(icon_brand(24, ic).pixmap(24, 24))

        for pid, (btn, _label, icon_fn) in self._nav_buttons.items():
            btn.setIcon(icon_fn(18, ic))

    def navigate(self, page_id: str) -> None:
        target = self._pages.get(page_id, self.home_page)
        self._active_page = page_id
        self.stack.setCurrentWidget(target)

        for pid, (btn, _lbl, _fn) in self._nav_buttons.items():
            btn.setProperty("active", "true" if pid == page_id else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if page_id == "home":
            self.home_page.refresh_all()
        elif page_id == "stats":
            self.stats_page.refresh()
        elif page_id == "dictionary":
            self.dictionary_page.refresh()
        elif page_id == "snippets":
            self.snippets_page.refresh()
        elif page_id == "notes":
            self.notes_page.refresh()
        elif page_id == "meetings":
            self.meetings_page.refresh()

    # ==================== BACKGROUND SERVICES ====================
    def _setup_background_services(self) -> None:
        self.pill = FloatingDictationPill()
        self.pill.clicked_toggle.connect(lambda: self._toggle_dictation_button("global"))
        if self.db.get_bool("show_floating_pill", True):
            self.pill.show()

        self.hotkey_monitor = GlobalHotkeyMonitor(
            get_ptt_key=lambda: self.db.get_setting("ptt_hotkey", "ctrl+win"),
            get_hands_free_key=lambda: self.db.get_setting("hands_free_hotkey", "ctrl+win+space"),
            on_start_dictation=lambda mode: self._sig_start_dictation.emit(mode),
            on_stop_dictation=lambda: self._sig_stop_dictation.emit(),
        )
        self.hotkey_monitor.start()

        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(icon_brand(24, "#1C1917"), self)
            menu = QMenu()
            act_open = QAction("Open Bulb Flow", self)
            act_open.triggered.connect(self._restore_from_tray)
            act_dict = QAction("Start / Stop Dictation", self)
            act_dict.triggered.connect(lambda: self._toggle_dictation_button("global"))
            act_quit = QAction("Quit Bulb Flow", self)
            act_quit.triggered.connect(QApplication.quit)
            menu.addAction(act_open)
            menu.addAction(act_dict)
            menu.addSeparator()
            menu.addAction(act_quit)
            self.tray.setContextMenu(menu)
            self.tray.setToolTip("Bulb Flow — Free Open-Source Voice Typing")
            self.tray.activated.connect(
                lambda reason: self._restore_from_tray()
                if reason == QSystemTrayIcon.ActivationReason.Trigger
                else None
            )
            self.tray.show()

    def _restore_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_config_changed(self) -> None:
        self.home_page.refresh_all()
        if self.pill:
            if self.db.get_bool("show_floating_pill", True):
                self.pill.show()
            else:
                self.pill.hide()

    # ==================== DICTATION ENGINE ====================
    def _toggle_dictation_button(self, target: str) -> None:
        if self.recorder.is_recording:
            self._finish_dictation()
        else:
            self._dictation_target = target
            self._begin_dictation("hands_free")

    def _begin_dictation(self, mode: str) -> None:
        if self.recorder.is_recording:
            return
        if self._dictation_target == "global":
            self._target_app_info = get_foreground_app_info()
        else:
            self._target_app_info = ("Bulb Flow", self._dictation_target)

        dev_str = self.db.get_setting("mic_device_id", "-1")
        dev_id = int(dev_str) if dev_str.lstrip("-").isdigit() else -1
        self.recorder.start(device_id=dev_id)

        if self.db.get_bool("sound_feedback", True):
            play_feedback_tone("start")

        label = "Hands-free" if mode == "hands_free" else "Listening..."
        if self.pill:
            self.pill.set_listening(label)
        self.home_page.set_recording_state(True, f"Recording ({label}) — speak naturally...")
        if self._dictation_target == "meeting":
            self.meetings_page.set_recording_state(True)

    def _finish_dictation(self) -> None:
        if not self.recorder.is_recording:
            return
        wav_bytes, duration_s = self.recorder.stop()
        if self.hotkey_monitor:
            self.hotkey_monitor.set_hands_free_active(False)

        if self.db.get_bool("sound_feedback", True):
            play_feedback_tone("stop")

        target = self._dictation_target
        self._dictation_target = "global"
        self.meetings_page.set_recording_state(False)

        # Debounce accidental taps (< 500ms matching Wispr Flow DICTATION_DEBOUNCE_DELAY)
        if not wav_bytes or duration_s * 1000.0 < DICTATION_DEBOUNCE_MS:
            self.home_page.set_recording_state(False, "")
            if self.pill:
                self.pill.set_resting()
            return

        if self.pill:
            self.pill.set_processing("Transcribing & polishing...")
        self.home_page.set_recording_state(False, "Transcribing and matching your writing style...")

        app_name, win_title = self._target_app_info
        category_id = detect_app_category(app_name, win_title)

        def _worker() -> None:
            try:
                res = self.pipeline.process_dictation(
                    wav_bytes=wav_bytes,
                    duration_s=duration_s,
                    app_name=app_name,
                    window_title=win_title,
                    category_id=category_id,
                )
                self._sig_dictation_done.emit(res, target)
            except Exception as exc:
                self._sig_dictation_error.emit(str(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_audio_level(self, level: float) -> None:
        if self.pill and self.recorder.is_recording:
            self.pill.push_audio_level(level)

    def _on_dictation_done(self, res: dict, target: str) -> None:
        text = res.get("formatted_text", "").strip()
        self.home_page.set_recording_state(False, "")
        if not text:
            if self.pill:
                self.pill.set_resting()
            return

        app_name, win_title = self._target_app_info
        self.db.add_history(
            asr_text=res.get("asr_text", text),
            formatted_text=text,
            app_name=app_name,
            window_title=win_title,
            e2e_latency_ms=res.get("e2e_latency_ms", 0.0),
            duration_s=res.get("duration_s", 0.0),
            language=res.get("language", "en"),
            style_used=res.get("style_used", "formal"),
            provider_used=res.get("provider_used", ""),
        )

        if target == "note":
            self.notes_page.append_dictated_text(text)
        elif target == "meeting":
            self.meetings_page.append_transcript(text)
        else:
            if self.db.get_bool("auto_paste", True) and app_name.lower() != "bulb flow":
                paste_text_into_active_window(text, restore_clipboard=self.db.get_bool("restore_clipboard", True))
            else:
                QApplication.clipboard().setText(text)

        if self.db.get_bool("sound_feedback", True):
            play_feedback_tone("done")
        if self.pill:
            self.pill.set_done(text)
        self.home_page.refresh_all()
        self.stats_page.refresh()

    def _on_dictation_error(self, err: str) -> None:
        self.home_page.set_recording_state(False, f"Error: {err}")
        if self.pill:
            self.pill.set_error(err)

    # ==================== DIALOGS & LIFECYCLE ====================
    def _show_quick_status(self) -> None:
        stt = self.db.get_setting("stt_provider", "local_faster_whisper")
        llm = self.db.get_setting("llm_provider", "builtin_smart")
        ptt = self.db.get_setting("ptt_hotkey", "ctrl+win").upper()
        QMessageBox.information(
            self,
            "Bulb Flow Status",
            f"Bulb Flow is active and ready (unlimited words).\n\n"
            f"• Speech-to-Text: {stt}\n"
            f"• AI Polish Engine: {llm}\n"
            f"• Push-to-Talk: Hold {ptt}\n"
            f"• Database: {self.db.db_path}",
        )

    def _show_help_dialog(self) -> None:
        ptt = self.db.get_setting("ptt_hotkey", "ctrl+win").replace("+", " + ").title()
        hf = self.db.get_setting("hands_free_hotkey", "ctrl+win+space").replace("+", " + ").title()
        QMessageBox.information(
            self,
            "Bulb Flow — Quick Guide",
            f"Welcome to Bulb Flow (Free & Open Source)\n\n"
            f"1. Push-to-Talk: Hold {ptt} in any Windows app, speak, and release to auto-paste.\n"
            f"2. Hands-Free Mode: Press {hf} to start/stop longer dictations.\n"
            f"3. Free Local Models: Works offline with Faster-Whisper + Ollama / llama.cpp or built-in instant cleanup.\n"
            f"4. API Keys & Subscriptions: Open 'AI Providers' to plug in Groq (free tier), Gemini (free tier), OpenAI, Anthropic, Deepgram, OpenRouter, or Claude/Codex/Gemini CLIs.\n"
            f"5. Self-Correction: Say 'scratch that' mid-sentence to replace what you just said.",
        )

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.hotkey_monitor:
            self.hotkey_monitor.stop()
        if self.recorder.is_recording:
            self.recorder.stop()
        if self.pill:
            self.pill.close()
        if self.tray:
            self.tray.hide()
        super().closeEvent(event)
