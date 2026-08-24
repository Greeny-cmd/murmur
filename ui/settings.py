"""
Settings Window — comprehensive configuration.

- Push-to-talk (free config + key combos)
- ASR engine + model dropdown + folder picker
- Input language (multi-select)
- LLM cleanup model selection
- Tool calling
- Symbol mode
- Behaviour
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QCheckBox, QFileDialog,
    QListWidget, QListWidgetItem, QAbstractItemView, QScrollArea, QRadioButton,
    QKeySequenceEdit,
    QButtonGroup, QStackedWidget
)
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QFont, QIcon, QPixmap, QKeySequence
from ui.design import DesignTokens
from ui.gear import make_gear_pixmap
from core import config
from core import settings_store as store
from core import keymap


# Language -> whisper code
LANGUAGES = {
    "Auto (detect)": None,
    "English": "en",
    "German": "de",
    "French": "fr",
    "Spanish": "es",
    "Italian": "it",
    "Portuguese": "pt",
    "Dutch": "nl",
    "Polish": "pl",
    "Russian": "ru",
    "Czech": "cs",
    "Turkish": "tr",
    "Japanese": "ja",
    "Korean": "ko",
    "Chinese": "zh",
}

# Whisper model sizes
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v3"]

# Hotkey choices
SINGLE_KEYS = {
    "Right Ctrl": 0xA3,
    "Scroll Lock": 0x91,
    "Right Shift": 0xA1,
    "F13": 0x7C,
    "Right Alt": 0xA5,
    "Left Ctrl": 0xA2,
    "Left Shift": 0xA0,
    "Caps Lock": 0x14,
    "F14": 0x7D,
    "F15": 0x7E,
    "Insert": 0x2D,
    "End": 0x23,
}

# Key combos: display name -> tuple of VK codes
KEY_COMBOS = {
    "Ctrl+Alt+R": (0xA2, 0xA4, 0x52),
    "Ctrl+Shift+R": (0xA2, 0xA0, 0x52),
    "Ctrl+Alt+Space": (0xA2, 0xA4, 0x20),
    "Ctrl+F12": (0xA2, 0x7B),
}


def find_whisper_models_installed():
    """Return list of whisper model sizes that are cached locally."""
    try:
        from faster_whisper import WhisperModel
        import huggingface_hub
        cached = set()
        # Check common hf cache locations for Systran/faster-whisper
        hf_home = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
        if os.path.isdir(hf_home):
            for entry in os.listdir(hf_home):
                if "Systran--faster-whisper-" in entry:
                    cached.add(entry.split("faster-whisper-")[-1])
        return cached
    except Exception:
        return set()


def find_parakeet_models():
    """Return list of Parakeet model directories found."""
    dirs = []
    for path in [
        config.PARAKEET_MODEL_DIR,
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Murmur", "models"),
        os.path.join(os.path.expanduser("~"), ".local", "share", "sherpa-onnx"),
    ]:
        if path and os.path.isdir(path):
            for entry in sorted(os.listdir(path)):
                full = os.path.join(path, entry)
                if os.path.isdir(full):
                    dirs.append(full)
    return dirs


class SettingsWindow(QMainWindow):
    """Settings window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Murmur Settings")
        self.on_live_preview_enabled = None  # set by the app to warm the live model

        # Fixed minimum size (pixels) — the window can't shrink below this, but it
        # IS freely draggable/movable and can be maximized to fullscreen.
        self.setMinimumSize(864, 700)  # 20% wider than before (was 720)
        # Restore last window size, if any.
        try:
            from core import settings_store as _store
            sz = _store.get_setting("SETTINGS_WINDOW_SIZE")
            if isinstance(sz, dict) and sz.get("w") and sz.get("h"):
                self.resize(sz["w"], sz["h"])
            else:
                self.resize(780, 820)
        except Exception:
            self.resize(780, 820)
        icon_path = config.icon_path("murmur.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central = QWidget()
        self.setCentralWidget(central)

        # Scroll area so all content is reachable
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(20)

        # Title with M-logos
        title_row = QHBoxLayout()
        logo_lbl = QLabel()
        logo_path = config.icon_path("murmur.png")
        if os.path.exists(logo_path):
            logo_lbl.setPixmap(QPixmap(logo_path).scaled(
                30, 30, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        else:
            logo_lbl.setText("m")
            logo_lbl.setStyleSheet("color: #1A73E8; font-size: 22px; font-weight: bold;")
        title_row.addWidget(logo_lbl)
        title_row.addSpacing(10)
        title = QLabel("Settings")
        title.setStyleSheet(f"font-size: {DesignTokens.Fonts.DISPLAY_MEDIUM}px; font-weight: bold;")
        title_row.addWidget(title)
        title_row.addStretch()
        layout.addLayout(title_row)

        # Push to Talk
        layout.addWidget(self._build_ptt_section())

        # Speech Model
        layout.addWidget(self._build_asr_section())

        # Language
        layout.addWidget(self._build_language_section())

        # LLM Cleanup
        layout.addWidget(self._build_llm_section())

        # Tool Calling
        layout.addWidget(self._build_tool_section())

        # Symbol Mode
        layout.addWidget(self._build_symbol_section())

        # Behaviour
        layout.addWidget(self._build_behaviour_section())

        # Data (export/import)
        layout.addWidget(self._build_data_section())

        # Text expansion snippets
        layout.addWidget(self._build_snippets_section())

        layout.addStretch()

        scroll.setWidget(container)
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.addWidget(scroll)

        self._load_current_settings()

    # ── Sections ──────────────────────────────────────────────────

    def _build_ptt_section(self) -> QWidget:
        section = self._section("HOTKEYS")
        layout = section.layout()

        # ---- Dictation hotkey ----
        layout.addWidget(self._small_label("Dictation (push to talk):"))
        dict_box = self._build_hotkey_row(
            title="",
            single_key=config.HOTKEY,
            combo=config.COMBO_HOTKEY,
            custom_key="DICT",
        )
        layout.addWidget(dict_box)

        # Hold vs toggle (push-to-talk behaviour)
        self.hold_mode = QCheckBox("Hold the key to record (uncheck for toggle mode)")
        self.hold_mode.setChecked(config.HOLD_TO_RECORD)
        self.hold_mode.toggled.connect(lambda v: store.set_setting("HOLD_TO_RECORD", v))
        layout.addWidget(self.hold_mode)

        # ---- Rewrite hotkey ----
        layout.addWidget(self._small_label("Rewrite selection (hold + speak instruction):"))
        rew_box = self._build_hotkey_row(
            title="",
            single_key=config.REWRITE_HOTKEY,
            combo=config.REWRITE_COMBO,
            custom_key="REWRITE",
        )
        layout.addWidget(rew_box)
        layout.addWidget(self._caption("Hold this key in any app while speaking a rewrite instruction "
                                       "(e.g. \"make this more formal\")."))

        return section

    # ── Reusable hotkey row (preset dropdown OR captured combo) ───────
    def _build_hotkey_row(self, title: str, single_key, combo, custom_key: str):
        """One hotkey editor: a preset dropdown + a quick capture for combos.

        Applies any single key OR arbitrary key combination (including Win).
        `custom_key` is the config namespace prefix: "DICT" or "REWRITE".
        """
        box = QWidget()
        box_l = QVBoxLayout(box)
        box_l.setContentsMargins(0, 0, 0, 0)
        box_l.setSpacing(4)

        mode_row = QHBoxLayout()
        pres = QRadioButton("Use a preset key")
        cust = QRadioButton("Capture my own")
        group = QButtonGroup(self)
        group.addButton(pres); group.addButton(cust)
        mode_row.addWidget(pres)
        mode_row.addWidget(cust)
        mode_row.addStretch()
        box_l.addLayout(mode_row)

        # Preset dropdown (single keys + predefined combos)
        pres_box = QWidget()
        pres_l = QHBoxLayout(pres_box)
        pres_l.setContentsMargins(0, 0, 0, 0)
        cbo = QComboBox()
        cbo.setMinimumWidth(260)
        for name, vk in SINGLE_KEYS.items():
            cbo.addItem(name, ("key", vk))
        for name, keys in KEY_COMBOS.items():
            cbo.addItem(name, ("combo", list(keys)))
        pres_l.addWidget(cbo, 1)
        box_l.addWidget(pres_box)

        # Custom capture (arbitrary keys incl. Win)
        capture_box = QWidget()
        cap_l = QHBoxLayout(capture_box)
        cap_l.setContentsMargins(0, 0, 0, 0)
        cap_edit = QKeySequenceEdit()
        cap_edit.setToolTip("Click, then press a key or combination (e.g. Win+Ctrl+H)")
        capadd = QPushButton("Set")
        cap_l.addWidget(cap_edit, 1)
        cap_l.addWidget(capadd)
        box_l.addWidget(capture_box)

        def apply_preset(idx):
            data = cbo.itemData(idx)
            if not data:
                return
            kind, val = data
            if custom_key == "DICT":
                if kind == "key":
                    store.set_setting("HOTKEY", val); store.set_setting("COMBO_HOTKEY", None)
                else:
                    store.set_setting("HOTKEY", None); store.set_setting("COMBO_HOTKEY", list(val))
            else:
                if kind == "key":
                    store.set_setting("REWRITE_HOTKEY", val); store.set_setting("REWRITE_COMBO", None)
                else:
                    store.set_setting("REWRITE_HOTKEY", None); store.set_setting("REWRITE_COMBO", list(val))

        def apply_capture():
            seq = cap_edit.keySequence()
            vk_list = keymap.sequence_to_vk_list(seq)
            if not vk_list:
                return
            if custom_key == "DICT":
                store.set_setting("HOTKEY", None); store.set_setting("COMBO_HOTKEY", list(vk_list))
            else:
                store.set_setting("REWRITE_HOTKEY", None); store.set_setting("REWRITE_COMBO", list(vk_list))
            cap_edit.clear()

        cbo.activated.connect(apply_preset)
        capadd.clicked.connect(apply_capture)
        pres.toggled.connect(lambda v: pres_box.setVisible(v))
        cust.toggled.connect(lambda v: capture_box.setVisible(v))

        # Restore current selection
        cur_combo = list(combo) if combo else None
        use_custom = cur_combo is not None and not self._is_preset_combo(cur_combo)
        if use_custom:
            cust.setChecked(True)
            pres_box.setVisible(False); capture_box.setVisible(True)
        else:
            pres.setChecked(True)
            pres_box.setVisible(True); capture_box.setVisible(False)
            if cur_combo:
                tgt = ("combo", list(cur_combo))
                for i in range(cbo.count()):
                    if cbo.itemData(i) == tgt:
                        cbo.setCurrentIndex(i); break
            else:
                tgt = ("key", single_key)
                for i in range(cbo.count()):
                    if cbo.itemData(i) == tgt:
                        cbo.setCurrentIndex(i); break

        return box

    def _is_preset_combo(self, keys: list) -> bool:
        return tuple(keys) in [tuple(v) for v in KEY_COMBOS.values()]

    def _build_asr_section(self) -> QWidget:
        section = self._section("SPEECH MODEL")
        layout = section.layout()

        # Use ONE aligned grid so every label/control lines up vertically and
        # horizontally (was several loose QHBox rows with varying widths).
        from PyQt6.QtWidgets import QGridLayout as _G
        grid = _G()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)

        def row(label, widget, r):
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #202124; font-size: 12px;")
            lbl.setMinimumWidth(130)
            grid.addWidget(lbl, r, 0)
            grid.addWidget(widget, r, 1)

        # Microphone
        self.mic_combo = QComboBox()
        self._populate_mic_devices()
        self.mic_combo.setMinimumWidth(320)
        self.mic_combo.activated.connect(self._on_mic_changed)
        cb = QCheckBox("")
        row("Microphone:", self.mic_combo, 0)

        # Engine
        self.asr_combo = QComboBox()
        self.asr_combo.addItem("faster-whisper", "faster-whisper")
        self.asr_combo.addItem("Parakeet", "parakeet")
        idx = self.asr_combo.findData(config.ASR_ENGINE.lower())
        self.asr_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.asr_combo.activated.connect(self._on_engine_changed)
        self.asr_combo.setMinimumWidth(320)
        row("Engine:", self.asr_combo, 1)

        # Whisper device
        self.whisper_dev_combo = QComboBox()
        self.whisper_dev_combo.addItem("Auto (GPU if available)", "auto")
        self.whisper_dev_combo.addItem("GPU", "cuda")
        self.whisper_dev_combo.addItem("CPU", "cpu")
        di = self.whisper_dev_combo.findData(getattr(config, "WHISPER_DEVICE", "auto"))
        self.whisper_dev_combo.setCurrentIndex(di if di >= 0 else 0)
        self.whisper_dev_combo.activated.connect(self._on_whisper_dev_changed)
        self.whisper_dev_combo.setMinimumWidth(320)
        row("Whisper device:", self.whisper_dev_combo, 2)

        # Model
        self.model_combo = QComboBox()
        self.model_combo.activated.connect(self._on_model_selected)
        self.model_combo.setMinimumWidth(320)
        row("Model:", self.model_combo, 3)

        # Parakeet folder picker
        self.pk_folder_label = QLabel(self._short_path(config.PARAKEET_MODEL_DIR))
        self.pk_folder_label.setStyleSheet(f"color: {DesignTokens.Light.SUCCESS}; font-size: 11px;")
        pk_wrap = QWidget()
        pk_h = QHBoxLayout(pk_wrap)
        pk_h.setContentsMargins(0, 0, 0, 0)
        pk_h.addWidget(self.pk_folder_label, 1)
        self.pk_browse_btn = QPushButton("Browse\u2026")
        self.pk_browse_btn.clicked.connect(self._browse_parakeet)
        self.pk_browse_btn.setMinimumWidth(120)
        pk_h.addWidget(self.pk_browse_btn)
        row("Parakeet model:", pk_wrap, 4)

        layout.addLayout(grid)

        self.model_note = QLabel("")
        self.model_note.setStyleSheet(f"color: {DesignTokens.Light.ON_SURFACE_VARIANT}; font-size: 11px;")
        self.model_note.setWordWrap(True)
        layout.addWidget(self.model_note)

        self._populate_model_combo()
        return section

    def _populate_mic_devices(self):
        """Populate the microphone dropdown from available input devices."""
        self.mic_combo.blockSignals(True)
        self.mic_combo.clear()
        self.mic_combo.addItem("Default (system)", None)
        try:
            import sounddevice as sd
            try:
                sd._terminate(); sd._initialize()
            except Exception:
                pass
            devices = sd.query_devices()
            current = config.MIC_DEVICE_NAME
            selected_idx = 0
            for i, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0:
                    name = dev["name"]
                    self.mic_combo.addItem(name, name)
                    if current and current == name:
                        selected_idx = self.mic_combo.count() - 1
            self.mic_combo.setCurrentIndex(selected_idx)
        except Exception as exc:
            from core.logger import log
            log.error("Failed to list devices: %s", exc)
        self.mic_combo.blockSignals(False)

    def _on_mic_changed(self):
        name = self.mic_combo.currentData()
        store.set_setting("MIC_DEVICE_NAME", name)
    def _build_language_section(self) -> QWidget:
        section = self._section("INPUT LANGUAGE")
        layout = section.layout()

        hint = self._caption("For the most accurate results pick ONE language (it's then forced). "
                             "Selecting several uses auto-detect, which is less accurate on small "
                             "Whisper models. Note: Parakeet only supports English.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.lang_list = QListWidget()
        self.lang_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.lang_list.setMaximumHeight(120)
        codes = config.WHISPER_LANGUAGE
        if isinstance(codes, str):
            codes = [codes]
        elif codes is None:
            codes = []
        for label, code in LANGUAGES.items():
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, code)
            # Select if language is in current selection (or Auto when empty)
            if code is None and not codes:
                item.setSelected(True)
            elif code in codes:
                item.setSelected(True)
            self.lang_list.addItem(item)
        self.lang_list.itemSelectionChanged.connect(self._on_language_changed)
        layout.addWidget(self.lang_list)

        return section

    def _build_llm_section(self) -> QWidget:
        section = self._section("LLM CLEANUP")
        layout = section.layout()

        self.llm_enabled = QCheckBox("Enable LLM cleanup (removes fillers, adds punctuation)")
        self.llm_enabled.setChecked(config.LLM_CLEANUP_ENABLED)
        self.llm_enabled.toggled.connect(lambda v: store.set_setting("LLM_CLEANUP_ENABLED", v))
        layout.addWidget(self.llm_enabled)

        # URL + model
        grid = QGridLayout()
        grid.addWidget(QLabel("Ollama URL:"), 0, 0)
        self.ollama_url = QLineEdit(config.OLLAMA_URL)
        self.ollama_url.textChanged.connect(lambda t: store.set_setting("OLLAMA_URL", t or config.OLLAMA_URL))
        grid.addWidget(self.ollama_url, 0, 1)

        grid.addWidget(QLabel("Model:"), 1, 0)
        self.llm_model_combo = QComboBox()
        self._populate_llm_models()
        self.llm_model_combo.activated.connect(self._on_llm_model_selected)
        # Save a custom model typed manually (fires when user leaves the field)
        grid.addWidget(self.llm_model_combo, 1, 1)

        refresh = QPushButton("Refresh")
        refresh.setToolTip("Reload the list of models installed in Ollama")
        refresh.clicked.connect(self._populate_llm_models)
        grid.addWidget(refresh, 1, 2)

        hint = self._caption("Pick a model from your installed Ollama models, or type any.")
        grid.addWidget(hint, 2, 0, 1, 3)

        layout.addLayout(grid)
        layout.addWidget(self._caption("Runs locally via Ollama. No data leaves your machine."))
        return section

    def _build_tool_section(self) -> QWidget:
        section = self._section("VOICE COMMANDS")
        layout = section.layout()

        self.tc_enabled = QCheckBox("Enable voice commands ('Open YouTube', 'Open Notepad'\u2026)")
        self.tc_enabled.setChecked(config.TOOL_CALLING_ENABLED)
        self.tc_enabled.toggled.connect(lambda v: store.set_setting("TOOL_CALLING_ENABLED", v))
        layout.addWidget(self.tc_enabled)

        layout.addWidget(self._small_label("Enabled commands (say \u201cOpen <name>\u201d):"))

        # Command list
        from core.functions import all_commands, ALIASES
        cmds = all_commands()
        self.cmd_checkboxes = {}
        cmd_widget = QWidget()
        cmd_layout = QVBoxLayout(cmd_widget)
        cmd_layout.setContentsMargins(0, 0, 0, 0)
        cmd_layout.setSpacing(2)
        enabled_set = None
        if config.ENABLED_COMMANDS is not None:
            enabled_set = set(config.ENABLED_COMMANDS)

        base_checked = enabled_set is None
        self.alias_edits = {}
        from PyQt6.QtWidgets import QGridLayout as _QGrid, QHBoxLayout as _QH

        # Split commands into two side-by-side groups so far more are visible
        # without scrolling (window is now wider).
        names = sorted(cmds.keys())
        half = (len(names) + 1) // 2
        groups = [names[:half], names[half:]]

        outer = _QH()
        outer.setSpacing(28)

        self.cmd_checkboxes = {}

        for gi, group in enumerate(groups):
            grid = _QGrid()
            grid.setHorizontalSpacing(10)
            grid.setVerticalSpacing(6)
            # Column headers
            hdr_cb = QLabel("On")
            hdr_cmd = QLabel("Command")
            hdr_al = QLabel("Optional aliases")
            for w, fw in ((hdr_cb,34),(hdr_cmd,150),(hdr_al,220)):
                w.setStyleSheet("color:#80868b;font-size:10px;font-weight:600;")
                w.setFixedWidth(fw)
            grid.addWidget(hdr_cb, 0, 0)
            grid.addWidget(hdr_cmd, 0, 1)
            grid.addWidget(hdr_al, 0, 2)

            r = 1
            for name in group:
                cb = QCheckBox(name)
                cb.setChecked(base_checked if enabled_set is None else (name in enabled_set))
                cb.toggled.connect(lambda _, n=name: self._on_command_toggled(n))
                self.cmd_checkboxes[name] = cb
                grid.addWidget(cb, r, 0)
                cmd_lbl = QLabel(name)
                cmd_lbl.setFixedWidth(150)
                cmd_lbl.setStyleSheet("color: #202124; font-size: 12px; font-weight: 600;")
                grid.addWidget(cmd_lbl, r, 1)
                builtin = [a for a in ALIASES.get(name, []) if a != name]
                user = (config.CUSTOM_ALIASES or {}).get(name, [])
                aliases = builtin + [a for a in user if a not in builtin]
                edit = QLineEdit(", ".join(aliases))
                edit.setPlaceholderText("aliases, comma-separated")
                edit.setFixedWidth(220)
                edit.editingFinished.connect(lambda _n=name, _e=edit: self._on_alias_edited(_n, _e))
                self.alias_edits[name] = edit
                grid.addWidget(edit, r, 2)
                r += 1

            outer.addLayout(grid, 1)

        cmd_layout.addLayout(outer)


        # Scroll for long command list
        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setMaximumHeight(320)
        scroll.setWidget(cmd_widget)
        layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        enable_all = QPushButton("Enable All")
        enable_all.setStyleSheet(self._btn_style(False))
        enable_all.clicked.connect(lambda: self._set_all_commands(True))
        disable_all = QPushButton("Disable All")
        disable_all.setStyleSheet(self._btn_style(False))
        disable_all.clicked.connect(lambda: self._set_all_commands(False))
        btn_row.addWidget(enable_all)
        btn_row.addWidget(disable_all)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addWidget(self._caption("Say \u201cOpen YouTube\u201d to launch it in your browser."))
        return section

    def _on_command_toggled(self, name: str):
        """Update the ENABLED_COMMANDS list when a command checkbox toggles."""
        enabled = getattr(config, "ENABLED_COMMANDS", None)
        if enabled is None:
            all_cmds = list(self.cmd_checkboxes.keys())
            enabled = list(all_cmds)
            config.ENABLED_COMMANDS = enabled
        if self.cmd_checkboxes[name].isChecked():
            if name not in enabled:
                enabled.append(name)
        else:
            if name in enabled:
                enabled.remove(name)
        store.set_setting("ENABLED_COMMANDS", enabled)


    def _on_alias_edited(self, name: str, edit):
        """Persist user-edited aliases for a command to CUSTOM_ALIASES."""
        parts = [p.strip().lower() for p in edit.text().split(",") if p.strip()]
        custom = dict(config.CUSTOM_ALIASES or {})
        custom[name] = parts
        config.CUSTOM_ALIASES = custom
        store.set_setting("CUSTOM_ALIASES", custom)

    def _set_all_commands(self, enabled_all: bool):
            """Enable or disable every command."""
            all_cmds = list(self.cmd_checkboxes.keys())
            for name, cb in self.cmd_checkboxes.items():
                cb.blockSignals(True)
                cb.setChecked(enabled_all)
                cb.blockSignals(False)
            config.ENABLED_COMMANDS = list(all_cmds) if enabled_all else []
            store.set_setting("ENABLED_COMMANDS", config.ENABLED_COMMANDS)

    def _build_symbol_section(self) -> QWidget:
        section = self._section("SYMBOL / SPELLING")
        layout = section.layout()

        self.symbol_enabled = QCheckBox("Enable symbol/spelling mode")
        self.symbol_enabled.setChecked(config.SYMBOL_MODE_ENABLED)
        self.symbol_enabled.toggled.connect(lambda v: store.set_setting("SYMBOL_MODE_ENABLED", v))
        layout.addWidget(self.symbol_enabled)
        layout.addWidget(self._caption("Say 'forward slash' → /  •  Say 'one two three' → 123"))
        return section

    def _build_behaviour_section(self) -> QWidget:
        section = self._section("BEHAVIOUR")
        layout = section.layout()

        self.inject_enabled = QCheckBox("Type transcripts into the focused app")
        self.inject_enabled.setChecked(config.INJECT_TEXT)
        self.inject_enabled.toggled.connect(lambda v: store.set_setting("INJECT_TEXT", v))
        layout.addWidget(self.inject_enabled)

        self.history_enabled = QCheckBox("Keep a transcript history")
        self.history_enabled.setChecked(config.KEEP_HISTORY)
        self.history_enabled.toggled.connect(lambda v: store.set_setting("KEEP_HISTORY", v))
        layout.addWidget(self.history_enabled)

        # Live preview toggle (off by default — CPU/GPU-hungry)
        self.live_preview = QCheckBox("Live speech preview while recording")
        self.live_preview.setChecked(config.LIVE_PREVIEW_ENABLED)
        def _on_live_toggle(v):
            store.set_setting("LIVE_PREVIEW_ENABLED", v)
            cb = getattr(self, "on_live_preview_enabled", None)
            if v and cb:
                cb()  # warm the live model so the first recording is live immediately
        self.live_preview.toggled.connect(_on_live_toggle)
        layout.addWidget(self.live_preview)

        # Live preview device (auto = GPU when ROCm available)
        dev_row = QHBoxLayout()
        dev_row.addSpacing(20)
        dev_row.addWidget(QLabel("Live preview device:"))
        self.live_dev_combo = QComboBox()
        self.live_dev_combo.addItem("Auto (GPU if available)", "auto")
        self.live_dev_combo.addItem("CPU", "cpu")
        self.live_dev_combo.addItem("GPU (ROCm)", "cuda")
        idx = self.live_dev_combo.findData(config.LIVE_PREVIEW_DEVICE)
        self.live_dev_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.live_dev_combo.activated.connect(self._on_live_dev_changed)
        dev_row.addWidget(self.live_dev_combo)
        dev_row.addStretch()
        layout.addLayout(dev_row)
        self.live_dev_row = dev_row
        self.live_dev_row.setEnabled(config.LIVE_PREVIEW_ENABLED)
        self.live_preview.toggled.connect(
        lambda v: self.live_dev_row.setEnabled(v))

        # Log file toggle
        self.logging_enabled = QCheckBox("Log to file (murmur.log)")
        self.logging_enabled.setChecked(config.LOG_TO_FILE)
        self.logging_enabled.toggled.connect(self._on_logging_toggled)
        caption = self._caption("A log file helps debugging. Disable it to free up disk space when not needed.")
        layout.addWidget(self.logging_enabled)
        layout.addWidget(caption)

        # Start with Windows (HKCU registry)
        self.autostart_enabled = QCheckBox("Start Murmur when I log in to Windows")
        from core import autostart_windows
        self.autostart_enabled.setChecked(autostart_windows.is_enabled())
        self.autostart_enabled.toggled.connect(self._on_autostart_toggled)
        layout.addWidget(self.autostart_enabled)

        return section

    def _on_autostart_toggled(self, checked: bool):
        from core import autostart_windows
        if checked:
            autostart_windows.enable()
        else:
            autostart_windows.disable()

    # ── Behaviour ─────────────────────────────────────────────────

    def _on_snippet_enabled(self, checked: bool):
        config.SNIPPET_EXPANSION_ENABLED = checked
        store.set_setting("SNIPPET_EXPANSION_ENABLED", checked)

    def _on_whisper_dev_changed(self):
        val = self.whisper_dev_combo.currentData()
        config.WHISPER_DEVICE = val
        store.set_setting("WHISPER_DEVICE", val)

    def _on_live_dev_changed(self):
        name = self.live_dev_combo.currentData()
        store.set_setting("LIVE_PREVIEW_DEVICE", name)
        config.LIVE_PREVIEW_DEVICE = name

    def _on_logging_toggled(self, checked: bool):
        from core import logger
        store.set_setting("LOG_TO_FILE", checked)
        config.LOG_TO_FILE = checked
        logger.set_file_log_enabled(checked)

    def _load_current_settings(self):
        """Highlight current hotkey (handled by _build_hotkey_row directly)."""
        pass

    def _on_engine_changed(self, *args):
        engine = (self.asr_combo.currentData() or "faster-whisper").lower()
        store.set_setting("ASR_ENGINE", engine)
        self._populate_model_combo()

    def _populate_model_combo(self):
            self.model_combo.blockSignals(True)
            self.model_combo.clear()
            if config.ASR_ENGINE.lower() == "parakeet":
                dirs = find_parakeet_models()
                if dirs:
                    for d in dirs:
                        self.model_combo.addItem(os.path.basename(d), d)
                else:
                    self.model_combo.addItem("No Parakeet model found", None)
                self.model_note.setText("Use 'Browse Parakeet Model' to select a downloaded model folder.")
                self.pk_browse_btn.setEnabled(True)
                self.pk_browse_btn.setVisible(True)
            else:
                cached = find_whisper_models_installed()
                for m in WHISPER_MODELS:
                    mark = " (✓ installed)" if m in cached else ""
                    self.model_combo.addItem(f"{m}{mark}", m)
                if config.WHISPER_MODEL:
                    idx = self.model_combo.findData(config.WHISPER_MODEL)
                    if idx >= 0:
                        self.model_combo.setCurrentIndex(idx)
                self.model_note.setText(f"Installed: {', '.join(sorted(cached)) if cached else 'base (auto-downloads on first use)'}")
                self.pk_browse_btn.setVisible(False)
                self.pk_browse_btn.setEnabled(False)
            self.model_combo.blockSignals(False)

    def _on_model_selected(self, _index=None):
        if config.ASR_ENGINE.lower() == "parakeet":
            data = self.model_combo.currentData()
            if data:
                store.set_setting("PARAKEET_MODEL_DIR", data)
        else:
            data = self.model_combo.currentData()
            if data:
                store.set_setting("WHISPER_MODEL", data)

    def _on_rewrite_hotkey(self, index):
        data = self.rewrite_combo.itemData(index)
        if data:
            store.set_setting("REWRITE_HOTKEY", int(data))

    def _on_model_typed(self):
            # Typed text is a custom whisper model name (whisper engine).
            # Strip the display-only " (✓ installed)" suffix so we never
            # save an invalid model name to config.
            import re
            text = self.model_combo.currentText().strip()
            text = re.sub(r"\s*\(✓ installed\)$", "", text)
            if text and config.ASR_ENGINE.lower() != "parakeet":
                store.set_setting("WHISPER_MODEL", text)

    def _browse_parakeet(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Parakeet Model Folder")
        if folder:
            store.set_setting("PARAKEET_MODEL_DIR", folder)
            self.pk_folder_label.setText(self._short_path(folder))
            # Re-check the combo
            self._populate_model_combo()

    def _on_language_changed(self):
        selected = []
        for i in range(self.lang_list.count()):
            item = self.lang_list.item(i)
            if item.isSelected():
                code = item.data(Qt.ItemDataRole.UserRole)
                if code is not None:
                    selected.append(code)
        store.set_setting("WHISPER_LANGUAGE", selected if selected else None)

    def _populate_llm_models(self):
        self.llm_model_combo.clear()
        try:
            import httpx
            r = httpx.get(f"{config.OLLAMA_URL}/api/tags", timeout=3)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                for m in models:
                    self.llm_model_combo.addItem(m)
                if config.OLLAMA_MODEL not in models:
                    self.llm_model_combo.addItem(config.OLLAMA_MODEL)
                self.llm_model_combo.setCurrentText(config.OLLAMA_MODEL)
                return
        except Exception:
            pass
        # Fallback: show configured model
        self.llm_model_combo.addItem(config.OLLAMA_MODEL)
        self.llm_model_combo.setCurrentText(config.OLLAMA_MODEL)

    def _on_llm_model_selected(self, index):
        text = self.llm_model_combo.itemText(index) if index >= 0 else self.llm_model_combo.currentText()
        if text:
            store.set_setting("OLLAMA_MODEL", text)

    def _on_llm_model_typed(self):
        text = self.llm_model_combo.currentText().strip()
        if text:
            store.set_setting("OLLAMA_MODEL", text)

    # ── Helpers ───────────────────────────────────────────────────

    def _short_name(self, name: str) -> str:
        return name.replace("Ctrl+", "^").replace("Shift+", "+")
        # Keep readable: return name.replace("Left ", "L ").replace("Right ", "R ")

    def _short_path(self, path) -> str:
        if not path:
            return "No Parakeet model selected"
        name = os.path.basename(path)
        return f"✓ {name}"

    def _btn_style(self, selected: bool) -> str:
        if selected:
            return f"""
                QPushButton {{
                    background-color: {DesignTokens.Light.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: {DesignTokens.Radius.FULL}px;
                    padding: 4px 10px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {DesignTokens.Light.PRIMARY_VARIANT};
                }}
            """
        return f"""
            QPushButton {{
                background-color: {DesignTokens.Light.SURFACE_VARIANT};
                color: {DesignTokens.Light.ON_SURFACE_VARIANT};
                border: 1px solid {DesignTokens.Light.OUTLINE};
                border-radius: {DesignTokens.Radius.FULL}px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background-color: {DesignTokens.Light.SURFACE};
                border-color: {DesignTokens.Light.PRIMARY};
            }}
        """

    def _caption(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {DesignTokens.Light.ON_SURFACE_VARIANT}; font-size: 11px;")
        lbl.setWordWrap(True)
        return lbl

    def _small_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {DesignTokens.Light.ON_SURFACE_VARIANT}; font-size: 11px; margin-top: 4px;")
        return lbl

    def _build_snippets_section(self) -> QWidget:
        """Editable text-expansion snippets (trigger -> expansion)."""
        from core.snippets import SnippetStore
        self.snippet_store = SnippetStore()
        section = self._section("TEXT EXPANSION SNIPPETS")
        layout = section.layout()

        hint = self._caption(
            "Say a trigger word mid-sentence while dictating and it expands on the fly "
            "(e.g. speaking \"... to NYC ...\" types \"... to New York City ...\"). "
            "Works during normal recording — no extra hotkey needed."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # Enable / disable expansion
        self.snippet_enabled = QCheckBox("Enable text expansion while dictating")
        self.snippet_enabled.setChecked(getattr(config, "SNIPPET_EXPANSION_ENABLED", True))
        self.snippet_enabled.toggled.connect(self._on_snippet_enabled)
        layout.addWidget(self.snippet_enabled)

        self.snippet_rows = []  # QHBoxLayout per row

        def add_row(trigger="", expansion=""):
            row = QHBoxLayout()
            e_t = QLineEdit(trigger)
            e_t.setPlaceholderText("Trigger (e.g. NYC)")
            e_t.setMinimumWidth(120)
            e_x = QLineEdit(expansion)
            e_x.setPlaceholderText("Expansion text / paragraph")
            rm = QPushButton("")
            rm.setFixedSize(34, 34)
            _red = DesignTokens.Light.ERROR
            # Use a pre-generated white cross icon (text glyphs render unreliably).
            _x_p = config.icon_path("delete_x.png")
            if os.path.exists(_x_p):
                from PyQt6.QtGui import QIcon
                rm.setIcon(QIcon(_x_p))
                rm.setIconSize(QSize(20, 20))
            rm.setStyleSheet(
                f"QPushButton {{ background: {_red}; color: #FFFFFF; border: none;"
                f" border-radius: 17px; }}"
                f"QPushButton:hover {{ background: #b3261e; }}"
                f"QPushButton:pressed {{ background: #8f1a13; }}"
            )
            def _remove(_=None, _t=e_t, _x=e_x, _r=row):
                if _r in self.snippet_rows:
                    self.snippet_rows.remove(_r)
                _t.deleteLater(); _x.deleteLater(); rm.deleteLater()
            rm.clicked.connect(_remove)
            row.addWidget(e_t)
            row.addWidget(e_x, 1)
            row.addWidget(rm)
            layout.addLayout(row)
            self.snippet_rows.append(row)

        for trig, exp in self.snippet_store.all().items():
            add_row(trig, exp)

        def do_save():
            st = SnippetStore()
            data = {}
            for row in self.snippet_rows:
                widgets = [row.itemAt(i).widget() for i in range(row.count())]
                eds = [w for w in widgets if isinstance(w, QLineEdit)]
                if len(eds) == 2:
                    trig = eds[0].text().strip()
                    exp = eds[1].text()
                    if trig and exp:
                        data[trig] = exp
            st._snippets = data
            st._save()
            self._info(f"Saved {len(data)} snippets.")

        btn_add = QPushButton("+ Add snippet")
        btn_add.clicked.connect(lambda: add_row("", ""))
        layout.addWidget(btn_add)

        btn_save = QPushButton("Save snippets")
        btn_save.clicked.connect(do_save)
        layout.addWidget(btn_save)

        return section

    def _build_data_section(self) -> QWidget:
        """Export / import dictionary + settings for sharing."""
        section = self._section("DATA")
        layout = section.layout()

        hint = self._caption("Your dictionary and settings live outside the app and survive updates. "
                             "Use Export/Import to back them up or share with others.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # Dictionary
        row = QHBoxLayout()
        row.addWidget(QLabel("Dictionary:"))
        row.addStretch()
        exp_d = QPushButton("Export")
        imp_d = QPushButton("Import")
        exp_d.clicked.connect(self._export_dictionary)
        imp_d.clicked.connect(self._import_dictionary)
        row.addWidget(exp_d)
        row.addWidget(imp_d)
        layout.addLayout(row)

        # Settings
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Settings:"))
        row2.addStretch()
        exp_s = QPushButton("Export")
        imp_s = QPushButton("Import")
        exp_s.clicked.connect(self._export_settings)
        imp_s.clicked.connect(self._import_settings)
        row2.addWidget(exp_s)
        row2.addWidget(imp_s)
        layout.addLayout(row2)

        # Snippets
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Snippets:"))
        row3.addStretch()
        exp_n = QPushButton("Export")
        imp_n = QPushButton("Import")
        exp_n.clicked.connect(self._export_snippets)
        imp_n.clicked.connect(self._import_snippets)
        row3.addWidget(exp_n)
        row3.addWidget(imp_n)
        layout.addLayout(row3)

        # Attribution
        attr = QLabel("Logo: ·Initiale Buchstabe M· by soepratman (via Magnific) — recolored to blue for Murmur")
        attr.setWordWrap(True)
        attr.setStyleSheet(f"color: {DesignTokens.Light.ON_SURFACE_VARIANT}; font-size: 10px;")
        layout.addWidget(attr)

        return section

    def _export_snippets(self):
        import shutil
        from core.snippets import SNIPPETS_FILE
        if not os.path.exists(SNIPPETS_FILE):
            self._info("No snippets to export yet.")
            return
        fname, _ = QFileDialog.getSaveFileName(self, "Export Snippets", "murmur_snippets.json", "JSON (*.json)")
        if fname:
            shutil.copy2(SNIPPETS_FILE, fname)
            self._info(f"Snippets exported to {fname}")

    def _import_snippets(self):
        from core.snippets import SnippetStore, SNIPPETS_FILE
        fname, _ = QFileDialog.getOpenFileName(self, "Import Snippets", "", "JSON (*.json)")
        if fname:
            try:
                import json, shutil
                with open(fname, encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("Not a valid snippets file (expected object of trigger -> expansion).")
                shutil.copy2(fname, SNIPPETS_FILE)
                self._info(f"Snippets imported ({len(data)} entries). Restart to apply.")
            except Exception as exc:
                self._error(f"Import failed: {exc}")

    def _export_dictionary(self):
        import shutil
        from core import dictionary
        src = dictionary.DICTIONARY_FILE
        if not os.path.exists(src):
            self._info("No dictionary to export yet.")
            return
        fname, _ = QFileDialog.getSaveFileName(self, "Export Dictionary", "murmur_dictionary.json", "JSON (*.json)")
        if fname:
            shutil.copy2(src, fname)
            self._info(f"Dictionary exported to {fname}")

    def _import_dictionary(self):
        from core import dictionary
        fname, _ = QFileDialog.getOpenFileName(self, "Import Dictionary", "", "JSON (*.json)")
        if fname:
            try:
                import json, shutil
                with open(fname, encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("Not a valid dictionary file (expected an object of word -> phrase).")
                shutil.copy2(fname, dictionary.DICTIONARY_FILE)
                if hasattr(self, "on_dictionary_changed"):
                    self.on_dictionary_changed(dictionary.DICTIONARY_FILE)
                self._info(f"Dictionary imported ({len(data)} entries). Restart to apply.")
            except Exception as exc:
                self._error(f"Import failed: {exc}")

    def _export_settings(self):
        import shutil
        from core import settings_store
        if not os.path.exists(settings_store.SETTINGS_FILE):
            self._info("No settings file to export.")
            return
        fname, _ = QFileDialog.getSaveFileName(self, "Export Settings", "murmur_settings.json", "JSON (*.json)")
        if fname:
            shutil.copy2(settings_store.SETTINGS_FILE, fname)
            self._info(f"Settings exported to {fname}")

    def _import_settings(self):
        from core import settings_store
        fname, _ = QFileDialog.getOpenFileName(self, "Import Settings", "", "JSON (*.json)")
        if fname:
            try:
                import json, shutil
                with open(fname, encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("Not a valid settings file.")
                shutil.copy2(fname, settings_store.SETTINGS_FILE)
                self._info("Settings imported. Restart to apply.")
            except Exception as exc:
                self._error(f"Import failed: {exc}")

    def _info(self, text):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Murmur", text)

    def _error(self, text):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Murmur", text)

    def closeEvent(self, event):
        """Remember the window size so it's restored next time."""
        try:
            from core import settings_store
            settings_store.set_setting("SETTINGS_WINDOW_SIZE", {
                "w": self.width(), "h": self.height(),
            })
        except Exception:
            pass
        super().closeEvent(event)

    def _section(self, title: str) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet(f"""
            background-color: {DesignTokens.Light.SURFACE};
            border-radius: {DesignTokens.Radius.MD}px;
            padding: 16px;
        """)
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        label = QLabel(title)
        label.setStyleSheet(f"""
            color: {DesignTokens.Light.PRIMARY};
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 1px;
        """)
        layout.addWidget(label)
        return widget