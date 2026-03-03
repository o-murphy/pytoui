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
import threading
from typing import TYPE_CHECKING

from pytoui._base_runtime import BaseRuntime
from pytoui._osdbuf import FrameBuffer
from pytoui._platform import (
    _UI_ANTIALIAS,
    _UI_RT,
)

if TYPE_CHECKING:
    from pytoui.ui._view import _ViewInternals


# --- LOAD DEFAULT FONTS ---


def _load_default_fonts():
    from pytoui._fonts import resolve_any_font

    for name, size in [("<system>", 17), ("<system-bold>", 17)]:
        path = resolve_any_font(name, size)
        if path:
            try:
                FrameBuffer.load_font_cached(str(path))
            except Exception:
                pass


_load_default_fonts()

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


def launch_runtime(root_view: _ViewInternals, render_fn) -> None:
    """Pick and run the appropriate runtime based on _UI_RUNTIME.

    Each windowed runtime runs in its own non-daemon thread so that multiple
    windows can coexist without freezing each other (e.g. presenting a second
    window from a button handler keeps the first window interactive).

    Non-daemon threads keep the process alive until every window is closed,
    matching Pythonista's behaviour where present() is non-blocking and the
    app stays open.  Use wait_modal() to block the caller until a window closes.

    RawFrameBufferRuntime (headless/testing) runs synchronously on the calling
    thread since it has no event loop and is expected to complete instantly.
    """
    w, h = root_view.frame.size
    w = int(w) if w > 0 else 400
    h = int(h) if h > 0 else 600
    runtime_class = _get_runtime()

    if runtime_class is RawFrameBufferRuntime:
        # Headless: run synchronously so tests can inspect results immediately.
        runtime_class(root_view, w, h, render_fn).run()
        return

    # Windowed runtimes: run in a dedicated thread.
    # Wait for __init__ to finish so init errors propagate to the caller and
    # the window is guaranteed to exist before present() returns.
    _init_done: threading.Event = threading.Event()
    _init_exc: list[BaseException | None] = [None]

    def _window_thread() -> None:
        try:
            rt = runtime_class(root_view, w, h, render_fn)
        except BaseException as exc:
            _init_exc[0] = exc
            _init_done.set()
            return
        _init_done.set()
        rt.run()

    t = threading.Thread(target=_window_thread, daemon=False, name="pytoui-window")
    t.start()
    _init_done.wait()
    if _init_exc[0] is not None:
        raise _init_exc[0]
