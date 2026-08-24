"""Transcriber — converts audio to text.

Supports two ASR engines:
1. faster-whisper (CTranslate2-based Whisper)
2. Parakeet (via sherpa-onnx)

User can choose which engine to use in settings.
"""

import os
import numpy as np
from core import config
from core.logger import log


def resolve_language():
    """Resolve the configured language(s) to a single Whisper language code.

    faster-whisper transcribe expects a single language string. If exactly
    one language is selected in settings, pass it; otherwise None (auto).
    """
    lang = config.WHISPER_LANGUAGE
    if isinstance(lang, list):
        if len(lang) == 1:
            return lang[0]
        return None  # multiple -> auto-detect
    return lang  # None (auto) or single string


def detect_gpu_device():
    """Return ('cuda'|'cpu', compute_type) based on this machine's GPU.

    - If a NVIDIA CUDA GPU is present AND the installed CTranslate2 is a CUDA
      build, use 'cuda'.
    - If an AMD ROCm GPU is present (HIP_PATH / ROCm) AND the CTranslate2 build
      is the ROCm one (it reports a CUDA device count via HIP), use 'cuda'.
    - Otherwise fall back to CPU int8.
    """
    try:
        import ctranslate2
        # ctranslate2's get_cuda_device_count() reports AMD-Rocm devices too
        # (the ROCm wheel exposes them under the same API).
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def _register_rocm_dlls():
    """Make AMD ROCm DLLs loadable so a ROCm-built CTranslate2 can use the GPU."""
    try:
        import os
        import glob
        base = os.environ.get("HIP_PATH", r"C:\Program Files\AMD\ROCm")
        cands = [base]
        if os.path.isdir(base):
            cands += glob.glob(os.path.join(base, "*"))
        added = set()
        for b in cands:
            for sub in (r"\bin", r"\lib"):
                d = b + sub
                if os.path.isdir(d) and d not in added:
                    try:
                        os.add_dll_directory(d)
                        added.add(d)
                    except OSError:
                        pass
    except Exception:
        pass


# Register ROCm DLL search dirs BEFORE any CTranslate2 import happens, so a
# ROCm-built ctranslate2 can resolve amdhip64/hipblas at import time.
_register_rocm_dlls()


class FasterWhisperTranscriber:
    """Transcriber using faster-whisper (CTranslate2)."""

    def __init__(self):
        self._model = None
        self.last_detected_language = None  # language Whisper actually detected

    def load(self):
        """Load the Whisper model (GPU/ROCm when available, else CPU)."""
        if self._model is not None:
            return
        from faster_whisper import WhisperModel
        _register_rocm_dlls()

        device = getattr(config, "WHISPER_DEVICE", "auto")
        compute_type = getattr(config, "WHISPER_COMPUTE_TYPE", "int8")
        if device in ("auto", "cpu"):
            # Auto-detect; explicit 'cuda' stays cuda.
            _device, _ct = detect_gpu_device()
            if device == "auto":
                device, compute_type = _device, _ct
            elif device == "cuda" and _device != "cuda":
                log.warning("Requested cuda but no GPU detected - using CPU.")
                device, compute_type = "cpu", "int8"

        log.info("Loading Whisper model '%s' (device=%s, %s)...",
                 config.WHISPER_MODEL, device, compute_type)
        try:
            self._model = WhisperModel(
                config.WHISPER_MODEL,
                device=device,
                compute_type=compute_type,
            )
        except Exception as exc:
            log.warning("GPU model load failed (%s) - falling back to CPU int8.", exc)
            self._model = WhisperModel(
                config.WHISPER_MODEL,
                device="cpu",
                compute_type="int8",
            )
        self._device = getattr(self._model, "device", device)
        log.info("Whisper model loaded on %s.", self._device)

    def transcribe(self, audio: np.ndarray, initial_prompt: str = "") -> str:
        """Transcribe audio to text."""
        self.load()
        segments, info = self._model.transcribe(
                    audio,
                    language=resolve_language(),
                    beam_size=1,           # greedy = fastest (Wispr-style single pass)
                    best_of=1,
                    vad_filter=True,
                    initial_prompt=initial_prompt,
                )
        detected = getattr(info, "language", None)
        probability = getattr(info, "language_probability", None)
        if detected:
            if probability is not None:
                log.info("Whisper detected language: %s (p=%.2f)", detected, probability)
            else:
                log.info("Whisper detected language: %s", detected)
        text = " ".join(seg.text.strip() for seg in segments)
        # Remember last detected language so cleanup can respect it.
        self.last_detected_language = detected
        return text.strip()


