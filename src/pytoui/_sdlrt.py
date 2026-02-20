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

import os
import ctypes
import queue
import time
import threading
from typing import TYPE_CHECKING

from pytoui._osdbuf import FrameBuffer

from pytoui.ui._constants import (
    GLOBAL_UI_ANTIALIAS,
    GLOBAL_UI_RT_FPS,
    GLOBAL_UI_RT_SDL_DELAY,
    GLOBAL_UI_RT_SDL_MAX_DELAY,
)
from pytoui.ui._draw import (
    _tick,
    _screen_origin,
    _tick_delays,
    convert_point,
)
from pytoui.ui._types import Touch

if TYPE_CHECKING:
    from pytoui.ui._view import View


__all__ = ("SDLRuntime",)

# ---------------------------------------------------------------------------
# Coordinate helpers (shared by all runtimes)
# ---------------------------------------------------------------------------


def _any_dirty(view: "View") -> bool:
    """Return True if view or any descendant has _needs_display set."""
    if view._needs_display:
        return True
    for sv in view._subviews:
        if _any_dirty(sv):
            return True
    return False


def find_view_at(view: View, screen_x: float, screen_y: float):
    """Return the topmost touch-enabled View at the given screen coordinates."""

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


# ---------------------------------------------------------------------------
# Global SDL event pump (single thread owns SDL_PollEvent)
# ---------------------------------------------------------------------------

# window_id → SDLRuntime; all access protected by _wmap_lock
_window_map: dict[int, "SDLRuntime"] = {}
_wmap_lock = threading.Lock()
_pump_thread: threading.Thread | None = None


def _register_runtime(rt: "SDLRuntime") -> None:
    global _pump_thread
    with _wmap_lock:
        _window_map[rt.window_id] = rt
        if _pump_thread is None or not _pump_thread.is_alive():
            _pump_thread = threading.Thread(
                target=_pump_loop, args=(rt._sdl2,), daemon=True, name="sdl-pump"
            )
            _pump_thread.start()


def _unregister_runtime(rt: "SDLRuntime") -> None:
    with _wmap_lock:
        _window_map.pop(rt.window_id, None)


def _pump_loop(sdl2) -> None:
    """Single thread that polls SDL events and routes them to per-window queues."""
    event = sdl2.SDL_Event()
    while True:
        with _wmap_lock:
            if not _window_map:
                break
        while sdl2.SDL_PollEvent(ctypes.byref(event)):
            _route_event(sdl2, event)
        time.sleep(0.001)


def _route_event(sdl2, event) -> None:
    t = event.type

    if t == sdl2.SDL_QUIT:
        with _wmap_lock:
            targets = list(_window_map.values())
        for rt in targets:
            rt._event_queue.put(("quit",))
        return

    elif t == sdl2.SDL_WINDOWEVENT:
        wid = event.window.windowID
        # Add special check for window closing
        if event.window.event == sdl2.SDL_WINDOWEVENT_CLOSE:
            _send(wid, ("window_close",))
        else:
            _send(wid, ("windowevent", event.window.event))

    if t == sdl2.SDL_MOUSEBUTTONDOWN:
        wid = event.button.windowID
        _send(wid, ("mousedown", event.button.button, event.button.x, event.button.y))
    elif t == sdl2.SDL_MOUSEBUTTONUP:
        wid = event.button.windowID
        _send(wid, ("mouseup", event.button.button, event.button.x, event.button.y))
    elif t == sdl2.SDL_MOUSEMOTION:
        wid = event.motion.windowID
        _send(wid, ("mousemove", event.motion.state, event.motion.x, event.motion.y))
    elif t == sdl2.SDL_KEYDOWN:
        wid = event.key.windowID
        _send(wid, ("keydown", event.key.keysym.sym))
    elif t == sdl2.SDL_WINDOWEVENT:
        wid = event.window.windowID
        _send(wid, ("windowevent", event.window.event))


def _send(wid: int, msg: tuple) -> None:
    with _wmap_lock:
        rt = _window_map.get(wid)
    if rt is not None:
        rt._event_queue.put(msg)


# ---------------------------------------------------------------------------
# SDLRuntime
# ---------------------------------------------------------------------------

CHECKER_SIZE = 8


