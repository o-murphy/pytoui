from __future__ import annotations
import ctypes
import time
from pathlib import Path
from typing import TYPE_CHECKING

from pytoui._osdbuf import FrameBuffer

from pytoui.ui._constants import (
    GLOBAL_UI_ANTIALIAS,
    GLOBAL_UI_RT_FPS,
)
from pytoui.ui._draw import (
    _tick,
    _tick_delays,
    _screen_origin,
    convert_point,
)
from pytoui.ui._types import Touch


if TYPE_CHECKING:
    from pytoui.ui._view import View


__all__ = ("WinitRuntime",)


# Coordinate Helpers
def _any_dirty(view: View) -> bool:
    """Recursively check if any view in the hierarchy needs to be redrawn."""
    if view._needs_display:
        return True
    for sv in view._subviews:
        if _any_dirty(sv):
            return True
    return False


def find_view_at(view: View, screen_x: float, screen_y: float):
    """Identify the topmost touch-enabled view at the specific screen coordinates."""
    if view.hidden:
        return None
    ox, oy = _screen_origin(view)
    fw, fh = view._frame.w, view._frame.h
    if not (ox <= screen_x < ox + fw and oy <= screen_y < oy + fh):
        return None
    for child in reversed(view.subviews):
        target = find_view_at(child, screen_x, screen_y)
        if target is not None and target.touch_enabled:
            return target
    return view if view.touch_enabled else None


_LIB_PATH = str(Path(__file__).parent / "libwinitrt.so")
CHECKER_SIZE = 8


class WinitRuntime:
    """Runtime using Rust-based winit for windowing and event handling."""

    def __init__(self, root_view: View, width: int, height: int, render_fn):
        self.root = root_view

        # Use ctypes for stable memory addresses used by the shared library
        self._width_c = ctypes.c_uint32(width)
        self._height_c = ctypes.c_uint32(height)

        self.render_fn = render_fn

        # Interaction State
        self.tracked_view = None
        self.active_touch_id = 0
        self.last_screen_point = (0.0, 0.0)

        # Performance Monitoring
        self._fps_frame_count = 0
        self._fps_last_t = time.time()

        # Pre-allocate pixel buffer. Standard softbuffer is 0xAARRGGBB (4 bytes per pixel).
        # We allocate for 4K resolution immediately to avoid reallocating memory.
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
                None, ctypes.c_int, ctypes.c_double, ctypes.c_double
            ),  # event_callback
            ctypes.c_char_p,  # title
        ]

        # Wrap methods in callbacks to prevent Garbage Collection
        self._render_cb = ctypes.CFUNCTYPE(ctypes.c_int)(self._internal_render)
        self._event_cb = ctypes.CFUNCTYPE(
            None, ctypes.c_int, ctypes.c_double, ctypes.c_double
        )(self._internal_event)

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

    @property
    def width(self):
        return self._width_c.value

    @property
    def height(self):
        return self._height_c.value

    def _internal_render(self) -> int:
        """Internal callback executed by Rust for every frame draw."""
        now = time.time()

        # FPS Logic
        if GLOBAL_UI_RT_FPS:
            self._fps_frame_count += 1
            elapsed = now - self._fps_last_t
            if elapsed >= 1.0:
                print(f"FPS: {self._fps_frame_count / elapsed:.1f}", flush=True)
                self._fps_frame_count = 0
                self._fps_last_t = now

        # System Updates
        self._update_hierarchy(self.root, now)
        _tick(now)
        _tick_delays(now)

        # Get current dimensions (might have changed due to resizing in Rust)
        w, h = self.width, self.height
        if w == 0 or h == 0:
            return 0

        fb = self._fb
        if fb is None:
            return 0

        # Handle window resizing: recreate FrameBuffer if dimensions changed
        if fb._width != w or fb._height != h:
            FrameBuffer._lib.DestroyFrameBuffer(fb._handle)
            fb._handle = 0
            self._fb = FrameBuffer(self.pixel_data, w, h)
            self._fb.antialias = GLOBAL_UI_ANTIALIAS
            fb = self._fb

        # Signal Rust to close the window if view.close() was called
        if not self.root._presented:
            return 1

        # Render directly to pixel_data
        fb.draw_checkerboard(CHECKER_SIZE)
        self.render_fn(fb)
        return 0

    def _internal_event(self, etype, x, y):
        """Internal callback for mouse/touch events from the native window."""
        # etype mapping: 0=Down, 1=Up, 2=Move, 3=Leave
        if x < 0 and y < 0:
            x, y = self.last_screen_point

        if etype == 0:
            self._mouse_down(x, y)
        elif etype == 1:
            self._mouse_up(x, y)
        elif etype == 2:
            self._mouse_move(x, y)
        elif etype == 3:
            self._mouse_cancel()

    def _update_hierarchy(self, view: View, now: float):
        """Recursively call update() on views that have a defined update_interval."""
        if view.update_interval > 0:
            if now - view._last_update_t >= view.update_interval:
                view.update()
                view._last_update_t = now
        for sv in view.subviews:
            self._update_hierarchy(sv, now)

    def _create_touch(self, view: View, screen_x, screen_y, phase):
        """Create a Touch object with localized coordinates."""
        local = convert_point((screen_x, screen_y), to_view=view)
        prev_local = convert_point(self.last_screen_point, to_view=view)
        return Touch(
            location=(local.x, local.y),
            phase=phase,
            prev_location=(prev_local.x, prev_local.y),
            timestamp=int(time.time() * 1000),
            touch_id=self.active_touch_id,
        )

    def _mouse_down(self, x, y):
        self.last_screen_point = (x, y)
        target = find_view_at(self.root, x, y)
        if target:
            self.tracked_view = target
            self.active_touch_id += 1
            target.touch_began(self._create_touch(target, x, y, "began"))

    def _mouse_move(self, x, y):
        if not self.tracked_view:
            self.last_screen_point = (x, y)
            return
        phase = "moved" if (x, y) != self.last_screen_point else "stationary"
        touch = self._create_touch(self.tracked_view, x, y, phase)
        self.last_screen_point = (x, y)
        self.tracked_view.touch_moved(touch)

    def _mouse_up(self, x, y):
        if not self.tracked_view:
            return
        current = find_view_at(self.root, x, y)
        phase = "ended" if current is self.tracked_view else "cancelled"
        self.tracked_view.touch_ended(
            self._create_touch(self.tracked_view, x, y, phase)
        )
        self.tracked_view = None
        self.last_screen_point = (x, y)

    def _mouse_cancel(self):
        if self.tracked_view:
            x, y = self.last_screen_point
            self.tracked_view.touch_ended(
                self._create_touch(self.tracked_view, x, y, "cancelled")
            )
            self.tracked_view = None

    def run(self):
        """Start the runtime loop and initialize the native window."""
        # Initialize the persistent FrameBuffer
        self._fb = FrameBuffer(
            self.pixel_data, self._width_c.value, self._height_c.value
        )
        self._fb.antialias = GLOBAL_UI_ANTIALIAS

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
            # Proper cleanup of the FrameBuffer handle
            if self._fb is not None and self._fb._handle > 0:
                self._fb._lib.DestroyFrameBuffer(self._fb._handle)
                self._fb._handle = 0
            self._fb = None
            self.root.close()