class ParakeetTranscriber:
    """Transcriber using Parakeet TDT via sherpa-onnx."""

    def __init__(self):
        self._recognizer = None

    def _find_model(self) -> str | None:
        """Find the Parakeet model directory."""
        search_paths = [
            config.PARAKEET_MODEL_DIR,
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Murmur", "models", "parakeet-v2"),
            os.path.join(os.path.expanduser("~"), ".local", "share", "sherpa-onnx", "parakeet-v2"),
        ]

        required_files = ["encoder.int8.onnx", "decoder.int8.onnx", "joiner.int8.onnx", "tokens.txt"]

        for path in search_paths:
            if path and os.path.isdir(path):
                if all(os.path.exists(os.path.join(path, f)) for f in required_files):
                    return path
        return None

    def load(self):
        """Load the Parakeet model."""
        if self._recognizer is not None:
            return

        model_dir = self._find_model()
        if model_dir is None:
            raise RuntimeError("Parakeet model not found. Please download it first.")

        import sherpa_onnx

        encoder = os.path.join(model_dir, "encoder.int8.onnx")
        decoder = os.path.join(model_dir, "decoder.int8.onnx")
        joiner = os.path.join(model_dir, "joiner.int8.onnx")
        tokens = os.path.join(model_dir, "tokens.txt")

        log.info("Loading Parakeet model from %s...", model_dir)

        # model_type="nemo_transducer" is REQUIRED for NeMo Parakeet-TDT models:
        # it selects the correct feature layout / reading of vocab_size+context_size.
        # (k2-fsa issue #2226 — without it the model either crashes or shape-mismatches.)
        self._recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=encoder,
            decoder=decoder,
            joiner=joiner,
            tokens=tokens,
            num_threads=config.PARAKEET_THREADS,
            decoding_method="greedy_search",
            model_type="nemo_transducer",
            debug=False,
        )
        log.info("Parakeet model loaded.")

    def transcribe(self, audio: np.ndarray, initial_prompt: str = "") -> str:
        """Transcribe audio to text."""
        self.load()

        # Convert float32 to int16 for sherpa-onnx
        audio_int16 = (audio * 32767).astype(np.int16)

        stream = self._recognizer.create_stream()
        stream.accept_waveform(config.SAMPLE_RATE, audio_int16)
        self._recognizer.decode_stream(stream)
        return (stream.result.text or "").strip()


class UnavailableTranscriber:
    """Placeholder when no transcriber is available."""

    def transcribe(self, audio: np.ndarray, initial_prompt: str = "") -> str:
        return ""


class FallbackTranscriber:
    """Tries a preferred engine; falls back to faster-whisper on any failure.

    Guarantees text is produced even if Parakeet (sherpa-onnx) fails to load
    or transcribe, so the user is never left without a dictation result.
    """

    def __init__(self, preferred):
        self._preferred = preferred
        self._fallback = None

    def load(self):
        """Pre-load the preferred engine if it supports it."""
        if hasattr(self._preferred, "load"):
            self._preferred.load()

    def _get_fallback(self):
        if self._fallback is None:
            self._fallback = FasterWhisperTranscriber()
        return self._fallback

    def transcribe(self, audio: np.ndarray, initial_prompt: str = "") -> str:
        try:
            text = self._preferred.transcribe(audio, initial_prompt)
            if text:
                return text
        except Exception as exc:
            log.warning("Preferred engine failed (%s); falling back to faster-whisper.", exc)
        try:
            return self._get_fallback().transcribe(audio, initial_prompt)
        except Exception as exc:
            log.error("Both engines failed: %s", exc)
            return ""


def create_transcriber(engine: str = "faster-whisper"):

    """Factory function to create a transcriber.

    Args:
        engine: "faster-whisper" or "parakeet"
    """
    engine = (engine or "faster-whisper").lower()
    if engine == "parakeet":
        # Prefer Parakeet, but never leave the user silent — fall back to Whisper.
        return FallbackTranscriber(ParakeetTranscriber())
    elif engine == "faster-whisper":
        return FasterWhisperTranscriber()
    else:
        log.warning("Unknown ASR engine: %s, using unavailable transcriber", engine)
        return UnavailableTranscriber()
