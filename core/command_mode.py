"""Command Mode — rewrite selected text using LLM.

Select text, hold command hotkey, speak your instruction,
see a preview, then confirm or cancel.
"""

import httpx
from core import config
from core.logger import log

COMMAND_SYSTEM_PROMPT = """You are an expert text editor. The user will tell you how to rewrite the selected text.

CRITICAL — LANGUAGE RULE:
- Output in EXACTLY the same language as the selected text (German stays German, English stays English).
- NEVER translate; only transform as requested.

Follow the instruction precisely. Understand common transforms such as:
- "make this more formal" / "formal"       → formal register
- "simplify" / "make it simpler"           → plainer, shorter sentences, common words
- "fix the grammar" / "grammar"            → correct grammar/punctuation
- "summarize" / "shorten" / "make it shorter" → concise summary
- "make it more friendly" / "casual"       → warmer, less stiff tone

Return ONLY the rewritten text — fully replace the selected text, no explanation, no quotes, no preamble."""


async def rewrite(selected_text: str, instruction: str, language: str | None = None) -> str:
    """Rewrite selected text based on user instruction.

    Args:
        selected_text: The currently selected text
        instruction: User's voice command (e.g. "make this more formal")
        language: Optional ISO-639 language code of the selected text (e.g. "de")

    Returns:
        Rewritten text, or original if LLM unavailable
    """
    if not selected_text or not instruction:
        return selected_text

    if language:
        lang_name = _lang_name(language)
        lang_hint = (
            f"The selected text is in {lang_name.lower()}. "
            f"IMPORTANT: write the rewritten text in the SAME language "
            f"({lang_name}). Do NOT switch to English or translate."
        )
    else:
        lang_hint = (
            "Write the rewritten text in the SAME language as the selected text "
            "(German stays German, English stays English)."
        )

    prompt = f"""{lang_hint}

Selected text:
---
{selected_text}
---

Instruction: {instruction}"""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{config.OLLAMA_URL}/api/chat",
                json={
                    "model": config.OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": COMMAND_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                    "keep_alive": -1,  # hold model in VRAM (no 7s cold-start reload)
                    "options": {
                        "temperature": 0.3,
                        # Hard cap so a rewrite never runs away.
                        "num_predict": getattr(config, "REWRITE_MAX_TOKENS", 400),
                        "num_ctx": 4096,
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            rewritten = result.get("message", {}).get("content", "").strip()
            if rewritten:
                log.info("Command rewrite: %r -> %r", selected_text, rewritten)
                return rewritten
            return selected_text
    except httpx.ConnectError:
        log.warning("Ollama not available for command mode")
        return selected_text
    except Exception as exc:
        log.error("Command rewrite failed: %s", exc)
        return selected_text


def _lang_name(code: str) -> str:
    """Return a human name for an ISO-639 language code."""
    names = {
        "de": "German", "en": "English", "fr": "French", "es": "Spanish",
        "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "pl": "Polish",
        "tr": "Turkish", "ja": "Japanese", "ko": "Korean", "ru": "Russian",
    }
    return names.get(code, code.capitalize())