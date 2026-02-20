"""UI runtimes for View.present().

GLOBAL_UI_RUNTIME (from env var UI_RUNTIME) selects which runtime to use:
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
from typing import TYPE_CHECKING

from osdbuf import FrameBuffer
from ui._constants import (
    GLOBAL_UI_ANTIALIAS,
    GLOBAL_UI_RT,
)

if TYPE_CHECKING:
    from ui._view import View

# ---------------------------------------------------------------------------
# RawFrameBufferRuntime (headless / testing)
# ---------------------------------------------------------------------------


class RawFrameBufferRuntime:
    """Renders one frame to a raw pixel buffer and exits. Useful for tests."""

    def __init__(self, root_view: View, width: int, height: int, render_fn):
        self.root = root_view
        self.width = width
        self.height = height
        self.render_fn = render_fn

    def run(self):
        pixel_data = (ctypes.c_ubyte * (self.width * self.height * 4))()
        with FrameBuffer(pixel_data, self.width, self.height) as fb:
            fb.antialias = GLOBAL_UI_ANTIALIAS
            fb.load_font("./src/osdbuf/DejaVuSans.ttf")
            self.render_fn(fb)
        self.root.close()


# ---------------------------------------------------------------------------
# Runtime launcher — called by View.present()
# ---------------------------------------------------------------------------


def get_screen_size() -> tuple[int, int]:
    """Return the size of the main screen as a (width, height) tuple (in points)."""
    if GLOBAL_UI_RT == "fb":
        return (1920, 1080)
    if GLOBAL_UI_RT == "winit":
        try:
            from winitrt import WinitRuntime

            return WinitRuntime.get_screen_size()
        except Exception:
            return (1920, 1080)
    try:
        try:
            from sdlrt import SDLRuntime

            return SDLRuntime.get_screen_size()
        except Exception:
            return (1920, 1080)
    except Exception:
        return (1920, 1080)


def get_window_size() -> tuple[int, int]:
    """Return the size of the app's main window as a (width, height) tuple.

    On desktop this is the same as get_screen_size() (no split-screen mode).
    """
    return get_screen_size()


def get_ui_style() -> str:
    """Return the current UI style: 'dark' or 'light'.

    Controlled by the UI_STYLE environment variable (default: 'dark').
    """
    import os

    style = os.environ.get("UI_STYLE", "dark").lower()
    return style if style in ("dark", "light") else "dark"


def launch_runtime(root_view: View, render_fn) -> None:
    """Pick and run the appropriate runtime based on GLOBAL_UI_RUNTIME."""
    w = int(root_view._frame.w)
    h = int(root_view._frame.h)
    match GLOBAL_UI_RT:
        case "fb":
            RawFrameBufferRuntime(root_view, w, h, render_fn).run()
        case "winit":
            from winitrt import WinitRuntime

            WinitRuntime(root_view, w, h, render_fn).run()
        case _:
            from sdlrt import SDLRuntime

            SDLRuntime(root_view, w, h, render_fn).run()
