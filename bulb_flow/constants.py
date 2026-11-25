"""Core constants, design tokens, and provider presets for Bulb Flow."""

# Window geometry (from Wispr Flow main bundle)
HUB_DEFAULT_WIDTH = 1350
HUB_DEFAULT_HEIGHT = 850
HUB_MIN_WIDTH = 1140
HUB_MIN_HEIGHT = 750
SIDEBAR_COLLAPSED_WIDTH = 56
SIDEBAR_EXPANDED_WIDTH = 216
TOPBAR_HEIGHT = 44

# Floating pill geometry (from Wispr Flow status bundle)
PILL_REST_WIDTH = 36
PILL_REST_HEIGHT = 6
PILL_ACTIVE_WIDTH = 260
PILL_ACTIVE_HEIGHT = 44
PILL_EXPANDED_WIDTH = 416
PILL_EXPANDED_HEIGHT = 48
PILL_DOCK_MARGIN_BOTTOM = 18

# Audio & timing constants (from Wispr Flow main bundle & Wispr Flow Helper.exe)
RECORDING_SAMPLE_RATE = 16000
RECORDING_CHANNELS = 1
RECORDING_BITS_PER_SAMPLE = 16
CHUNK_DURATION_MS = 40
HOLD_THRESHOLD_MS = 350
DICTATION_DEBOUNCE_MS = 500
DICTATION_WARNING_TIMEOUT_MS = 19 * 60 * 1000
DICTATION_MAX_TIMEOUT_MS = 20 * 60 * 1000
PASTE_COMPLETE_SLEEP_MS = 50       # Ghidra FUN_140327e50 (Thread.Sleep(0x32))
CLIPBOARD_RESTORE_DELAY_MS = 250   # Wispr Flow Helper.exe str 0x11fa544
PASTE_DELIMITER_REGEX = r"\{\{[A-Z]+\}\}"  # Ghidra FUN_1403530e0 @ 0x14121ac98
CLIPBOARD_PRIVACY_FORMATS = (      # Ghidra FUN_14032a5a0 / FUN_14032c450
    "ExcludeClipboardContentFromMonitorProcessing",
    "CanIncludeInClipboardHistory",
    "CanUploadToCloudClipboard",
    "Clipboard Viewer Ignore",
)
TYPING_BASELINE_WPM = 45

# App categories & automatic detection rules
APP_CATEGORIES = [
    {
        "id": "personal",
        "label": "Personal messages",
        "apps": ["WhatsApp", "Messages", "Telegram", "Discord", "Signal", "WeChat"],
        "keywords": ["whatsapp", "telegram", "discord", "signal", "wechat", "messenger", "messages"],
        "default_tone": "casual",
        "default_cleanup": "light",
    },
    {
        "id": "work",
        "label": "Work messages",
        "apps": ["Slack", "Microsoft Teams", "Mattermost", "Zoom Chat"],
        "keywords": ["slack", "teams", "ms-teams", "mattermost", "zoom"],
        "default_tone": "casual",
        "default_cleanup": "medium",
    },
    {
        "id": "email",
        "label": "Email",
        "apps": ["Gmail", "Microsoft Outlook", "Superhuman", "Thunderbird"],
        "keywords": ["outlook", "gmail", "mail", "superhuman", "thunderbird", "proton mail"],
        "default_tone": "formal",
        "default_cleanup": "medium",
    },
    {
        "id": "code",
        "label": "Code & IDE",
        "apps": ["VS Code", "Cursor", "Windsurf", "GitHub Desktop", "Devin", "Replit", "ChatGPT", "Claude", "Terminal"],
        "keywords": [
            "code", "cursor", "windsurf", "pycharm", "idea", "windowsterminal",
            "powershell", "cmd", "antigravity", "githubdesktop", "github.com",
            "devin", "replit", "v0.dev", "chatgpt", "claude.ai", "gemini.google.com",
        ],
        "default_tone": "formal",
        "default_cleanup": "light",
    },
    {
        "id": "other",
        "label": "Other",
        "apps": ["Notion", "Google Docs", "Word", "Browser", "Any App"],
        "keywords": [],
        "default_tone": "formal",
        "default_cleanup": "medium",
    },
]

