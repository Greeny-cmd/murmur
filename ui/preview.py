"""Command Mode preview window — shows original vs rewritten text with Apply/Undo/Cancel."""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from ui.design import DesignTokens


class PreviewWindow(QDialog):
    """Non-modal preview so Apply / Undo / Cancel all work in place."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Murmur — Command Mode")
        self.setMinimumSize(520, 430)
        self.resize(600, 470)

        import os
        icon = os.path.join(os.path.dirname(__file__), "icons", "murmur.ico")
        if os.path.exists(icon):
            self.setWindowIcon(QIcon(icon))

        self._apply_cb = None
        self._regen_cb = None
        self._regen_timer = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title = QLabel("Rewrite Selection")
        title.setStyleSheet(f"font-size: {DesignTokens.Fonts.HEADLINE_MEDIUM}px; font-weight: 700;")
        root.addWidget(title)

        self.status = QLabel("")
        self.status.setStyleSheet(f"color: {DesignTokens.Light.PRIMARY}; font-size: 12px;")
        root.addWidget(self.status)

        root.addWidget(self._label("Your instruction:"))
        self.instruction_edit = QTextEdit()
        self.instruction_edit.setAcceptRichText(False)
        self.instruction_edit.setMaximumHeight(50)
        self.instruction_edit.textChanged.connect(self._on_instruction_changed)
        root.addWidget(self.instruction_edit)

        root.addWidget(self._label("Original text:"))
        self.original_view = QTextEdit()
        self.original_view.setReadOnly(True)
        self.original_view.setMaximumHeight(90)
        self.original_view.setStyleSheet("background:#F8F9FA;")
        root.addWidget(self.original_view)

        root.addWidget(self._label("Rewritten:"))
        self.rewritten_view = QTextEdit()
        self.rewritten_view.setReadOnly(True)
        self.rewritten_view.setMaximumHeight(90)
        self.rewritten_view.setStyleSheet("background:#F8F9FA;")
        root.addWidget(self.rewritten_view)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.cancel_btn = QPushButton("Close")
        self.cancel_btn.setStyleSheet(self._secondary())
        self.cancel_btn.clicked.connect(self._close)
        btn_row.addWidget(self.cancel_btn)

        self.undo_btn = QPushButton("Undo")
        self.undo_btn.setStyleSheet(self._secondary())
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self._undo)
        btn_row.addWidget(self.undo_btn)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setStyleSheet(self._primary())
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply)
        btn_row.addWidget(self.apply_btn)

        self.regen_btn = QPushButton("↻ Regenerate")
        self.regen_btn.setStyleSheet(self._secondary())
        self.regen_btn.setEnabled(False)
        self.regen_btn.clicked.connect(self._regen)
        btn_row.addWidget(self.regen_btn)

        root.addLayout(btn_row)

    # ── setters ──────────────────────────────────────────────────────
    def set_original(self, text):
        self.original_view.setPlainText(text)

    def set_instruction(self, text):
        self.instruction_edit.setPlainText(text)

    def set_rewritten(self, text):
        self.rewritten_view.setPlainText(text)
        self.apply_btn.setEnabled(True)
        self.regen_btn.setEnabled(True)
        if self._regen_timer is not None:
            self._regen_timer.stop()

    def set_status(self, msg):
        self.status.setText(msg)

    def set_apply_callback(self, cb):
        """cb(text) applies the given text to the focused selection (used for Apply/Undo)."""
        self._apply_cb = cb

    def set_regen_callback(self, cb):
        """cb(instruction) recomputes the rewrite. The result should be delivered
        back via a later set_rewritten() call."""
        self._regen_cb = cb
        self.regen_btn.setEnabled(bool(cb))

    # ── actions ──────────────────────────────────────────────────────
    def _on_instruction_changed(self):
        # Debounce: (re)generate only after a short pause of typing.
        from PyQt6.QtCore import QTimer
        if self._regen_timer is not None:
            self._regen_timer.stop()
        self._regen_timer = QTimer(self)
        self._regen_timer.setSingleShot(True)
        self._regen_timer.setInterval(700)
        self._regen_timer.timeout.connect(self._regen)
        self._regen_timer.start()
        # While waiting, keep Apply based on the old result but disable the
        # regenerate button feedback via the status line.
        self.status.setText("Waiting… adjust the instruction and it will re-rewrite.")

    def _regen(self):
        if not self._regen_cb:
            return
        instruction = self.instruction_edit.toPlainText().strip()
        self.status.setText("Rewriting…")
        self.rewritten_view.setPlainText("")
        self.apply_btn.setEnabled(False)
        self.regen_btn.setEnabled(False)
        self._regen_cb(instruction)

    def _apply(self):
        if self._apply_cb:
            self._apply_cb(self.rewritten_view.toPlainText())
        self.apply_btn.setEnabled(False)
        self.undo_btn.setEnabled(True)
        self.status.setText("Applied. Use Undo to restore the original.")

    def _undo(self):
        if self._apply_cb:
            self._apply_cb(self.original_view.toPlainText())
        self.undo_btn.setEnabled(False)
        self.apply_btn.setEnabled(True)
        self.status.setText("Reverted to original. Apply again to re-apply the rewrite.")

    def _close(self):
        self.close()

    # ── helpers ──────────────────────────────────────────────────────
    def _label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {DesignTokens.Light.ON_SURFACE_VARIANT}; font-size: 11px; font-weight: 600;")
        return lbl

    def _primary(self):
        return f"""
            QPushButton {{ background: {DesignTokens.Light.PRIMARY}; color: white; font-weight: 600;
                border: none; border-radius: {DesignTokens.Radius.FULL}px; padding: 8px 20px; }}
            QPushButton:disabled {{ background: #C0C7CE; color: white; }}
            QPushButton:hover:enabled {{ background: {DesignTokens.Light.PRIMARY_VARIANT}; }}
        """

    def _secondary(self):
        return f"""
            QPushButton {{ background: {DesignTokens.Light.SURFACE_VARIANT};
                color: {DesignTokens.Light.ON_SURFACE_VARIANT};
                border: 1px solid {DesignTokens.Light.OUTLINE};
                border-radius: {DesignTokens.Radius.FULL}px; padding: 8px 20px; }}
            QPushButton:hover {{ border-color: {DesignTokens.Light.PRIMARY}; color: {DesignTokens.Light.PRIMARY}; }}
        """