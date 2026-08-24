<p align="center">
  <img src="ui/icons/murmur.png" width="120" alt="Murmur logo">
</p>

<h1 align="center">Murmur v2</h1>

<p align="center">
  <strong>Lokale Sprachdiktat-Anwendung für Windows — sprich, und der Text erscheint direkt am Cursor. 100&nbsp;% offline, keine Cloud, kein Login.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows%2011-0078D6?logo=windows" alt="Windows 11">
  <img src="https://img.shields.io/badge/python-3.12-3776AB?logo=python" alt="Python 3.12">
  <img src="https://img.shields.io/badge/GPU-AMD%20ROCm%20%2B%20NVIDIA%20CUDA-orange" alt="ROCm/CUDA">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT">
</p>

<p align="center">
  Murmur ist ein lokaler, datenschutzfreundlicher Diktat-Assistent. Du hältst eine Taste, sprichst,
  und der Text wird direkt in die aktuell fokussierte Anwendung eingefügt — ohne dass dein Audio je
  deinen Rechner verlässt. Es ist speziell für die gute Erkennung von Deutsch und Englisch optimiert
  und läuft vollständig auf **AMD ROCm** sowie **NVIDIA CUDA** GPUs (mit CPU-Fallback).
</p>

---

## ✨ Funktionen

- **Diktat am Cursor** — Halte die Diktier-Taste (Standard: **AltGr**), sprich, und der Text wird mit Win32-Clipboard-Injection in das aktuell fokussierte Fenster eingefügt.
- **Live-Transkription** — Während du sprichst, siehst du deine gesprochenen Wörter in Echtzeit im Overlay (optional, in den Einstellungen aktivierbar).
- **Sprach-Erkennung** — Auto-Detect für **Deutsch & Englisch**; du kannst eine Sprache in den Einstellungen erzwingen, um die Genauigkeit zu maximieren.
- **Rewrite-Modus** — Markiere Text, halte die Rewrite-Taste (**Scroll Lock**), sprich eine Anweisung (z.&nbsp;B. *"mach das formeller"*), und ein lokales LLM (Ollama) schreibt den Text um — mit editierbarer, automatisch aktualisierender Vorschau.
- **Voice-Commands** — Sage z.&nbsp;B. *"Open YouTube"*, um eine Anwendung oder Webseite zu starten. Mit editierbaren Aliassen.
- **Text-Expansion-Snippets** — Erstelle Kürzel wie `NYC → New York City` (oder ganze Absätze), die beim Sprechen mitten im Satz expandiert werden.
- **LLM-Textverbesserung (optional)** — Satzzeichen, Grammatik & Füller per lokalem Ollama-Modell (Standard: `gemma2:2b`). Sprach-treu (übersetzt Deutsch/Englisch nicht).
- **Symbol- & Buchstabier-Modus** — Sage *"forward slash"* → `/`, *"one two three"* → `123`.
- **Phonetisches Alias-System** — Gleiche Befehle über mehrere Aussprachen.
- **Wörterbuch** — Eigene Begriffe/Eigennamen, die Whisper zuverlässig transkribieren soll. Import/Export als JSON.
- **Persistente Einstellungen + Import/Export** — Dictionary, Settings und Snippets lassen sich als JSON sichern/teilen.
- **System-Tray + Autostart** — Läuft unsichtbar im Tray, optionaler Autostart beim Windows-Login (ohne Konsolenfenster).
- **Google-Material-Design** — Modernes, abgerundetes UI (Material × Apple HIG-Hybrid).

---

## 📦 Was es braucht

