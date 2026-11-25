"""Native Windows OS integrations: global hotkeys, foreground app detection, clipboard-safe auto-paste."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import threading
import time
from typing import Callable

from .constants import (
    APP_CATEGORIES,
    CLIPBOARD_PRIVACY_FORMATS,
    CLIPBOARD_RESTORE_DELAY_MS,
    DICTATION_DEBOUNCE_MS,
    HOLD_THRESHOLD_MS,
    PASTE_COMPLETE_SLEEP_MS,
)

_IS_WIN = os.name == "nt"
_user32 = ctypes.windll.user32 if _IS_WIN else None
_kernel32 = ctypes.windll.kernel32 if _IS_WIN else None

# Virtual key codes
VK_CONTROL = 0x11
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_MENU = 0x12
VK_LMENU = 0xA4
VK_RMENU = 0xA5
VK_SHIFT = 0x10
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_SPACE = 0x20
VK_F8 = 0x77
VK_F9 = 0x78
VK_F10 = 0x79
VK_D = 0x44
VK_V = 0x56

# Clipboard / SendInput constants
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002

# Window positioning constants
HWND_BOTTOM = 1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("padding", ctypes.c_byte * 32)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _INPUT_UNION)]


def _is_vk_down(vk: int) -> bool:
    if not _user32:
        return False
    return bool(_user32.GetAsyncKeyState(vk) & 0x8000)


def is_combo_down(combo_id: str) -> bool:
    """Evaluate whether a preset hotkey combination is currently held."""
    if not _IS_WIN:
        return False
    c = (combo_id or "").lower().strip()
    if c == "ctrl+win":
        return _is_vk_down(VK_CONTROL) and (_is_vk_down(VK_LWIN) or _is_vk_down(VK_RWIN))
    if c == "ctrl+win+space":
        return _is_vk_down(VK_CONTROL) and (_is_vk_down(VK_LWIN) or _is_vk_down(VK_RWIN)) and _is_vk_down(VK_SPACE)
    if c == "ralt":
        return _is_vk_down(VK_RMENU) and not _is_vk_down(VK_CONTROL)
    if c == "ctrl+shift+space":
        return _is_vk_down(VK_CONTROL) and _is_vk_down(VK_SHIFT) and _is_vk_down(VK_SPACE)
    if c == "ctrl+shift+d":
        return _is_vk_down(VK_CONTROL) and _is_vk_down(VK_SHIFT) and _is_vk_down(VK_D)
    if c == "alt+space":
        return _is_vk_down(VK_MENU) and _is_vk_down(VK_SPACE)
    if c == "f8":
        return _is_vk_down(VK_F8)
    if c == "f9":
        return _is_vk_down(VK_F9)
    if c == "f10":
        return _is_vk_down(VK_F10)
    return False


def get_foreground_app_info() -> tuple[str, str]:
    """Return (friendly_app_name, window_title) of the currently focused Windows app."""
    if not _IS_WIN or not _user32 or not _kernel32:
        return "Bulb Flow", ""
    try:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return "Desktop", ""
        length = _user32.GetWindowTextLengthW(hwnd)
        title_buf = ctypes.create_unicode_buffer(max(length + 1, 256))
        _user32.GetWindowTextW(hwnd, title_buf, len(title_buf))
        title = title_buf.value.strip()

        pid = wintypes.DWORD(0)
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc_name = ""
        if pid.value:
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            h_proc = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
            if h_proc:
                try:
                    exe_buf = ctypes.create_unicode_buffer(512)
                    size = wintypes.DWORD(len(exe_buf))
                    if _kernel32.QueryFullProcessImageNameW(h_proc, 0, exe_buf, ctypes.byref(size)):
                        proc_name = os.path.splitext(os.path.basename(exe_buf.value))[0]
                finally:
                    _kernel32.CloseHandle(h_proc)

        friendly = _prettify_app_name(proc_name, title)
        return friendly, title
    except Exception:
        return "Desktop", ""


def _prettify_app_name(proc_name: str, title: str) -> str:
    low_proc = proc_name.lower()
    low_title = title.lower()
    if "gmail" in low_title:
        return "Gmail"
    if "outlook" in low_proc or "outlook" in low_title:
        return "Microsoft Outlook"
    if "slack" in low_proc or "slack" in low_title:
        return "Slack"
    if "teams" in low_proc or "microsoft teams" in low_title:
        return "Microsoft Teams"
    if "whatsapp" in low_proc or "whatsapp" in low_title:
        return "WhatsApp"
    if "discord" in low_proc or "discord" in low_title:
        return "Discord"
    if "telegram" in low_proc:
        return "Telegram"
    if low_proc in ("code", "code - insiders"):
        return "VS Code"
    if "cursor" in low_proc:
        return "Cursor"
    if "notion" in low_proc or "notion" in low_title:
        return "Notion"
    if "chrome" in low_proc:
        return "Chrome"
    if "msedge" in low_proc:
        return "Edge"
    if "firefox" in low_proc:
        return "Firefox"
    if "notepad" in low_proc:
        return "Notepad"
    if "winword" in low_proc:
        return "Microsoft Word"
    return proc_name or "Desktop"


def detect_app_category(app_name: str, window_title: str = "") -> str:
    """Map an active application + title to one of the Bulb Flow style category IDs."""
    haystack = f"{app_name} {window_title}".lower()
    for cat in APP_CATEGORIES:
        for kw in cat["keywords"]:
            if kw in haystack:
                return cat["id"]
    return "other"


def _get_clipboard_text() -> str | None:
    if not _IS_WIN or not _user32 or not _kernel32:
        return None
    if not _user32.OpenClipboard(None):
        return None
    try:
        if not _user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            return None
        handle = _user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        ptr = _kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            return ctypes.wstring_at(ptr)
        finally:
            _kernel32.GlobalUnlock(handle)
    finally:
        _user32.CloseClipboard()


def _get_clipboard_sequence_number() -> int:
    if not _IS_WIN or not _user32:
        return 0
    try:
        return int(_user32.GetClipboardSequenceNumber())
    except Exception:
        return 0


def _set_clipboard_dword_format(fmt_name: str, dword_val: int = 0) -> None:
    """Attach a Windows clipboard privacy marker (Wispr Flow Helper.exe fn 0x14032a5a0)."""
    if not _IS_WIN or not _user32 or not _kernel32:
        return
    try:
        fmt_id = _user32.RegisterClipboardFormatW(fmt_name)
        if not fmt_id:
            return
        h_mem = _kernel32.GlobalAlloc(GMEM_MOVEABLE, 4)
        if not h_mem:
            return
        ptr = _kernel32.GlobalLock(h_mem)
        if not ptr:
            _kernel32.GlobalFree(h_mem)
            return
        try:
            ctypes.memmove(ptr, ctypes.c_uint32(dword_val).value.to_bytes(4, "little"), 4)
        finally:
            _kernel32.GlobalUnlock(h_mem)
        _user32.SetClipboardData(fmt_id, h_mem)
    except Exception:
        pass


def set_clipboard_text(text: str, mark_private: bool = False) -> bool:
    if not _IS_WIN or not _user32 or not _kernel32:
        return False
    for _ in range(5):
        if _user32.OpenClipboard(None):
            break
        time.sleep(0.02)
    else:
        return False
    try:
        _user32.EmptyClipboard()
        encoded = (text + "\x00").encode("utf-16-le")
        h_mem = _kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        if not h_mem:
            return False
        ptr = _kernel32.GlobalLock(h_mem)
        if not ptr:
            _kernel32.GlobalFree(h_mem)
            return False
        try:
            ctypes.memmove(ptr, encoded, len(encoded))
        finally:
            _kernel32.GlobalUnlock(h_mem)
        _user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        if mark_private:
            for fmt_name in CLIPBOARD_PRIVACY_FORMATS:
                _set_clipboard_dword_format(fmt_name, 0)
        return True
    finally:
        _user32.CloseClipboard()


def _send_ctrl_v() -> None:
    if not _IS_WIN or not _user32:
        return
    # Release any still-held modifiers (Win/Alt/Shift) before Ctrl+V (Helper.exe 0x11e0bdc)
    seq: list[tuple[int, int]] = []
    for mod_vk in (VK_LWIN, VK_RWIN, VK_MENU, VK_LMENU, VK_RMENU, VK_SHIFT):
        if _is_vk_down(mod_vk):
            seq.append((mod_vk, KEYEVENTF_KEYUP))
    seq.extend([
        (VK_CONTROL, 0),
        (VK_V, 0),
        (VK_V, KEYEVENTF_KEYUP),
        (VK_CONTROL, KEYEVENTF_KEYUP),
    ])
    inputs = (INPUT * len(seq))()
    for i, (vk, flags) in enumerate(seq):
        inputs[i].type = INPUT_KEYBOARD
        inputs[i].union.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags, time=0, dwExtraInfo=None)
    _user32.SendInput(len(seq), ctypes.byref(inputs), ctypes.sizeof(INPUT))


def paste_text_into_active_window(text: str, restore_clipboard: bool = True) -> bool:
    """Copy text privately to clipboard, send Ctrl+V, verify seq, and safely restore previous clipboard.

    Matches Wispr Flow Helper.exe mechanics:
    - Privacy clipboard formats (fn 0x14032a5a0 / 0x14032c450) prevent Win+V history pollution
    - Sequence verification before restore (fn 0x14031d060) skips restore if user copied new text
    - 50ms post-paste sleep (fn 0x140327e50 @ 0x140328058)
    """
    if not text:
        return False
    previous = _get_clipboard_text() if restore_clipboard else None
    seq_before = _get_clipboard_sequence_number()
    if not set_clipboard_text(text, mark_private=True):
        return False
    seq_after_write = _get_clipboard_sequence_number()
    if seq_after_write == seq_before:
        # Retry write once if clipboard sequence did not advance
        time.sleep(0.02)
        if not set_clipboard_text(text, mark_private=True):
            return False
        seq_after_write = _get_clipboard_sequence_number()

    time.sleep(PASTE_COMPLETE_SLEEP_MS / 1000.0)
    _send_ctrl_v()
    time.sleep(PASTE_COMPLETE_SLEEP_MS / 1000.0)

    if restore_clipboard and previous is not None:
        expected_seq = seq_after_write

        def _restore() -> None:
            time.sleep(CLIPBOARD_RESTORE_DELAY_MS / 1000.0)
            # Only restore if clipboard was not modified by user or another app (fn 0x14031d060)
            if _get_clipboard_sequence_number() == expected_seq:
                set_clipboard_text(previous, mark_private=True)

        threading.Thread(target=_restore, daemon=True).start()
    return True


def lower_window_without_activating(hwnd: int) -> None:
    """Push window behind all other windows without stealing focus (Windows screenshot mode)."""
    if not _IS_WIN or not _user32 or not hwnd:
        return
    try:
        _user32.SetWindowPos(
            ctypes.c_void_p(hwnd),
            ctypes.c_void_p(HWND_BOTTOM),
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
        )
    except Exception:
        pass


class GlobalHotkeyMonitor:
    """Lightweight Windows global hotkey watcher supporting Push-to-Talk & Hands-Free modes.

    Implements Wispr Flow's gesture timings:
    - Hold threshold: 350ms (SCRATCHPAD_PTT_DELAY_MS)
    - Double-tap window / debounce: 500ms (DICTATION_DEBOUNCE_DELAY)
    """

    def __init__(
        self,
        get_ptt_key: Callable[[], str],
        get_hands_free_key: Callable[[], str],
        on_start_dictation: Callable[[str], None],
        on_stop_dictation: Callable[[], None],
    ):
        self._get_ptt = get_ptt_key
        self._get_hf = get_hands_free_key
        self._on_start = on_start_dictation
        self._on_stop = on_stop_dictation
        self._running = False
        self._thread: threading.Thread | None = None
        self._hands_free_active = False

    def start(self) -> None:
        if not _IS_WIN or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def set_hands_free_active(self, active: bool) -> None:
        self._hands_free_active = active

    def _loop(self) -> None:
        ptt_was_down = False
        ptt_down_since = 0.0
        ptt_dictating = False
        last_tap_release = 0.0
        hf_was_down = False

        while self._running:
            try:
                now = time.monotonic()
                ptt_key = self._get_ptt()
                hf_key = self._get_hf()

                # Check hands-free dedicated chord first (takes precedence over PTT if overlapping)
                if hf_key and hf_key != "double_tap":
                    hf_down = is_combo_down(hf_key)
                    if hf_down and not hf_was_down:
                        if self._hands_free_active or ptt_dictating:
                            self._hands_free_active = False
                            ptt_dictating = False
                            self._on_stop()
                        else:
                            self._hands_free_active = True
                            self._on_start("hands_free")
                    hf_was_down = hf_down
                    if hf_down:
                        ptt_was_down = False
                        time.sleep(0.025)
                        continue

                # Push-to-Talk & optional double-tap hands-free
                ptt_down = is_combo_down(ptt_key)
                if ptt_down and not ptt_was_down:
                    ptt_down_since = now
                    if self._hands_free_active:
                        # Single press cancels hands-free recording
                        self._hands_free_active = False
                        self._on_stop()
                    elif hf_key == "double_tap" and (now - last_tap_release) * 1000.0 <= DICTATION_DEBOUNCE_MS:
                        self._hands_free_active = True
                        self._on_start("hands_free")
                    else:
                        ptt_dictating = True
                        self._on_start("ptt")
                elif not ptt_down and ptt_was_down:
                    held_ms = (now - ptt_down_since) * 1000.0
                    if ptt_dictating:
                        ptt_dictating = False
                        if held_ms < HOLD_THRESHOLD_MS and hf_key == "double_tap":
                            last_tap_release = now
                        self._on_stop()

                ptt_was_down = ptt_down
            except Exception:
                pass
            time.sleep(0.02)
