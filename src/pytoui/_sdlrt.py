"""SDLRuntime — renders to an SDL2 window.

Multi-window note
-----------------
SDL's event queue is global. Calling SDL_PollEvent from multiple threads
causes events to be randomly consumed by the wrong window. The fix: a single
background pump thread owns all SDL_PollEvent calls and routes events to
per-window queues via _window_map. Each SDLRuntime drains its own queue.
"""

from __future__ import annotations

import ctypes
import queue
import threading
import time
from typing import TYPE_CHECKING

from pytoui._base_runtime import _CHECKER_SIZE, _SCROLL_LINE_PX, BaseRuntime, _any_dirty
from pytoui._hid import MOUSE_LEFT_ID, MOUSE_MIDDLE_ID, MOUSE_RIGHT_ID
from pytoui._osdbuf import FrameBuffer
from pytoui._platform import (
    _UI_ANTIALIAS,
    _UI_RT_FPS,
    _UI_RT_SDL_DELAY,
    _UI_RT_SDL_MAX_DELAY,
)
from pytoui.ui._draw import _tick, _tick_delays
from pytoui.ui._types import Rect

if TYPE_CHECKING:
    from pytoui.ui._view import _ViewInternals


__all__ = ("SDLRuntime",)


# ---------------------------------------------------------------------------
# Global SDL event pump (single thread owns SDL_PollEvent)
# ---------------------------------------------------------------------------

# window_id → SDLRuntime; all access protected by _wmap_lock
_window_map: dict[int, SDLRuntime] = {}
_wmap_lock = threading.Lock()
_pump_thread: threading.Thread | None = None


def _register_runtime(rt: SDLRuntime) -> None:
    global _pump_thread
    with _wmap_lock:
        _window_map[rt.window_id] = rt
        if _pump_thread is None or not _pump_thread.is_alive():
            _pump_thread = threading.Thread(
                target=_pump_loop,
                args=(rt._sdl2,),
                daemon=True,
                name="sdl-pump",
            )
            _pump_thread.start()


def _unregister_sdl_runtime(rt: SDLRuntime) -> None:
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

    if t == sdl2.SDL_WINDOWEVENT:
        wid = event.window.windowID
        if event.window.event == sdl2.SDL_WINDOWEVENT_CLOSE:
            _send(wid, ("window_close",))
        elif event.window.event == sdl2.SDL_WINDOWEVENT_SIZE_CHANGED:
            _send(wid, ("window_resize", event.window.data1, event.window.data2))
        else:
            _send(wid, ("windowevent", event.window.event))
    elif t == sdl2.SDL_MOUSEBUTTONDOWN:
        wid = event.button.windowID
        _send(wid, ("mousedown", event.button.button, event.button.x, event.button.y))
    elif t == sdl2.SDL_MOUSEBUTTONUP:
        wid = event.button.windowID
        _send(wid, ("mouseup", event.button.button, event.button.x, event.button.y))
    elif t == sdl2.SDL_MOUSEMOTION:
        wid = event.motion.windowID
        _send(wid, ("mousemove", event.motion.state, event.motion.x, event.motion.y))
    elif t == sdl2.SDL_FINGERDOWN:
        wid = event.tfinger.windowID
        _send(
            wid,
            (
                "fingerdown",
                int(event.tfinger.fingerId),
                float(event.tfinger.x),
                float(event.tfinger.y),
            ),
        )
    elif t == sdl2.SDL_FINGERUP:
        wid = event.tfinger.windowID
        _send(
            wid,
            (
                "fingerup",
                int(event.tfinger.fingerId),
                float(event.tfinger.x),
                float(event.tfinger.y),
            ),
        )
    elif t == sdl2.SDL_FINGERMOTION:
        wid = event.tfinger.windowID
        _send(
            wid,
            (
                "fingermotion",
                int(event.tfinger.fingerId),
                float(event.tfinger.x),
                float(event.tfinger.y),
            ),
        )
    elif t == sdl2.SDL_MOUSEWHEEL:
        wid = event.wheel.windowID
        # SDL 2.0.18+ exposes preciseX/Y (float, already in "lines" with sub-line
        # precision — suitable for smooth trackpad scroll).  Older SDL has only
        # the integer x/y fields.  We pass an is_precise flag so the dispatch
        # side knows whether to multiply by _SCROLL_LINE_PX.
        try:
            dx = float(event.wheel.preciseX)
            dy = float(event.wheel.preciseY)
            is_precise = True
        except AttributeError:
            dx = float(event.wheel.x)
            dy = float(event.wheel.y)
            is_precise = False
        if event.wheel.direction == sdl2.SDL_MOUSEWHEEL_FLIPPED:
            dx, dy = -dx, -dy
        _send(wid, ("mousewheel", dx, dy, is_precise))
    elif t == sdl2.SDL_KEYDOWN:
        wid = event.key.windowID
        _send(wid, ("keydown", event.key.keysym.sym, int(event.key.keysym.mod)))