TONE_OPTIONS = [
    {
        "id": "formal",
        "title": "Formal.",
        "subtitle": "Caps + Punctuation",
        "sample": {
            "personal": "Hey, are you free for lunch today? Let's do 12:00 if that works for you.",
            "work": "Hey team, if you're free at 3 PM, let's sync on the Q3 release notes.",
            "email": "Hi Alex,\n\nThanks for sending over the proposal. I'll review it and follow up by tomorrow.\n\nBest,\nAshwath",
            "code": "Refactor the audio buffer handler to prevent clipping on 16kHz mono streams.",
            "other": "So far, everything is running smoothly after a full night of testing.",
        },
        "instruction": "Use proper capitalization, clean grammar, and complete punctuation. Professional and polished.",
    },
    {
        "id": "casual",
        "title": "Casual",
        "subtitle": "Natural & relaxed",
        "sample": {
            "personal": "Hey, free for lunch today? Let's do 12 if that works for you",
            "work": "Hey, if you're free at 3 let's quickly chat about the great results",
            "email": "Hi Alex,\n\nThanks for sending the proposal — I'll take a look and get back to you tomorrow.\n\nThanks,\nAshwath",
            "code": "Let's refactor the audio buffer handler so it doesn't clip on 16kHz streams",
            "other": "So far everything is running smoothly after a full night of testing",
        },
        "instruction": "Keep it natural, friendly, and conversational with light punctuation. Avoid overly stiff phrasing.",
    },
    {
        "id": "very_casual",
        "title": "very casual",
        "subtitle": "Lowercase, minimal",
        "sample": {
            "personal": "hey free for lunch today lets do 12 if that works for u",
            "work": "hey if ur free at 3 lets chat about the results",
            "email": "hi alex thanks for the proposal, ill check it out and reply tomorrow",
            "code": "refactor audio buffer handler to stop clipping on 16khz",
            "other": "so far everything is running great after testing all night",
        },
        "instruction": "Use mostly lowercase, minimal punctuation, very relaxed texting style.",
    },
    {
        "id": "excited",
        "title": "Excited!",
        "subtitle": "More exclamations",
        "sample": {
            "personal": "Hey! Are you free for lunch today? Let's do 12 if that works for you!",
            "work": "Hey! If you're free at 3, let's chat about these awesome results!",
            "email": "Hi Alex!\n\nThanks so much for sending over the proposal! I'll review it right away and follow up tomorrow!\n\nBest,\nAshwath",
            "code": "Let's ship this audio buffer refactor — it makes 16kHz capture rock solid!",
            "other": "So far, everything is running amazingly well after a full night of testing!",
        },
        "instruction": "Use an upbeat, enthusiastic tone with natural exclamation marks while keeping the meaning exact.",
    },
]

CLEANUP_LEVELS = [
    ("none", "None", "Keep exact transcript with minimal changes"),
    ("light", "Light", "Remove filler words (um, uh) and fix basic punctuation"),
    ("medium", "Medium", "Remove fillers, handle self-corrections, and polish flow"),
]

