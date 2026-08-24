"""
Configuration — defaults and settings.
"""

# ── Audio ────────────────────────────────────────────────────────────────

SAMPLE_RATE = 16000  # Hz, what Whisper/Parakeet expect
MIC_DEVICE_NAME = None  # None = system default

# ── ASR ──────────────────────────────────────────────────────────────────

ASR_ENGINE = "faster-whisper"  # Stable default. "parakeet" needs a sherpa-onnx-compatible model
WHISPER_MODEL = "base"  # default: balanced speed/accuracy (tiny faster, small/medium more accurate)
WHISPER_DEVICE = "auto"  # auto (GPU when available), cuda, or cpu
WHISPER_COMPUTE_TYPE = "int8"  # int8, float16, float32
WHISPER_LANGUAGE = None  # Auto-detect by default (DE/EN respected). Pick one in Settings to force.
SYMBOL_MODE_ENABLED = False

PARAKEET_MODEL_DIR = None  # Path to Parakeet model, or None to auto-detect
PARAKEET_THREADS = 4

# ── Hotkey ───────────────────────────────────────────────────────────────

# Default dictation key: Right Alt / AltGr (0xA5) — on DE keyboards AltGr
HOTKEY = 0xA5  # Default: Right Alt / ALTGR (0xA5) — on DE keyboards AltGr
COMBO_HOTKEY = None  # e.g. (0xA2, 0xA5, 0x52) for Ctrl+Alt+R
REWRITE_HOTKEY = 0x91  # Scroll Lock — rewrite-selection hotkey (default, single key)
REWRITE_COMBO = None   # optional rewrite combo, e.g. [0x5B, 0xA2, 0x52] = Win+Ctrl+R
SNIPPET_EXPANSION_ENABLED = True  # expand snippet triggers spoken during dictation
HOLD_TO_RECORD = True  # True = hold to record, False = toggle mode
CUSTOM_HOTKEYS = []  # list of vk-code lists added by the user

# ── LLM ──────────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "gemma2:2b"  # fast GPU cleanup model
LLM_CLEANUP_ENABLED = False  # OPTIONAL — off by default for speed (fast deterministic clean is used instead)

# ── Tool Calling ──────────────────────────────────────────────────────────

TOOL_CALLING_ENABLED = True
ENABLED_COMMANDS = None  # None = all enabled; else list of command names
CUSTOM_ALIASES = {}      # {command: [extra aliases]} added by the user in settings

# ── Clipboard ────────────────────────────────────────────────────────────

KEEP_TRANSCRIPT_IN_CLIPBOARD = False
CLIPBOARD_RESTORE_DELAY = 0.5  # seconds

# ── Behaviour ─────────────────────────────────────────────────────────────

INJECT_TEXT = True   # type transcripts into the focused app
KEEP_HISTORY = True  # keep a transcript history in the UI
LOG_TO_FILE = False  # off by default (logs are for debugging only); enable in settings
ONBOARDING_DONE = False  # first-run wizard shown?
LIVE_PREVIEW_ENABLED = False  # live partial transcription in overlay
LIVE_PREVIEW_DEVICE = "auto"  # 'auto' (GPU when available), 'cpu', or 'cuda'

# ── Recording ────────────────────────────────────────────────────────────

MAX_RECORD_SECONDS = 120
MIN_DURATION = 0.5  # minimum seconds to transcribe

# ── Paths ────────────────────────────────────────────────────────────────

import os
import sys
DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Murmur")
os.makedirs(DATA_DIR, exist_ok=True)

# ── Bundled-asset resolution (PyInstaller frozen vs source) ─────────────
def _bundled_dir():
    """Return the dir holding read-only bundled assets (icons, etc.).

    In a frozen (PyInstaller) build this is _MEIPASS (the unpacked bundle,
    `_internal` on onedir builds). In source runs it's the project root.
    """
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root


def icon_path(name: str) -> str:
    """Resolve an icon file bundled under 'ui/icons/<name>'."""
    return os.path.join(_bundled_dir(), "ui", "icons", name)

SETTINGS_WINDOW_SIZE = None  # persisted by SettingsWindow (window-geometry memory)
