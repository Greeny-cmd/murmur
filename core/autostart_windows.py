"""
Windows autostart — register/remove Murmur in HKCU Run key.

Key: HKCU\Software\Microsoft\Windows\CurrentVersion\Run
Applies only to the current user (no admin needed).
"""

import os
import sys
import winreg
from core.logger import log

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "Murmur"


def _launch_command() -> str:
    """Build the command that starts Murmur at logon."""
    # autostart_windows.py lives in core/, so the project root is 2 levels up.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    venv_pythonw = os.path.join(root, ".venv", "Scripts", "pythonw.exe")
    main_py = os.path.join(root, "main.py")
    interpreter = venv_pythonw if os.path.exists(venv_pythonw) else "pythonw"
    # Start pythonw directly (NO cmd wrapper), so no console window flashes
    # at logon. main.py adds its own dir to sys.path, so cwd doesn't matter.
    return f'"{interpreter}" "{main_py}"'


def is_enabled() -> bool:
    """Return True if Murmur autostart is registered."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        log.error("Autostart check failed: %s", exc)
        return False


def enable() -> bool:
    """Register Murmur to start with Windows."""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _launch_command())
        log.info("Autostart enabled: %s", _launch_command())
        return True
    except OSError as exc:
        log.error("Failed to enable autostart: %s", exc)
        return False


def disable() -> bool:
    """Remove Murmur from Windows autostart."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
        log.info("Autostart disabled")
        return True
    except FileNotFoundError:
        return True  # Already disabled
    except OSError as exc:
        log.error("Failed to disable autostart: %s", exc)
        return False