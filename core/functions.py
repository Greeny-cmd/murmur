"""
Function-Calling — execute commands based on voice input.

"Open YouTube" or "Youtube" → browser opens YouTube
"Open Calculator" → opens Calculator
"""

import subprocess
import webbrowser
from core import config
from core.logger import log

WEBSITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "chatgpt": "https://chat.openai.com",
    "reddit": "https://www.reddit.com",
    "wikipedia": "https://www.wikipedia.org",
    "twitter": "https://twitter.com",
    "x": "https://twitter.com",
    "amazon": "https://www.amazon.com",
    "netflix": "https://www.netflix.com",
    "maps": "https://maps.google.com",
    "translate": "https://translate.google.com",
    "drive": "https://drive.google.com",
    "google docs": "https://docs.google.com",
    "calendar": "https://calendar.google.com",
}

APPS = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "explorer": ["explorer.exe"],
    "file explorer": ["explorer.exe"],
    "terminal": ["cmd.exe"],
    "command prompt": ["cmd.exe"],
    "paint": ["mspaint.exe"],
    "task manager": ["taskmgr.exe"],
    "control panel": ["control.exe"],
    "snipping tool": ["SnippingTool.exe"],
}


# Phonetic aliases — map misheard variants to their canonical command.
# This handles ASR errors like "docs" heard as "Tox" / "Docks".
ALIASES = {
    "google docs": ["google docs", "docs", "doc", "documents", "docks", "tox",
                    "google dock", "google tox", "googledocs"],
    "translate": ["translate", "google translate", "translator", "google traducate"],
    "github": ["github", "git hub"],
}

def resolve_alias(spoken: str) -> str:
    """Return the canonical command name for a spoken phrase (or unchanged)."""
    s = spoken.strip().lower().rstrip(".!?")
    # merge built-in aliases with user-custom aliases (custom wins)
    merged = dict(ALIASES)
    custom = getattr(config, "CUSTOM_ALIASES", None) or {}
    for canonical, variants in custom.items():
        merged.setdefault(canonical, [])
        merged[canonical] = list(dict.fromkeys(list(merged[canonical]) + list(variants)))
    for canonical, variants in merged.items():
        if s in variants:
            return canonical
    return s

def all_aliases() -> list[str]:
    """All alias phrases (used for the settings command list)."""
    out = set(ALIASES.keys())
    for vs in ALIASES.values():
        out.update(vs)
    return sorted(out)


def execute(function_name: str) -> bool:
    """Execute a function by name. Returns True if executed."""
    name = function_name.strip().lower()

    # Website
    if name in WEBSITES:
        try:
            webbrowser.open(WEBSITES[name])
            log.info("Opened website: %s", name)
            return True
        except Exception as exc:
            log.error("Failed to open %s: %s", name, exc)
            return False

    # App
    if name in APPS:
        try:
            subprocess.Popen(APPS[name])
            log.info("Launched app: %s", name)
            return True
        except Exception as exc:
            log.error("Failed to launch %s: %s", name, exc)
            return False

    log.warning("Unknown function: %s", name)
    return False


def list_functions() -> list[str]:
    """List all available functions."""
    return list(WEBSITES.keys()) + list(APPS.keys())


def all_commands() -> dict:
    """Return a dict of {command_name: description} for all available commands."""
    desc = {}
    for name, url in WEBSITES.items():
        desc[name] = f"Open {name.title()} in browser"
    for name, _ in APPS.items():
        app = name.title()
        desc[name] = f"Open {app}"
    return desc


def is_command_enabled(name: str) -> bool:
    """Check whether a command is enabled in settings."""
    from core import config, settings_store
    enabled = getattr(config, "ENABLED_COMMANDS", None)
    if enabled is None:
        return True  # default: all enabled
    return name in enabled