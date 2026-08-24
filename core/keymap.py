"""
Key mapping — convert Qt key sequences to Windows VK codes.

Lets users capture arbitrary keys/combos (via QKeySequenceEdit) and store
them as VK-code lists that the polling HotkeyListener understands.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence


# Qt.Key value -> Windows VK code (for keys whose Qt value != VK)
_QT_TO_VK = {
    Qt.Key.Key_Space: 0x20,
    Qt.Key.Key_Return: 0x0D,
    Qt.Key.Key_Enter: 0x0D,
    Qt.Key.Key_Tab: 0x09,
    Qt.Key.Key_Escape: 0x1B,
    Qt.Key.Key_Backspace: 0x08,
    Qt.Key.Key_Delete: 0x2E,
    Qt.Key.Key_Insert: 0x2D,
    Qt.Key.Key_Home: 0x24,
    Qt.Key.Key_End: 0x23,
    Qt.Key.Key_PageUp: 0x21,
    Qt.Key.Key_PageDown: 0x22,
    Qt.Key.Key_Left: 0x25,
    Qt.Key.Key_Up: 0x26,
    Qt.Key.Key_Right: 0x27,
    Qt.Key.Key_Down: 0x28,
    Qt.Key.Key_CapsLock: 0x14,
    Qt.Key.Key_Print: 0x2C,
    Qt.Key.Key_Pause: 0x13,
}

# Qt.KeyboardModifier -> Windows modifier VK code
_MODIFIER_VK = {
    Qt.KeyboardModifier.ControlModifier: 0xA2,   # left ctrl
    Qt.KeyboardModifier.AltModifier: 0xA4,       # left alt
    Qt.KeyboardModifier.ShiftModifier: 0xA0,     # left shift
    Qt.KeyboardModifier.MetaModifier: 0x5B,      # left win
}


def _key_to_vk(key) -> int | None:
    """Convert a Qt.Key to a Windows VK code."""
    if key in _QT_TO_VK:
        return _QT_TO_VK[key]
    # Function keys F1..F24: Qt.Key_F1 = 0x01000030 + n, VK_F1 = 0x70
    if key >= Qt.Key.Key_F1 and key <= Qt.Key.Key_F24:
        n = key - Qt.Key.Key_F1
        return 0x70 + n
    # Letters/digits: Qt.Key_A..Z = 0x41..0x5A = VK (ASCII)
    if 0x30 <= int(key) <= 0x5A:  # includes 0-9, A-Z, :;<=>?@
        return int(key)
    return None


def sequence_to_vk_list(seq: QKeySequence) -> list[int] | None:
    """Convert a QKeySequence to a list of VK codes.

    Returns [mod1, mod2, ..., trigger] in no particular modifier order,
    with the non-modifier key LAST. None if unmappable/empty.
    """
    if seq.isEmpty():
        return None
    # No way to split modifiers/key from a formatted QKeySequence easily,
    # so use the accelerator combo if available, else parse the string.
    combo = seq[0]  # QKeyCombination (Qt 6.4+)
    key = combo.key()
    mods = combo.keyboardModifiers()

    vk_list = []
    for mod, vk in _MODIFIER_VK.items():
        if mods & mod:
            vk_list.append(vk)

    trigger = _key_to_vk(key)
    if trigger is None:
        return None

    vk_list.append(trigger)
    # If no modifiers and it's just a key, return it as a single combo [trigger]
    return vk_list


def vk_list_to_label(vk_list: list[int]) -> str:
    """Produce a human label from a VK list, e.g. [0xA2, 0xA4, 0x52] -> Ctrl+Alt+R."""
    names = {0xA2: "Ctrl", 0xA4: "Alt", 0xA0: "Shift", 0x5B: "Win"}
    if not vk_list:
        return ""
    if len(vk_list) == 1:
        return _single_vk_label(vk_list[0])
    # Last is trigger, rest modifiers
    trigger = vk_list[-1]
    prefix = "+".join(names.get(m, f"0x{m:X}") for m in vk_list[:-1])
    return f"{prefix} + {_single_vk_label(trigger)}"


def _single_vk_label(vk: int) -> str:
    letters = {0x41 + i: chr(ord("A") + i) for i in range(26)}
    digits = {0x30 + i: str(i) for i in range(10)}
    glyphs = {
        0x20: "Space", 0x0D: "Enter", 0x09: "Tab", 0x1B: "Esc",
        0x08: "Backspace", 0x2E: "Delete", 0x2D: "Insert",
        0x24: "Home", 0x23: "End", 0x21: "PgUp", 0x22: "PgDn",
        0x25: "Left", 0x26: "Up", 0x27: "Right", 0x28: "Down",
        0x14: "CapsLock", 0xA3: "Right Ctrl", 0xA5: "Right Alt",
        0xA1: "Right Shift",
    }
    if vk in glyphs:
        return glyphs[vk]
    if vk in letters:
        return letters[vk]
    if vk in digits:
        return digits[vk]
    if 0x70 <= vk <= 0x87:
        return f"F{vk - 0x70 + 1}"
    return f"0x{vk:X}"