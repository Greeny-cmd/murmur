"""
Onboarding Wizard — first-run setup.

Walks through: welcome, microphone check, hotkey selection, ASR model.
On completion it persists settings and marks onboarding as done.
"""

import os
import sounddevice as sd
from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QLineEdit, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from core import config
from core import settings_store as store
from ui.settings import SINGLE_KEYS, KEY_COMBOS
from ui.design import DesignTokens
from ui.gear import make_gear_pixmap


class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to Murmur")
        self.setSubTitle("Local voice dictation — everything runs on your machine.")
        lay = QVBoxLayout(self)
        txt = QLabel(
            "Murmur lets you dictate with your voice and have the text appear where your "
            "cursor is.\n\n"
            "• Hold a hotkey, speak, release — text is typed at the cursor\n"
            "• Rewrite any selected text with your voice\n"
            "• Speech-to-text and LLM cleanup run fully locally\n"
            "\nLet's set you up in a minute."
        )
        txt.setWordWrap(True)
        lay.addWidget(txt)

    def validatePage(self):
        return True


class MicrophonePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Microphone")
        self.setSubTitle("Pick the microphone Murmur should listen to.")
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Input device:"))
        self.device_combo = QComboBox()
        self._populate_devices()
        lay.addWidget(self.device_combo)

        test = QPushButton("Test recording (5s)")
        test.clicked.connect(self._test)
        lay.addWidget(test)

        self.status_label = QLabel("")
        lay.addWidget(self.status_label)
        lay.addStretch()

    def _populate_devices(self):
        try:
            devices = sd.query_devices()
            sd._terminate(); sd._initialize()
            for i, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0:
                    self.device_combo.addItem(dev["name"], i)
        except Exception:
            pass

    def _test(self):
        self.status_label.setText("Recording…")
        self.status_label.repaint()
        try:
            idx = self.device_combo.currentData()
            import numpy as np
            duration = 5.0
            rate = 16000
            audio = sd.rec(int(duration * rate), samplerate=rate, channels=1,
                           dtype="float32", device=idx)
            sd.wait()
            rms = float(np.sqrt(np.mean(audio ** 2)))
            ok = "✓ Mic works" if rms > 0.002 else "Mic silent — check it's unmuted"
            self.status_label.setText(ok)
        except Exception as e:
            self.status_label.setText(f"Error: {e}")

    def validatePage(self):
        store.set_setting("MIC_DEVICE_NAME", self.device_combo.currentText())
        return True


class HotkeyPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Push-to-talk hotkey")
        self.setSubTitle("Choose the key you'll hold to dictate.")
        lay = QVBoxLayout(self)
        lay.setSpacing(8)

        group = QButtonGroup(self)

        # Single keys in a 2-column grid so none get clipped
        self.key_buttons = {}
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)
        single_items = list(SINGLE_KEYS.items())[:6]
        for i, (name, vk) in enumerate(single_items):
            btn = QRadioButton(name)
            btn.setMinimumHeight(28)
            btn.setProperty("vk", vk)
            group.addButton(btn)
            if vk == config.HOTKEY:
                btn.setChecked(True)
            self.key_buttons[name] = btn
            grid.addWidget(btn, i // 2, i % 2)
        lay.addLayout(grid)

        comp_label = QLabel("Or a combination:")
        lay.addWidget(comp_label)

        # Combos in a 2-column grid too
        self.combo_buttons = {}
        cgrid = QGridLayout()
        cgrid.setHorizontalSpacing(12)
        cgrid.setVerticalSpacing(4)
        combo_items = list(KEY_COMBOS.items())
        for i, (name, keys) in enumerate(combo_items):
            btn = QRadioButton(name)
            btn.setMinimumHeight(28)
            btn.setProperty("keys", keys)
            group.addButton(btn)
            self.combo_buttons[name] = btn
            cgrid.addWidget(btn, i // 2, i % 2)
        lay.addLayout(cgrid)

        hint = QLabel("Hold this key anywhere to dictate. Release to finish and type at the cursor.")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lay.addSpacing(12)

        # Rewrite hotkey (default Scroll Lock)
        rw_title = QLabel("Rewrite hotkey (to rewrite selected text):")
        rw_title.setStyleSheet("font-weight: 600;")
        lay.addWidget(rw_title)

        self.rw_buttons = {}
        rwg = QButtonGroup(self)
        rw_items = [("Scroll Lock", 0x91), ("F13", 0x7C), ("Right Alt", 0xA5),
                    ("Right Ctrl", 0xA3), ("Right Shift", 0xA1)]
        rw_grid = QGridLayout()
        rw_grid.setHorizontalSpacing(12)
        rw_grid.setVerticalSpacing(4)
        default_rw = getattr(config, "REWRITE_HOTKEY", 0x91)
        for i, (name, vk) in enumerate(rw_items):
            btn = QRadioButton(name)
            btn.setMinimumHeight(28)
            btn.setProperty("vk", vk)
            rwg.addButton(btn)
            if vk == default_rw:
                btn.setChecked(True)
            self.rw_buttons[name] = btn
            rw_grid.addWidget(btn, i // 2, i % 2)
        lay.addLayout(rw_grid)

        rw_hint = QLabel("Hold this key after selecting text, speak an instruction, then release.")
        rw_hint.setWordWrap(True)
        lay.addWidget(rw_hint)
        lay.addStretch()

    def validatePage(self):
        chosen_single = next((n for n, b in self.key_buttons.items() if b.isChecked()), None)
        chosen_combo = next((n for n, b in self.combo_buttons.items() if b.isChecked()), None)
        if chosen_single:
            vk = SINGLE_KEYS[chosen_single]
            store.set_setting("HOTKEY", vk)
            store.set_setting("COMBO_HOTKEY", None)
        rw_chosen = next((n for n, b in self.rw_buttons.items() if b.isChecked()), None)
        if rw_chosen:
            store.set_setting("REWRITE_HOTKEY", self.rw_buttons[rw_chosen].property("vk"))
        elif chosen_combo:
            store.set_setting("HOTKEY", None)
            store.set_setting("COMBO_HOTKEY", list(KEY_COMBOS[chosen_combo]))
        return True


class ModelPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Speech model")
        self.setSubTitle("Choose a Whisper model size. Base is a good default; larger is more accurate.")
        lay = QVBoxLayout(self)

        self.model_combo = QComboBox()
        for m in ["tiny", "base", "small", "medium"]:
            self.model_combo.addItem(m, m)
        idx = self.model_combo.findData(config.WHISPER_MODEL)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        lay.addWidget(self.model_combo)

        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["faster-whisper", "Parakeet"])
        self.engine_combo.setCurrentText(config.ASR_ENGINE)
        lay.addWidget(QLabel("Engine:"))
        lay.addWidget(self.engine_combo)

        hint = QLabel("Start with 'base'. You can change it anytime in Settings.")
        hint.setStyleSheet(f"color: {DesignTokens.Light.ON_SURFACE_VARIANT};")
        lay.addWidget(hint)
        lay.addStretch()

    def validatePage(self):
        store.set_setting("ASR_ENGINE", self.engine_combo.currentText())
        store.set_setting("WHISPER_MODEL", self.model_combo.currentData())
        return True


class OnboardingWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Murmur — First-time setup")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setWindowIcon(QIcon(make_gear_pixmap(24)))

        icon_path = os.path.join(os.path.dirname(__file__), "icons", "murmur.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.addPage(WelcomePage())
        self.addPage(MicrophonePage())
        self.addPage(HotkeyPage())
        self.addPage(ModelPage())

        self.setWindowTitle("Set up Murmur")

    def accept(self):
        # Mark onboarding as done
        store.set_setting("ONBOARDING_DONE", True)
        super().accept()

    def cancel(self):
        # Cancelling still marks it done so it doesn't nag on every launch
        store.set_setting("ONBOARDING_DONE", True)
        super().cancel()