| Komponente | Anforderung |
|---|---|
| Betriebssystem | **Windows 10/11** (getestet auf Windows 11) |
| Python | **3.12** (venv empfohlen) |
| GPU (empfohlen) | AMD **ROCm** **oder** NVIDIA **CUDA** — für schnelle Whisper-Transkription; ohne GPU funktioniert es **CPU-Fallback** |
| RAM | ≥ 8 GB (16 GB empfohlen) |
| Mikrofon | Jedes Eingabegerät (Test, z.&nbsp;B. mit 48 kHz) |
| [Ollama](https://ollama.com) (nur für Rewrite/LLM-Cleanup) | Optional — nur nötig, wenn du die LLM-Funktionen aktivierst |

> **Hinweis:** Whisper-Modelle werden beim ersten Start automatisch heruntergeladen (Modelle: `base` Standard, wählbar `tiny/base/small/medium/large-v3`).

---

## 🚀 Installation & Start (aus dem Quellcode)

```bash
git clone https://github.com/Greeny-cmd/murmur.git
cd murmur

# venv erstellen + Abhängigkeiten installieren
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt

# Start (pythonw = ohne Konsolenfenster; python = mit Konsolenausgabe zum Debuggen)
.venv/Scripts/pythonw.exe main.py
```

Alternativ unter Windows:
```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\pythonw.exe main.py
```

---

## 🎮 Hotkeys (Standard)

| Aktion | Taste | Beschreibung |
|---|---|---|
| Diktieren | **AltGr** (Right Alt) | Halten → sprechen → loslassen |
| Rewrite | **Scroll Lock** | Halten → Anweisung sprechen → loslassen |
| Beides frei belegenbar | — | In Einstellungen: Preset-Dropdown *oder* eigene Tastenkombination aufnehmen (inkl. Combo wie `Win+Ctrl+H`) |

---

## 🟠 ROCm-Unterstützung (AMD-GPUs)

**Murmur unterstützt AMD-GPUs nativ über ROCm.** Getestet mit einer **AMD Radeon RX 9070 (16 GB)** unter Windows 11.

faster-whisper (via ctranslate2) läuft dabei als `cuda`-Gerät mit `float16` — für AMD ist das der ROCm-Build. Einrichtung:

1. **ROCm-ctranslate2-Wheel** installieren (statt des Standard-PyPI-Builds) — z.&nbsp;B. das `rocm-python-wheels-Windows`-Release von OpenNMT für `cp312`:
   ```bash
   uv pip install --python .venv/Scripts/python.exe <pfad-zu>/ctranslate2-*-rocm.whl
   ```
2. **`hipblas.dll`-Alias** in die `site-packages`-Verzeichnis kopieren (faster-whisper erwartet die DLL unter diesem Namen).
3. Der Code registriert die Hinweis-Verzeichnisse automatisch über `os.add_dll_directory`, **bevor** ctranslate2 importiert wird.

Die GPU wird beim Start automatisch erkannt (`Whisper model loaded on cuda`). In den Einstellungen kannst du das Gerät auf **Auto / GPU / CPU** umschalten.

**NVIDIA:** Der gleiche Code erkennt NVIDIA-GPUs (CUDA-ctranslate2) — für eine reine NVIDIA-Distribution ersetzt du das ROCm-Wheel durch den CUDA-Build.

---

## 🖥️ Getestete Hardware

| Komponente | System |
|---|---|
| GPU | **AMD Radeon RX 9070 16 GB** (ROCm) |
| CPU | moderne x86_64 (Mehrkern) |
| OS | Windows 11 (Build 22H2+) |
| Python | 3.12 |
| ASR | faster-whisper `small`/`base` (GPU, float16) |

---

## 🔧 Technologie-Stack

- **PyQt6** — GUI (Google-Material-Design System)
- **faster-whisper** (CTranslate2) — Sprachmodell (AMD ROCm / NVIDIA CUDA / CPU)
- **Parakeet (sherpa-onnx)** — alternative, schnellere ASR-Engine
- **Ollama** — lokales LLM für Rewrite & Textverbesserung (Standard `gemma2:2b`)
- **ctypes / Win32** — Clipboard-Injection, Hotkeys, Autostart

---

## 🧪 Tests

```bash
.venv/Scripts/python.exe -m pytest
```

---

## 📄 Lizenz

[MIT](LICENSE) — frei für private & kommerzielle Nutzung.

---

> **Datenschutz:** Murmur ist zu 100 % lokal. Deine Diktate verlassen deinen Rechner nicht. Die LLM-Funktionen laufen ausschließlich gegen dein lokales Ollama.