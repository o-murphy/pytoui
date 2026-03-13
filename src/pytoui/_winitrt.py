"""WinitRuntime — renders via a Rust/winit native window (libwinitrt.so)."""

from __future__ import annotations

import ctypes
import math
import signal
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from pytoui._osdbuf import FrameBuffer
from pytoui._platform import (
    _UI_ANTIALIAS,
    _UI_DISABLE_WINIT_CSD,
    _UI_RT_FPS,
)
from pytoui.base_runtime import _CHECKER_SIZE, _SCROLL_LINE_PX, BaseRuntime, any_dirty
from pytoui.hid import (
    KEY_INPUT_ESC,
    MOUSE_LEFT_ID,
    MOUSE_MIDDLE_ID,
    MOUSE_RIGHT_ID,
    _winit_key_to_str,
    _winit_mods_to_set,
)
from pytoui.ui._draw import _tick, _tick_delays

if TYPE_CHECKING:
    from pytoui.ui._view import _ViewInternals


__all__ = ("WinitRuntime",)


def _lib_filename(name: str) -> str:
    if sys.platform.startswith("linux"):
        return f"lib{name}.so"
    elif sys.platform == "darwin":
        return f"lib{name}.dylib"
    elif sys.platform == "win32":
        return f"{name}.dll"
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")


_LIB_PATH = str(Path(__file__).parent / _lib_filename("winitrt"))


