"""Multi-backend Speech-to-Text + AI Polishing & Transform Pipeline for Bulb Flow.

Supports:
1. 100% Free Local Offline Models:
   - Faster-Whisper (CTranslate2, built-in Python library)
   - Local Whisper.cpp / OpenAI-compatible STT HTTP server
   - Built-in Smart Local Cleanup (0ms deterministic filler removal, self-correction & styling)
   - Local Ollama (localhost:11434)
   - Local llama.cpp / LM Studio server (localhost:8080 / :1234)
2. Bring-Your-Own API Keys:
   - Groq (whisper-large-v3-turbo + llama-3.3-70b-versatile)
   - OpenAI (gpt-4o-mini-transcribe / whisper-1 + gpt-4o-mini)
   - Google Gemini (gemini-2.5-flash native audio + text)
   - Deepgram (nova-3)
   - Anthropic Claude (claude-haiku-4-5 / sonnet)
   - OpenRouter (200+ free & paid models)
3. Existing Subscriptions via CLI Bridges & Proxies:
   - Claude Code CLI (`claude -p`)
   - OpenAI Codex CLI (`codex`)
   - Gemini CLI (`gemini`)
   - Custom OpenAI-compatible subscription proxy (LiteLLM / Copilot proxy)
"""

from __future__ import annotations

import base64
import io
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Any

import httpx

from .constants import TONE_OPTIONS
from .database import Database


