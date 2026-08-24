"""
Murmur v2 — Main Application

Local voice dictation tool for Windows (PyQt6).
PyQt6 + Hybrid Design (Material + Apple).
"""

import sys
import os
import asyncio
import threading
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QAction

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.recorder import Recorder
from core.transcriber import create_transcriber, resolve_language
from core.streaming_transcriber import StreamingTranscriber
from core.injector import inject, save_recovery
from core.dictionary import Dictionary
from core.snippets import SnippetStore
from core.replacements import apply_replacements, deterministic_clean
from core import window_target
from core import keys
from core.llm_cleanup import cleanup, warm_up
from core.command_mode import rewrite as command_rewrite
from core.functions import execute as execute_function
from core.hotkey import HotkeyListener
from core import config
from core import settings_store as store
from core.logger import log

# Windowed (PyInstaller) apps swallow fatal errors with no traceback. Send them
# to the log file so frozen crashes are diagnosable.
import traceback as _tb


def _frozen_excepthook(etype, value, tb):
    try:
        log.error("Unhandled exception:\n%s", "".join(_tb.format_exception(etype, value, tb)))
    except Exception:
        pass
    sys.__excepthook__(etype, value, tb)


if getattr(sys, "frozen", False):
    sys.excepthook = _frozen_excepthook
from ui.main_window import MainWindow
from ui.overlay import RecordingOverlay
from ui.preview import PreviewWindow
from core import gui_log
from ui.settings import SettingsWindow

_VERBS = ["open", "launch", "start", "go to", "show me", "take me to"]


class SignalBridge(QObject):
    """Bridge for thread-safe GUI updates."""
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    transcribing = pyqtSignal()
    completed = pyqtSignal(str)
    error = pyqtSignal(str)
    overlay_state = pyqtSignal(str)
    overlay_text = pyqtSignal(str)
    overlay_level = pyqtSignal(float)
    preview_requested = pyqtSignal(str, str, str)
    preview_result = pyqtSignal(str)


