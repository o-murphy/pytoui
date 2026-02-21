"""WinitRuntime — renders via a Rust/winit native window (libwinitrt.so)."""

from __future__ import annotations

import ctypes
import time
from pathlib import Path
from typing import TYPE_CHECKING

from pytoui._osdbuf import FrameBuffer

from pytoui._base_runtime import BaseRuntime, CHECKER_SIZE
from pytoui.ui._constants import (
    _UI_ANTIALIAS,
    _UI_RT_FPS,
)
from pytoui.ui._draw import _tick, _tick_delays

if TYPE_CHECKING:
    from pytoui.ui._view import View


__all__ = ("WinitRuntime",)

_LIB_PATH = str(Path(__file__).parent / "libwinitrt.so")


class WinitRuntime(BaseRuntime):
    """Runtime using Rust-based winit for windowing and event handling."""

    def __init__(self, root_view: "View", width: int, height: int, render_fn):
        super().__init__(root_view, width, height, render_fn)

        # Use ctypes for stable memory addresses used by the shared library
        self._width_c = ctypes.c_uint32(width)
        self._height_c = ctypes.c_uint32(height)

        # Performance Monitoring
        self._fps_frame_count = 0
        self._fps_last_t = time.time()

        # Pre-allocate pixel buffer (0xAARRGGBB, 4 bytes/pixel).
        # Allocate for 4K immediately to avoid reallocation on resize.
        self._max_pixels = 3840 * 2160
        self.pixel_data = (ctypes.c_uint32 * self._max_pixels)()

        # Keep FrameBuffer alive for the duration of the runtime
        self._fb: FrameBuffer | None = None

        self._lib = ctypes.CDLL(_LIB_PATH)

        # Define Rust function signatures
        self._lib.winit_run.argtypes = [
            ctypes.c_uint32,  # initial_width
            ctypes.c_uint32,  # initial_height
            ctypes.POINTER(ctypes.c_uint32),  # pixel_ptr
            ctypes.POINTER(ctypes.c_uint32),  # width_ptr
            ctypes.POINTER(ctypes.c_uint32),  # height_ptr
            ctypes.CFUNCTYPE(ctypes.c_int),  # render_callback -> 0=continue, 1=close
            ctypes.CFUNCTYPE(
                None, ctypes.c_int, ctypes.c_double, ctypes.c_double, ctypes.c_int64
            ),  # event_callback(etype, x, y, touch_id)  touch_id==-1 → mouse
            ctypes.c_char_p,  # title
        ]

        # Wrap methods in callbacks to prevent Garbage Collection
        self._render_cb = ctypes.CFUNCTYPE(ctypes.c_int)(self._internal_render)
        self._event_cb = ctypes.CFUNCTYPE(
            None, ctypes.c_int, ctypes.c_double, ctypes.c_double, ctypes.c_int64
        )(self._internal_event)

    @property
    def _cur_width(self):
        return self._width_c.value

    @property
    def _cur_height(self):
        return self._height_c.value

    @classmethod
    def get_screen_size(cls):
        """Retrieve the primary display bounds using the winit library."""
        lib = ctypes.CDLL(
            str(Path(__file__).parent.parent / "winitrt" / "libwinitrt.so")
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

        w, h = self._cur_width, self._cur_height
        if w == 0 or h == 0:
            return 0

        fb = self._fb
        if fb is None:
            return 0

        if fb._width != w or fb._height != h:
            FrameBuffer._lib.DestroyFrameBuffer(fb._handle)
            fb._handle = 0
            self._fb = FrameBuffer(self.pixel_data, w, h)
            self._fb.antialias = _UI_ANTIALIAS
            fb = self._fb
            rf = self.root._frame
            self.root.frame = (rf.x, rf.y, float(w), float(h))

        if not self.root._presented:
            return 1

        fb.draw_checkerboard(CHECKER_SIZE)
        self.render_fn(fb)
        return 0

    def _internal_event(self, etype, x, y, touch_id: int):
        """Internal callback for mouse/touch events from the native window.

        etype: 0=Down, 1=Up, 2=Move, 3=Cancel/Leave
        touch_id: -1 for mouse pointer, >= 0 for real touch fingers
        """
        if etype == 0:
            self._touch_down(x, y, touch_id)
        elif etype == 1:
            self._touch_up(x, y, touch_id)
        elif etype == 2:
            self._touch_move(x, y, touch_id)
        elif etype == 3:
            self._touch_cancel(touch_id)

    def run(self):
        """Start the runtime loop and initialize the native window."""
        self._fb = FrameBuffer(
            self.pixel_data, self._width_c.value, self._height_c.value
        )
        self._fb.antialias = _UI_ANTIALIAS

        try:
            self._lib.winit_run(
                self._width_c.value,
                self._height_c.value,
                self.pixel_data,
                ctypes.byref(self._width_c),
                ctypes.byref(self._height_c),
                self._render_cb,
                self._event_cb,
                self.root.name.encode("utf-8"),
            )
        finally:
            if self._fb is not None and self._fb._handle > 0:
                self._fb._lib.DestroyFrameBuffer(self._fb._handle)
                self._fb._handle = 0
            self._fb = None
            self._unregister()
            self.root.close()
