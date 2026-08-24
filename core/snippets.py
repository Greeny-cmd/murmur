"""
Text expansion snippets — editable abbreviation -> expansion map.

e.g. "NYC" -> "New York City", or whole paragraphs. Manually triggered
by a hotkey (the selected/typed trigger word is replaced by its expansion).
"""

import json
import os
from core import config
from core.logger import log

SNIPPETS_FILE = os.path.join(config.DATA_DIR, "snippets.json")

DEFAULTS = {
    "NYC": "New York City",
    "afaik": "as far as I know",
    "btw": "by the way",
    "imho": "in my humble opinion",
}


class SnippetStore:
    """Load/save a word -> expansion map under %LOCALAPPDATA%\\Murmur."""

    def __init__(self):
        self._snippets: dict[str, str] = {}
        self._load()

    def _load(self):
        try:
            if os.path.exists(SNIPPETS_FILE):
                with open(SNIPPETS_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self._snippets = {str(k).strip(): v for k, v in data.items()}
                else:
                    self._snippets = dict(DEFAULTS)
            else:
                self._snippets = dict(DEFAULTS)  # seed defaults on first run
                self._save()
        except Exception as exc:
            log.warning("Snippet load failed: %s", exc)
            self._snippets = dict(DEFAULTS)

    def _save(self):
        try:
            with open(SNIPPETS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._snippets, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            log.error("Snippet save failed: %s", exc)

    def all(self):
        return self._snippets

    def lookup(self, word: str):
        """Return the expansion for a trigger word (case-insensitive), or None."""
        if not word:
            return None
        key = word.strip()
        return (self._snippets.get(key)
                or self._snippets.get(key.lower())
                or self._snippets.get(key.capitalize())
                or self._snippets.get(key.upper()))

    def set(self, word: str, expansion: str):
        word = word.strip()
        if not word:
            return
        if expansion:
            self._snippets[word] = expansion
        elif word in self._snippets:
            del self._snippets[word]
        self._save()

    def remove(self, word: str):
        self._snippets.pop(word, None)
        self._save()


def expand_snippets_in_text(text: str, store: SnippetStore) -> tuple[str, list[str]]:
    """Replace spoken trigger words in free text with their expansions.

    Returns (expanded_text, list_of_trigger_words_found). Word-boundary aware so
    'NYC' mid-sentence becomes 'New York City' without touching 'NYCTA'.
    """
    if not text or not store.all():
        return text, []
    import re
    # Sort by length desc so longer triggers match first.
    triggers = sorted(store.all().keys(), key=lambda t: -len(t))
    found = []
    result = text
    for trig in triggers:
        pattern = re.compile(r'(?<!\w)' + re.escape(trig) + r'(?!\w)', re.IGNORECASE)
        new = pattern.sub(store.lookup(trig), result)
        if new != result:
            found.append(trig)
            result = new
    return result, found