"""
Hotkey Listener — polling-based using GetAsyncKeyState.

Supports both single keys and key combos (from settings).
"""

import ctypes
import threading
import time
from core import config
from core.logger import log

user32 = ctypes.windll.user32


class HotkeyListener:
    """Polling-based hotkey listener supporting single keys and combos."""

    def __init__(self, on_press_cb, on_release_cb, key=None, combo=None):
        self._on_press = on_press_cb
        self._on_release = on_release_cb
        self._key = key          # optional override (single vk)
        self._combo = combo      # optional override (list of vk)
        self._thread = None
        self._running = False
        self._was_pressed = False

    def start(self):
        if self._running:
            return True
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        log.info("Hotkey listener started")
        return True

    def _poll_loop(self):
        while self._running:
            active = self._hotkey_active()

            if active and not self._was_pressed:
                self._was_pressed = True
                try:
                    self._on_press()
                except Exception as e:
                    log.error("Hotkey press error: %s", e)
            elif not active and self._was_pressed:
                self._was_pressed = False
                try:
                    self._on_release()
                except Exception as e:
                    log.error("Hotkey release error: %s", e)

            time.sleep(0.012)

    def _hotkey_active(self) -> bool:
        """Return True if the configured hotkey is currently held."""
        combo = self._combo if self._combo is not None else getattr(config, "COMBO_HOTKEY", None)
        if combo:
            mods, trigger = combo[:-1], combo[-1]
            if not self._key_down(trigger):
                return False
            for mod in mods:
                if not self._modifier_down(mod):
                    return False
            return True

        key = self._key if self._key is not None else getattr(config, "HOTKEY", 0xA3)
        return self._key_down(key)

    def _key_down(self, vk: int) -> bool:
        return (user32.GetAsyncKeyState(vk) & 0x8000) != 0

    def _modifier_down(self, vk: int) -> bool:
        # Modifier VK codes from settings are like 0xA2 (Ctrl), 0xA4 (Alt), 0xA0 (Shift)
        return self._key_down(vk)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        log.info("Hotkey listener stopped")