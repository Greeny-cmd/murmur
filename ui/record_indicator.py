"""
RecordIndicator — a dot-grid that animates like a moving wave.

Drawn directly in paintEvent (no GIF asset) so it is cheap on CPU. Slow, blue
wave when idle; red/orange-gradient wave when recording (slower than idle so
it reads as a calm, deliberate pulse).

The phase is derived from a monotonic clock at paint time, so the wave keeps
moving smoothly even if the GUI event loop is briefly busy (no "frozen" frames).
"""

import math
import time

from PyQt6.QtCore import QTimer, Qt, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtWidgets import QWidget


class RecordIndicator(QWidget):
    clicked = pyqtSignal()

    # Idle: slow, gentle blue. Recording: slightly faster but still calm.
    _IDLE_SPEED = 1.4
    _REC_SPEED = 2.6

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(64, 64)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.recording = False

        # Timer only triggers a repaint; the wave position comes from time.
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(50)  # ~20 fps — smooth but very light

    # -- public state --
    def set_recording(self, recording: bool):
        self.recording = bool(recording)
        self.update()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    @property
    def _speed(self):
        return self._REC_SPEED if self.recording else self._IDLE_SPEED

    @property
    def _amp(self):
        return 3.2 if self.recording else 2.2

    def _phase(self):
        return time.monotonic() * self._speed

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2
        R = self.width() / 2 - 6   # circle boundary
        cols, rows = 9, 9
        dot_r = 2.2
        spacing_x = R * 2 / (cols - 1)
        spacing_y = R * 2 / (rows - 1)

        if self.recording:
            c_start = QColor(238, 82, 54)     # red-orange
            c_end = QColor(255, 165, 40)      # amber
        else:
            c_start = QColor(30, 115, 232)    # Google blue
            c_end = QColor(122, 190, 255)     # light blue

        base_phase = self._phase()

        for r in range(rows):
            for c in range(cols):
                nx = (c - (cols - 1) / 2) * spacing_x
                ny = (r - (rows - 1) / 2) * spacing_y
                dist = (nx * nx + ny * ny) ** 0.5
                if dist > R:
                    continue

                phase = base_phase + dist * 0.9
                s = math.sin(phase)
                wave = self._amp * (0.5 + 0.5 * s)

                # radial breathing along the ring
                if dist > 1:
                    scale = 1.0 + (self._amp / R) * math.sin(phase * 1.3)
                else:
                    scale = 1.0 + 0.1 * math.sin(phase)
                ox = nx * scale
                oy = ny * scale

                t = (c / (cols - 1) + r / (rows - 1)) / 2
                color = self._lerp(c_start, c_end, t)
                color.setAlpha(255 if self.recording else 200)

                size = dot_r + wave * 0.35
                p.setBrush(color)
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(cx + ox, cy + oy), size, size)

        p.end()

    def _lerp(self, a: QColor, b: QColor, t):
        return QColor(
            int(a.red() + (b.red() - a.red()) * t),
            int(a.green() + (b.green() - a.green()) * t),
            int(a.blue() + (b.blue() - a.blue()) * t),
        )