# Speech-to-Text Providers
STT_PROVIDERS = [
    {
        "id": "local_faster_whisper",
        "name": "Local Faster-Whisper (Free · Offline)",
        "tier": "local",
        "needs_key": False,
        "models": ["tiny", "base", "small", "medium", "large-v3-turbo"],
        "default_model": "base",
        "desc": "Runs 100% locally on your CPU/GPU using CTranslate2. Zero cost, full privacy.",
    },
    {
        "id": "groq_whisper",
        "name": "Groq Whisper (Free Tier · Ultra-Fast)",
        "tier": "api",
        "needs_key": True,
        "key_setting": "groq_api_key",
        "models": ["whisper-large-v3-turbo", "whisper-large-v3", "distil-whisper-large-v3-en"],
        "default_model": "whisper-large-v3-turbo",
        "desc": "Sub-second cloud Whisper transcription with a generous free API tier.",
    },
    {
        "id": "openai_whisper",
        "name": "OpenAI Speech-to-Text (API Key)",
        "tier": "api",
        "needs_key": True,
        "key_setting": "openai_api_key",
        "models": ["gpt-4o-mini-transcribe", "gpt-4o-transcribe", "whisper-1"],
        "default_model": "gpt-4o-mini-transcribe",
        "desc": "High-accuracy OpenAI audio transcription models.",
    },
    {
        "id": "gemini_audio",
        "name": "Google Gemini Audio (Free Tier / API Key)",
        "tier": "api",
        "needs_key": True,
        "key_setting": "gemini_api_key",
        "models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
        "default_model": "gemini-2.5-flash",
        "desc": "Single-pass native audio understanding + context-aware formatting.",
    },
    {
        "id": "deepgram",
        "name": "Deepgram Nova (API Key)",
        "tier": "api",
        "needs_key": True,
        "key_setting": "deepgram_api_key",
        "models": ["nova-3", "nova-2"],
        "default_model": "nova-3",
        "desc": "Low-latency streaming-grade speech recognition.",
    },
    {
        "id": "local_whisper_server",
        "name": "Local Whisper.cpp / OpenAI-Compatible Server",
        "tier": "local",
        "needs_key": False,
        "models": ["whisper-1", "large-v3-turbo"],
        "default_model": "whisper-1",
        "desc": "Connect to your own local whisper.cpp, Speaches, or Faster-Whisper HTTP server.",
    },
]

