from core import config
"""
Murmur v2 — Main Window

Hybrid Design: Material Design 3 + Apple HIG
"""

import os
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTabWidget, QListWidget,
    QListWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap

from ui.design import DesignTokens, get_stylesheet
from ui.gear import make_gear_pixmap


class MainWindow(QMainWindow):
    """Main application window with Hybrid Design."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Murmur")
        self.setMinimumSize(480, 520)
        self.resize(560, 620)

        icon_path = config.icon_path("murmur.ico")
        self.setWindowIcon(QIcon(icon_path))
        self.setStyleSheet(get_stylesheet(is_dark=False))

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # ── Header: title + settings button ─────────────────────────────
        header = QHBoxLayout()
        logo_lbl = QLabel()
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "murmur.png")
        if os.path.exists(icon_path):
            logo_lbl.setPixmap(QPixmap(icon_path).scaled(
                26, 26, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        header.addWidget(logo_lbl)
        header.addSpacing(8)
        title = QLabel("Murmur")
        title.setStyleSheet(f"font-size: {DesignTokens.Fonts.HEADLINE_LARGE}px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch()
        self.settings_btn = QPushButton()
        self.settings_btn.setFixedSize(36, 36)
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setIcon(QIcon(make_gear_pixmap(28)))
        self.settings_btn.setIconSize(self.settings_btn.size())
        self.settings_btn.setStyleSheet(self._gear_style())
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self.open_settings)
        header.addWidget(self.settings_btn)
        layout.addLayout(header)

        # ── Record indicator (animated dot-grid wave) ─────────────────────
        from ui.record_indicator import RecordIndicator
        self.record_btn = RecordIndicator()
        self.record_btn.setToolTip("Hold the hotkey, or click to toggle")
        self.record_btn.clicked.connect(self.toggle_recording)
        layout.addWidget(self.record_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        # ── Status ──────────────────────────────────────────────────────
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(
            f"color: {DesignTokens.Light.ON_SURFACE_VARIANT}; font-size: 12px;")
        layout.addWidget(self.status_label)

        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #E8EAED;")
        layout.addWidget(divider)

        # ── Tabs ────────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_transcriptions_tab(), "Transcriptions")
        self.tabs.addTab(self._create_dictionary_tab(), "Dictionary")
        self.tabs.addTab(self._create_logs_tab(), "Logs")
        layout.addWidget(self.tabs)

        self.is_recording = False
        self._settings_callback = None
        self._command_callback = None
        self._dictionary = None          # set by app
        self._log_handler = None         # set by app

        # Timer to drain log lines into the GUI
        self._log_timer = QTimer()
        self._log_timer.timeout.connect(self._drain_logs)
        self._log_timer.start(500)

    # ── Public wiring (called by MurmurApp) ──────────────────────────

    def set_dictionary(self, dictionary):
        self._dictionary = dictionary
        self._refresh_dictionary()

    def set_log_handler(self, handler):
        self._log_handler = handler
        self._flush_log_snapshot()

    def set_settings_callback(self, cb):
        self._settings_callback = cb
    def set_command_callback(self, cb):
        self._command_callback = cb

    def open_command_mode(self):
        if self._command_callback:
            self._command_callback()


    def open_settings(self):
        if self._settings_callback:
            self._settings_callback()

    # ── Tabs ─────────────────────────────────────────────────────────

    def _create_transcriptions_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        self.transcript_list = QListWidget()
        self.transcript_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; font-size: 13px; }
            QListWidget::item { border-bottom: 1px solid #E8EAED; padding: 10px 6px; }
        """)
        layout.addWidget(self.transcript_list)

        self.transcript_empty = QLabel("No recordings yet.\nPress and hold the hotkey, then speak.")
        self.transcript_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.transcript_empty.setStyleSheet(
            f"color: {DesignTokens.Light.ON_SURFACE_VARIANT}; border: none;")
        layout.addWidget(self.transcript_empty)
        self.transcript_empty.hide()

        return widget

    def _create_dictionary_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        # Add form
        form = QHBoxLayout()
        self.dict_key_input = QLineEdit()
        self.dict_key_input.setPlaceholderText("Spoken form (e.g. 'my-app')")
        form.addWidget(self.dict_key_input, 2)
        self.dict_value_input = QLineEdit()
        self.dict_value_input.setPlaceholderText("Written form (e.g. 'MyApp')")
        form.addWidget(self.dict_value_input, 2)
        add_btn = QPushButton("Add")
        add_btn.setStyleSheet(self._primary_style())
        add_btn.clicked.connect(self._add_dictionary_entry)
        form.addWidget(add_btn)
        layout.addLayout(form)

        # Entry list
        self.dict_list = QListWidget()
        self.dict_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; font-size: 13px; }
            QListWidget::item { border-bottom: 1px solid #E8EAED; padding: 8px 4px; }
        """)
        layout.addWidget(self.dict_list)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.setStyleSheet(self._secondary_style())
        remove_btn.clicked.connect(self._remove_dictionary_entry)
        layout.addWidget(remove_btn)

        return widget

    def _create_logs_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        self.log_list = QListWidget()
        self.log_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; font-size: 11px;
                font-family: monospace; color: #3C4043; }
        """)
        self.log_list.setWordWrap(True)
        layout.addWidget(self.log_list)

        clear_btn = QPushButton("Clear Logs")
        clear_btn.setStyleSheet(self._secondary_style())
        clear_btn.clicked.connect(self.log_list.clear)
        layout.addWidget(clear_btn)

        return widget

    # ── Dictionary actions ───────────────────────────────────────────

    def _refresh_dictionary(self):
        if self._dictionary is None:
            return
        self.dict_list.clear()
        for spoken, written in sorted(self._dictionary.get_all().items()):
            item = QListWidgetItem(f"{spoken}  \u2192  {written}")
            item.setData(Qt.ItemDataRole.UserRole, spoken)
            self.dict_list.addItem(item)

    def _add_dictionary_entry(self):
        spoken = self.dict_key_input.text().strip()
        written = self.dict_value_input.text().strip()
        if not spoken or not written:
            QMessageBox.information(self, "Dictionary", "Enter both spoken and written forms.")
            return
        if self._dictionary is not None:
            self._dictionary.add(spoken, written)
        self.dict_key_input.clear()
        self.dict_value_input.clear()
        self._refresh_dictionary()

    def _remove_dictionary_entry(self):
        item = self.dict_list.currentItem()
        if item is None:
            return
        spoken = item.data(Qt.ItemDataRole.UserRole)
        if self._dictionary is not None and spoken:
            self._dictionary.remove(spoken)
        self._refresh_dictionary()

    # ── Logs ─────────────────────────────────────────────────────────

    def _drain_logs(self):
        if self._log_handler is None:
            return
        for line in self._log_handler.drain():
            self.log_list.addItem(line)
            # Trim old entries
            while self.log_list.count() > 400:
                self.log_list.takeItem(0)
            self.log_list.scrollToBottom()

    def _flush_log_snapshot(self):
        if self._log_handler is None:
            return
        for line in self._log_handler.snapshot():
            self.log_list.addItem(line)

    # ── Transcript handling ──────────────────────────────────────────

    def add_transcript(self, record: dict):
        self.transcript_empty.hide()
        item = QListWidgetItem(f"{record['time']}  \u00b7  {record['text']}")
        item.setToolTip(record['text'])
        self.transcript_list.insertItem(0, item)

    # ── Record state ─────────────────────────────────────────────────

    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        self.is_recording = True
        self.record_btn.set_recording(True)
        self.record_btn.setToolTip("Recording — release hotkey to finish")
        self.status_label.setText("Listening...")

    def stop_recording(self):
        self.is_recording = False
        self.record_btn.set_recording(False)
        self.record_btn.setToolTip("Hold the hotkey, or click to toggle")
        self.status_label.setText("Processing...")
        QTimer.singleShot(1000, lambda: self.status_label.setText("Ready"))

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    # ── Styles ───────────────────────────────────────────────────────

    def _gear_style(self) -> str:
        # Modern: plain icon, subtle hover, no box
        return f"""
            QPushButton {{
                background: transparent;
                color: {DesignTokens.Light.ON_SURFACE_VARIANT};
                font-size: 20px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {DesignTokens.Light.SURFACE_VARIANT};
                border-radius: {DesignTokens.Radius.FULL}px;
                color: {DesignTokens.Light.PRIMARY};
            }}
        """

    def _primary_style(self) -> str:
        return f"""
            QPushButton {{
                background-color: {DesignTokens.Light.PRIMARY};
                color: white;
                border: none;
                border-radius: {DesignTokens.Radius.FULL}px;
                padding: 8px 18px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {DesignTokens.Light.PRIMARY_VARIANT}; }}
        """

    def _secondary_style(self) -> str:
        return f"""
            QPushButton {{
                background-color: {DesignTokens.Light.SURFACE_VARIANT};
                color: {DesignTokens.Light.ON_SURFACE_VARIANT};
                border: 1px solid {DesignTokens.Light.OUTLINE};
                border-radius: {DesignTokens.Radius.FULL}px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                border-color: {DesignTokens.Light.PRIMARY};
                color: {DesignTokens.Light.PRIMARY};
            }}
        """

    def _chip_style(self) -> str:
        return f"""
            QPushButton {{
                background: {DesignTokens.Light.SURFACE_VARIANT};
                color: {DesignTokens.Light.ON_SURFACE_VARIANT};
                border: 1px solid {DesignTokens.Light.OUTLINE};
                border-radius: {DesignTokens.Radius.FULL}px;
                padding: 4px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {DesignTokens.Light.SURFACE};
                border-color: {DesignTokens.Light.PRIMARY};
                color: {DesignTokens.Light.PRIMARY};
            }}
        """

