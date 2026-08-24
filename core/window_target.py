"""
Window target lock — pins text injection to a specific window.

Solves the "text lands in the wrong window" bug: the window focused when
recording STARTED is captured, then re-activated right before injection.
"""

import ctypes
import ctypes.wintypes
from core.logger import log

_user32 = ctypes.windll.user32


def get_foreground_window():
    """Return the current foreground window handle (or 0)."""
    return _user32.GetForegroundWindow()


def is_valid(hwnd):
    return bool(hwnd) and bool(_user32.IsWindow(hwnd))


def activate_window(hwnd):
    """Bring a captured window to the foreground so injection lands there."""
    if not hwnd or not _user32.IsWindow(hwnd):
        return False
    try:
        # The ALT-key trick relaxes Windows' foreground-lock restrictions,
        # letting a background process steal focus.
        _user32.keybd_event(0x12, 0, 0, 0)   # ALT down
        _user32.keybd_event(0x12, 0, 2, 0)   # ALT up
        _user32.SetForegroundWindow(hwnd)
        _user32.BringWindowToTop(hwnd)
        return True
    except Exception as exc:
        log.error("activate_window failed: %s", exc)
        return False


def try_restore_to(hwnd):
    """Best-effort: switch focus to hwnd if it's still a valid window."""
    if is_valid(hwnd):
        return activate_window(hwnd)
    return False