# Post-Processing / Polish / Transform LLM Providers
LLM_PROVIDERS = [
    {
        "id": "builtin_smart",
        "name": "Built-in Smart Local Cleanup (Instant · Offline)",
        "tier": "local",
        "needs_key": False,
        "models": ["rule-engine-v1"],
        "default_model": "rule-engine-v1",
        "desc": "Instant 0ms deterministic filler removal, self-correction, dictionary & style formatting.",
    },
    {
        "id": "ollama",
        "name": "Local Ollama (Free · Offline)",
        "tier": "local",
        "needs_key": False,
        "models": ["llama3.2", "qwen2.5:7b", "gemma3:4b", "mistral", "phi4"],
        "default_model": "llama3.2",
        "desc": "Full Wispr-grade AI polishing using your local Ollama models at localhost:11434.",
    },
    {
        "id": "llamacpp",
        "name": "Local llama.cpp / LM Studio Server",
        "tier": "local",
        "needs_key": False,
        "models": ["local-model"],
        "default_model": "local-model",
        "desc": "Connect to llama-server (:8080) or LM Studio (:1234) OpenAI-compatible API.",
    },
    {
        "id": "groq_llm",
        "name": "Groq LLM (Free Tier · Ultra-Fast)",
        "tier": "api",
        "needs_key": True,
        "key_setting": "groq_api_key",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-120b"],
        "default_model": "llama-3.3-70b-versatile",
        "desc": "Blazing-fast cloud cleanup and style matching.",
    },
    {
        "id": "openai_llm",
        "name": "OpenAI (API Key)",
        "tier": "api",
        "needs_key": True,
        "key_setting": "openai_api_key",
        "models": ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"],
        "default_model": "gpt-4o-mini",
        "desc": "High-precision writing polish and transforms.",
    },
    {
        "id": "gemini_llm",
        "name": "Google Gemini (API Key)",
        "tier": "api",
        "needs_key": True,
        "key_setting": "gemini_api_key",
        "models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
        "default_model": "gemini-2.5-flash",
        "desc": "Fast, high-quality polishing with Google Gemini.",
    },
    {
        "id": "anthropic_llm",
        "name": "Anthropic Claude (API Key)",
        "tier": "api",
        "needs_key": True,
        "key_setting": "anthropic_api_key",
        "models": ["claude-haiku-4-5", "claude-sonnet-4-5"],
        "default_model": "claude-haiku-4-5",
        "desc": "Natural, human-sounding tone and prose editing.",
    },
    {
        "id": "openrouter_llm",
        "name": "OpenRouter (API Key · 200+ Models)",
        "tier": "api",
        "needs_key": True,
        "key_setting": "openrouter_api_key",
        "models": ["openai/gpt-4o-mini", "anthropic/claude-3.5-haiku", "google/gemini-2.5-flash", "meta-llama/llama-3.3-70b-instruct:free"],
        "default_model": "meta-llama/llama-3.3-70b-instruct:free",
        "desc": "Access free and paid frontier models through a single key.",
    },
    {
        "id": "sub_claude_cli",
        "name": "Claude Subscription (Claude Code CLI)",
        "tier": "subscription",
        "needs_key": False,
        "models": ["claude-cli-default"],
        "default_model": "claude-cli-default",
        "desc": "Uses your existing Claude Pro/Max subscription via installed `claude` CLI.",
    },
    {
        "id": "sub_codex_cli",
        "name": "ChatGPT Subscription (Codex CLI)",
        "tier": "subscription",
        "needs_key": False,
        "models": ["codex-cli-default"],
        "default_model": "codex-cli-default",
        "desc": "Uses your existing ChatGPT Plus/Pro subscription via installed `codex` CLI.",
    },
    {
        "id": "sub_gemini_cli",
        "name": "Google AI Subscription (Gemini CLI)",
        "tier": "subscription",
        "needs_key": False,
        "models": ["gemini-cli-default"],
        "default_model": "gemini-cli-default",
        "desc": "Uses your Google account login via installed `gemini` CLI.",
    },
    {
        "id": "custom_openai",
        "name": "Custom OpenAI-Compatible / Subscription Proxy",
        "tier": "subscription",
        "needs_key": False,
        "models": ["custom-model"],
        "default_model": "custom-model",
        "desc": "Point to any LiteLLM, GitHub Copilot proxy, or self-hosted endpoint.",
    },
]

HOTKEY_PRESETS = [
    ("ctrl+win", "Ctrl + Win"),
    ("capslock", "Caps Lock (auto-restores toggle)"),
    ("ralt", "Right Alt"),
    ("ctrl+shift+space", "Ctrl + Shift + Space"),
    ("f9", "F9"),
    ("f8", "F8"),
    ("alt+space", "Alt + Space"),
]

HANDS_FREE_PRESETS = [
    ("ctrl+win+space", "Ctrl + Win + Space"),
    ("ctrl+shift+d", "Ctrl + Shift + D"),
    ("f10", "F10"),
    ("double_tap", "Double-tap Push-to-Talk key"),
]

DEFAULT_TRANSFORMS = [
    (
        "Clean & Polish",
        "Remove filler words (um, uh, like, you know), fix grammar and punctuation, and keep the speaker's exact meaning and voice. Return ONLY the polished text.",
    ),
    (
        "Professional Email",
        "Turn the spoken thoughts into a clear, concise, polite professional email with a greeting and sign-off. Return ONLY the email body.",
    ),
    (
        "Make Concise",
        "Tighten the text to be ~40% shorter while preserving every key fact and action item. Return ONLY the shortened text.",
    ),
    (
        "Bullet Summary",
        "Convert the text into crisp markdown bullet points highlighting key takeaways and next steps. Return ONLY the bullet list.",
    ),
    (
        "Code Prompt / Issue",
        "Format the dictated engineering thoughts into a clear, structured technical specification or prompt for a coding assistant. Return ONLY the formatted prompt.",
    ),
    (
        "Translate to English",
        "Translate the dictated text into natural, fluent English preserving tone. Return ONLY the English translation.",
    ),
]
