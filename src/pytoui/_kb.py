"""Keyboard input constants for use with get_key_commands().

'input' values — pass as the 'input' key in key-command dicts.
'modifiers' values — pass (comma-separated) as the 'modifiers' key.

Pythonista-compatible inputs are marked with (P).
Desktop-only inputs (SDL/Winit, no-op on Pythonista) are marked with (D).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Special input strings  (Pythonista-compatible)
# ---------------------------------------------------------------------------

KEY_INPUT_UP: str = "up"           # (P) Up arrow
KEY_INPUT_DOWN: str = "down"       # (P) Down arrow
KEY_INPUT_LEFT: str = "left"       # (P) Left arrow
KEY_INPUT_RIGHT: str = "right"     # (P) Right arrow
KEY_INPUT_ESC: str = "esc"         # (P) Escape
KEY_INPUT_RETURN: str = "\r"       # (P) Return / Enter
KEY_INPUT_BACKSPACE: str = "\b"    # (P) Backspace
KEY_INPUT_TAB: str = "\t"          # (P) Tab
KEY_INPUT_SPACE: str = " "         # (P) Space bar

# ---------------------------------------------------------------------------
# Extended input strings  (desktop + iOS 13.4+ UIKit)
# ---------------------------------------------------------------------------

KEY_INPUT_DELETE: str = "delete"       # (D) Forward-delete (Del key)
KEY_INPUT_HOME: str = "home"           # (D) Home
KEY_INPUT_END: str = "end"             # (D) End
KEY_INPUT_PAGE_UP: str = "pageup"      # (D) Page Up
KEY_INPUT_PAGE_DOWN: str = "pagedown"  # (D) Page Down
KEY_INPUT_INSERT: str = "insert"       # (D) Insert

KEY_INPUT_F1: str = "f1"
KEY_INPUT_F2: str = "f2"
KEY_INPUT_F3: str = "f3"
KEY_INPUT_F4: str = "f4"
KEY_INPUT_F5: str = "f5"
KEY_INPUT_F6: str = "f6"
KEY_INPUT_F7: str = "f7"
KEY_INPUT_F8: str = "f8"
KEY_INPUT_F9: str = "f9"
KEY_INPUT_F10: str = "f10"
KEY_INPUT_F11: str = "f11"
KEY_INPUT_F12: str = "f12"

# ---------------------------------------------------------------------------
# Modifier strings — use in the 'modifiers' field (comma-separated)
# ---------------------------------------------------------------------------

KEY_MOD_CMD: str = "cmd"      # ⌘ on iOS/macOS; mapped to Ctrl on Linux/Windows
KEY_MOD_CTRL: str = "ctrl"    # Control key (literal, all platforms)
KEY_MOD_ALT: str = "alt"      # Option/Alt
KEY_MOD_SHIFT: str = "shift"  # Shift

# ---------------------------------------------------------------------------
# SDL keycode → KEY_INPUT_* lookup table (populated lazily on first import)
# Used internally by SDLRuntime; not part of the public API.
# ---------------------------------------------------------------------------

_sdl_map_cache: dict[int, str] | None = None


def _build_sdl_map(sdl2) -> dict[int, str]:
    """Return a cached dict mapping SDL keysym.sym values to KEY_INPUT_* strings."""
    global _sdl_map_cache
    if _sdl_map_cache is not None:
        return _sdl_map_cache
    m: dict[int, str] = {
        sdl2.SDLK_UP: KEY_INPUT_UP,
        sdl2.SDLK_DOWN: KEY_INPUT_DOWN,
        sdl2.SDLK_LEFT: KEY_INPUT_LEFT,
        sdl2.SDLK_RIGHT: KEY_INPUT_RIGHT,
        sdl2.SDLK_ESCAPE: KEY_INPUT_ESC,
        sdl2.SDLK_RETURN: KEY_INPUT_RETURN,
        sdl2.SDLK_RETURN2: KEY_INPUT_RETURN,
        sdl2.SDLK_KP_ENTER: KEY_INPUT_RETURN,
        sdl2.SDLK_BACKSPACE: KEY_INPUT_BACKSPACE,
        sdl2.SDLK_TAB: KEY_INPUT_TAB,
        sdl2.SDLK_SPACE: KEY_INPUT_SPACE,
        sdl2.SDLK_DELETE: KEY_INPUT_DELETE,
        sdl2.SDLK_HOME: KEY_INPUT_HOME,
        sdl2.SDLK_END: KEY_INPUT_END,
        sdl2.SDLK_PAGEUP: KEY_INPUT_PAGE_UP,
        sdl2.SDLK_PAGEDOWN: KEY_INPUT_PAGE_DOWN,
        sdl2.SDLK_INSERT: KEY_INPUT_INSERT,
        sdl2.SDLK_F1: KEY_INPUT_F1,
        sdl2.SDLK_F2: KEY_INPUT_F2,
        sdl2.SDLK_F3: KEY_INPUT_F3,
        sdl2.SDLK_F4: KEY_INPUT_F4,
        sdl2.SDLK_F5: KEY_INPUT_F5,
        sdl2.SDLK_F6: KEY_INPUT_F6,
        sdl2.SDLK_F7: KEY_INPUT_F7,
        sdl2.SDLK_F8: KEY_INPUT_F8,
        sdl2.SDLK_F9: KEY_INPUT_F9,
        sdl2.SDLK_F10: KEY_INPUT_F10,
        sdl2.SDLK_F11: KEY_INPUT_F11,
        sdl2.SDLK_F12: KEY_INPUT_F12,
    }
    # Printable ASCII letters a-z  (SDL stores lowercase)
    for c in range(ord("a"), ord("z") + 1):
        m[c] = chr(c)
    # Digits 0-9
    for c in range(ord("0"), ord("9") + 1):
        m[c] = chr(c)
    _sdl_map_cache = m
    return m


def _sdl_mods_to_set(sdl2, mod_flags: int) -> frozenset[str]:
    """Convert SDL KMOD_* bitmask to a frozenset of KEY_MOD_* strings.

    Transparent mapping: on macOS the GUI (Cmd) key maps to KEY_MOD_CMD;
    on Linux/Windows the Ctrl key maps to KEY_MOD_CMD so that cross-platform
    code written for Pythonista ('modifiers': 'cmd') works the same way.
    """
    import sys

    mods: set[str] = set()
    if mod_flags & sdl2.KMOD_SHIFT:
        mods.add(KEY_MOD_SHIFT)
    if mod_flags & sdl2.KMOD_ALT:
        mods.add(KEY_MOD_ALT)
    if sys.platform == "darwin":
        if mod_flags & sdl2.KMOD_GUI:
            mods.add(KEY_MOD_CMD)
        if mod_flags & sdl2.KMOD_CTRL:
            mods.add(KEY_MOD_CTRL)
    else:  # Linux / Windows: Ctrl is the "command" modifier
        if mod_flags & sdl2.KMOD_CTRL:
            mods.add(KEY_MOD_CMD)
        if mod_flags & sdl2.KMOD_GUI:
            mods.add(KEY_MOD_CTRL)
    return frozenset(mods)


# ---------------------------------------------------------------------------
# Winit key code → KEY_INPUT_* lookup table
# Integer codes match key_to_code() in deps/winitrt/src/lib.rs.
# Named keys: 1-15 and 101-112; character keys: Unicode codepoint (lowercase).
# Used internally by WinitRuntime; not part of the public API.
# ---------------------------------------------------------------------------

_WINIT_MOD_SHIFT: int = 1
_WINIT_MOD_CTRL:  int = 2
_WINIT_MOD_ALT:   int = 4
_WINIT_MOD_SUPER: int = 8

_WINIT_KEY_MAP: dict[int, str] = {
    1:  KEY_INPUT_UP,
    2:  KEY_INPUT_DOWN,
    3:  KEY_INPUT_LEFT,
    4:  KEY_INPUT_RIGHT,
    5:  KEY_INPUT_ESC,
    6:  KEY_INPUT_RETURN,
    7:  KEY_INPUT_BACKSPACE,
    8:  KEY_INPUT_TAB,
    9:  KEY_INPUT_SPACE,
    10: KEY_INPUT_DELETE,
    11: KEY_INPUT_HOME,
    12: KEY_INPUT_END,
    13: KEY_INPUT_PAGE_UP,
    14: KEY_INPUT_PAGE_DOWN,
    15: KEY_INPUT_INSERT,
    101: KEY_INPUT_F1,
    102: KEY_INPUT_F2,
    103: KEY_INPUT_F3,
    104: KEY_INPUT_F4,
    105: KEY_INPUT_F5,
    106: KEY_INPUT_F6,
    107: KEY_INPUT_F7,
    108: KEY_INPUT_F8,
    109: KEY_INPUT_F9,
    110: KEY_INPUT_F10,
    111: KEY_INPUT_F11,
    112: KEY_INPUT_F12,
}


def _winit_key_to_str(code: int) -> str:
    """Map a winit key code (etype=5 event x field) to a KEY_INPUT_* string."""
    if code in _WINIT_KEY_MAP:
        return _WINIT_KEY_MAP[code]
    if 32 <= code <= 0x10FFFF:
        return chr(code)
    return ""


def _winit_mods_to_set(flags: int) -> frozenset[str]:
    """Convert winit modifier bitmask to a frozenset of KEY_MOD_* strings.

    Transparent mapping: on macOS the Super (Cmd) key maps to KEY_MOD_CMD;
    on Linux/Windows the Ctrl key maps to KEY_MOD_CMD.
    """
    import sys

    mods: set[str] = set()
    if flags & _WINIT_MOD_SHIFT:
        mods.add(KEY_MOD_SHIFT)
    if flags & _WINIT_MOD_ALT:
        mods.add(KEY_MOD_ALT)
    if sys.platform == "darwin":
        if flags & _WINIT_MOD_SUPER:
            mods.add(KEY_MOD_CMD)
        if flags & _WINIT_MOD_CTRL:
            mods.add(KEY_MOD_CTRL)
    else:  # Linux / Windows: Ctrl is the "command" modifier
        if flags & _WINIT_MOD_CTRL:
            mods.add(KEY_MOD_CMD)
        if flags & _WINIT_MOD_SUPER:
            mods.add(KEY_MOD_CTRL)
    return frozenset(mods)


__all__ = (
    # Special inputs (Pythonista-compatible)
    "KEY_INPUT_UP",
    "KEY_INPUT_DOWN",
    "KEY_INPUT_LEFT",
    "KEY_INPUT_RIGHT",
    "KEY_INPUT_ESC",
    "KEY_INPUT_RETURN",
    "KEY_INPUT_BACKSPACE",
    "KEY_INPUT_TAB",
    "KEY_INPUT_SPACE",
    # Extended inputs (desktop + iOS 13.4+)
    "KEY_INPUT_DELETE",
    "KEY_INPUT_HOME",
    "KEY_INPUT_END",
    "KEY_INPUT_PAGE_UP",
    "KEY_INPUT_PAGE_DOWN",
    "KEY_INPUT_INSERT",
    "KEY_INPUT_F1",
    "KEY_INPUT_F2",
    "KEY_INPUT_F3",
    "KEY_INPUT_F4",
    "KEY_INPUT_F5",
    "KEY_INPUT_F6",
    "KEY_INPUT_F7",
    "KEY_INPUT_F8",
    "KEY_INPUT_F9",
    "KEY_INPUT_F10",
    "KEY_INPUT_F11",
    "KEY_INPUT_F12",
    # Modifiers
    "KEY_MOD_CMD",
    "KEY_MOD_CTRL",
    "KEY_MOD_ALT",
    "KEY_MOD_SHIFT",
)
