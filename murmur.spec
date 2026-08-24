# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Murmur v2 (windowed, onedir portable bundle)."""

import os

# Application entry point
a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Bundle icons under 'ui/icons' so config.icon_path() resolves them
        # in the frozen bundle (_MEIPASS/ui/icons/...).
        ('ui/icons', 'ui/icons'),
    ],
    hiddenimports=[
        # faster-whisper / ctranslate2 dynamically-imported submodules
        'faster_whisper',
        'faster_whisper.transcribe',
        'faster_whisper.decode',
        'faster_whisper.vad',
        'faster_whisper.audio',
        'ctranslate2',
        'tokenizers',
        'onnxruntime',
        'av',
        # PyQt plugins/dynamic modules
        'PyQt6.QtGui',
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtSvg',
        # sherpa-onnx (optional ASR engine)
        'sherpa_onnx',
        # audio
        'sounddevice',
        'pynput.keyboard',
        'pynput.mouse',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pandas', 'scipy', 'matplotlib', 'sklearn', 'IPython', 'jupyter',
        'pytest', 'tkinter',
    ],
    noarchive=False,
)

# Icon for the exe (murmur.ico)
icon = 'ui/icons/murmur.ico'
if not os.path.exists(icon):
    icon = None

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Murmur',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # windowed — no console window (matches pythonw)
    disable_windowed_traceback=False,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Murmur',
)