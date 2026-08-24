"""
Dictation Pipeline — the main flow.

Hotkey → Record → Transcribe → Cleanup → Dictionary → Symbol Mode → Inject
"""

import asyncio
from core.recorder import Recorder
from core.transcriber import create_transcriber
from core.injector import inject, save_recovery
from core.dictionary import Dictionary
from core.replacements import apply_replacements
from core.llm_cleanup import cleanup
from core import config
from core.logger import log


class DictationPipeline:
    """Main dictation pipeline."""

    def __init__(self, asr_engine: str = "faster-whisper"):
        self.recorder = Recorder()
        self.transcriber = create_transcriber(asr_engine)
        self.dictionary = Dictionary()
        self.on_transcribing = None  # callback
        self.on_completed = None     # callback(text)
        self.on_error = None         # callback(error)

    async def process(self, audio):
        """Process recorded audio through the pipeline."""
        if audio is None or len(audio) == 0:
            log.info("No audio recorded")
            return

        duration = len(audio) / config.SAMPLE_RATE
        if duration < config.MIN_DURATION:
            log.info("Too short (%.2fs), skipping", duration)
            return

        try:
            if self.on_transcribing:
                self.on_transcribing()

            # 1. Transcribe
            log.info("Transcribing...")
            initial_prompt = self.dictionary.get_initial_prompt()
            text = self.transcriber.transcribe(audio, initial_prompt)
            if not text:
                log.info("No speech detected")
                return

            log.info("Raw: %r", text)

            # 2. Apply dictionary replacements
            text = apply_replacements(text, self.dictionary)

            # 3. LLM cleanup (if enabled)
            text = await cleanup(text)

            # 4. Save to recovery file
            save_recovery(text)

            # 5. Inject into focused app
            log.info("Injecting: %r", text)
            inject(text)

            if self.on_completed:
                self.on_completed(text)

        except Exception as exc:
            log.error("Pipeline error: %s", exc)
            if self.on_error:
                self.on_error(str(exc))
