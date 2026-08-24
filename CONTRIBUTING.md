# Contributing to Murmur

Thanks for your interest in contributing! Murmur is a local, offline voice dictation app for Windows.
Every contribution matters — code, bug reports, translations, docs, or just feedback.

## Project basics

- **Language:** English (UI strings can be German/English; code, comments and docs in English).
- **Stack:** Python 3.12, PyQt6, faster-whisper (CTranslate2), optional Ollama.
- **Repository:** https://github.com/Greeny-cmd/murmur
- **License:** MIT

## Getting started

1. Fork the repo and clone your fork.
2. Set up the environment:
   ```bash
   uv venv .venv
   uv pip install --python .venv/Scripts/python.exe -r requirements.txt
   ```
3. Run the app:
   ```bash
   .venv/Scripts/pythonw.exe main.py   # no console
   # or
   .venv/Scripts/python.exe main.py    # console output for debugging
   ```
4. Hold **AltGr** to dictate, hold **Scroll Lock** to rewrite a selection.

### GPU note
Whisper/ASR runs on AMD ROCm, NVIDIA CUDA, or CPU fallback. On AMD, faster-whisper
needs the ROCm CTranslate2 wheel (see the ROCm section in the README). On NVIDIA use the CUDA build.

## Tests

```bash
.venv/Scripts/python.exe -m pytest
```

Please keep tests passing before opening a pull request.

## How to contribute

### Reporting bugs
Open an [issue](https://github.com/Greeny-cmd/murmur/issues) and include:

- Windows version and whether you're on a GPU (ROCm / CUDA / CPU only).
- ASR engine + model in use (Settings → Speech Model).
- Steps to reproduce.
- Relevant log output. Logs are disabled by default; enable **Settings → Behaviour → Logging**,
  then check `%LOCALAPPDATA%\Murmur\murmur.log`.

### Feature requests / ideas
Open an issue with a clear description of the use case. We keep things 100% local and offline,
so cloud dependencies are out of scope.

### Code / pull requests
- Fork + branch, then open a PR with a clear description.
- Keep changes focused; one feature/fix per PR.
- `main.py`, `core/` and `ui/` hold the app logic — no legacy fork files.
- Match the existing code style (PyQt6, clear method names, concise comments).

## Design

The UI follows a Google Material × Apple HIG hybrid. Reusable design tokens live in
`ui/design.py`. Dropdowns must use `.activated` (not `currentIndexChanged`) so scrolling
never silently changes a setting.

## Code of conduct

Be kind and constructive. Harassment, racism, sexism or similar won't be tolerated.