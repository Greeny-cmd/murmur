"""
GUI log handler — forwards log records to the main window log tab.

A logging.Handler stores recent lines in a thread-safe deque; the main
window polls it with a QTimer and appends new lines to its log list.
"""

import logging
import threading
from collections import deque

MAX_LINES = 200  # keep only the most recent entries in the GUI log


class GuiLogHandler(logging.Handler):
    """A logging handler that queues lines for the GUI."""

    def __init__(self):
        super().__init__()
        self._lines = deque(maxlen=MAX_LINES)
        self._lock = threading.Lock()

    def emit(self, record):
        try:
            msg = self.format(record)
            with self._lock:
                self._lines.append(msg)
        except Exception:
            pass

    def drain(self) -> list[str]:
        """Return and clear any pending lines."""
        with self._lock:
            if not self._lines:
                return []
            lines = list(self._lines)
            self._lines.clear()
            return lines

    def snapshot(self) -> list[str]:
        """Return all current lines without clearing."""
        with self._lock:
            return list(self._lines)


# Singleton handler installed once
_gui_handler = GuiLogHandler()
_gui_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))


def install_gui_log_handler():
    """Attach the GUI handler to the 'murmur' logger and root logger."""
    import logging as _logging
    for name in ("murmur",):
        lg = _logging.getLogger(name)
        if _gui_handler not in lg.handlers:
            lg.addHandler(_gui_handler)


def get_gui_handler() -> GuiLogHandler:
    return _gui_handler