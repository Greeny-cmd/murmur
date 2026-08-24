"""
Symbol Mode — spoken symbols become actual characters.

"forward slash" → "/"
"one two three" → "123"
"W H slash F A T" → "WH/FAT"

Opt-in via settings.
"""

import re
from core import config

# Multi-word phrases first (longer patterns take precedence)
_SUBS = [
    # Multi-word
    (re.compile(r"\bforward slash\b", re.IGNORECASE), "/"),
    (re.compile(r"\bback slash\b", re.IGNORECASE), r"\\"),
    (re.compile(r"\bbackslash\b", re.IGNORECASE), r"\\"),
    (re.compile(r"\bdouble colon\b", re.IGNORECASE), "::"),
    (re.compile(r"\bdouble quote\b", re.IGNORECASE), '"'),
    (re.compile(r"\bsingle quote\b", re.IGNORECASE), "'"),
    (re.compile(r"\bopen bracket\b", re.IGNORECASE), "("),
    (re.compile(r"\bclose bracket\b", re.IGNORECASE), ")"),
    (re.compile(r"\bopen parenthesis\b", re.IGNORECASE), "("),
    (re.compile(r"\bclose parenthesis\b", re.IGNORECASE), ")"),
    (re.compile(r"\bopen curly\b", re.IGNORECASE), "{"),
    (re.compile(r"\bclose curly\b", re.IGNORECASE), "}"),
    (re.compile(r"\bopen square\b", re.IGNORECASE), "["),
    (re.compile(r"\bclose square\b", re.IGNORECASE), "]"),
    (re.compile(r"\bless than\b", re.IGNORECASE), "<"),
    (re.compile(r"\bgreater than\b", re.IGNORECASE), ">"),
    (re.compile(r"\bexclamation mark\b", re.IGNORECASE), "!"),
    (re.compile(r"\bquestion mark\b", re.IGNORECASE), "?"),
    (re.compile(r"\bat sign\b", re.IGNORECASE), "@"),
    (re.compile(r"\bhash sign\b", re.IGNORECASE), "#"),
    (re.compile(r"\bdollar sign\b", re.IGNORECASE), "$"),
    (re.compile(r"\bpercent sign\b", re.IGNORECASE), "%"),
    (re.compile(r"\bplus sign\b", re.IGNORECASE), "+"),
    (re.compile(r"\bminus sign\b", re.IGNORECASE), "-"),
    (re.compile(r"\bnew line\b", re.IGNORECASE), "\n"),
    (re.compile(r"\bnew paragraph\b", re.IGNORECASE), "\n\n"),
    # Single-word
    (re.compile(r"\bslash\b", re.IGNORECASE), "/"),
    (re.compile(r"\bsemicolon\b", re.IGNORECASE), ";"),
    (re.compile(r"\bcolon\b", re.IGNORECASE), ":"),
    (re.compile(r"\bunderscore\b", re.IGNORECASE), "_"),
    (re.compile(r"\bdash\b", re.IGNORECASE), "-"),
    (re.compile(r"\bhyphen\b", re.IGNORECASE), "-"),
    (re.compile(r"\bminus\b", re.IGNORECASE), "-"),
    (re.compile(r"\bplus\b", re.IGNORECASE), "+"),
    (re.compile(r"\basterisk\b", re.IGNORECASE), "*"),
    (re.compile(r"\btilde\b", re.IGNORECASE), "~"),
    (re.compile(r"\bcaret\b", re.IGNORECASE), "^"),
    (re.compile(r"\bpercent\b", re.IGNORECASE), "%"),
    (re.compile(r"\bampersand\b", re.IGNORECASE), "&"),
    (re.compile(r"\bpipe\b", re.IGNORECASE), "|"),
    (re.compile(r"\bbacktick\b", re.IGNORECASE), "`"),
    # Number words → digits
    (re.compile(r"\bzero\b|\bnought\b", re.IGNORECASE), "0"),
    (re.compile(r"\bone\b", re.IGNORECASE), "1"),
    (re.compile(r"\btwo\b", re.IGNORECASE), "2"),
    (re.compile(r"\bthree\b", re.IGNORECASE), "3"),
    (re.compile(r"\bfour\b", re.IGNORECASE), "4"),
    (re.compile(r"\bfive\b", re.IGNORECASE), "5"),
    (re.compile(r"\bsix\b", re.IGNORECASE), "6"),
    (re.compile(r"\bseven\b", re.IGNORECASE), "7"),
    (re.compile(r"\beight\b", re.IGNORECASE), "8"),
    (re.compile(r"\bnine\b", re.IGNORECASE), "9"),
]

# Symbols that may appear embedded in a token
_SPLIT_SYM_RE = re.compile(r"[/\\:;_@#$%&|~^*+=<>!?()\[\]{}\"\-]")

# Contraction: word+apostrophe+word (e.g. don't, we're)
_CONTRACTION_RE = re.compile(r"^\w+'\w+$")

# Common spoken filler words / phrases (removed by the fast cleaner)
_FILLERS = [
    "you know", "i mean", "kind of", "sort of", "uh", "um", "er",
    "basically", "literally", "so like", "right",
]
_FILLER_RE = [re.compile(r"\b" + re.escape(f) + r"\b", re.IGNORECASE) for f in _FILLERS]

# Sentence-ending punctuation
_TERMINAL = ".!?"


def deterministic_clean(text: str) -> str:
    """Fast, deterministic cleanup (no LLM).

    Strips fillers, collapses spaces, capitalizes sentence starts, and adds a
    terminal period when the text reads like a sentence.
    """
    if not text:
        return text

    # Remove fillers (whole words/phrases)
    for pattern in _FILLER_RE:
        text = pattern.sub(" ", text)

    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text).strip()

    # Remove space before punctuation
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)

    # Capitalize sentence starts
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s[:1].upper() + s[1:] if s and s[0].isalpha() else s for s in sentences]
    text = " ".join(sentences)

    # Capitalize first letter
    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    # Add terminal period if it ends with a letter/digit and looks like a sentence
    if text and not text[-1] in _TERMINAL and len(text) > 1:
        text += "."

    return text.strip()


def apply_symbol_mode(text: str) -> str:
    """Apply symbol/number substitution + spelling collapse."""
    if not text:
        return text

    # Apply substitutions
    for pattern, replacement in _SUBS:
        text = pattern.sub(replacement, text)

    # Split embedded symbols
    parts = []
    for token in text.split(" "):
        if _CONTRACTION_RE.match(token):
            parts.append(token)
        elif len(token) > 1 and _SPLIT_SYM_RE.search(token):
            parts.append(" ".join(token))
        else:
            parts.append(token)
    text = " ".join(parts)

    # Collapse consecutive single-character or digit tokens
    tokens = text.split(" ")
    result = []
    buf = []

    def flush():
        if buf:
            result.append("".join(buf))
            buf.clear()

    for tok in tokens:
        if tok == "":
            flush()
            result.append("")
        elif len(tok) == 1 or tok.isdigit():
            buf.append(tok)
        else:
            flush()
            result.append(tok)
    flush()

    return " ".join(result)


def apply_replacements(text: str, dictionary=None) -> str:
    """Run the full replacement pipeline.

    1. Dictionary replacements (always)
    2. Symbol mode (if enabled)
    """
    if not text:
        return text

    # Layer A: dictionary
    if dictionary is not None:
        text = dictionary.apply(text)

    # Layer B: symbol mode
    if getattr(config, "SYMBOL_MODE_ENABLED", False):
        text = apply_symbol_mode(text)

    return text.strip()
