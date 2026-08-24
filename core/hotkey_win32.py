"""
Hotkey Listener — Win32 RegisterHotKey.

Uses RegisterHotKey for global hotkey detection.
Simpler than low-level hooks, works without admin rights.
"""

import ctypes
import ctypes.wintypes
import threading
import time
from core import config
from core.logger import log

user32 = ctypes.windll.user32

# Hotkey ID
HOTKEY_ID = 1

# Message
WM_HOTKEY = 0x0312

# Virtual key codes
VK_RCONTROL = 0xA3


class Win32HotkeyListener:
    """Global hotkey listener using RegisterHotKey."""

    def __init__(self, on_press_cb, on_release_cb):
        self._on_press = on_press_cb
        self._on_release = on_release_cb
        self._registered = False
        self._thread = None
        self._running = False

    def start(self):
        """Register the global hotkey."""
        if self._running:
            return True

        self._running = True

        target_vk = getattr(config, "HOTKEY", VK_RCONTROL)
        if target_vk is None:
            target_vk = VK_RCONTROL

        # Register the hotkey (no modifiers, just the key)
        result = user32.RegisterHotKey(None, HOTKEY_ID, 0, target_vk)

        if not result:
            error = ctypes.GetLastError()
            if error == 1409:  # Hotkey already registered
                log.warning("Hotkey already registered by another app")
            else:
                log.error("Failed to register hotkey: error %d", error)
                self._running = False
                return False

        log.info("Hotkey registered (vk=0x%X)", target_vk)

        # Start message pump
        self._thread = threading.Thread(target=self._message_pump, daemon=True)
        self._thread.start()

        return True

    def _message_pump(self):
        """Run message pump to receive hotkey events."""
        msg = ctypes.wintypes.MSG()

        while self._running:
            result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)

            if result == 0:  # WM_QUIT
                break
            elif result == -1:  # Error
                break

            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                # Toggle: first press = start, second press = stop
                try:
                    self._on_press()
                    # Small delay then check if key is still held
                    time.sleep(0.05)
                    # For hold mode, we need to detect key release
                    # RegisterHotKey doesn't provide release events,
                    # so we poll GetAsyncKeyState
                    target_vk = getattr(config, "HOTKEY", VK_RCONTROL)
                    if target_vk is None:
                        target_vk = VK_RCONTROL

                    while user32.GetAsyncKeyState(target_vk) & 0x8000:
                        time.sleep(0.01)

                    self._on_release()
                except Exception as e:
                    log.error("Hotkey callback error: %s", e)

    def stop(self):
        """Unregister the hotkey."""
        self._running = False
        if self._registered:
            user32.UnregisterHotKey(None, HOTKEY_ID)
            self._registered = False
        if self._thread:
            # Send WM_QUIT to stop the message pump
            user32.PostThreadMessageW(
                self._thread.ident if self._thread else 0,
                0x0012,  # WM_QUIT
                0, 0
            )
            self._thread.join(timeout=2)
            self._thread = None
        log.info("Hotkey unregistered")