def _send(wid: int, msg: tuple) -> None:
    with _wmap_lock:
        rt = _window_map.get(wid)
    if rt is not None:
        rt._event_queue.put(msg)


# ---------------------------------------------------------------------------
# SDLRuntime
# ---------------------------------------------------------------------------


class SDLRuntime(BaseRuntime):
    _sdl_ref_count = 0
    _sdl_lock = threading.Lock()

    def __init__(self, root_view: _ViewInternals, width: int, height: int, render_fn):
        super().__init__(root_view, width, height, render_fn)

        # os.environ.setdefault("SDL_VIDEODRIVER", "wayland")
        # os.environ.setdefault("PYSDL2_DLL_PATH", "/usr/lib")

        import sdl2  # type: ignore[import-untyped]

        self._sdl2 = sdl2
        self.running = False

        self._current_w = width
        self._current_h = height

        self._event_queue: queue.SimpleQueue = queue.SimpleQueue()
        self._cursor_pos: tuple[float, float] = (0.0, 0.0)

        with SDLRuntime._sdl_lock:
            if SDLRuntime._sdl_ref_count == 0:
                if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO) != 0:
                    raise RuntimeError(sdl2.SDL_GetError().decode())
            SDLRuntime._sdl_ref_count += 1

        self.window = sdl2.SDL_CreateWindow(
            root_view._name.encode(),
            sdl2.SDL_WINDOWPOS_CENTERED,
            sdl2.SDL_WINDOWPOS_CENTERED,
            width,
            height,
            sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_RESIZABLE,
        )
        self.window_id = sdl2.SDL_GetWindowID(self.window)
        self.renderer = sdl2.SDL_CreateRenderer(
            self.window,
            -1,
            sdl2.SDL_RENDERER_ACCELERATED,
        )
        self.texture = sdl2.SDL_CreateTexture(
            self.renderer,
            sdl2.SDL_PIXELFORMAT_ABGR8888,
            sdl2.SDL_TEXTUREACCESS_STREAMING,
            width,
            height,
        )
        sdl2.SDL_SetTextureBlendMode(self.texture, sdl2.SDL_BLENDMODE_BLEND)
        # Pre-allocate for 4K to avoid reallocation on resize
        _max_pixels = 3840 * 2160
        self.pixel_data = (ctypes.c_ubyte * (_max_pixels * 4))()

        _register_runtime(self)

    @property
    def current_size(self) -> tuple[int, int]:
        return (self._current_w, self._current_h)

    @classmethod
    def get_screen_size(cls):
        import sdl2  # type: ignore[import-untyped]

        sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
        rect = sdl2.rect.SDL_Rect()
        sdl2.SDL_GetDisplayBounds(0, ctypes.byref(rect))
        return (rect.w, rect.h)

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
            match msg[0]:
                case "quit" | "window_close":
                    self.running = False
                case "keydown":
                    sym, mod = msg[1], msg[2]
                    from pytoui._hid import _build_sdl_map, _sdl_mods_to_set

                    key_str = _build_sdl_map(sdl2).get(sym, "")
                    handled = False
                    if key_str:
                        mods = _sdl_mods_to_set(sdl2, mod)
                        handled = self._key_down(key_str, mods)
                    if sym == sdl2.SDLK_ESCAPE and not handled:
                        self.running = False
                case "window_resize":
                    self._current_w, self._current_h = msg[1], msg[2]
                case "windowevent":
                    if msg[1] == sdl2.SDL_WINDOWEVENT_LEAVE:
                        for bid in (MOUSE_LEFT_ID, MOUSE_RIGHT_ID, MOUSE_MIDDLE_ID):
                            self._mouse_cancel(bid)
                case "mousedown":
                    match msg[1]:
                        case sdl2.SDL_BUTTON_LEFT:
                            self._mouse_down(msg[2], msg[3], MOUSE_LEFT_ID)
                        case sdl2.SDL_BUTTON_RIGHT:
                            self._mouse_down(msg[2], msg[3], MOUSE_RIGHT_ID)
                        case sdl2.SDL_BUTTON_MIDDLE:
                            self._mouse_down(msg[2], msg[3], MOUSE_MIDDLE_ID)
                case "mouseup":
                    match msg[1]:
                        case sdl2.SDL_BUTTON_LEFT:
                            self._mouse_up(msg[2], msg[3], MOUSE_LEFT_ID)
                        case sdl2.SDL_BUTTON_RIGHT:
                            self._mouse_up(msg[2], msg[3], MOUSE_RIGHT_ID)
                        case sdl2.SDL_BUTTON_MIDDLE:
                            self._mouse_up(msg[2], msg[3], MOUSE_MIDDLE_ID)
                case "mousemove":
                    self._cursor_pos = (float(msg[2]), float(msg[3]))
                    any_drag = False
                    if msg[1] & sdl2.SDL_BUTTON_LMASK:
                        self._mouse_dragged(msg[2], msg[3], MOUSE_LEFT_ID)
                        any_drag = True
                    if msg[1] & sdl2.SDL_BUTTON_RMASK:
                        self._mouse_dragged(msg[2], msg[3], MOUSE_RIGHT_ID)
                        any_drag = True
                    if msg[1] & sdl2.SDL_BUTTON_MMASK:
                        self._mouse_dragged(msg[2], msg[3], MOUSE_MIDDLE_ID)
                        any_drag = True
                    if not any_drag:
                        self._mouse_moved(msg[2], msg[3])
                case "mousewheel":
                    dx, dy, is_precise = msg[1], msg[2], msg[3]
                    if not is_precise:
                        dx *= _SCROLL_LINE_PX
                        dy *= _SCROLL_LINE_PX
                    cx, cy = self._cursor_pos
                    self._scroll_event(cx, cy, dx, dy)
                case "fingerdown":
                    fid, nx, ny = msg[1], msg[2], msg[3]
                    self._touch_down(nx * self._current_w, ny * self._current_h, fid)
                case "fingerup":
                    fid, nx, ny = msg[1], msg[2], msg[3]
                    self._touch_up(nx * self._current_w, ny * self._current_h, fid)
                case "fingermotion":
                    fid, nx, ny = msg[1], msg[2], msg[3]
                    self._touch_move(nx * self._current_w, ny * self._current_h, fid)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        self.running = True
        sdl2 = self._sdl2
        _fps_frame_count = 0
        _fps_last_t = time.time()

        fb = FrameBuffer(self.pixel_data, self.width, self.height)
        fb.antialias = _UI_ANTIALIAS
        try:
            while self.running and self.root.pytoui_presented:
                now = time.time()

                if _UI_RT_FPS:
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

                w, h = self._current_w, self._current_h
                if fb._width != w or fb._height != h:
                    FrameBuffer._lib.DestroyFrameBuffer(fb._handle)
                    fb._handle = 0
                    fb = FrameBuffer(self.pixel_data, w, h)
                    fb.antialias = _UI_ANTIALIAS
                    sdl2.SDL_DestroyTexture(self.texture)
                    self.texture = sdl2.SDL_CreateTexture(
                        self.renderer,
                        sdl2.SDL_PIXELFORMAT_ABGR8888,
                        sdl2.SDL_TEXTUREACCESS_STREAMING,
                        w,
                        h,
                    )
                    sdl2.SDL_SetTextureBlendMode(self.texture, sdl2.SDL_BLENDMODE_BLEND)
                    self.width, self.height = w, h
                    rf = self.root.frame
                    self.root.frame = Rect(rf.x, rf.y, float(w), float(h))

                needs_redraw = _any_dirty(self.root)

                if needs_redraw:
                    fb.draw_checkerboard(_CHECKER_SIZE)
                    self.render_fn(fb)

                    pixels_ptr = ctypes.c_void_p()
                    pitch = ctypes.c_int()
                    sdl2.SDL_LockTexture(
                        self.texture,
                        None,
                        ctypes.byref(pixels_ptr),
                        ctypes.byref(pitch),
                    )
                    ctypes.memmove(pixels_ptr, self.pixel_data, w * h * 4)
                    sdl2.SDL_UnlockTexture(self.texture)

                    sdl2.SDL_RenderClear(self.renderer)
                    sdl2.SDL_RenderCopy(self.renderer, self.texture, None, None)
                    sdl2.SDL_RenderPresent(self.renderer)

                    sdl2.SDL_Delay(_UI_RT_SDL_DELAY)

                else:
                    sdl2.SDL_Delay(_UI_RT_SDL_MAX_DELAY)
        finally:
            if fb._handle > 0:
                FrameBuffer._lib.DestroyFrameBuffer(fb._handle)
                fb._handle = 0

        self._cleanup()
        self.root.close()

    def _cleanup(self):
        self._unregister()
        _unregister_sdl_runtime(self)
        sdl2 = self._sdl2
        sdl2.SDL_DestroyTexture(self.texture)
        sdl2.SDL_DestroyRenderer(self.renderer)
        sdl2.SDL_DestroyWindow(self.window)
        with SDLRuntime._sdl_lock:
            SDLRuntime._sdl_ref_count -= 1
            if SDLRuntime._sdl_ref_count == 0:
                sdl2.SDL_Quit()