class WhisperModelCache:
    """Lazy singleton cache for local faster-whisper models so transcription stays instant."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._key: tuple[str, str, str] | None = None
        self._model: Any = None

    def get_model(self, model_size: str = "base", device: str = "auto", compute_type: str = "int8") -> Any:
        key = (model_size, device, compute_type)
        with self._lock:
            if self._model is not None and self._key == key:
                return self._model
            from faster_whisper import WhisperModel

            dev = device
            ctype = compute_type
            if dev == "auto":
                try:
                    import torch

                    dev = "cuda" if torch.cuda.is_available() else "cpu"
                except Exception:
                    dev = "cpu"
            if dev == "cpu" and ctype == "float16":
                ctype = "int8"

            self._model = WhisperModel(model_size, device=dev, compute_type=ctype)
            self._key = key
            return self._model


_whisper_cache = WhisperModelCache()


def detect_available_local_tools() -> dict[str, Any]:
    """Probe the machine for installed local models, servers, and subscription CLIs."""
    info: dict[str, Any] = {
        "faster_whisper": False,
        "ollama_running": False,
        "ollama_models": [],
        "llamacpp_running": False,
        "claude_cli": bool(shutil.which("claude")),
        "codex_cli": bool(shutil.which("codex")),
        "gemini_cli": bool(shutil.which("gemini")),
    }
    try:
        import faster_whisper  # noqa: F401

        info["faster_whisper"] = True
    except Exception:
        pass

    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=0.9)
        if r.status_code == 200:
            data = r.json()
            info["ollama_running"] = True
            info["ollama_models"] = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        pass

    for port in (8080, 1234):
        try:
            r = httpx.get(f"http://localhost:{port}/v1/models", timeout=0.6)
            if r.status_code == 200:
                info["llamacpp_running"] = True
                break
        except Exception:
            pass

    return info


class AIPipeline:
    """Unified dictation, cleanup, transform, and meeting-summary orchestrator."""

    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------------
    # Full Dictation Flow: WAV -> STT -> Snippets -> Dictionary -> Polish
    # ------------------------------------------------------------------
    def process_dictation(
        self,
        wav_bytes: bytes,
        duration_s: float,
        app_name: str = "Bulb Flow",
        window_title: str = "",
        category_id: str = "other",
    ) -> dict[str, Any]:
        t0 = time.monotonic()
        settings = self.db.get_all_settings()
        stt_provider = settings.get("stt_provider", "local_faster_whisper")
        stt_model = settings.get("stt_model", "base")
        llm_provider = settings.get("llm_provider", "builtin_smart")
        llm_model = settings.get("llm_model", "rule-engine-v1")
        language = settings.get("language", "auto")

        styles = self.db.get_styles()
        style_cfg = styles.get(category_id, {"tone": "formal", "cleanup_level": "medium", "custom_prompt": ""})
        tone = style_cfg.get("tone", "formal")
        cleanup = style_cfg.get("cleanup_level", "medium")
        custom_style_prompt = style_cfg.get("custom_prompt", "")

        dictionary = self.db.list_dictionary()
        snippets = self.db.list_snippets()
        vocab_hints = [d["replacement"] or d["phrase"] for d in dictionary[:40]]

        # Step 1: Speech-to-Text
        raw_text, detected_lang = self.transcribe_audio(
            wav_bytes=wav_bytes,
            provider=stt_provider,
            model=stt_model,
            language=language,
            vocab_hints=vocab_hints,
            settings=settings,
        )
        raw_text = raw_text.strip()
        if not raw_text:
            return {
                "asr_text": "",
                "formatted_text": "",
                "e2e_latency_ms": (time.monotonic() - t0) * 1000.0,
                "duration_s": duration_s,
                "language": detected_lang,
                "style_used": tone,
                "provider_used": f"{stt_provider} + {llm_provider}",
            }

        # Step 2: Check exact Snippet trigger match first
        snippet_expanded = self._apply_snippets(raw_text, snippets)
        if snippet_expanded is not None:
            formatted = snippet_expanded
        else:
            # Step 3: Apply dictionary replacements
            working = self._apply_dictionary(raw_text, dictionary)

            # Step 4: AI / Smart Local Polishing & Style Matching
            if cleanup == "none" and llm_provider == "builtin_smart":
                formatted = working
            else:
                formatted = self.polish_text(
                    text=working,
                    tone=tone,
                    cleanup_level=cleanup,
                    app_name=app_name,
                    custom_prompt=custom_style_prompt or settings.get("custom_system_prompt", ""),
                    dictionary_terms=vocab_hints,
                    provider=llm_provider,
                    model=llm_model,
                    settings=settings,
                )

        latency_ms = (time.monotonic() - t0) * 1000.0
        return {
            "asr_text": raw_text,
            "formatted_text": formatted.strip(),
            "e2e_latency_ms": round(latency_ms, 1),
            "duration_s": round(duration_s, 2),
            "language": detected_lang or "en",
            "style_used": tone,
            "provider_used": f"{stt_provider} · {llm_provider}",
        }

    # ------------------------------------------------------------------
    # Speech-to-Text Backends
    # ------------------------------------------------------------------
    def transcribe_audio(
        self,
        wav_bytes: bytes,
        provider: str,
        model: str,
        language: str,
        vocab_hints: list[str],
        settings: dict[str, str],
    ) -> tuple[str, str]:
        prompt_hint = ", ".join(vocab_hints[:30]) if vocab_hints else ""
        lang_param = None if not language or language == "auto" else language

        if provider == "local_faster_whisper":
            return self._stt_faster_whisper(wav_bytes, model, lang_param, prompt_hint, settings)
        if provider == "groq_whisper":
            return self._stt_openai_compat(
                wav_bytes=wav_bytes,
                url="https://api.groq.com/openai/v1/audio/transcriptions",
                api_key=settings.get("groq_api_key", ""),
                model=model or "whisper-large-v3-turbo",
                language=lang_param,
                prompt_hint=prompt_hint,
                provider_label="Groq",
            )
        if provider == "openai_whisper":
            return self._stt_openai_compat(
                wav_bytes=wav_bytes,
                url="https://api.openai.com/v1/audio/transcriptions",
                api_key=settings.get("openai_api_key", ""),
                model=model or "gpt-4o-mini-transcribe",
                language=lang_param,
                prompt_hint=prompt_hint,
                provider_label="OpenAI",
            )
        if provider == "gemini_audio":
            return self._stt_gemini(wav_bytes, model or "gemini-2.5-flash", lang_param, prompt_hint, settings)
        if provider == "deepgram":
            return self._stt_deepgram(wav_bytes, model or "nova-3", lang_param, settings)
        if provider == "local_whisper_server":
            base = settings.get("local_whisper_url", "http://localhost:8000").rstrip("/")
            url = base if base.endswith("/audio/transcriptions") else f"{base}/v1/audio/transcriptions"
            return self._stt_openai_compat(
                wav_bytes=wav_bytes,
                url=url,
                api_key="local",
                model=model or "whisper-1",
                language=lang_param,
                prompt_hint=prompt_hint,
                provider_label="Local Whisper Server",
            )
        raise ValueError(f"Unknown STT provider: {provider}")

    def _stt_faster_whisper(
        self,
        wav_bytes: bytes,
        model_size: str,
        language: str | None,
        prompt_hint: str,
        settings: dict[str, str],
    ) -> tuple[str, str]:
        device = settings.get("whisper_device", "auto")
        compute_type = settings.get("whisper_compute_type", "int8")
        model = _whisper_cache.get_model(model_size or "base", device=device, compute_type=compute_type)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            tf.write(wav_bytes)
            tmp_path = tf.name
        try:
            segments, info = model.transcribe(
                tmp_path,
                language=language,
                initial_prompt=prompt_hint or None,
                vad_filter=True,
                beam_size=2,
            )
            text = " ".join(seg.text.strip() for seg in segments if seg.text.strip())
            return text.strip(), getattr(info, "language", language or "en") or "en"
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    def _stt_openai_compat(
        self,
        wav_bytes: bytes,
        url: str,
        api_key: str,
        model: str,
        language: str | None,
        prompt_hint: str,
        provider_label: str,
    ) -> tuple[str, str]:
        if not api_key and provider_label != "Local Whisper Server":
            raise RuntimeError(f"Missing {provider_label} API key. Add it in Providers & API Keys.")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        data: dict[str, Any] = {"model": model}
        if language:
            data["language"] = language
        if prompt_hint:
            data["prompt"] = prompt_hint
        files = {"file": ("dictation.wav", io.BytesIO(wav_bytes), "audio/wav")}
        resp = httpx.post(url, headers=headers, data=data, files=files, timeout=45.0)
        if resp.status_code >= 400:
            raise RuntimeError(f"{provider_label} STT error ({resp.status_code}): {resp.text[:240]}")
        payload = resp.json()
        return payload.get("text", "").strip(), language or "en"

    def _stt_gemini(
        self,
        wav_bytes: bytes,
        model: str,
        language: str | None,
        prompt_hint: str,
        settings: dict[str, str],
    ) -> tuple[str, str]:
        api_key = settings.get("gemini_api_key", "").strip()
        if not api_key:
            raise RuntimeError("Missing Google Gemini API key. Add it in Providers & API Keys.")
        b64 = base64.b64encode(wav_bytes).decode("ascii")
        prompt = "Transcribe the spoken audio accurately verbatim. Return ONLY the transcript text."
        if prompt_hint:
            prompt += f" Custom vocabulary hints: {prompt_hint}."
        if language:
            prompt += f" Primary language: {language}."
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        body = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "audio/wav", "data": b64}},
                    ]
                }
            ]
        }
        resp = httpx.post(url, json=body, timeout=45.0)
        if resp.status_code >= 400:
            raise RuntimeError(f"Gemini Audio error ({resp.status_code}): {resp.text[:240]}")
        data = resp.json()
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        return text, language or "en"

    def _stt_deepgram(
        self,
        wav_bytes: bytes,
        model: str,
        language: str | None,
        settings: dict[str, str],
    ) -> tuple[str, str]:
        api_key = settings.get("deepgram_api_key", "").strip()
        if not api_key:
            raise RuntimeError("Missing Deepgram API key. Add it in Providers & API Keys.")
        params = {"model": model, "smart_format": "true"}
        if language:
            params["language"] = language
        resp = httpx.post(
            "https://api.deepgram.com/v1/listen",
            params=params,
            headers={"Authorization": f"Token {api_key}", "Content-Type": "audio/wav"},
            content=wav_bytes,
            timeout=45.0,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Deepgram error ({resp.status_code}): {resp.text[:240]}")
        data = resp.json()
        text = (
            data.get("results", {})
            .get("channels", [{}])[0]
            .get("alternatives", [{}])[0]
            .get("transcript", "")
        )
        return text.strip(), language or "en"

    # ------------------------------------------------------------------
    # LLM Polishing, Style Matching, & Transforms
    # ------------------------------------------------------------------
    def polish_text(
        self,
        text: str,
        tone: str,
        cleanup_level: str,
        app_name: str,
        custom_prompt: str,
        dictionary_terms: list[str],
        provider: str,
        model: str,
        settings: dict[str, str],
    ) -> str:
        if provider == "builtin_smart" or not text.strip():
            return self.smart_local_cleanup(text, tone=tone, cleanup_level=cleanup_level)

        tone_inst = next((t["instruction"] for t in TONE_OPTIONS if t["id"] == tone), TONE_OPTIONS[0]["instruction"])
        cleanup_desc = {
            "none": "Preserve exact wording; only fix glaring spelling mistakes.",
            "light": "Remove filler words (um, uh, er) and fix basic punctuation.",
            "medium": "Remove filler words and false starts, resolve mid-sentence self-corrections (e.g. 'Tuesday, actually Wednesday' -> 'Wednesday'), and make sentences crisp and natural.",
        }.get(cleanup_level, "Remove fillers and polish clarity.")

        system_prompt = (
            "You are Bulb Flow, an ultra-accurate voice dictation editor. "
            f"Target app: {app_name}. "
            f"Writing style: {tone_inst} "
            f"Cleanup level: {cleanup_desc} "
            "Never add commentary, quotes, or explanations. Never invent facts. Return ONLY the final ready-to-paste text."
        )
        if dictionary_terms:
            system_prompt += f" Preferred spellings: {', '.join(dictionary_terms[:25])}."
        if custom_prompt.strip():
            system_prompt += f" User instructions: {custom_prompt.strip()}"

        try:
            out = self.run_llm(system_prompt=system_prompt, user_text=text, provider=provider, model=model, settings=settings)
            return out.strip() or self.smart_local_cleanup(text, tone=tone, cleanup_level=cleanup_level)
        except Exception:
            # Graceful fallback to instant local cleanup so dictation never loses the user's words
            return self.smart_local_cleanup(text, tone=tone, cleanup_level=cleanup_level)

    def run_transform(self, text: str, system_prompt: str) -> str:
        settings = self.db.get_all_settings()
        provider = settings.get("llm_provider", "builtin_smart")
        model = settings.get("llm_model", "rule-engine-v1")
        if provider == "builtin_smart":
            # Helpful deterministic fallback when user hasn't configured an LLM yet
            cleaned = self.smart_local_cleanup(text, tone="formal", cleanup_level="medium")
            if "bullet" in system_prompt.lower():
                sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
                return "\n".join(f"- {s}" for s in sents)
            if "email" in system_prompt.lower():
                return f"Hi there,\n\n{cleaned}\n\nBest regards,"
            return cleaned
        return self.run_llm(system_prompt=system_prompt, user_text=text, provider=provider, model=model, settings=settings)

    def summarize_meeting(self, transcript: str, title: str = "Meeting") -> tuple[str, str]:
        """Generate (summary, action_items) using configured LLM or local extractive fallback."""
        if not transcript.strip():
            return "No transcript recorded yet.", ""
        settings = self.db.get_all_settings()
        provider = settings.get("llm_provider", "builtin_smart")
        model = settings.get("llm_model", "rule-engine-v1")
        if provider == "builtin_smart":
            sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", transcript.strip()) if s.strip()]
            summary = " ".join(sents[:4]) if sents else transcript[:400]
            actions = [
                f"- {s}"
                for s in sents
                if any(k in s.lower() for k in ("will ", "need to", "action", "todo", "follow up", "send ", "schedule", "review", "ship"))
            ]
            return summary, "\n".join(actions[:8]) or "- Review meeting transcript and assign next steps."

        sys_prompt = (
            "You are Bulb Flow Notetaker. Summarize the meeting transcript clearly.\n"
            "Format your response in two exact sections:\n"
            "SUMMARY:\n<concise 3-5 bullet overview>\n\n"
            "ACTION ITEMS:\n<bulleted list of concrete tasks and owners>"
        )
        out = self.run_llm(
            system_prompt=sys_prompt,
            user_text=f"Meeting Title: {title}\n\nTranscript:\n{transcript}",
            provider=provider,
            model=model,
            settings=settings,
        )
        if "ACTION ITEMS:" in out:
            left, right = out.split("ACTION ITEMS:", 1)
            return left.replace("SUMMARY:", "").strip(), right.strip()
        return out.strip(), ""

    def run_llm(
        self,
        system_prompt: str,
        user_text: str,
        provider: str,
        model: str,
        settings: dict[str, str],
    ) -> str:
        if provider == "ollama":
            base = settings.get("ollama_url", "http://localhost:11434").rstrip("/")
            resp = httpx.post(
                f"{base}/api/chat",
                json={
                    "model": model or "llama3.2",
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_text},
                    ],
                },
                timeout=45.0,
            )
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "").strip()

        if provider == "llamacpp":
            base = settings.get("llamacpp_url", "http://localhost:8080").rstrip("/")
            return self._llm_openai_compat(f"{base}/v1/chat/completions", "", model or "local-model", system_prompt, user_text)

        if provider == "groq_llm":
            key = settings.get("groq_api_key", "").strip()
            if not key:
                raise RuntimeError("Missing Groq API key.")
            return self._llm_openai_compat(
                "https://api.groq.com/openai/v1/chat/completions",
                key,
                model or "llama-3.3-70b-versatile",
                system_prompt,
                user_text,
            )

        if provider == "openai_llm":
            key = settings.get("openai_api_key", "").strip()
            if not key:
                raise RuntimeError("Missing OpenAI API key.")
            return self._llm_openai_compat(
                "https://api.openai.com/v1/chat/completions",
                key,
                model or "gpt-4o-mini",
                system_prompt,
                user_text,
            )

        if provider == "openrouter_llm":
            key = settings.get("openrouter_api_key", "").strip()
            if not key:
                raise RuntimeError("Missing OpenRouter API key.")
            return self._llm_openai_compat(
                "https://openrouter.ai/api/v1/chat/completions",
                key,
                model or "meta-llama/llama-3.3-70b-instruct:free",
                system_prompt,
                user_text,
                extra_headers={"HTTP-Referer": "https://github.com/bulb-flow", "X-Title": "Bulb Flow"},
            )

        if provider == "custom_openai":
            base = settings.get("custom_openai_url", "http://localhost:4000/v1").rstrip("/")
            url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
            key = settings.get("custom_openai_key", "").strip()
            m = settings.get("custom_openai_model", "").strip() or model or "gpt-4o-mini"
            return self._llm_openai_compat(url, key, m, system_prompt, user_text)

        if provider == "gemini_llm":
            key = settings.get("gemini_api_key", "").strip()
            if not key:
                raise RuntimeError("Missing Google Gemini API key.")
            m = model or "gemini-2.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
            body = {
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": user_text}]}],
                "generationConfig": {"temperature": 0.2},
            }
            resp = httpx.post(url, json=body, timeout=45.0)
            resp.raise_for_status()
            parts = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts).strip()

        if provider == "anthropic_llm":
            key = settings.get("anthropic_api_key", "").strip()
            if not key:
                raise RuntimeError("Missing Anthropic API key.")
            resp = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model or "claude-haiku-4-5",
                    "max_tokens": 1024,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_text}],
                },
                timeout=45.0,
            )
            resp.raise_for_status()
            content = resp.json().get("content", [])
            return "".join(b.get("text", "") for b in content if b.get("type") == "text").strip()

        if provider in ("sub_claude_cli", "sub_codex_cli", "sub_gemini_cli"):
            return self._llm_cli_subscription(provider, system_prompt, user_text)

        return self.smart_local_cleanup(user_text)

    def _llm_openai_compat(
        self,
        url: str,
        api_key: str,
        model: str,
        system_prompt: str,
        user_text: str,
        extra_headers: dict[str, str] | None = None,
    ) -> str:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        if extra_headers:
            headers.update(extra_headers)
        resp = httpx.post(
            url,
            headers=headers,
            json={
                "model": model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
            },
            timeout=45.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def _llm_cli_subscription(self, provider: str, system_prompt: str, user_text: str) -> str:
        combined = f"{system_prompt}\n\nInput:\n{user_text}"
        if provider == "sub_claude_cli":
            exe = shutil.which("claude")
            if not exe:
                raise RuntimeError("`claude` CLI not found on PATH. Install Claude Code to use your Claude subscription.")
            cmd = [exe, "-p", combined]
        elif provider == "sub_codex_cli":
            exe = shutil.which("codex")
            if not exe:
                raise RuntimeError("`codex` CLI not found on PATH. Install Codex CLI to use your ChatGPT subscription.")
            cmd = [exe, "exec", combined]
        else:
            exe = shutil.which("gemini")
            if not exe:
                raise RuntimeError("`gemini` CLI not found on PATH. Install Gemini CLI to use your Google AI subscription.")
            cmd = [exe, "-p", combined]

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45, check=False)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or f"{provider} exited with {proc.returncode}")
        return proc.stdout.strip()

    # ------------------------------------------------------------------
    # Smart Local Deterministic Cleanup + Dictionary + Snippets
    # ------------------------------------------------------------------
    def _apply_snippets(self, raw_text: str, snippets: list[dict[str, Any]]) -> str | None:
        normalized = re.sub(r"[^\w\s]", "", raw_text).strip().lower()
        for sn in snippets:
            trig = re.sub(r"[^\w\s]", "", sn["trigger_phrase"]).strip().lower()
            if trig and normalized == trig:
                self.db.increment_snippet_usage(sn["trigger_phrase"])
                return sn["expansion_text"]
        return None

    def _apply_dictionary(self, text: str, dictionary: list[dict[str, Any]]) -> str:
        result = text
        for entry in dictionary:
            phrase = entry["phrase"].strip()
            repl = (entry["replacement"] or phrase).strip()
            if not phrase:
                continue
            pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
            if pattern.search(result):
                result = pattern.sub(repl, result)
                self.db.increment_dictionary_usage(phrase)
        return result

    @staticmethod
    def smart_local_cleanup(text: str, tone: str = "formal", cleanup_level: str = "medium") -> str:
        """Fast 0ms offline cleanup: filler removal, self-corrections, and style formatting."""
        s = text.strip()
        if not s:
            return ""

        if cleanup_level in ("light", "medium"):
            # Handle explicit spoken self-corrections ("... scratch that ...")
            for marker in ("scratch that", "never mind", "nevermind", "disregard that"):
                idx = s.lower().rfind(marker)
                if idx != -1:
                    after = s[idx + len(marker) :].lstrip(" ,.-")
                    if after:
                        s = after
                    else:
                        # Drop the last clause before the marker
                        before = s[:idx].rstrip(" ,.-")
                        parts = re.split(r"[.!?]+", before)
                        s = ". ".join(p.strip() for p in parts[:-1] if p.strip())

            # Remove common speech fillers
            s = re.sub(r"\b(?:um+|uh+|er+|ah+|hmm+)\b[,\s]*", "", s, flags=re.IGNORECASE)
            if cleanup_level == "medium":
                s = re.sub(r"\b(?:you know|i mean)\b[,\s]*", "", s, flags=re.IGNORECASE)
                # Deduplicate stuttered repeated words ("the the" -> "the")
                s = re.sub(r"\b(\w+)\s+\1\b", r"\1", s, flags=re.IGNORECASE)

            # Collapse whitespace and clean orphan punctuation
            s = re.sub(r"\s+([,.;:!?])", r"\1", s)
            s = re.sub(r"\s{2,}", " ", s).strip()

        if not s:
            return ""

        # Apply tone styling
        if tone == "very_casual":
            s = s.lower()
            s = re.sub(r"[.]+$", "", s)
        elif tone == "casual":
            s = s[0].upper() + s[1:]
            if s.endswith(".") and not s.endswith("..."):
                s = s[:-1]
        elif tone == "excited":
            s = s[0].upper() + s[1:]
            if s[-1] not in ".!?":
                s += "!"
            elif s.endswith("."):
                s = s[:-1] + "!"
        else:  # formal
            s = s[0].upper() + s[1:]
            if s[-1] not in ".!?":
                s += "."

        return s

    # ------------------------------------------------------------------
    # Live Connection Tester for Providers UI
    # ------------------------------------------------------------------
    def test_connection(self) -> tuple[bool, str]:
        settings = self.db.get_all_settings()
        llm_provider = settings.get("llm_provider", "builtin_smart")
        llm_model = settings.get("llm_model", "rule-engine-v1")
        stt_provider = settings.get("stt_provider", "local_faster_whisper")

        # Validate STT readiness
        if stt_provider == "local_faster_whisper":
            try:
                import faster_whisper  # noqa: F401
            except ImportError:
                return False, "faster-whisper is not installed. Run `pip install faster-whisper`."
        elif stt_provider == "groq_whisper" and not settings.get("groq_api_key"):
            return False, "Groq STT selected, but Groq API key is empty."
        elif stt_provider == "openai_whisper" and not settings.get("openai_api_key"):
            return False, "OpenAI STT selected, but OpenAI API key is empty."
        elif stt_provider == "gemini_audio" and not settings.get("gemini_api_key"):
            return False, "Gemini Audio selected, but Google Gemini API key is empty."
        elif stt_provider == "deepgram" and not settings.get("deepgram_api_key"):
            return False, "Deepgram selected, but Deepgram API key is empty."

        if llm_provider == "builtin_smart":
            return True, f"Ready! STT: {stt_provider} · Cleanup: Built-in Smart Local Engine (0ms offline)."

        try:
            reply = self.run_llm(
                system_prompt="Reply with exactly: OK",
                user_text="Health check",
                provider=llm_provider,
                model=llm_model,
                settings=settings,
            )
            return True, f"Connected! STT: {stt_provider} · LLM ({llm_provider}): {reply[:60]}"
        except Exception as exc:
            return False, f"Connection failed ({llm_provider}): {exc}"
