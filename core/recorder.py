"""
Audio Recorder — captures microphone audio.

Uses sounddevice (PortAudio) for cross-platform audio capture, with native-rate
resampling to Whisper's 16 kHz before feeding the transcript.
"""

import numpy as np
import sounddevice as sd
from core import config
from core.logger import log


def _resolve_device(name: str | None) -> int | None:
    """Resolve a device name to a WASAPI device index at call time.

    Returns None (system default) if name is None or not found.
    Prefers WASAPI host API for reliable Windows audio.
    """
    if not name:
        return None
    try:
        # Re-init PortAudio to get current indices
        sd._terminate()
        sd._initialize()

        host_apis = sd.query_hostapis()
        wasapi_idx = None
        for i, api in enumerate(host_apis):
            if "WASAPI" in api.get("name", ""):
                wasapi_idx = i
                break

        all_devs = sd.query_devices()

        # First pass: exact match on WASAPI
        for i, dev in enumerate(all_devs):
            if dev["max_input_channels"] <= 0:
                continue
            if wasapi_idx is not None and dev.get("hostapi") != wasapi_idx:
                continue
            if dev["name"] == name:
                return i

        # Second pass: partial match on WASAPI
        target = name.lower()
        for i, dev in enumerate(all_devs):
            if dev["max_input_channels"] <= 0:
                continue
            if wasapi_idx is not None and dev.get("hostapi") != wasapi_idx:
                continue
            if target in dev["name"].lower():
                return i

        # Third pass: any host API, exact match
        for i, dev in enumerate(all_devs):
            if dev["max_input_channels"] <= 0:
                continue
            if dev["name"] == name:
                return i

        log.warning("Microphone '%s' not found, falling back to default", name)
    except Exception as exc:
        log.warning("Device resolution failed: %s", exc)
    return None


class Recorder:
    """Records audio from the microphone."""

    def __init__(self):
        self._frames = []
        self._stream = None
        self.recording = False
        self._sample_rate = config.SAMPLE_RATE
        self.on_level = None       # optional callback(rms: float)
        self.on_mic_error = None   # optional callback(msg: str)
        self.on_audio = None        # optional callback(audio_chunk: np.ndarray)

    def _callback(self, indata, frames, time, status):
        if self.recording:
            chunk = indata.copy()
            self._frames.append(chunk)
            if self.on_level is not None:
                rms = float(np.sqrt(np.mean(indata ** 2)))
                self.on_level(rms)
            if self.on_audio is not None:
                # Whisper needs 16 kHz; our stream may record at native 48 kHz.
                feed = self._to_16k(chunk)
                self.on_audio(feed)

    def _to_16k(self, chunk: np.ndarray) -> np.ndarray:
        """Resample a chunk to config.SAMPLE_RATE (16 kHz) for the live stream."""
        if self._sample_rate == config.SAMPLE_RATE or len(chunk) < 2:
            return chunk
        n = len(chunk)
        duration = n / self._sample_rate
        target_len = max(1, int(duration * config.SAMPLE_RATE))
        idx = np.linspace(0, n - 1, target_len).astype(np.int64)
        return chunk[idx].astype(np.float32)


    def start(self):
        """Start recording audio."""
        if self.recording:
            return
        self._frames = []
        self._sample_rate = config.SAMPLE_RATE
        self.recording = True
        try:
            device_name = getattr(config, "MIC_DEVICE_NAME", None)
            device_idx = _resolve_device(device_name)
            log.info("Opening mic: name=%s resolved_idx=%s", device_name, device_idx)

            # Always try 16000 Hz first (what Whisper expects)
            sample_rate = config.SAMPLE_RATE
            try:
                self._stream = sd.InputStream(
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                    device=device_idx,
                    callback=self._callback,
                )
                self._stream.start()
                self._sample_rate = sample_rate
                return
            except (sd.PortAudioError, OSError):
                log.info("Device does not support %d Hz, trying native rate", sample_rate)

            # Fall back to device default sample rate + resample later
            if device_idx is not None:
                dev_info = sd.query_devices(device_idx)
                sample_rate = int(dev_info.get("default_samplerate", 48000))
            else:
                sample_rate = 48000
            log.info("Using device native sample rate: %d Hz", sample_rate)

            self._stream = sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
                device=device_idx,
                callback=self._callback,
            )
            self._stream.start()
            self._sample_rate = sample_rate
        except (sd.PortAudioError, OSError, Exception) as exc:
            log.error("Failed to open microphone: %s", exc)
            self.recording = False
            self._stream = None
            if self.on_mic_error:
                self.on_mic_error("🎤 No microphone detected")

    def stop(self):
        """Stop recording and return audio as numpy array."""
        if not self.recording:
            return None
        self.recording = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._frames:
            return None
        audio = np.concatenate(self._frames, axis=0).flatten()

        # Resample to 16kHz if recorded at a different rate
        target_rate = config.SAMPLE_RATE
        if self._sample_rate != target_rate:
            duration = len(audio) / self._sample_rate
            target_len = int(duration * target_rate)
            indices = np.linspace(0, len(audio) - 1, target_len)
            audio = np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)
            log.info("Resampled audio from %d Hz to %d Hz", self._sample_rate, target_rate)

        return audio
