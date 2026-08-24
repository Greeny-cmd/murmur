"""
Text Injector — pastes text into the focused application.

Uses the Win32 clipboard API (via ctypes) for atomic clipboard access.
This is a battle-tested clipboard-injection approach — reliable on Windows.
"""

import ctypes
import ctypes.wintypes
import os
import time
from pynput.keyboard import Controller, Key
from core import config
from core.logger import log

# ── Win32 clipboard constants & functions ─────────────────────────────────

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

_OpenClipboard = _user32.OpenClipboard
_OpenClipboard.argtypes = [ctypes.wintypes.HWND]
_OpenClipboard.restype = ctypes.wintypes.BOOL

_CloseClipboard = _user32.CloseClipboard
_CloseClipboard.argtypes = []
_CloseClipboard.restype = ctypes.wintypes.BOOL

_EmptyClipboard = _user32.EmptyClipboard
_EmptyClipboard.argtypes = []
_EmptyClipboard.restype = ctypes.wintypes.BOOL

_SetClipboardData = _user32.SetClipboardData
_SetClipboardData.argtypes = [ctypes.wintypes.UINT, ctypes.wintypes.HANDLE]
_SetClipboardData.restype = ctypes.wintypes.HANDLE

_GetClipboardData = _user32.GetClipboardData
_GetClipboardData.argtypes = [ctypes.wintypes.UINT]
_GetClipboardData.restype = ctypes.wintypes.HANDLE

_GlobalAlloc = _kernel32.GlobalAlloc
_GlobalAlloc.argtypes = [ctypes.wintypes.UINT, ctypes.c_size_t]
_GlobalAlloc.restype = ctypes.wintypes.HANDLE

_GlobalLock = _kernel32.GlobalLock
_GlobalLock.argtypes = [ctypes.wintypes.HANDLE]
_GlobalLock.restype = ctypes.c_void_p

_GlobalUnlock = _kernel32.GlobalUnlock
_GlobalUnlock.argtypes = [ctypes.wintypes.HANDLE]
_GlobalUnlock.restype = ctypes.wintypes.BOOL

_GlobalFree = _kernel32.GlobalFree
_GlobalFree.argtypes = [ctypes.wintypes.HANDLE]
_GlobalFree.restype = ctypes.wintypes.HANDLE

# ── Keyboard controller ──────────────────────────────────────────────────

_keyboard = Controller()

_MAX_RETRIES = 5
_RETRY_DELAY = 0.02


def _open_clipboard(retries: int = _MAX_RETRIES) -> bool:
    """Try to open the clipboard with retries."""
    for _ in range(retries):
        if _OpenClipboard(None):
            return True
        time.sleep(_RETRY_DELAY)
    return False


def _allocate_clipboard_text(text: str):
    """Allocate a movable UTF-16 block suitable for SetClipboardData."""
    encoded = text.encode("utf-16-le") + b"\x00\x00"
    h_mem = _GlobalAlloc(GMEM_MOVEABLE, len(encoded))
    if not h_mem:
        return None
    ptr = _GlobalLock(h_mem)
    if not ptr:
        _GlobalFree(h_mem)
        return None
    try:
        ctypes.memmove(ptr, encoded, len(encoded))
    finally:
        _GlobalUnlock(h_mem)
    return h_mem


def _set_clipboard_text(text: str) -> bool:
    """Write text to the clipboard."""
    h_mem = _allocate_clipboard_text(text)
    if not h_mem:
        return False

    if not _open_clipboard():
        log.warning("Cannot open clipboard for writing")
        _GlobalFree(h_mem)
        return False

    transferred = False
    try:
        if not _EmptyClipboard():
            return False
        if not _SetClipboardData(CF_UNICODETEXT, h_mem):
            return False
        transferred = True
        return True
    finally:
        _CloseClipboard()
        if not transferred:
            _GlobalFree(h_mem)


def _get_clipboard_text() -> str:
    """Return current clipboard text, or empty string on failure."""
    if not _open_clipboard():
        return ""
    try:
        handle = _GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        ptr = _GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)
        finally:
            _GlobalUnlock(handle)
    finally:
        _CloseClipboard()


def inject(text: str):
    """Paste text into the currently focused application.

    1. Save current clipboard
    2. Set clipboard to our text
    3. Press Ctrl+V
    4. Wait for paste
    5. Restore clipboard
    """
    if not text:
        return

    # Save current clipboard
    saved_text = _get_clipboard_text() if not config.KEEP_TRANSCRIPT_IN_CLIPBOARD else None

    # Set clipboard to our text
    if not _set_clipboard_text(text):
        log.error("Failed to set clipboard text")
        return

    # Wait for clipboard to settle
    time.sleep(0.05)

    # Press Ctrl+V
    with _keyboard.pressed(Key.ctrl):
        _keyboard.press("v")
        _keyboard.release("v")

    # Wait for paste to complete
    time.sleep(config.CLIPBOARD_RESTORE_DELAY)

    # Restore clipboard
    if saved_text is not None and saved_text != text:
        _set_clipboard_text(saved_text)


def save_recovery(text: str):
    """Save text to recovery file as a safety net."""
    try:
        recovery_path = os.path.join(config.DATA_DIR, "recovery_notes.txt")
        max_size = 512_000  # 500 KB

        # Rotate if too large
        if os.path.exists(recovery_path) and os.path.getsize(recovery_path) > max_size:
            backup = recovery_path + ".1"
            if os.path.exists(backup):
                os.remove(backup)
            os.rename(recovery_path, backup)

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(recovery_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {text}\n")
    except Exception as exc:
        log.error("Failed to save recovery text: %s", exc)
