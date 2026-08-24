<div align="center">

<img src="ui/icons/murmur.png" width="110" alt="Murmur logo">

# Murmur v2

**Local voice dictation for Windows — speak, and the text appears right at your cursor. 100% offline, no cloud, no login.**

[![Windows 11](https://img.shields.io/badge/platform-Windows%2011-0078D6?logo=windows)](https://github.com/Greeny-cmd/murmur)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python)](https://github.com/Greeny-cmd/murmur)
[![AMD ROCm / NVIDIA CUDA](https://img.shields.io/badge/GPU-ROCm%20%2B%20CUDA-orange)](https://github.com/Greeny-cmd/murmur)
[![MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

⚠️ **Portable build available** → **click [Murmur-v1.0.0-win64.zip](https://github.com/Greeny-cmd/murmur/releases/download/v1.0.0/Murmur-v1.0.0-win64.zip) (140 MB)** — unzip, run `Murmur\Murmur.exe`, done. No Python needed.

[🔗 Releases & all downloads](https://github.com/Greeny-cmd/murmur/releases)

</div>

---

**Murmur** is a private, offline dictation assistant. Hold a key, speak, and the text is injected straight into the focused app — your audio never leaves your machine. It is tuned for great German and English recognition and runs fully on **AMD ROCm** and **NVIDIA CUDA** GPUs (with CPU fallback).

---

## <img src="assets/section-icon.png" width="22" align="center"> Features

- **Dictate at the cursor** — Hold the dictation key (default **AltGr**), speak, and the text is inserted into the focused window via Win32 clipboard injection.
- **Live transcription** — See your words appear in real time in the overlay while you speak (optional, enable in Settings).
- **Language detection** — Auto-detect **German & English**; force one language in Settings for maximum accuracy.
- **Rewrite mode** — Select text, hold the rewrite key (**Scroll Lock**), speak an instruction (e.g. *"make this more formal"*), and a local LLM (Ollama) rewrites it — with an editable, auto-refreshing preview.
- **Voice commands** — Say e.g. *"Open YouTube"* to launch an app or website. Editable aliases included.
- **Text expansion snippets** — Create shortcuts like `NYC → New York City` (or whole paragraphs) that expand mid-sentence while dictating.
- **LLM text cleanup (optional)** — Punctuation, grammar & filler via a local Ollama model (default `gemma2:2b`). Language-preserving (won't translate German/English).
- **Symbol & spell mode** — Say *"forward slash"* → `/`, *"one two three"* → `123`.
- **Phonetic alias system** — Same command matched across multiple pronunciations.
- **Dictionary** — Add your own terms/names Whisper should transcribe reliably. Import/export as JSON.
- **Persistent settings + import/export** — Dictionary, settings and snippets can be backed up or shared as JSON.
- **System tray + autostart** — Runs quietly in the tray, optional Windows logon autostart (no console flash).
- **Google Material design** — Modern rounded UI (Material × Apple HIG hybrid).

---

## <img src="assets/section-icon.png" width="22" align="center"> Requirements

| Component | Requirement |
|---|---|
| OS | **Windows 10/11** (tested on Windows 11) |
| Python | **3.12** (venv recommended) |
| GPU (recommended) | AMD **ROCm** **or** NVIDIA **CUDA** for fast Whisper transcription; **CPU fallback** works without a GPU |
| RAM | ≥ 8 GB (16 GB recommended) |
| Microphone | Any input device (tested at 48 kHz) |
| [Ollama](https://ollama.com) (Rewrite/LLM only) | Optional — only needed if you enable the LLM features |

> **Note:** Whisper models are downloaded automatically on first run (`base` default; choose `tiny/base/small/medium/large-v3` in Settings).

---

## <img src="assets/section-icon.png" width="22" align="center"> Install & run (from source)

```bash
git clone https://github.com/Greeny-cmd/murmur.git
cd murmur

# Create venv + install deps
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt

# Run (pythonw = no console; python = console output for debugging)
.venv/Scripts/pythonw.exe main.py
```

Or on Windows with plain pip:
```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\pythonw.exe main.py
```

---

## <img src="assets/section-icon.png" width="22" align="center"> Hotkeys (defaults)

| Action | Key | Description |
|---|---|---|
| Dictate | **AltGr** (Right Alt) | Hold → speak → release |
| Rewrite | **Scroll Lock** | Hold → speak instruction → release |
| Both freely remappable | — | In Settings: preset dropdown *or* record your own key/combo (incl. combos like `Win+Ctrl+H`) |

---

## <img src="assets/section-icon.png" width="22" align="center"> ROCm support (AMD GPUs)

**Murmur supports AMD GPUs natively via ROCm.** Tested with an **AMD Radeon RX 9070 (16 GB)** on Windows 11.

faster-whisper (via CTranslate2) runs as a `cuda` device with `float16` — for AMD that's the ROCm build. Setup:

1. **Install the ROCm CTranslate2 wheel** (instead of the stock PyPI build) — e.g. the `rocm-python-wheels-Windows` release from OpenNMT for `cp312`:
   ```bash
   uv pip install --python .venv/Scripts/python.exe <path-to>/ctranslate2-*-rocm.whl
   ```
2. **Copy `hipblas.dll`** into the `site-packages` directory (faster-whisper expects it under that name).
3. The code registers the DLL directories via `os.add_dll_directory` automatically, **before** CTranslate2 is imported.

The GPU is detected automatically at startup (`Whisper model loaded on cuda`). In Settings you can switch the device to **Auto / GPU / CPU**.

**NVIDIA:** The same code detects NVIDIA GPUs (CUDA CTranslate2) — for a pure NVIDIA distribution, replace the ROCm wheel with the CUDA build.

---

## <img src="assets/section-icon.png" width="22" align="center"> Tested hardware

| Component | System |
|---|---|
| GPU | **AMD Radeon RX 9070 16 GB** (ROCm) |
| CPU | modern x86_64 (multi-core) |
| OS | Windows 11 (Build 22H2+) |
| Python | 3.12 |
| ASR | faster-whisper `small`/`base` (GPU, float16) |

---

## <img src="assets/section-icon.png" width="22" align="center"> Tech stack

- **PyQt6** — GUI (Google Material design system)
- **faster-whisper** (CTranslate2) — speech-to-text (AMD ROCm / NVIDIA CUDA / CPU)
- **Parakeet (sherpa-onnx)** — alternative, faster ASR engine
- **Ollama** — local LLM for rewrite & text cleanup (default `gemma2:2b`)
- **ctypes / Win32** — clipboard injection, hotkeys, autostart

---

## <img src="assets/section-icon.png" width="22" align="center"> Tests

```bash
.venv/Scripts/python.exe -m pytest
```

---

## <img src="assets/section-icon.png" width="22" align="center"> License

[MIT](LICENSE) — free for personal & commercial use.

> **Privacy:** Murmur is 100% local. Your dictations never leave your machine. LLM features run exclusively against your local Ollama.