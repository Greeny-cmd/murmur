"""
Streaming Transcriber — provides partial results during recording.

Accumulates audio and periodically transcribes the growing buffer
for live feedback in the overlay.
"""

import numpy as np
import threading
import time
from core import config
from core.logger import log


class StreamingTranscriber:
    """Provides partial transcription results during recording."""

    def __init__(self, transcriber):
        self._transcriber = transcriber
        self._live_model = None   # separate fast model for live partials
        self._model_lock = threading.Lock()  # prevents parallel model loads
        self._audio_buffer = []
        self._buffer_lock = threading.Lock()  # protects _audio_buffer across threads
        self._running = False
        self._thread = None
        self._last_partial = ""
        self._on_partial = None  # callback(text)
        self._initial_prompt = ""  # dictionary words to bias recognition
        self._interval = 0.3     # seconds between partial transcriptions
        self._min_samples = int(config.SAMPLE_RATE * 0.4)  # ~0.4s min
        self._max_window = int(config.SAMPLE_RATE * 3)     # last ~3s for context
        # Coalesce: only emit every N ms to avoid flooding the GUI
        self._emit_interval = 0.15
        self._last_emit = 0.0

    def _get_live_model(self):
        """Lazily load the live Whisper model (medium for best quality).

        Protected by a lock so the startup preload and the stream loop never
        load it twice concurrently (which previously broke live preview).
        """
        if self._live_model is not None:
            return self._live_model
        with self._model_lock:
            if self._live_model is not None:
                return self._live_model
            from core.transcriber import _register_rocm_dlls
            _register_rocm_dlls()
            from faster_whisper import WhisperModel

            model_name = "medium"  # best default quality; GPU handles it
            device = getattr(config, "LIVE_PREVIEW_DEVICE", "auto")
            compute_type = getattr(config, "WHISPER_COMPUTE_TYPE", "int8")
            if device == "auto":
                try:
                    import ctranslate2
                    if ctranslate2.get_cuda_device_count() > 0:
                        device = "cuda"
                        compute_type = "float16"
                    else:
                        device = "cpu"
                        compute_type = "int8"
                except Exception:
                    device = "cpu"
                    compute_type = "int8"
            elif device == "cuda":
                compute_type = "float16"
            else:
                device = "cpu"
                compute_type = "int8"

            log.info("Loading live-preview Whisper model '%s' (device=%s, %s)...",
                     model_name, device, compute_type)
            try:
                self._live_model = WhisperModel(
                    model_name, device=device, compute_type=compute_type,
                )
            except Exception as exc:
                log.warning("Live GPU load failed (%s) - using CPU.", exc)
                self._live_model = WhisperModel(
                    model_name, device="cpu", compute_type="int8",
                )
        return self._live_model

    def start(self, on_partial=None, initial_prompt=""):
        """Start streaming transcription."""
        self._on_partial = on_partial
        self._initial_prompt = initial_prompt or ""
        self._running = True
        self._audio_buffer = []
        self._last_partial = ""
        self._last_emit = 0.0
        self._thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._thread.start()
        log.info("Streaming transcriber started")

    def feed_audio(self, audio_chunk: np.ndarray):
        """Feed an audio chunk from the recorder (kept at native rate)."""
        if self._running:
            with self._buffer_lock:
                self._audio_buffer.append(audio_chunk.copy())

    def stop(self) -> np.ndarray:
        """Stop streaming and return the full audio for final transcription."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

        with self._buffer_lock:
            if self._audio_buffer:
                audio = np.concatenate(self._audio_buffer, axis=0).flatten()
            else:
                audio = np.array([], dtype=np.float32)
            self._audio_buffer = []
        log.info("Streaming transcriber stopped, %d samples", len(audio))
        return audio

    def _stream_loop(self):
        """Periodically transcribe the accumulated audio for live feedback."""
        while self._running:
            time.sleep(self._interval)

            if not self._running or not self._audio_buffer:
                continue

            try:
                with self._buffer_lock:
                    if not self._audio_buffer:
                        continue
                    recent = np.concatenate(self._audio_buffer, axis=0).flatten()
                if len(recent) < self._min_samples:
                    continue

                # Cap the window for transcription speed
                if len(recent) > self._max_window:
                    recent = recent[-self._max_window:]

                from core.transcriber import resolve_language
                model = self._get_live_model()
                segments, info = model.transcribe(
                    recent,
                    language=resolve_language(),
                    initial_prompt=self._initial_prompt,  # bias dictionary words
                    beam_size=1,   # fast
                    best_of=1,
                    vad_filter=False,   # keep quiet/short word starts visible live
                    condition_on_previous_text=False,  # avoid repetition in live partials
                )
                text = " ".join(seg.text.strip() for seg in segments).strip()
                log.info("[live-loop] n=%d len=%.1fs lang=%s result=%r",
                         len(recent), len(recent)/config.SAMPLE_RATE,
                         getattr(info, "language", None), text)

                # Coalesce GUI updates (don't spam every 0.x sec)
                now = time.monotonic()
                if text and text != self._last_partial and \
                   (now - self._last_emit) >= self._emit_interval:
                    self._last_emit = now
                    self._last_partial = text
                    if self._on_partial:
                        try:
                            self._on_partial(text)
                        except Exception as e:
                            log.error("Partial callback error: %s", e)

            except Exception as e:
                log.debug("Streaming transcription error: %s", e)