class SDLRuntime:
    _sdl_ref_count = 0
    _sdl_lock = threading.Lock()

    def __init__(self, root_view: View, width: int, height: int, render_fn):
        os.environ.setdefault("SDL_VIDEODRIVER", "wayland")
        os.environ.setdefault("PYSDL2_DLL_PATH", "/usr/lib")

        import sdl2  # type: ignore[import-untyped]

        self._sdl2 = sdl2
        self._FrameBuffer = FrameBuffer

        self.root = root_view
        self.width = width
        self.height = height
        self.render_fn = render_fn
        self.running = False

        self.tracked_view = None
        self.active_touch_id = 0
        self.last_screen_point = (0, 0)

        self._event_queue: queue.SimpleQueue = queue.SimpleQueue()

        with SDLRuntime._sdl_lock:
            if SDLRuntime._sdl_ref_count == 0:
                if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO) != 0:
                    raise RuntimeError(sdl2.SDL_GetError().decode())
            SDLRuntime._sdl_ref_count += 1

        self.window = sdl2.SDL_CreateWindow(
            root_view.name.encode(),
            sdl2.SDL_WINDOWPOS_CENTERED,
            sdl2.SDL_WINDOWPOS_CENTERED,
            width,
            height,
            sdl2.SDL_WINDOW_SHOWN,
        )
        self.window_id = sdl2.SDL_GetWindowID(self.window)
        self.renderer = sdl2.SDL_CreateRenderer(
            self.window, -1, sdl2.SDL_RENDERER_ACCELERATED
        )
        self.texture = sdl2.SDL_CreateTexture(
            self.renderer,
            sdl2.SDL_PIXELFORMAT_ABGR8888,
            sdl2.SDL_TEXTUREACCESS_STREAMING,
            width,
            height,
        )
        sdl2.SDL_SetTextureBlendMode(self.texture, sdl2.SDL_BLENDMODE_BLEND)
        self.pixel_data = (ctypes.c_ubyte * (width * height * 4))()

        _register_runtime(self)

    @classmethod
    def get_screen_size(cls):
        import sdl2  # type: ignore[import-untyped]

        sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
        rect = sdl2.rect.SDL_Rect()
        sdl2.SDL_GetDisplayBounds(0, ctypes.byref(rect))
        return (rect.w, rect.h)

    # ------------------------------------------------------------------
    # Touch helpers
    # ------------------------------------------------------------------

    def _create_touch(self, view: View, screen_x, screen_y, phase):
        local_pos = convert_point((screen_x, screen_y), to_view=view)
        prev_local = convert_point(self.last_screen_point, to_view=view)
        return Touch(
            location=(local_pos.x, local_pos.y),
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

    # ------------------------------------------------------------------
    # Event dispatch (from per-window queue)
    # ------------------------------------------------------------------

    def _dispatch_queued_events(self):
        sdl2 = self._sdl2
        while True:
            try:
                msg = self._event_queue.get_nowait()
            except queue.Empty:
                break
            kind = msg[0]
            if kind == "quit" or kind == "window_close":
                self.running = False
            elif kind == "keydown":
                if msg[1] == sdl2.SDLK_ESCAPE:
                    self.running = False
            elif kind == "windowevent":
                if msg[1] == sdl2.SDL_WINDOWEVENT_LEAVE:
                    self._mouse_cancel()
            elif kind == "mousedown":
                if msg[1] == sdl2.SDL_BUTTON_LEFT:
                    self._mouse_down(msg[2], msg[3])
            elif kind == "mouseup":
                if msg[1] == sdl2.SDL_BUTTON_LEFT:
                    self._mouse_up(msg[2], msg[3])
            elif kind == "mousemove":
                if msg[1] & sdl2.SDL_BUTTON_LMASK:
                    self._mouse_move(msg[2], msg[3])

    # ------------------------------------------------------------------
    # Update hierarchy (update_interval)
    # ------------------------------------------------------------------

    def _update_hierarchy(self, view: View, now: float):
        if view.update_interval > 0:
            if now - view._last_update_t >= view.update_interval:
                view.update()
                view._last_update_t = now
        for sv in view.subviews:
            self._update_hierarchy(sv, now)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        self.running = True
        sdl2 = self._sdl2
        _fps_frame_count = 0
        _fps_last_t = time.time()

        with self._FrameBuffer(self.pixel_data, self.width, self.height) as fb:
            fb.antialias = GLOBAL_UI_ANTIALIAS

            while self.running and self.root._presented:
                now = time.time()

                if GLOBAL_UI_RT_FPS:
                    _fps_frame_count += 1
                    elapsed = now - _fps_last_t
                    if elapsed >= 1.0:
                        print(f"FPS: {_fps_frame_count / elapsed:.1f}", flush=True)
                        _fps_frame_count = 0
                        _fps_last_t = now

                self._dispatch_queued_events()
                self._update_hierarchy(self.root, now)
                _tick(now)
                _tick_delays(now)

                needs_redraw = _any_dirty(self.root)

                if needs_redraw:
                    fb.draw_checkerboard(CHECKER_SIZE)
                    self.render_fn(fb)

                    pixels_ptr = ctypes.c_void_p()
                    pitch = ctypes.c_int()
                    sdl2.SDL_LockTexture(
                        self.texture,
                        None,
                        ctypes.byref(pixels_ptr),
                        ctypes.byref(pitch),
                    )
                    ctypes.memmove(pixels_ptr, self.pixel_data, len(self.pixel_data))
                    sdl2.SDL_UnlockTexture(self.texture)

                    sdl2.SDL_RenderClear(self.renderer)
                    sdl2.SDL_RenderCopy(self.renderer, self.texture, None, None)
                    sdl2.SDL_RenderPresent(self.renderer)

                    sdl2.SDL_Delay(GLOBAL_UI_RT_SDL_DELAY)

                else:
                    # if nothing changes — sleep longer
                    sdl2.SDL_Delay(GLOBAL_UI_RT_SDL_MAX_DELAY)

        self._cleanup()
        self.root.close()

    def _cleanup(self):
        _unregister_runtime(self)
        sdl2 = self._sdl2
        sdl2.SDL_DestroyTexture(self.texture)
        sdl2.SDL_DestroyRenderer(self.renderer)
        sdl2.SDL_DestroyWindow(self.window)
        with SDLRuntime._sdl_lock:
            SDLRuntime._sdl_ref_count -= 1
            if SDLRuntime._sdl_ref_count == 0:
                sdl2.SDL_Quit()
