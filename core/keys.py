"""
Keyboard helpers — send key combos via ctypes (for command mode).

Used to copy the current selection (Ctrl+C) and to paste a rewrite back
(Ctrl+A then Ctrl+V) so command mode can operate on the focused app.
"""

import ctypes
import os
import time

user32 = ctypes.windll.user32

VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12
VK_A = 0x41
VK_C = 0x43
VK_V = 0x56


def _keybd(vk: int, flags):
    user32.keybd_event(vk, 0, flags, 0)


def _press_once(vk: int):
    _keybd(vk, 0)                 # down
    _keybd(vk, 2)                 # up (KEYEVENTF_KEYUP)


def send_combo(*codes: int, hold_delay: float = 0.04):
    """Hold all modifier codes, tap the last code, then release modifiers.

    e.g. send_combo(VK_CONTROL, VK_C) -> Ctrl+C
    """
    if not codes:
        return
    modifiers = codes[:-1]
    trigger = codes[-1]
    # Press modifiers down
    for m in modifiers:
        _keybd(m, 0)
    time.sleep(hold_delay)
    # Tap trigger
    _press_once(trigger)
    time.sleep(hold_delay)
    # Release modifiers
    for m in modifiers:
        _keybd(m, 2)


def copy_selection():
    """Send Ctrl+C to copy the focused app's selection."""
    send_combo(VK_CONTROL, VK_C)


def select_all():
    """Send Ctrl+A to select all text in the focused field."""
    send_combo(VK_CONTROL, VK_A)


def paste():
    """Send Ctrl+V to paste."""
    send_combo(VK_CONTROL, VK_V)


def paste_into_selection(text: str):
    """Put text on the clipboard and Ctrl+V it into the current selection.

    Unlike select_all+paste, this only replaces the existing selection and
    leaves the rest of the document intact. Requires a working clipboard.
    """
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from PyQt6.QtWidgets import QApplication
    QApplication.clipboard().setText(text)
    time.sleep(0.05)  # let the clipboard settle
    paste()