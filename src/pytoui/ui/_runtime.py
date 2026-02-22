"""UI runtimes for View.present().

_UI_RUNTIME (from env var UI_RUNTIME) selects which runtime to use:
  "sdl"  — SDLRuntime:            renders to an SDL2 window (default)
  "fb"   — RawFrameBufferRuntime: renders to raw pixel buffer (headless/test)

View.present() calls launch_runtime(self) which picks and runs the right one.

Multi-window note
-----------------
SDL's event queue is global. Calling SDL_PollEvent from multiple threads
causes events to be randomly consumed by the wrong window. The fix: a single
background pump thread owns all SDL_PollEvent calls and routes events to
per-window queues via _window_map. Each SDLRuntime drains its own queue.
"""

from __future__ import annotations

import ctypes
from pathlib import Path
from typing import TYPE_CHECKING

from pytoui._osdbuf import FrameBuffer
from pytoui._base_runtime import BaseRuntime

from pytoui._platform import (
    _UI_ANTIALIAS,
    _UI_RT,
)

if TYPE_CHECKING:
    from pytoui.ui._view import View


# --- LOAD DEFAULT FONTS ---
_DEFAULT_FONTS_PATH = Path(__file__).parent.parent
FrameBuffer.load_font(str(_DEFAULT_FONTS_PATH / "fonts" / "DejaVuSans.ttf"))
FrameBuffer.load_font(str(_DEFAULT_FONTS_PATH / "fonts" / "DejaVuSans-Bold.ttf"))


# ---------------------------------------------------------------------------
# RawFrameBufferRuntime (headless / testing)
# ---------------------------------------------------------------------------


class RawFrameBufferRuntime(BaseRuntime):
    """Renders one frame to a raw pixel buffer and exits. Useful for tests."""

    def run(self):
        pixel_data = (ctypes.c_ubyte * (self.width * self.height * 4))()
        with FrameBuffer(pixel_data, self.width, self.height) as fb:
            fb.antialias = _UI_ANTIALIAS
            self.render_fn(fb)
        self._unregister()
        self.root.close()


# ---------------------------------------------------------------------------
# Runtime launcher — called by View.present()
# ---------------------------------------------------------------------------


def get_screen_size() -> tuple[int, int]:
    """Return the size of the main screen as a (width, height) tuple (in points)."""
    runtime = _get_runtime()
    try:
        return runtime.get_screen_size()
    except Exception:
        return (1920, 1080)


def get_window_size() -> tuple[int, int]:
    """Return the current window size as a (width, height) tuple.

    Unlike get_screen_size(), this reflects the actual window dimensions
    and changes when the window is resized.  Falls back to get_screen_size()
    if no window is currently open.
    """
    from pytoui._base_runtime import _root_to_runtime

    for rt in _root_to_runtime.values():
        return rt.current_size
    return get_screen_size()


def get_ui_style() -> str:
    """Return the current UI style: 'dark' or 'light'.

    Controlled by the UI_STYLE environment variable (default: 'dark').
    """
    import os

    style = os.environ.get("UI_STYLE", "dark").lower()
    return style if style in ("dark", "light") else "dark"


def _get_runtime():
    match _UI_RT:
        case "fb":
            return RawFrameBufferRuntime
        case "winit":
            from pytoui._winitrt import WinitRuntime

            return WinitRuntime
        case _:
            from pytoui._sdlrt import SDLRuntime

            return SDLRuntime


def launch_runtime(root_view: View, render_fn) -> None:
    """Pick and run the appropriate runtime based on _UI_RUNTIME."""
    w = int(root_view._frame.w)
    h = int(root_view._frame.h)
    runtime = _get_runtime()
    runtime(root_view, w, h, render_fn).run()
