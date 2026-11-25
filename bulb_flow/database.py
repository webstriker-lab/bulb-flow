"""SQLite persistence layer for Bulb Flow (mirrors Wispr Flow tables locally)."""

from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from .constants import APP_CATEGORIES, DEFAULT_TRANSFORMS


def get_data_dir() -> Path:
    base = os.environ.get("BULB_FLOW_DATA_DIR")
    if base:
        p = Path(base)
    else:
        appdata = os.environ.get("APPDATA") or str(Path.home())
        p = Path(appdata) / "BulbFlow"
    p.mkdir(parents=True, exist_ok=True)
    return p


class Database:
    """Thread-safe SQLite store for history, dictionary, snippets, notes, meetings, styles & settings."""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else get_data_dir() / "bulb_flow.sqlite"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._seed_defaults()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS history (
                    id TEXT PRIMARY KEY,
                    asr_text TEXT NOT NULL DEFAULT '',
                    formatted_text TEXT NOT NULL DEFAULT '',
                    edited_text TEXT,
                    timestamp TEXT NOT NULL,
                    app_name TEXT NOT NULL DEFAULT 'Bulb Flow',
                    window_title TEXT NOT NULL DEFAULT '',
                    e2e_latency_ms REAL NOT NULL DEFAULT 0,
                    duration_s REAL NOT NULL DEFAULT 0,
                    num_words INTEGER NOT NULL DEFAULT 0,
                    language TEXT NOT NULL DEFAULT 'en',
                    style_used TEXT NOT NULL DEFAULT 'formal',
                    provider_used TEXT NOT NULL DEFAULT 'local_faster_whisper',
                    archived INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_history_ts ON history(timestamp DESC);

                CREATE TABLE IF NOT EXISTS dictionary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phrase TEXT NOT NULL UNIQUE,
                    replacement TEXT NOT NULL DEFAULT '',
                    frequency_used INTEGER NOT NULL DEFAULT 0,
                    manually_added INTEGER NOT NULL DEFAULT 1,
                    starred INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS snippets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trigger_phrase TEXT NOT NULL UNIQUE,
                    expansion_text TEXT NOT NULL,
                    usage_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS styles (
                    category_id TEXT PRIMARY KEY,
                    tone TEXT NOT NULL DEFAULT 'formal',
                    cleanup_level TEXT NOT NULL DEFAULT 'medium',
                    custom_prompt TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS transforms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    system_prompt TEXT NOT NULL,
                    usage_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT 'Untitled Note',
                    content TEXT NOT NULL DEFAULT '',
                    pinned INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS meetings (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT 'New Meeting',
                    transcript TEXT NOT NULL DEFAULT '',
                    summary TEXT NOT NULL DEFAULT '',
                    action_items TEXT NOT NULL DEFAULT '',
                    participants TEXT NOT NULL DEFAULT '',
                    duration_s REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                """
            )

    def _seed_defaults(self) -> None:
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        user_name = os.environ.get("USERNAME") or os.environ.get("USER") or "Friend"
        if " " in user_name:
            user_name = user_name.split()[0]

        default_settings = {
            "user_name": user_name,
            "theme": "light",
            "sidebar_expanded": "false",
            "show_hero_banner": "true",
            "show_voice_card": "true",
            "stt_provider": "local_faster_whisper",
            "stt_model": "base",
            "llm_provider": "builtin_smart",
            "llm_model": "rule-engine-v1",
            "language": "auto",
            "ptt_hotkey": "ctrl+win",
            "hands_free_hotkey": "ctrl+win+space",
            "auto_paste": "true",
            "restore_clipboard": "true",
            "show_floating_pill": "true",
            "pill_dock_edge": "bottom",
            "sound_feedback": "true",
            "mic_device_id": "-1",
            "whisper_device": "auto",
            "whisper_compute_type": "int8",
            "ollama_url": "http://localhost:11434",
            "llamacpp_url": "http://localhost:8080",
            "local_whisper_url": "http://localhost:8000",
            "custom_openai_url": "http://localhost:4000/v1",
            "custom_openai_key": "",
            "custom_openai_model": "gpt-4o-mini",
            "groq_api_key": os.environ.get("GROQ_API_KEY", ""),
            "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
            "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
            "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
            "deepgram_api_key": os.environ.get("DEEPGRAM_API_KEY", ""),
            "openrouter_api_key": os.environ.get("OPENROUTER_API_KEY", ""),
            "custom_system_prompt": "",
        }
        with self._connect() as conn:
            for k, v in default_settings.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
                    (k, str(v)),
                )
            for cat in APP_CATEGORIES:
                conn.execute(
                    "INSERT OR IGNORE INTO styles(category_id, tone, cleanup_level, custom_prompt) VALUES (?, ?, ?, '')",
                    (cat["id"], cat["default_tone"], cat["default_cleanup"]),
                )
            for name, prompt in DEFAULT_TRANSFORMS:
                conn.execute(
                    "INSERT OR IGNORE INTO transforms(name, system_prompt, usage_count, created_at) VALUES (?, ?, 0, ?)",
                    (name, prompt, now),
                )

            # Seed helpful starter dictionary & snippets if completely empty
            if conn.execute("SELECT COUNT(*) FROM dictionary").fetchone()[0] == 0:
                starter_dict = [
                    ("Bulb Flow", "Bulb Flow", 1),
                    ("Ollama", "Ollama", 1),
                    ("Faster-Whisper", "Faster-Whisper", 0),
                    ("Kubernetes", "Kubernetes", 0),
                ]
                for phrase, repl, star in starter_dict:
                    conn.execute(
                        "INSERT OR IGNORE INTO dictionary(phrase, replacement, frequency_used, manually_added, starred, created_at) VALUES (?, ?, 0, 1, ?, ?)",
                        (phrase, repl, star, now),
                    )
            if conn.execute("SELECT COUNT(*) FROM snippets").fetchone()[0] == 0:
                starter_snippets = [
                    ("my calendar", "https://cal.com/your-link"),
                    ("sign off", "Best regards,\n" + user_name),
                    ("standup template", "Yesterday:\n- \nToday:\n- \nBlockers:\n- None"),
                ]
                for trig, exp in starter_snippets:
                    conn.execute(
                        "INSERT OR IGNORE INTO snippets(trigger_phrase, expansion_text, usage_count, created_at) VALUES (?, ?, 0, ?)",
                        (trig, exp, now),
                    )

    # --- Settings ---
    def get_setting(self, key: str, default: str = "") -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def get_bool(self, key: str, default: bool = False) -> bool:
        val = self.get_setting(key, "true" if default else "false").lower()
        return val in ("1", "true", "yes", "on")

    def set_setting(self, key: str, value: Any) -> None:
        sval = "true" if value is True else ("false" if value is False else str(value))
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, sval),
            )

    def get_all_settings(self) -> dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            return {r["key"]: r["value"] for r in rows}

    # --- History ---
    def add_history(
        self,
        asr_text: str,
        formatted_text: str,
        app_name: str = "Bulb Flow",
        window_title: str = "",
        e2e_latency_ms: float = 0.0,
        duration_s: float = 0.0,
        language: str = "en",
        style_used: str = "formal",
        provider_used: str = "local_faster_whisper",
    ) -> dict[str, Any]:
        entry_id = str(uuid.uuid4())
        now = dt.datetime.now().isoformat(timespec="seconds")
        words = len((formatted_text or asr_text).split())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO history(
                    id, asr_text, formatted_text, timestamp, app_name, window_title,
                    e2e_latency_ms, duration_s, num_words, language, style_used, provider_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    asr_text,
                    formatted_text,
                    now,
                    app_name,
                    window_title,
                    e2e_latency_ms,
                    duration_s,
                    words,
                    language,
                    style_used,
                    provider_used,
                ),
            )
        return {
            "id": entry_id,
            "asr_text": asr_text,
            "formatted_text": formatted_text,
            "timestamp": now,
            "app_name": app_name,
            "window_title": window_title,
            "e2e_latency_ms": e2e_latency_ms,
            "duration_s": duration_s,
            "num_words": words,
            "language": language,
            "style_used": style_used,
            "provider_used": provider_used,
        }

    def list_history(self, search: str = "", limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if search.strip():
                q = f"%{search.strip()}%"
                rows = conn.execute(
                    """
                    SELECT * FROM history
                    WHERE archived = 0 AND (formatted_text LIKE ? OR asr_text LIKE ? OR app_name LIKE ?)
                    ORDER BY timestamp DESC LIMIT ?
                    """,
                    (q, q, q, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM history WHERE archived = 0 ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]

    def update_history_text(self, entry_id: str, new_text: str) -> None:
        words = len(new_text.split())
        with self._connect() as conn:
            conn.execute(
                "UPDATE history SET formatted_text = ?, edited_text = ?, num_words = ? WHERE id = ?",
                (new_text, new_text, words, entry_id),
            )

    def delete_history(self, entry_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM history WHERE id = ?", (entry_id,))

    def clear_history(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM history")

    # --- Stats ---
    def get_stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            agg = conn.execute(
                """
                SELECT
                    COALESCE(SUM(num_words), 0) AS total_words,
                    COALESCE(SUM(duration_s), 0.0) AS total_duration_s,
                    COUNT(*) AS total_dictations,
                    COALESCE(AVG(NULLIF(e2e_latency_ms, 0)), 0.0) AS avg_latency_ms
                FROM history WHERE archived = 0
                """
            ).fetchone()
            total_words = int(agg["total_words"] or 0)
            total_dur = float(agg["total_duration_s"] or 0.0)
            total_dictations = int(agg["total_dictations"] or 0)
            avg_latency_ms = float(agg["avg_latency_ms"] or 0.0)
            wpm = int(round(total_words / (total_dur / 60.0))) if total_dur >= 1.0 and total_words > 0 else 0

            # Compute day streak
            day_rows = conn.execute(
                "SELECT DISTINCT substr(timestamp, 1, 10) AS d FROM history WHERE archived = 0 ORDER BY d DESC"
            ).fetchall()
            days = []
            for r in day_rows:
                try:
                    days.append(dt.date.fromisoformat(r["d"]))
                except ValueError:
                    pass

            streak = 0
            if days:
                today = dt.date.today()
                expected = today if days[0] == today else (today - dt.timedelta(days=1) if days[0] == today - dt.timedelta(days=1) else None)
                if expected:
                    for d in days:
                        if d == expected:
                            streak += 1
                            expected -= dt.timedelta(days=1)
                        elif d < expected:
                            break

            # Per-app breakdown
            app_rows = conn.execute(
                """
                SELECT app_name, SUM(num_words) AS words, COUNT(*) AS cnt
                FROM history WHERE archived = 0
                GROUP BY app_name ORDER BY words DESC LIMIT 8
                """
            ).fetchall()

            # Last 7 days daily word counts
            daily = []
            today = dt.date.today()
            for i in range(6, -1, -1):
                day = today - dt.timedelta(days=i)
                ds = day.isoformat()
                row = conn.execute(
                    "SELECT COALESCE(SUM(num_words), 0) AS w FROM history WHERE archived = 0 AND substr(timestamp, 1, 10) = ?",
                    (ds,),
                ).fetchone()
                daily.append((day.strftime("%a"), int(row["w"] or 0)))

            # Time saved vs 45 WPM typing
            typing_minutes = total_words / 45.0
            speaking_minutes = total_dur / 60.0
            saved_minutes = max(0.0, typing_minutes - speaking_minutes)

            return {
                "total_words": total_words,
                "total_duration_s": total_dur,
                "total_dictations": total_dictations,
                "wpm": wpm,
                "day_streak": streak,
                "avg_latency_ms": avg_latency_ms,
                "saved_minutes": saved_minutes,
                "top_apps": [dict(r) for r in app_rows],
                "daily_words": daily,
            }

    # --- Dictionary ---
    def list_dictionary(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM dictionary ORDER BY starred DESC, frequency_used DESC, phrase ASC"
            ).fetchall()
            return [dict(r) for r in rows]

    def upsert_dictionary(self, phrase: str, replacement: str = "", starred: bool = False) -> None:
        now = dt.datetime.now().isoformat(timespec="seconds")
        phrase = phrase.strip()
        if not phrase:
            return
        repl = replacement.strip() or phrase
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO dictionary(phrase, replacement, frequency_used, manually_added, starred, created_at)
                VALUES (?, ?, 0, 1, ?, ?)
                ON CONFLICT(phrase) DO UPDATE SET replacement=excluded.replacement, starred=excluded.starred
                """,
                (phrase, repl, 1 if starred else 0, now),
            )

    def toggle_dictionary_star(self, entry_id: int) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE dictionary SET starred = CASE WHEN starred=1 THEN 0 ELSE 1 END WHERE id = ?", (entry_id,))

    def increment_dictionary_usage(self, phrase: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE dictionary SET frequency_used = frequency_used + 1 WHERE phrase = ?", (phrase,))

    def delete_dictionary(self, entry_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM dictionary WHERE id = ?", (entry_id,))

    # --- Snippets ---
    def list_snippets(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM snippets ORDER BY usage_count DESC, trigger_phrase ASC").fetchall()
            return [dict(r) for r in rows]

    def upsert_snippet(self, trigger_phrase: str, expansion_text: str) -> None:
        now = dt.datetime.now().isoformat(timespec="seconds")
        trig = trigger_phrase.strip()
        if not trig:
            return
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO snippets(trigger_phrase, expansion_text, usage_count, created_at)
                VALUES (?, ?, 0, ?)
                ON CONFLICT(trigger_phrase) DO UPDATE SET expansion_text=excluded.expansion_text
                """,
                (trig, expansion_text, now),
            )

    def increment_snippet_usage(self, trigger_phrase: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE snippets SET usage_count = usage_count + 1 WHERE trigger_phrase = ?", (trigger_phrase,))

    def delete_snippet(self, snippet_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM snippets WHERE id = ?", (snippet_id,))

    # --- Styles ---
    def get_styles(self) -> dict[str, dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM styles").fetchall()
            return {r["category_id"]: dict(r) for r in rows}

    def set_style(self, category_id: str, tone: str, cleanup_level: str, custom_prompt: str = "") -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO styles(category_id, tone, cleanup_level, custom_prompt)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(category_id) DO UPDATE SET
                    tone=excluded.tone,
                    cleanup_level=excluded.cleanup_level,
                    custom_prompt=excluded.custom_prompt
                """,
                (category_id, tone, cleanup_level, custom_prompt),
            )

    # --- Transforms ---
    def list_transforms(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM transforms ORDER BY id ASC").fetchall()
            return [dict(r) for r in rows]

    def upsert_transform(self, name: str, system_prompt: str) -> None:
        now = dt.datetime.now().isoformat(timespec="seconds")
        name = name.strip()
        if not name:
            return
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO transforms(name, system_prompt, usage_count, created_at)
                VALUES (?, ?, 0, ?)
                ON CONFLICT(name) DO UPDATE SET system_prompt=excluded.system_prompt
                """,
                (name, system_prompt.strip(), now),
            )

    def delete_transform(self, tid: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM transforms WHERE id = ?", (tid,))

    # --- Notes ---
    def list_notes(self, search: str = "") -> list[dict[str, Any]]:
        with self._connect() as conn:
            if search.strip():
                q = f"%{search.strip()}%"
                rows = conn.execute(
                    "SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? ORDER BY pinned DESC, updated_at DESC",
                    (q, q),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM notes ORDER BY pinned DESC, updated_at DESC").fetchall()
            return [dict(r) for r in rows]

    def save_note(self, title: str, content: str, note_id: str | None = None, pinned: bool = False) -> str:
        now = dt.datetime.now().isoformat(timespec="seconds")
        nid = note_id or str(uuid.uuid4())
        with self._connect() as conn:
            exists = conn.execute("SELECT 1 FROM notes WHERE id = ?", (nid,)).fetchone()
            if exists:
                conn.execute(
                    "UPDATE notes SET title=?, content=?, pinned=?, updated_at=? WHERE id=?",
                    (title.strip() or "Untitled Note", content, 1 if pinned else 0, now, nid),
                )
            else:
                conn.execute(
                    "INSERT INTO notes(id, title, content, pinned, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (nid, title.strip() or "Untitled Note", content, 1 if pinned else 0, now, now),
                )
        return nid

    def delete_note(self, note_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))

    # --- Meetings ---
    def list_meetings(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM meetings ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def save_meeting(
        self,
        title: str,
        transcript: str,
        summary: str = "",
        action_items: str = "",
        participants: str = "",
        duration_s: float = 0.0,
        meeting_id: str | None = None,
    ) -> str:
        now = dt.datetime.now().isoformat(timespec="seconds")
        mid = meeting_id or str(uuid.uuid4())
        with self._connect() as conn:
            exists = conn.execute("SELECT 1 FROM meetings WHERE id = ?", (mid,)).fetchone()
            if exists:
                conn.execute(
                    """
                    UPDATE meetings SET title=?, transcript=?, summary=?, action_items=?, participants=?, duration_s=?
                    WHERE id=?
                    """,
                    (title.strip() or "Meeting Note", transcript, summary, action_items, participants, duration_s, mid),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO meetings(id, title, transcript, summary, action_items, participants, duration_s, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (mid, title.strip() or "Meeting Note", transcript, summary, action_items, participants, duration_s, now),
                )
        return mid

    def delete_meeting(self, meeting_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))

    # --- Export / Backup ---
    def export_json(self) -> str:
        payload = {
            "app": "Bulb Flow",
            "exported_at": dt.datetime.now().isoformat(timespec="seconds"),
            "history": self.list_history(limit=10000),
            "dictionary": self.list_dictionary(),
            "snippets": self.list_snippets(),
            "styles": self.get_styles(),
            "transforms": self.list_transforms(),
            "notes": self.list_notes(),
            "meetings": self.list_meetings(),
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)