class WinitRuntime(BaseRuntime):
    """Runtime using Rust-based winit for windowing and event handling."""

    def __init__(self, root_view: _ViewInternals, width: int, height: int, render_fn):
        super().__init__(root_view, width, height, render_fn)

        # Use ctypes for stable memory addresses used by the shared library
        self._width_c = ctypes.c_uint32(width)
        self._height_c = ctypes.c_uint32(height)
        # Scale factor written by Rust; 1.0 on non-HiDPI, >1 on HiDPI/Wayland
        self._scale_factor_c = ctypes.c_double(1.0)
        # Last logical dims — avoid redundant root.frame updates
        self._last_lw: int = width
        self._last_lh: int = height

        # Performance Monitoring
        self._fps_frame_count = 0
        self._fps_last_t = time.time()

        # Pre-allocate pixel buffer (0xAARRGGBB, 4 bytes/pixel).
        # Allocate for 4K immediately to avoid reallocation on resize.
        self._max_pixels = 3840 * 2160
        self.pixel_data = (ctypes.c_uint32 * self._max_pixels)()

        # Keep FrameBuffer alive for the duration of the runtime
        self._fb: FrameBuffer | None = None
        self._cursor_pos: tuple[float, float] = (0.0, 0.0)

        self._lib = ctypes.CDLL(_LIB_PATH)

        # Define Rust function signatures
        self._lib.winit_run.argtypes = [
            ctypes.c_uint32,  # initial_width
            ctypes.c_uint32,  # initial_height
            ctypes.POINTER(ctypes.c_uint32),  # pixel_ptr
            ctypes.POINTER(ctypes.c_uint32),  # width_ptr (physical pixels)
            ctypes.POINTER(ctypes.c_uint32),  # height_ptr (physical pixels)
            ctypes.POINTER(ctypes.c_double),  # scale_factor_ptr (written by Rust)
            ctypes.CFUNCTYPE(ctypes.c_int),  # render_callback -> 0=continue, 1=close
            ctypes.CFUNCTYPE(
                None,
                ctypes.c_int,
                ctypes.c_double,
                ctypes.c_double,
                ctypes.c_int64,
            ),  # event_callback(etype, x, y, touch_id) — coords in logical pixels
            ctypes.c_uint8,  # decorations: 1=CSD (winit draws), 0=SSD (compositor)
            ctypes.c_char_p,  # title
        ]

        # Wrap methods in callbacks to prevent Garbage Collection
        self._render_cb = ctypes.CFUNCTYPE(ctypes.c_int)(self._internal_render)
        self._event_cb = ctypes.CFUNCTYPE(
            None,
            ctypes.c_int,
            ctypes.c_double,
            ctypes.c_double,
            ctypes.c_int64,
        )(self._internal_event)

    @property
    def _cur_width(self):
        return self._width_c.value

    @property
    def _cur_height(self):
        return self._height_c.value

    @property
    def current_size(self) -> tuple[int, int]:
        return (self._width_c.value, self._height_c.value)

    @classmethod
    def get_screen_size(cls):
        """Retrieve the primary display bounds using the winit library."""
        lib = ctypes.CDLL(
            _LIB_PATH,
        )
        lib.winit_screen_size.argtypes = [
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
        ]
        lib.winit_screen_size.restype = None
        w, h = ctypes.c_uint32(0), ctypes.c_uint32(0)
        lib.winit_screen_size(ctypes.byref(w), ctypes.byref(h))
        return (w.value, h.value)

    def _internal_render(self) -> int:
        """Internal callback executed by Rust for every frame draw."""
        now = time.time()

        if _UI_RT_FPS:
            self._fps_frame_count += 1
            elapsed = now - self._fps_last_t
            if elapsed >= 1.0:
                print(f"FPS: {self._fps_frame_count / elapsed:.1f}", flush=True)
                self._fps_frame_count = 0
                self._fps_last_t = now

        self._update_hierarchy(self.root, now)
        _tick(now)
        _tick_delays(now)

        w, h = self._cur_width, self._cur_height  # physical pixels
        if w == 0 or h == 0:
            return 0

        fb = self._fb
        if fb is None:
            return 0

        scale = self._scale_factor_c.value
        if scale <= 0.0:
            scale = 1.0
        lw = max(1, math.ceil(w / scale))
        lh = max(1, math.ceil(h / scale))

        if fb._width != w or fb._height != h:
            FrameBuffer._lib.DestroyFrameBuffer(fb._handle)
            fb._handle = 0
            self._fb = FrameBuffer(self.pixel_data, w, h)
            self._fb.antialias = _UI_ANTIALIAS
            self._fb.scale_factor = scale
            fb = self._fb
            self._last_lw = lw
            self._last_lh = lh
            rf = self.root.frame()
            self.root.setFrame_((rf.x, rf.y, float(lw), float(lh)))
        elif lw != self._last_lw or lh != self._last_lh or fb.scale_factor != scale:
            fb.scale_factor = scale
            self._last_lw = lw
            self._last_lh = lh
            rf = self.root.frame()
            self.root.setFrame_((rf.x, rf.y, float(lw), float(lh)))

        if not self.root.pytoui_presented:
            return 1

        if not any_dirty(self.root):
            return 0

        fb.draw_checkerboard(_CHECKER_SIZE)
        self.render_fn(fb)
        return 0

    def _internal_event(self, etype, x, y, touch_id: int):
        """Internal callback for mouse/touch events from the native window.

        etype: 0=Down, 1=Up, 2=Move, 3=Cancel/Leave, 4=Scroll
        touch_id: -1=left mouse, -2=right mouse, -3=middle mouse,
                  >= 0=real touch fingers
        For etype=2 (CursorMoved): touch_id is always -1 regardless of buttons.
        For etype=4: x=dx, y=dy in lines (touch_id=0) or pixels (touch_id=1).
        """
        match etype:
            case 0:
                if touch_id < 0:
                    self._mouse_down(x, y, touch_id)
                else:
                    self._touch_down(x, y, touch_id)
            case 1:
                if touch_id < 0:
                    self._mouse_up(x, y, touch_id)
                else:
                    self._touch_up(x, y, touch_id)
            case 2:
                self._cursor_pos = (x, y)
                if touch_id < 0:
                    any_drag = False
                    for bid in (MOUSE_LEFT_ID, MOUSE_RIGHT_ID, MOUSE_MIDDLE_ID):
                        if bid in self._held_mouse_buttons:
                            self._mouse_dragged(x, y, bid)
                            any_drag = True
                    if not any_drag:
                        self._mouse_moved(x, y)
                else:
                    self._touch_move(x, y, touch_id)
            case 3:
                if touch_id < 0:
                    self._mouse_cancel(touch_id)
                else:
                    self._touch_cancel(touch_id)
            case 4:
                cx, cy = self._cursor_pos
                # touch_id doubles as is_pixel:
                # 0=LineDelta (lines), 1=PixelDelta (logical px)
                if touch_id:
                    self._scroll_event(cx, cy, x, y)
                else:
                    self._scroll_event(cx, cy, x * _SCROLL_LINE_PX, y * _SCROLL_LINE_PX)
            case 5:
                code, flags = int(x), int(y)
                key_str = _winit_key_to_str(code)
                mods = _winit_mods_to_set(flags)
                handled = False
                if key_str:
                    handled = self._key_down(key_str, mods)
                if not handled and key_str == KEY_INPUT_ESC:
                    self.root.close()

    def run(self):
        """Start the runtime loop and initialize the native window."""
        self._fb = FrameBuffer(
            self.pixel_data,
            self._width_c.value,
            self._height_c.value,
        )
        self._fb.antialias = _UI_ANTIALIAS

        old_sigint = None
        try:
            old_sigint = signal.signal(
                signal.SIGINT,
                lambda *_: self.root.close(),
            )
        except (ValueError, OSError):
            pass
        try:
            self._lib.winit_run(
                self._width_c.value,
                self._height_c.value,
                self.pixel_data,
                ctypes.byref(self._width_c),
                ctypes.byref(self._height_c),
                ctypes.byref(self._scale_factor_c),
                self._render_cb,
                self._event_cb,
                ctypes.c_uint8(0 if _UI_DISABLE_WINIT_CSD else 1),
                self.root._name.encode("utf-8"),
            )
        finally:
            if old_sigint is not None:
                signal.signal(signal.SIGINT, old_sigint)
            if self._fb is not None and self._fb._handle > 0:
                self._fb._lib.DestroyFrameBuffer(self._fb._handle)
                self._fb._handle = 0
            self._fb = None
            self._unregister()
            self.root.close()
