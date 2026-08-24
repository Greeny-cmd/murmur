"""
LLM Cleanup — cleans up transcribed text using local Ollama.

Strips fillers, fixes spacing, capitalizes sentences, adds punctuation.
"""

import httpx
from core import config
from core.logger import log

SYSTEM_PROMPT = """You are a text editor. Edit the transcript for clarity.

CRITICAL — LANGUAGE RULE:
- Respond in EXACTLY the same language as the text you were given.
- If the text is German, output fluent German. If English, output English.
- NEVER translate, convert, or switch to another language.

Other rules:
1. Fix punctuation and capitalization
2. Remove filler words (e.g. "um", "uh", "you know", "also", "äh", "also im Grunde")
3. Fix spacing issues
4. Keep the original meaning and all spoken content
5. Do NOT add words that weren't spoken
6. Do NOT provide reasoning, explanations, or thinking steps
7. Return ONLY the edited text — no quotes, no commentary, same language."""

# Cap output so qwen3 thinking mode can't run away.
MAX_OUTPUT = 512


async def cleanup(text: str, language: str | None = None) -> str:
    """Clean up transcribed text using Ollama.

    Args:
        text: Raw transcribed text
        language: Optional source language (e.g. "de", "en") — passed to the
            model as an explicit hint so it keeps the correct language.

    Returns:
        Cleaned up text, or original text if Ollama is unavailable
    """
    if not config.LLM_CLEANUP_ENABLED:
        return text

    if not text or not text.strip():
        return text

    user_message = text
    if language:
        lang_name = {"de": "German", "en": "English"}.get(language, language)
        user_message = f"[The text below is in {lang_name}. Keep it in {lang_name}.]\n{text}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{config.OLLAMA_URL}/api/chat",
                json={
                    "model": config.OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message}
                    ],
                    "stream": False,
                    "keep_alive": -1,  # hold model in VRAM (no 7s cold-start reload)
                    "options": {"temperature": 0.0, "num_predict": MAX_OUTPUT, "num_ctx": 4096}
                }
            )
            response.raise_for_status()
            result = response.json()
            cleaned = result.get("message", {}).get("content", "").strip()
            if cleaned:
                log.debug("LLM cleanup: %r -> %r", text, cleaned)
                return cleaned
            return text
    except httpx.ConnectError:
        log.warning("Ollama not available at %s", config.OLLAMA_URL)
        return text
    except Exception as exc:
        log.error("LLM cleanup failed: %s", exc)
        return text


def unload_model() -> None:
    """Unload the cleanup model from Ollama's VRAM (keep_alive=0).

    Called when Murmur quits so gemma2:2b doesn't stay resident in the
    background and consume VRAM after the app is closed.
    """
    try:
        import httpx
        r = httpx.post(
            f"{config.OLLAMA_URL}/api/generate",
            json={"model": config.OLLAMA_MODEL, "prompt": "", "stream": False,
                  "keep_alive": 0},
            timeout=10,
        )
        log.info("Ollama model '%s' unloaded on quit (status %s)", config.OLLAMA_MODEL, r.status_code)
    except Exception as exc:
        log.debug("Ollama unload on quit failed: %s", exc)


def warm_up() -> bool:
    """Load the cleanup model into memory so the first dictation is fast.

    Runs a tiny no-op generation against the configured model. Call in a
    background thread at app startup.
    """
    try:
        import httpx
        r = httpx.post(
            f"{config.OLLAMA_URL}/api/generate",
            json={"model": config.OLLAMA_MODEL, "prompt": "OK", "stream": False,
                  "keep_alive": -1,
                  "options": {"num_predict": 1}},
            timeout=120,
        )
        ok = r.status_code == 200
        log.info("Ollama warm-up %s (%s)", "OK" if ok else "failed", config.OLLAMA_MODEL)
        return ok
    except Exception as exc:
        log.warning("Ollama warm-up failed: %s", exc)
        return False
