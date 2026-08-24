"""
Recording Overlay Widget — floating pill indicator.

Shows recording status with the Murmur logo in a circle.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QPixmap, QPainterPath, QBrush
from ui.design import DesignTokens
import os


class RecordingOverlay(QWidget):
    """Floating recording indicator widget."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._state = "idle"
        self._text = ""
        self._partial = ""
        self._level = 0.0
        self._opacity = 0.0
        self._visible = False

        # Load the logo
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "murmur.png")
        self._logo = QPixmap(icon_path) if os.path.exists(icon_path) else None

        # Start at the "normal" width so the very first trigger is already
        # full-size (not a tiny 320 pill before text arrives). Grows to 760.
        self.setMinimumSize(560, 56)
        self.setMaximumWidth(760)
        self.setFixedSize(560, 56)
        self._last_text = ""

        # Timer for hiding
        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

        # Timer for redraw
        self._redraw_timer = QTimer()
        self._redraw_timer.timeout.connect(self.update)
        self._redraw_timer.start(33)

    def set_state(self, state: str):
            # Always cancel any pending auto-hide from a PREVIOUS interaction —
            # otherwise the old 3s timer can hide the overlay mid new recording.
            self._hide_timer.stop()
            self._state = state
            if state == "idle":
                self._visible = False
                self._opacity = 0.0
                self.hide()
            elif state in ("listening", "processing", "done"):
                self._visible = True
                self._opacity = 1.0
                self.show()
            if state == "done":
                self._hide_timer.start(3000)

    def set_text(self, text: str):
        self._partial = text
        self._resize_for_text()
        self.update()

    def _resize_for_text(self):
        """Keep the pill at a comfortable fixed width for ONE line of text."""
        # Fixed width fits ~45-55 chars with the logo; longer text is elided.
        if (self.width(), self.height()) != (560, 56):
            self.setFixedSize(560, 56)
            self.updateGeometry()

    def set_level(self, level: float):
        self._level = level
        self.update()

    def _draw_circle_logo(self, painter, x, y, size, opacity):
        """Draw the logo clipped to a circle with white background."""
        # Draw white circle background
        painter.setBrush(QColor(253, 250, 244, int(opacity * 0.95)))  # Match logo background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(x, y, size, size)

        if not self._logo:
            # Fallback: draw "m" in circle
            font = QFont(DesignTokens.Fonts.SANS, 14, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor(26, 115, 232, int(opacity * 0.9)))
            painter.drawText(x, y, size, size, Qt.AlignmentFlag.AlignCenter, "m")
            return

        # Create circular clip path
        painter.save()
        clip_path = QPainterPath()
        clip_path.addEllipse(x, y, size, size)
        painter.setClipPath(clip_path)

        # Draw logo centered in circle
        logo_size = size  # Fill entire circle
        logo_x = x + (size - logo_size) // 2
        logo_y = y + (size - logo_size) // 2
        painter.setOpacity(opacity * 0.9)
        painter.drawPixmap(logo_x, logo_y, logo_size, logo_size, self._logo)

        # Draw subtle border circle
        painter.setOpacity(opacity * 0.3)
        painter.setPen(QPen(QColor(26, 115, 232), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(x + 1, y + 1, size - 2, size - 2)

        painter.restore()

    def paintEvent(self, event):
        if not self._visible or self._opacity <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        radius = h // 2

        opacity = int(255 * self._opacity)

        # Colors
        border_color = QColor(255, 255, 255, int(opacity * 0.08))
        fill_color = QColor(20, 20, 24, int(opacity * 0.95))

        # Draw pill background
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(fill_color)
        painter.drawRoundedRect(0, 0, w, h, radius, radius)

        # Draw circular logo (left side)
        logo_size = 36
        logo_x = 10
        logo_y = (h - logo_size) // 2
        self._draw_circle_logo(painter, logo_x, logo_y, logo_size, self._opacity)

        # Draw text area
        text_x = logo_x + logo_size + 12
        text_width = w - text_x - 50  # Leave space for waveform

        # Determine what text to show
        display_text = ""
        text_color = QColor(26, 115, 232, opacity)  # Google Blue

        if self._state == "listening":
            display_text = self._partial if self._partial else "Listening..."
            text_color = QColor(26, 115, 232, opacity)
        elif self._state == "processing":
            display_text = self._partial if self._partial else "Thinking..."
            text_color = QColor(255, 170, 0, opacity)
        elif self._state == "done":
            display_text = self._partial if self._partial else "Done!"
            text_color = QColor(30, 142, 62, opacity)
        else:
            display_text = "Ready"
            text_color = QColor(255, 255, 255, int(opacity * 0.5))

        if display_text:
            font = QFont(DesignTokens.Fonts.SANS, 11)
            painter.setFont(font)
            painter.setPen(text_color)
            # ONE line; long text ends with "..." (elide right), never wraps.
            metrics = painter.fontMetrics()
            elided = metrics.elidedText(display_text, Qt.TextElideMode.ElideRight, text_width)
            painter.drawText(text_x, 0, text_width, h, Qt.AlignmentFlag.AlignVCenter, elided)

        # Draw waveform bars (right side)
        if self._state == "listening":
            import math
            bar_x = w - 45
            bar_w = 2
            bar_gap = 3
            for i in range(5):
                phase = (i * 0.8 + self._level * 10) % (math.pi * 2)
                bar_h = max(3, int(14 * (0.3 + 0.7 * abs(math.sin(phase)))))
                bar_y = (h - bar_h) // 2
                painter.setBrush(QColor(26, 115, 232, int(opacity * 0.6)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(int(bar_x + i * (bar_w + bar_gap)), bar_y, bar_w, bar_h)
        else:
            # Static bars when not listening
            bar_x = w - 45
            bar_w = 2
            bar_gap = 3
            for i in range(5):
                bar_h = 3
                bar_y = (h - bar_h) // 2
                painter.setBrush(QColor(255, 255, 255, int(opacity * 0.12)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(int(bar_x + i * (bar_w + bar_gap)), bar_y, bar_w, bar_h)

        painter.end()
