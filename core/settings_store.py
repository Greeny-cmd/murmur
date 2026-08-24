"""
Persistent settings store — saves/loads user settings to JSON.

Keeps settings across restarts (previously they were in-memory only).
"""

import json
import os
from core import config
from core.logger import log

SETTINGS_FILE = os.path.join(config.DATA_DIR, "settings.json")

# Whitelist of settable keys with their defaults
DEFAULTS = {
    # Audio
    "MIC_DEVICE_NAME": None,
    # ASR
    "ASR_ENGINE": "faster-whisper",
    "WHISPER_MODEL": "base",
    "WHISPER_DEVICE": "auto",
    "WHISPER_LANGUAGE": None,       # Auto-detect default; pick one to force
    "PARAKEET_MODEL_DIR": None,
    # Hotkey
    "HOTKEY": 0xA3,
    "COMBO_HOTKEY": None,
    "HOLD_TO_RECORD": True,
    "CUSTOM_HOTKEYS": [],
    "REWRITE_HOTKEY": 0x91,
    "REWRITE_COMBO": None,       # optional rewrite combo (list of vks)
    # LLM
    "OLLAMA_URL": "http://localhost:11434",
    "OLLAMA_MODEL": "gemma2:2b",
    "LLM_CLEANUP_ENABLED": False,
    # Tool calling
    "TOOL_CALLING_ENABLED": True,
    "ENABLED_COMMANDS": None,
    # Symbol mode
    "SYMBOL_MODE_ENABLED": False,
    # Clipboard
    "KEEP_TRANSCRIPT_IN_CLIPBOARD": False,
    # Behaviour
    "INJECT_TEXT": True,
    "KEEP_HISTORY": True,
    "LOG_TO_FILE": False,       # logs are for debugging; off by default
    "ONBOARDING_DONE": False,
    "LIVE_PREVIEW_ENABLED": False,
    "LIVE_PREVIEW_DEVICE": "auto",
    # Snippets
    "SNIPPET_EXPANSION_ENABLED": True,
    # UI
    "SETTINGS_WINDOW_SIZE": None,  # {w, h} restored on next open
}


def load_settings():
    """Load saved settings into the config module."""
    if not os.path.exists(SETTINGS_FILE):
        return

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)

        for key, value in saved.items():
            if key in DEFAULTS and hasattr(config, key):
                setattr(config, key, value)

        log.info("Loaded settings: %s", ", ".join(saved.keys()))
    except Exception as exc:
        log.error("Failed to load settings: %s", exc)


def save_settings():
    """Save current config values to JSON."""
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        payload = {}
        for key in DEFAULTS:
            if hasattr(config, key):
                payload[key] = getattr(config, key)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        log.info("Settings saved")
    except Exception as exc:
        log.error("Failed to save settings: %s", exc)


def set_setting(key: str, value):
    """Set a config value and persist it."""
    if key in DEFAULTS and hasattr(config, key):
        setattr(config, key, value)
    save_settings()


def get_setting(key: str):
    """Read a setting from current config (or stored file)."""
    if hasattr(config, key):
        return getattr(config, key)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            return json.load(f).get(key)
    except Exception:
        return None