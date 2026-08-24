"""
Personal Dictionary — custom vocabulary for ASR biasing.

Teach the speech engine to recognize your names, jargon, and acronyms.
"""

import json
import os
from core import config
from core.logger import log

DICTIONARY_FILE = os.path.join(config.DATA_DIR, "dictionary.json")


class Dictionary:
    """Personal dictionary for ASR biasing."""

    def __init__(self):
        self._entries: dict[str, str] = {}
        self._load()

    def _load(self):
        """Load dictionary from file."""
        if os.path.exists(DICTIONARY_FILE):
            try:
                with open(DICTIONARY_FILE, "r", encoding="utf-8") as f:
                    self._entries = json.load(f)
                log.info("Loaded %d dictionary entries", len(self._entries))
            except Exception as exc:
                log.error("Failed to load dictionary: %s", exc)
                self._entries = {}

    def _save(self):
        """Save dictionary to file."""
        try:
            os.makedirs(os.path.dirname(DICTIONARY_FILE), exist_ok=True)
            with open(DICTIONARY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            log.error("Failed to save dictionary: %s", exc)

    def add(self, spoken: str, written: str):
        """Add or update a dictionary entry."""
        self._entries[spoken.lower().strip()] = written
        self._save()
        log.info("Dictionary: added %r -> %r", spoken, written)

    def remove(self, spoken: str):
        """Remove a dictionary entry."""
        key = spoken.lower().strip()
        if key in self._entries:
            del self._entries[key]
            self._save()
            log.info("Dictionary: removed %r", spoken)

    def get(self, spoken: str) -> str | None:
        """Look up a spoken form."""
        return self._entries.get(spoken.lower().strip())

    def get_all(self) -> dict[str, str]:
        """Return all entries."""
        return dict(self._entries)

    def get_initial_prompt(self) -> str:
        """Get priming terms for Whisper's initial_prompt.

        This nudges the recognizer toward your custom vocabulary.
        """
        if not self._entries:
            return ""
        return ", ".join(self._entries.keys())

    def apply(self, text: str) -> str:
        """Apply dictionary replacements to transcribed text.

        Case-insensitive, whole-word, longest-first.
        """
        if not self._entries or not text:
            return text

        result = text
        # Sort by length descending so longer matches take priority
        for spoken in sorted(self._entries.keys(), key=len, reverse=True):
            if not spoken.strip():
                continue
            import re
            pattern = re.compile(r"\b" + re.escape(spoken) + r"\b", re.IGNORECASE)
            result = pattern.sub(self._entries[spoken], result)

        return result