class MurmurApp:
    """Main application controller."""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Murmur")
        self.app.setOrganizationName("Murmur")
        
        # Windows: Set app user model ID for taskbar icon
        if sys.platform == "win32":
            import ctypes
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Murmur.VoiceDictation")
            except Exception:
                pass

        # Apply stylesheet
        from ui.design import get_stylesheet
        self.app.setStyleSheet(get_stylesheet(is_dark=False))

        # Load persisted settings BEFORE creating components
        store.load_settings()

        # Core components
        self.recorder = Recorder()
        self.transcriber = create_transcriber(config.ASR_ENGINE)
        self.streaming = StreamingTranscriber(self.transcriber)
        self.dictionary = Dictionary()
        self.snippets = SnippetStore()
        self.hotkey_listener = None

        # Transcript history
        self.transcripts = []

        # UI
        self.main_window = MainWindow()
        self.overlay = RecordingOverlay()
        self.settings_window = None
        self.tray_icon = None

        # Signal bridge
        self.signals = SignalBridge()
        self.signals.recording_started.connect(self._on_recording_started)
        self.signals.recording_stopped.connect(self._on_recording_stopped)
        self.signals.transcribing.connect(self._on_transcribing)
        self.signals.completed.connect(self._on_completed)
        self.signals.error.connect(self._on_error)
        self.signals.overlay_state.connect(self._on_overlay_state)
        self.signals.overlay_text.connect(self._on_overlay_text)
        self.signals.overlay_level.connect(self._on_overlay_level)
        self.signals.preview_requested.connect(self._on_preview_requested)
        self.signals.preview_result.connect(self._on_preview_result)

        # Recording state
        self._rec_start = 0.0
        self._recording = False
        self._last_text = ""

        # Audio level timer
        self._level_timer = QTimer()
        self._level_timer.timeout.connect(self._update_level)

        self._setup_ui()
        self._setup_hotkey()
        self._setup_tray()

        # Pre-load the Ollama cleanup model in the background so the first
        # dictation doesn't pay for a cold model load.
        if config.LLM_CLEANUP_ENABLED:
            threading.Thread(target=warm_up, daemon=True).start()

        # Pre-load the Whisper STT model in the background so the FIRST
        # dictation is instantly fast (measured: lazy load = ~1.7s cold).
        threading.Thread(target=self._preload_transcriber, daemon=True).start()

        # Pre-load the live-preview model too, so enabling live preview gives
        # real-time words from the very first recording instead of only after
        # the model loads mid-dictation.
        if config.LIVE_PREVIEW_ENABLED:
            threading.Thread(target=self._preload_live_model, daemon=True).start()

    def _preload_live_model(self):
        """Warm the live-preview Whisper model off the GUI thread."""
        try:
            self.streaming._get_live_model()
        except Exception as e:
            log.error("Live-preview model preload failed: %s", e)

    def _preload_transcriber(self):
        """Load the ASR model off the GUI thread so dictations are warm from t0."""
        try:
            self.transcriber.load()
        except Exception as e:
            log.error("Transcriber preload failed: %s", e)

    def _setup_ui(self):
        """Setup the main window."""
        self.main_window.toggle_recording = self.toggle_recording
        self.main_window.set_settings_callback(self._show_settings)
        self.main_window.set_dictionary(self.dictionary)
        # Route logs into the GUI Logs tab
        gui_log.install_gui_log_handler()
        self.main_window.set_log_handler(gui_log.get_gui_handler())

    def _setup_hotkey(self):
        """Setup the hotkey listener."""
        self.hotkey_listener = HotkeyListener(
            on_press_cb=self._on_hotkey_press,
            on_release_cb=self._on_hotkey_release,
        )
        self.hotkey_listener.start()

        # Second hotkey: Rewrite Selection (hold to speak an instruction)
        rw = getattr(config, "REWRITE_HOTKEY", 0x91)
        rw_combo = getattr(config, "REWRITE_COMBO", None)
        rwc = tuple(rw_combo) if rw_combo else None
        dict_combo = tuple(config.COMBO_HOTKEY) if config.COMBO_HOTKEY else None
        # Only start a separate listener when it differs from the dictation hotkey
        # (single-key vs single-key, or effective combo).
        dict_single = getattr(config, "HOTKEY", 0xA5)
        same = False
        if dict_combo or rwc:
            same = dict_combo == rwc
        else:
            same = dict_single == rw
        if not same:
            log.info("Rewrite hotkey listener: key=0x%X combo=%s", rw, rwc)
            self.rewrite_listener = HotkeyListener(
                on_press_cb=self.start_command_mode,
                on_release_cb=self.finish_command_mode,
                key=rw if not rwc else None,
                combo=rwc,
            )
            self.rewrite_listener.start()
        else:
            log.info("Rewrite hotkey same as dictation — skipping separate listener")


    def _on_hotkey_press(self):
        """Handle hotkey press."""
        self._start_recording()

    def _on_hotkey_release(self):
        """Handle hotkey release."""
        self._stop_recording()

    def _setup_tray(self):
        """Setup system tray icon."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        icon_path = config.icon_path("murmur.ico")
        self.tray_icon = QSystemTrayIcon(QIcon(icon_path), self.app)
        tray_menu = QMenu()

        show_action = QAction("Show", self.app)
        show_action.triggered.connect(self.main_window.show)
        tray_menu.addAction(show_action)

        settings_action = QAction("Settings", self.app)
        settings_action.triggered.connect(self._show_settings)
        tray_menu.addAction(settings_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self.app)
        quit_action.triggered.connect(self._quit)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def toggle_recording(self):
        """Toggle recording state."""
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Start recording."""
        import time
        self._rec_start = time.monotonic()
        self._recording = True
        self.recorder.start()
        # Freeze the focused window so injected text always lands here
        # (even if the user clicks elsewhere during the ~1s processing delay)
        self._target_hwnd = window_target.get_foreground_window()
        self.signals.recording_started.emit()
        self.signals.overlay_state.emit("listening")
        self.signals.overlay_text.emit("")  # Clear old text

        # Optional live preview: only stream when enabled (CPU-hungry)
        self.recorder.on_audio = None
        if config.LIVE_PREVIEW_ENABLED:
            self.recorder.on_audio = self.streaming.feed_audio
            self.streaming.start(
                on_partial=self._on_partial_text,
                initial_prompt=self.dictionary.get_initial_prompt(),
            )
        self._level_timer.start(50)
        log.info("Recording started (live_preview=%s)", config.LIVE_PREVIEW_ENABLED)

    def _stop_recording(self):
        """Stop recording."""
        import time
        duration = time.monotonic() - self._rec_start
        self._recording = False
        self.recorder.on_audio = None  # Disconnect audio feed
        # ALWAYS use the recorder as the source of truth for the final
        # transcription. The streaming transcriber is ONLY a
        # parallel live-preview display and must never feed the final result.
        self.streaming.stop()          # stop live-preview thread (ignore its buffer)
        audio = self.recorder.stop()
        self._level_timer.stop()
        self.signals.recording_stopped.emit()
        self.signals.overlay_state.emit("processing")
        log.info("Recording stopped (%.2fs)", duration)

        if audio is not None and len(audio) > 0 and duration >= config.MIN_DURATION:
            self.signals.transcribing.emit()
            threading.Thread(target=self._process_audio, args=(audio,), daemon=True).start()
        else:
            self.signals.overlay_state.emit("idle")
            log.info("Too short or empty, skipping")

    def _update_level(self):
        """Update audio level for overlay."""
        if self._recording and hasattr(self.recorder, '_frames'):
            # Simple RMS calculation
            import numpy as np
            if self.recorder._frames:
                last_frame = self.recorder._frames[-1]
                rms = float(np.sqrt(np.mean(last_frame ** 2)))
                self.signals.overlay_level.emit(min(1.0, rms * 5))

    def _on_partial_text(self, text: str):
        """Handle partial transcription text."""
        log.info("LIVE-PARTIAL: %r", text)
        self.signals.overlay_text.emit(text)

    def _process_audio(self, audio):
        """Process audio through the pipeline (runs in background thread)."""
        try:
            # Transcribe
            initial_prompt = self.dictionary.get_initial_prompt()
            text = self.transcriber.transcribe(audio, initial_prompt)
            if not text:
                self.signals.overlay_state.emit("idle")
                return

            log.info("Raw: %r", text)
            self.signals.overlay_text.emit(text)

            # Apply dictionary
            text = apply_replacements(text, self.dictionary)

            # Text-expansion snippets: expand spoken trigger words mid-sentence
            # (e.g. "... to NYC ..." -> "... to New York City ...").
            if getattr(config, "SNIPPET_EXPANSION_ENABLED", True):
                from core.snippets import expand_snippets_in_text
                text, used_triggers = expand_snippets_in_text(text, self.snippets)
                if used_triggers:
                    log.info("Snippets expanded in text: %s", ", ".join(used_triggers))

            # Fast deterministic cleanup (fillers, spacing, capitalization)
            text = deterministic_clean(text)

            # Optional LLM cleanup — only when explicitly enabled (adds latency).
            # Pass the language Whisper ACTUALLY detected so English stays English
            # and German stays German (never force the configured default).
            if config.LLM_CLEANUP_ENABLED:
                detected_lang = getattr(self.transcriber, "last_detected_language", None)
                loop = asyncio.new_event_loop()
                text = loop.run_until_complete(cleanup(text, language=detected_lang))
                loop.close()

            # Save recovery
            save_recovery(text)

            # Check for tool-calling (e.g., "open youtube")
            if config.TOOL_CALLING_ENABLED and text:
                text = self._try_tool_call(text)

            # Inject — only restore focus if the user switched windows during
            # the processing delay; the common case already has the right app
            # focused, so we avoid flaky reactivation that broke injection.
            target = getattr(self, "_target_hwnd", 0) or 0
            current = window_target.get_foreground_window()
            log.info("Injecting (target=%s, current=%s): %r", target, current, text)
            # Re-activate ONLY if the user switched windows during processing
            # (common case keeps the right app focused -> no flaky reactivation
            # that breaks the cursor context). This also covers long LLM
            # cleanup: if the user clicked away meanwhile, target != current
            # and we bring the ORIGINAL window back before injecting.
            if target and current and current != target and window_target.is_valid(target):
                window_target.activate_window(target)
            inject(text)

            self._last_text = text
            # Store transcript for the UI
            if config.KEEP_HISTORY:
                from datetime import datetime
                self.transcripts.insert(0, {
                    "time": datetime.now().strftime("%H:%M"),
                    "text": text,
                })
                self.main_window.add_transcript(self.transcripts[0])
            self.signals.completed.emit(text)
            self.signals.overlay_state.emit("done")

            # Hide overlay after 3 seconds
            QTimer.singleShot(3000, lambda: self._hide_overlay())

        except Exception as exc:
            log.error("Pipeline error: %s", exc)
            self.signals.error.emit(str(exc))
            self.signals.overlay_state.emit("idle")

    def _try_tool_call(self, text: str) -> str:
        """Try to match text as a voice command.

        Returns the original text if no command was matched, or "" if a
        command was executed (so it is not injected as text).
        """
        from core import functions

        cleaned = text.lower().strip().rstrip(".!?")

        # 1) Explicit verb phrases: "open youtube", "launch calculator", etc.
        for verb in sorted(_VERBS, key=len, reverse=True):
            if cleaned.startswith(verb + " "):
                target = functions.resolve_alias(cleaned[len(verb):].strip())
                if functions.is_command_enabled(target) and functions.execute(target):
                    log.info("Command detected: %r -> %s", text, target)
                    return ""
                break

        # 2) Bare command: the ENTIRE utterance resolves to a command
        #    (single word OR multi-word alias, e.g. "Google docs", "Tox")
        canonical = functions.resolve_alias(cleaned)
        if functions.is_command_enabled(canonical) and functions.execute(canonical):
            log.info("Bare command detected: %r -> %s", text, canonical)
            return ""

        return text


    # ── Command Mode (rewrite selection) ─────────────────────────────

    def start_command_mode(self):
        """Start command mode: capture the focused selection, then record an instruction."""
        import time
        self._command_recording = False

        # Capture the focused app's selection into the clipboard (retry a few times)
        from PyQt6.QtWidgets import QApplication
        clip = QApplication.clipboard()
        self._cmd_selection = ""
        for attempt in range(3):
            try:
                keys.copy_selection()
                time.sleep(0.2)
                self._cmd_selection = clip.text() or ""
            except Exception as e:
                log.error("Command selection capture failed: %s", e)
            if self._cmd_selection.strip():
                break

        if not self._cmd_selection.strip():
            log.warning("Rewrite: no selection captured from focused app")
            self.main_window.status_label.setText("No text selected — select text, then retry Rewrite.")
            self.signals.overlay_text.emit("No text selected — re-select and retry Rewrite")
            self.signals.overlay_state.emit("done")
            QTimer.singleShot(3000, self._hide_overlay)
            return

        # Start recording the spoken instruction
        self._command_recording = True
        self._rec_start = time.monotonic()
        self._recording = True
        self.recorder.start()
        self.recorder.on_audio = self.streaming.feed_audio
        self.streaming.start(on_partial=self._on_partial_text)
        self._level_timer.start(50)
        self.signals.overlay_state.emit("listening")
        self.signals.overlay_text.emit("")
        self.main_window.status_label.setText("Speak an instruction (e.g. 'make this more formal')…")
        log.info("Command mode: recording instruction")

    def finish_command_mode(self):
        """Transcribe the instruction, rewrite, and show a preview."""
        try:
            # Use the proven recorder path (same as dictation) for the
            # instruction audio; streaming.stop() tended to return empty.
            audio = self.recorder.stop()
        except Exception:
            audio = None
        # stop any live-preview streaming thread (its audio is not used here)
        try:
            self.streaming.stop()
        except Exception:
            pass
        self.recorder.on_audio = None
        self._level_timer.stop()
        self.signals.overlay_state.emit("idle")
        self._command_recording = False

        if audio is None or len(audio) < 1:
            self.main_window.status_label.setText("Nothing recorded. Try again.")
            return

        # Transcribe the instruction
        try:
            instruction = self.transcriber.transcribe(audio, self.dictionary.get_initial_prompt())
        except Exception as e:
            instruction = ""
            log.error("Command instruction transcription failed: %s", e)

        if not instruction:
            self.main_window.status_label.setText("Couldn't hear the instruction.")
            return
        log.info("Command instruction: %r", instruction)

        # Rewrite via local LLM
        self.main_window.status_label.setText("Rewriting…")
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            from core.transcriber import resolve_language
            rewritten = loop.run_until_complete(command_rewrite(self._cmd_selection, instruction, language=resolve_language()))
            loop.close()
        except Exception as e:
            log.error("Rewrite failed: %s", e)
            rewritten = self._cmd_selection

        self.signals.preview_requested.emit(self._cmd_selection, instruction, rewritten)

    def _on_preview_requested(self, original, instruction, rewritten):
        # Runs on the GUI thread (queued via the signal)
        self._show_command_preview(original, instruction, rewritten)

    def _show_command_preview(self, original: str, instruction: str, rewritten: str):
        """Show a non-modal preview with Apply/Undo/Close (stays open)."""
        win = PreviewWindow(self.main_window)
        win.set_original(original)
        win.set_instruction(instruction)
        win.set_status("")
        win.set_rewritten(rewritten)
        win.set_apply_callback(lambda text: self._apply_text_to_selection(text))
        win.set_regen_callback(lambda instr: self._regen_preview(instr))
        # keep a reference so the window isn't garbage-collected
        self._cmd_preview = win
        win.show()
        win.raise_()
        self.main_window.status_label.setText("Preview: Apply / Undo / Close")
        log.info("Command-mode preview shown")

    def _regen_preview(self, instruction: str):
        """Re-run the rewrite for a new instruction, off the GUI thread."""
        if not instruction:
            self.signals.preview_result.emit("<Enter an instruction first>")
            return
        original = getattr(self, "_cmd_selection", "") or ""

        def worker():
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                try:
                    result = loop.run_until_complete(
                        command_rewrite(original, instruction, language=resolve_language())
                    )
                finally:
                    loop.close()
            except Exception as e:
                log.error("Re-rewrite failed: %s", e)
                result = self._cmd_selection
            self.signals.preview_result.emit(result or "")

        threading.Thread(target=worker, daemon=True).start()

    def _on_preview_result(self, new_rewritten: str):
        # Runs on the GUI thread (queued via the signal)
        win = getattr(self, "_cmd_preview", None)
        if win is not None:
            win.set_rewritten(new_rewritten)
            win.set_status("Updated.")

    def _apply_text_to_selection(self, text: str):
        """Replace the current selection with the given text (target-window locked)."""
        from PyQt6.QtWidgets import QApplication
        import time
        target = getattr(self, "_target_hwnd", 0) or 0
        if target:
            try:
                window_target.try_restore_to(target)
            except Exception:
                pass
        time.sleep(0.05)
        try:
            # selection is still active in the target app, so a plain paste replaces it
            QApplication.clipboard().setText(text)
            keys.paste()
        except Exception as e:
            log.error("Apply rewrite failed: %s", e)
        self.main_window.status_label.setText("Applied.")
        log.info("Applied rewrite: %r", text)

    # ── Signal handlers (run on GUI thread) ──────────────────────────

    def _position_overlay(self):
        """Center the overlay near the bottom of the primary screen."""
        from PyQt6.QtGui import QGuiApplication
        # Force a native window handle so position stores correctly on first run.
        self.overlay.winId()
        screen = QGuiApplication.primaryScreen().geometry()
        ow, oh = self.overlay.width(), self.overlay.height()
        overlay_x = (screen.width() - ow) // 2
        overlay_y = screen.height() - 120  # 120px from bottom
        self.overlay.move(overlay_x, overlay_y)

    def _on_recording_started(self):
        self.main_window.start_recording()
        # Position overlay at screen center-bottom.
        self._position_overlay()

    def _on_recording_stopped(self):
        self.main_window.stop_recording()

    def _on_transcribing(self):
        self.main_window.status_label.setText("Processing...")

    def _on_completed(self, text: str):
        self.main_window.status_label.setText("Ready")

    def _on_error(self, error: str):
        self.main_window.status_label.setText(f"Error: {error}")
        self.signals.overlay_state.emit("idle")

    def _on_overlay_state(self, state: str):
        self.overlay.set_state(state)

    def _on_overlay_text(self, text: str):
        self.overlay.set_text(text)

    def _on_overlay_level(self, level: float):
        self.overlay.set_level(level)

    def _hide_overlay(self):
        """Hide the overlay."""
        self.overlay.hide()
        self.overlay._visible = False
        self.overlay._opacity = 0.0

    def _show_settings(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow()
            # Warm the live-preview model as soon as live preview is toggled ON,
            # so the FIRST recording after enabling shows live words instead of
            # "Listening" while the model lazily loads (~4s).
            self.settings_window.on_live_preview_enabled = self._preload_live_model
        self.settings_window.show()

    def _quit(self):
        """Quit the application."""
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        # Unload the LLM model from VRAM if we loaded it (keep it from running
        # in the background after Murmur closes).
        if config.LLM_CLEANUP_ENABLED:
            try:
                from core.llm_cleanup import unload_model
                unload_model()
            except Exception as exc:
                log.debug("Unload on quit skipped: %s", exc)
        self.app.quit()

    def run(self):
        """Run the application."""
        self._position_overlay()
        self.main_window.show()

        # Show first-run onboarding wizard once the loop is up
        if not config.ONBOARDING_DONE:
            try:
                from ui.onboarding import OnboardingWizard
                QTimer.singleShot(600, self._show_onboarding)
            except Exception as e:
                log.error("Onboarding wizard error: %s", e)

        return self.app.exec()

    def _show_onboarding(self):
        """Show the onboarding wizard (if applicable)."""
        from ui.onboarding import OnboardingWizard
        wizard = OnboardingWizard(self.main_window)
        wizard.exec()
        # Refresh hotkey listener in case wizard changed it
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self._setup_hotkey()


def main():
    """Entry point."""
    log.info("Starting Murmur v2")
    murmur = MurmurApp()
    sys.exit(murmur.run())


if __name__ == "__main__":
    main()
