"""Pythonista-compatible drawing API.

These functions are meant to be called inside a View's draw() method.
A backend (e.g. osdbuf FrameBuffer) should set the active context
before invoking draw().

Usage:
    import ui

    class MyView(ui.View):
        def draw(self):
            ui.set_color("red")
            path = ui.Path.oval(10, 10, 100, 80)
            path.fill()

            ui.set_color((0, 0, 0, 1))
            path.line_width = 2
            path.stroke()

View tree renderer — walks the hierarchy and paints into an osdbuf FrameBuffer.

Usage:
    from pytoui.ui._render import render_view_tree
    render_view_tree(root_view, fb)

NOTE: If needed we should delegate some operations to rust (osdbuf/src/lib.rs)
"""

from __future__ import annotations

import math
import re
import time
from collections.abc import Callable, Sequence
from functools import lru_cache
from re import fullmatch
from threading import local
from typing import TYPE_CHECKING, cast

from pytoui._platform import pytoui_desktop_only
from pytoui.ui._constants import (
    ALIGN_LEFT,
    ALIGN_NATURAL,
    BLEND_NORMAL,
    CONTENT_BOTTOM,
    CONTENT_BOTTOM_LEFT,
    CONTENT_BOTTOM_RIGHT,
    CONTENT_CENTER,
    CONTENT_LEFT,
    CONTENT_RIGHT,
    CONTENT_SCALE_ASPECT_FILL,
    CONTENT_SCALE_ASPECT_FIT,
    CONTENT_SCALE_TO_FILL,
    CONTENT_TOP,
    CONTENT_TOP_LEFT,
    CONTENT_TOP_RIGHT,
    LB_TRUNCATE_TAIL,
    LB_WORD_WRAP,
    LINE_CAP_BUTT,
    LINE_JOIN_MITER,
)
from pytoui.ui._internals import _final_
from pytoui.ui._types import (
    Point,
    Rect,
    Size,
)

if TYPE_CHECKING:
    from pytoui._osdbuf import FrameBuffer
    from pytoui.ui._types import (
        _RGBA,
        _Alignment,
        _BlendMode,
        _ColorLike,
        _ContentMode,
        _LineBrakeMode,
        _LineCapStyle,
        _LineJoinMode,
        _PointLike,
        _RectLike,
        _UiStyle,
    )


__all__ = (
    "GState",
    "ImageContext",
    "Path",
    "Transform",
    "_content_mode_transform",
    "_record",
    "_set_origin",
    "_tick",
    "_tick_delays",
    "animate",
    "cancel_delays",
    "concat_ctm",
    "convert_point",
    "convert_rect",
    "delay",
    "draw_string",
    "fill_rect",
    "get_screen_size",
    "get_ui_style",
    "get_window_size",
    "in_background",
    "measure_string",
    "parse_color",
    "set_blend_mode",
    "set_color",
    "set_shadow",
)


# -- Drawing context (thread-local) ------------------------------------------


class ImageContext:
    """Context manager for offscreen drawing into an Image.

    Usage::

        with ui.ImageContext(100, 100) as ctx:
            ui.set_color("red")
            ui.Path.oval(0, 0, 100, 100).fill()
            img = ctx.get_image()
    """

    def __init__(self, width: float, height: float, scale: float = 1.0):
        self.width = width
        self.height = height
        self.scale = scale
        self._fb: FrameBuffer | None = None
        self._buf = None
        self._prev_backend = None
        self._prev_origin = None

    def __enter__(self):
        import ctypes

        ctx = _get_draw_ctx()
        self._prev_backend = ctx.backend

        pw = int(self.width * self.scale)
        ph = int(self.height * self.scale)

        try:
            from pytoui._osdbuf import FrameBuffer

            self._buf = (ctypes.c_ubyte * (pw * ph * 4))()
            self._fb = FrameBuffer(self._buf, pw, ph)
            ctx.backend = self._fb
        except (ImportError, RuntimeError):
            pass

        self._prev_origin = ctx.origin
        ctx.origin = (0.0, 0.0)
        ctx._image_context = self
        _sync_ctm_to_rust(ctx)
        return self

    def __exit__(self, type, value, traceback):
        ctx = _get_draw_ctx()
        ctx.backend = self._prev_backend
        ctx.origin = self._prev_origin
        ctx._image_context = None
        if self._fb is not None:
            try:
                self._fb.destroy()
            except Exception:
                pass
            self._fb = None

    def get_image(self):
        """Create an Image from the current drawing."""
        from pytoui.ui._image import _Image

        if self._buf is None:
            return _Image._make()
        pw = int(self.width * self.scale)
        ph = int(self.height * self.scale)
        # FrameBuffer stores premultiplied RGBA (tiny-skia requirement).
        # Image._data must be straight (non-premultiplied) RGBA, as expected by blit().
        raw = bytearray(self._buf[: pw * ph * 4])
        for i in range(0, len(raw), 4):
            a = raw[i + 3]
            if a == 0:
                raw[i] = raw[i + 1] = raw[i + 2] = 0
            elif a < 255:
                raw[i] = min(255, raw[i] * 255 // a)
                raw[i + 1] = min(255, raw[i + 1] * 255 // a)
                raw[i + 2] = min(255, raw[i + 2] * 255 // a)
        return _Image._make(
            width=self.width,
            height=self.height,
            scale=self.scale,
            data=bytes(raw),
        )


@_final_
class Transform:
    """Thin wrapper around a Rust-side Transform handle.

    Python fields (a, b, c, d, tx, ty) are kept in sync as a local cache
    so that _sync_ctm_to_rust and repr work without a Rust round-trip.
    The Rust handle is created lazily on first use.
    """

    __slots__ = ("_handle", "a", "b", "c", "d", "tx", "ty")

    def __init__(self, a=1.0, b=0.0, c=0.0, d=1.0, tx=0.0, ty=0.0):
        self.a = float(a)
        self.b = float(b)
        self.c = float(c)
        self.d = float(d)
        self.tx = float(tx)
        self.ty = float(ty)
        self._handle: int = 0  # lazily created

    def __del__(self):
        backend = _get_draw_ctx().backend
        if not backend:
            return

        h = getattr(self, "_handle", 0)
        if h > 0:
            try:
                type(backend).destroy_transform(h)
            except Exception:
                pass

    def _ensure_handle(self) -> int:
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        if self._handle <= 0:
            self._handle = type(backend).create_transform(
                self.a,
                self.b,
                self.c,
                self.d,
                self.tx,
                self.ty,
            )
        return self._handle

    @classmethod
    def _from_handle(cls, handle: int) -> Transform:
        """Wrap an existing Rust handle; reads values back via TransformGet."""
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        a, b, c, d, tx, ty, *_ = type(backend).transform_get(handle)
        obj = cls(a, b, c, d, tx, ty)
        obj._handle = handle
        return obj

    @classmethod
    def rotation(cls, rad: float) -> Transform:
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        h = type(backend).transform_rotation(rad)
        if h > 0:
            return cls._from_handle(h)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        return cls(cos_a, sin_a, -sin_a, cos_a, 0.0, 0.0)

    @classmethod
    def scale(cls, sx: float, sy: float) -> Transform:
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        h = type(backend).transform_scale(sx, sy)
        if h > 0:
            return cls._from_handle(h)
        return cls(sx, 0.0, 0.0, sy, 0.0, 0.0)

    @classmethod
    def translation(cls, tx: float, ty: float) -> Transform:
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        h = type(backend).transform_translation(tx, ty)
        if h > 0:
            return cls._from_handle(h)
        return cls(1.0, 0.0, 0.0, 1.0, tx, ty)

    def concat(self, other: Transform) -> Transform:
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        ha = self._ensure_handle()
        hb = other._ensure_handle()

        h = type(backend).transform_concat(ha, hb)
        if h > 0:
            return Transform._from_handle(h)

        # Python fallback
        return Transform(
            self.a * other.a + self.c * other.b,
            self.b * other.a + self.d * other.b,
            self.a * other.c + self.c * other.d,
            self.b * other.c + self.d * other.d,
            self.a * other.tx + self.c * other.ty + self.tx,
            self.b * other.tx + self.d * other.ty + self.ty,
        )

    def invert(self) -> Transform:
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        h = self._ensure_handle()
        ih = type(backend).transform_invert(h)
        if ih > 0:
            return Transform._from_handle(ih)
        # Python fallback
        det = self.a * self.d - self.b * self.c
        if abs(det) < 1e-10:
            raise ValueError("Matrix has no inverse (determinant = 0)")
        inv_det = 1.0 / det
        return Transform(
            self.d * inv_det,
            -self.b * inv_det,
            -self.c * inv_det,
            self.a * inv_det,
            (self.c * self.ty - self.d * self.tx) * inv_det,
            (self.b * self.tx - self.a * self.ty) * inv_det,
        )

    def __repr__(self):
        return (
            f"Transform(a={self.a:.2f}, b={self.b:.2f}, c={self.c:.2f}, "
            f"d={self.d:.2f}, tx={self.tx:.2f}, ty={self.ty:.2f})"
        )


_IDENTITY_TRANSFORM = Transform()


@_final_
class _DrawingContext:
    """Description of the context structure for static analysis."""

    color: tuple[float, float, float, float]
    blend_mode: _BlendMode
    backend: FrameBuffer | None
    clip: Rect | None
    origin: tuple[float, float]
    shadow: tuple[_RGBA | None, float, float, float] | None
    ctm: Transform
    alpha: float
    _stack: list[dict]


_draw_ctx = cast("_DrawingContext", local())


def _get_draw_ctx() -> _DrawingContext:
    if not hasattr(_draw_ctx, "color"):
        _draw_ctx.color = (0.0, 0.0, 0.0, 1.0)
        _draw_ctx.blend_mode = BLEND_NORMAL
        _draw_ctx.backend = None
        _draw_ctx.origin = (0.0, 0.0)
        _draw_ctx.shadow = None
        _draw_ctx.ctm = _IDENTITY_TRANSFORM
        _draw_ctx.alpha = 1.0
        _draw_ctx._stack = []
    return _draw_ctx


def _save_gstate():
    ctx = _get_draw_ctx()
    m = ctx.ctm
    # Create a copy of the transformation matrix
    ctm_copy = Transform(m.a, m.b, m.c, m.d, m.tx, m.ty)

    ctx._stack.append(
        {
            "color": ctx.color,
            "blend_mode": ctx.blend_mode,
            "origin": ctx.origin,
            "shadow": ctx.shadow,
            "ctm": ctm_copy,
            "alpha": ctx.alpha,
        },
    )
    if ctx.backend is not None:
        ctx.backend.gstate_push()


def _restore_gstate():
    ctx = _get_draw_ctx()
    if not ctx._stack:
        return

    state = ctx._stack.pop()
    ctx.color = state["color"]
    ctx.blend_mode = state["blend_mode"]
    ctx.origin = state["origin"]
    ctx.shadow = state["shadow"]
    ctx.ctm = state["ctm"]
    ctx.alpha = state["alpha"]
    _sync_ctm_to_rust(ctx)
    if ctx.backend is not None:
        ctx.backend.gstate_pop()


class GState:
    """Context manager that saves/restores the current drawing state.

    Saves and restores Python-side state (color, blend_mode, alpha, origin,
    shadow, ctm). On restore, CTM is synced to Rust via _sync_ctm_to_rust.

    Usage::

        with ui.GState():
            ui.set_color("red")
            ui.concat_ctm(ui.Transform.rotation(0.5))
            # ... draw ...
        # state is restored here
    """

    def __enter__(self):
        _save_gstate()

    def __exit__(self, exc_type, exc_val, exc_tb):
        _restore_gstate()


def _sync_ctm_to_rust(ctx) -> None:
    """Push the current Python CTM
    (composed with origin translation) to the Rust backend.

    Full transform sent to Rust = T(origin) * ctx.ctm, which means:
      - All Path coordinates are passed as view-local (without origin offset)
      - Rust applies the full transform including origin translation
      - This allows correct rotation/scale around the view's own origin (0,0)
    """
    fb = ctx.backend
    if fb is None:
        return
    ox, oy = ctx.origin
    m = ctx.ctm
    scale = getattr(fb, "scale_factor", 1.0)
    # T(ox, oy).concat(m), then scale all components to physical pixels
    fb.set_ctm(
        m.a * scale,
        m.b * scale,
        m.c * scale,
        m.d * scale,
        (m.tx + ox) * scale,
        (m.ty + oy) * scale,
    )


@pytoui_desktop_only
def _set_origin(x: float, y: float):
    """Set the coordinate origin for subsequent draw calls.
    Called by the render loop to translate to the view's absolute position.
    Internal only — not part of the Pythonista public API.
    """
    ctx = _get_draw_ctx()
    ctx.origin = (x, y)
    _sync_ctm_to_rust(ctx)


def set_alpha(alpha: float):
    """Set a global alpha multiplier applied to all subsequent drawing operations.
    Internal only — not part of the Pythonista public API.
    Used by View._render() to apply view.alpha to the entire view's drawing.
    """
    ctx = _get_draw_ctx()
    ctx.alpha = max(0.0, min(1.0, float(alpha)))


# -- Public Pythonista-compatible API -----------------------------------------

_CSS_COLORS_STANDARD: dict[str, _RGBA] = {
    "aliceblue": (0.94, 0.97, 1.0, 1.0),
    "antiquewhite": (0.98, 0.92, 0.84, 1.0),
    "aqua": (0.0, 1.0, 1.0, 1.0),
    "aquamarine": (0.5, 1.0, 0.83, 1.0),
    "azure": (0.94, 1.0, 1.0, 1.0),
    "beige": (0.96, 0.96, 0.86, 1.0),
    "bisque": (1.0, 0.89, 0.77, 1.0),
    "black": (0.0, 0.0, 0.0, 1.0),
    "blanchedalmond": (1.0, 0.92, 0.8, 1.0),
    "blue": (0.0, 0.0, 1.0, 1.0),
    "blueviolet": (0.54, 0.17, 0.89, 1.0),
    "brown": (0.65, 0.16, 0.16, 1.0),
    "burlywood": (0.87, 0.72, 0.53, 1.0),
    "cadetblue": (0.37, 0.62, 0.63, 1.0),
    "chartreuse": (0.5, 1.0, 0.0, 1.0),
    "chocolate": (0.82, 0.41, 0.12, 1.0),
    "clear": (0.0, 0.0, 0.0, 0.0),
    "coral": (1.0, 0.5, 0.31, 1.0),
    "cornflowerblue": (0.39, 0.58, 0.93, 1.0),
    "cornsilk": (1.0, 0.97, 0.86, 1.0),
    "crimson": (0.86, 0.08, 0.24, 1.0),
    "cyan": (0.0, 1.0, 1.0, 1.0),
    "darkblue": (0.0, 0.0, 0.55, 1.0),
    "darkcyan": (0.0, 0.55, 0.55, 1.0),
    "darkgoldenrod": (0.72, 0.53, 0.04, 1.0),
    "darkgray": (0.66, 0.66, 0.66, 1.0),
    "darkgreen": (0.0, 0.39, 0.0, 1.0),
    "darkgrey": (0.66, 0.66, 0.66, 1.0),
    "darkkhaki": (0.74, 0.72, 0.42, 1.0),
    "darkmagenta": (0.55, 0.0, 0.55, 1.0),
    "darkolivegreen": (0.33, 0.42, 0.18, 1.0),
    "darkorange": (1.0, 0.55, 0.0, 1.0),
    "darkorchid": (0.6, 0.2, 0.8, 1.0),
    "darkred": (0.55, 0.0, 0.0, 1.0),
    "darksalmon": (0.91, 0.59, 0.48, 1.0),
    "darkseagreen": (0.56, 0.74, 0.56, 1.0),
    "darkslateblue": (0.28, 0.24, 0.55, 1.0),
    "darkslategray": (0.18, 0.31, 0.31, 1.0),
    "darkslategrey": (0.18, 0.31, 0.31, 1.0),
    "darkturquoise": (0.0, 0.81, 0.82, 1.0),
    "darkviolet": (0.58, 0.0, 0.83, 1.0),
    "deeppink": (1.0, 0.08, 0.58, 1.0),
    "deepskyblue": (0.0, 0.75, 1.0, 1.0),
    "dimgray": (0.41, 0.41, 0.41, 1.0),
    "dimgrey": (0.41, 0.41, 0.41, 1.0),
    "dodgerblue": (0.12, 0.56, 1.0, 1.0),
    "firebrick": (0.7, 0.13, 0.13, 1.0),
    "floralwhite": (1.0, 0.98, 0.94, 1.0),
    "forestgreen": (0.13, 0.55, 0.13, 1.0),
    "fuchsia": (1.0, 0.0, 1.0, 1.0),
    "gainsboro": (0.86, 0.86, 0.86, 1.0),
    "ghostwhite": (0.97, 0.97, 1.0, 1.0),
    "gold": (1.0, 0.84, 0.0, 1.0),
    "goldenrod": (0.85, 0.65, 0.13, 1.0),
    "gray": (0.5, 0.5, 0.5, 1.0),
    "green": (0.0, 0.5, 0.0, 1.0),
    "greenyellow": (0.68, 1.0, 0.18, 1.0),
    "grey": (0.5, 0.5, 0.5, 1.0),
    "honeydew": (0.94, 1.0, 0.94, 1.0),
    "hotpink": (1.0, 0.41, 0.71, 1.0),
    "indianred": (0.8, 0.36, 0.36, 1.0),
    "indigo": (0.29, 0.0, 0.51, 1.0),
    "ivory": (1.0, 1.0, 0.94, 1.0),
    "khaki": (0.94, 0.9, 0.55, 1.0),
    "lavender": (0.9, 0.9, 0.98, 1.0),
    "lavenderblush": (1.0, 0.94, 0.96, 1.0),
    "lawngreen": (0.49, 0.99, 0.0, 1.0),
    "lemonchiffon": (1.0, 0.98, 0.8, 1.0),
    "lightblue": (0.68, 0.85, 0.9, 1.0),
    "lightcoral": (0.94, 0.5, 0.5, 1.0),
    "lightcyan": (0.88, 1.0, 1.0, 1.0),
    "lightgoldenrodyellow": (0.98, 0.98, 0.82, 1.0),
    "lightgray": (0.83, 0.83, 0.83, 1.0),
    "lightgreen": (0.56, 0.93, 0.56, 1.0),
    "lightgrey": (0.83, 0.83, 0.83, 1.0),
    "lightpink": (1.0, 0.71, 0.76, 1.0),
    "lightsalmon": (1.0, 0.63, 0.48, 1.0),
    "lightseagreen": (0.13, 0.7, 0.67, 1.0),
    "lightskyblue": (0.53, 0.81, 0.98, 1.0),
    "lightslategray": (0.47, 0.53, 0.6, 1.0),
    "lightslategrey": (0.47, 0.53, 0.6, 1.0),
    "lightsteelblue": (0.69, 0.77, 0.87, 1.0),
    "lightyellow": (1.0, 1.0, 0.88, 1.0),
    "lime": (0.0, 1.0, 0.0, 1.0),
    "limegreen": (0.2, 0.8, 0.2, 1.0),
    "linen": (0.98, 0.94, 0.9, 1.0),
    "magenta": (1.0, 0.0, 1.0, 1.0),
    "maroon": (0.5, 0.0, 0.0, 1.0),
    "mediumaquamarine": (0.4, 0.8, 0.67, 1.0),
    "mediumblue": (0.0, 0.0, 0.8, 1.0),
    "mediumorchid": (0.73, 0.33, 0.83, 1.0),
    "mediumpurple": (0.58, 0.44, 0.86, 1.0),
    "mediumseagreen": (0.24, 0.7, 0.44, 1.0),
    "mediumslateblue": (0.48, 0.41, 0.93, 1.0),
    "mediumspringgreen": (0.0, 0.98, 0.6, 1.0),
    "mediumturquoise": (0.28, 0.82, 0.8, 1.0),
    "mediumvioletred": (0.78, 0.08, 0.52, 1.0),
    "midnightblue": (0.1, 0.1, 0.44, 1.0),
    "mintcream": (0.96, 1.0, 0.98, 1.0),
    "mistyrose": (1.0, 0.89, 0.88, 1.0),
    "moccasin": (1.0, 0.89, 0.71, 1.0),
    "navajowhite": (1.0, 0.87, 0.68, 1.0),
    "navy": (0.0, 0.0, 0.5, 1.0),
    "oldlace": (0.99, 0.96, 0.9, 1.0),
    "olive": (0.5, 0.5, 0.0, 1.0),
    "olivedrab": (0.42, 0.56, 0.14, 1.0),
    "orange": (1.0, 0.65, 0.0, 1.0),
    "orangered": (1.0, 0.27, 0.0, 1.0),
    "orchid": (0.85, 0.44, 0.84, 1.0),
    "palegoldenrod": (0.93, 0.91, 0.67, 1.0),
    "palegreen": (0.6, 0.98, 0.6, 1.0),
    "paleturquoise": (0.69, 0.93, 0.93, 1.0),
    "palevioletred": (0.86, 0.44, 0.58, 1.0),
    "papayawhip": (1.0, 0.94, 0.84, 1.0),
    "peachpuff": (1.0, 0.85, 0.73, 1.0),
    "peru": (0.8, 0.52, 0.25, 1.0),
    "pink": (1.0, 0.75, 0.8, 1.0),
    "plum": (0.87, 0.63, 0.87, 1.0),
    "powderblue": (0.69, 0.88, 0.9, 1.0),
    "purple": (0.5, 0.0, 0.5, 1.0),
    "rebeccapurple": (0.4, 0.2, 0.6, 1.0),
    "red": (1.0, 0.0, 0.0, 1.0),
    "rosybrown": (0.74, 0.56, 0.56, 1.0),
    "royalblue": (0.25, 0.41, 0.88, 1.0),
    "saddlebrown": (0.55, 0.27, 0.07, 1.0),
    "salmon": (0.98, 0.5, 0.45, 1.0),
    "sandybrown": (0.96, 0.64, 0.38, 1.0),
    "seagreen": (0.18, 0.55, 0.34, 1.0),
    "seashell": (1.0, 0.96, 0.93, 1.0),
    "sienna": (0.63, 0.32, 0.18, 1.0),
    "silver": (0.75, 0.75, 0.75, 1.0),
    "skyblue": (0.53, 0.81, 0.92, 1.0),
    "slateblue": (0.42, 0.35, 0.8, 1.0),
    "slategray": (0.44, 0.5, 0.56, 1.0),
    "slategrey": (0.44, 0.5, 0.56, 1.0),
    "snow": (1.0, 0.98, 0.98, 1.0),
    "springgreen": (0.0, 1.0, 0.5, 1.0),
    "steelblue": (0.27, 0.51, 0.71, 1.0),
    "tan": (0.82, 0.71, 0.55, 1.0),
    "teal": (0.0, 0.5, 0.5, 1.0),
    "thistle": (0.85, 0.75, 0.85, 1.0),
    "tomato": (1.0, 0.39, 0.28, 1.0),
    "transparent": (0.0, 0.0, 0.0, 0.0),
    "turquoise": (0.25, 0.88, 0.82, 1.0),
    "violet": (0.93, 0.51, 0.93, 1.0),
    "wheat": (0.96, 0.87, 0.7, 1.0),
    "white": (1.0, 1.0, 1.0, 1.0),
    "whitesmoke": (0.96, 0.96, 0.96, 1.0),
    "yellow": (1.0, 1.0, 0.0, 1.0),
    "yellowgreen": (0.6, 0.8, 0.2, 1.0),
}


_CSS_COLORS_UIKIT: dict[str, _RGBA] = {
    "aliceblue": (0.94, 0.97, 1.0, 1.0),
    "antiquewhite": (0.98, 0.92, 0.84, 1.0),
    "aqua": (0.0, 1.0, 1.0, 1.0),
    "aquamarine": (0.5, 1.0, 0.83, 1.0),
    "azure": (0.94, 1.0, 1.0, 1.0),
    "beige": (0.96, 0.96, 0.86, 1.0),
    "bisque": (1.0, 0.89, 0.77, 1.0),
    "black": (0.0, 0.0, 0.0, 1.0),
    "blanchedalmond": (1.0, 0.92, 0.8, 1.0),
    "blue": (0.0, 0.0, 1.0, 1.0),
    "blueviolet": (0.54, 0.17, 0.89, 1.0),
    "brown": (0.65, 0.16, 0.16, 1.0),
    "burlywood": (0.87, 0.72, 0.53, 1.0),
    "cadetblue": (0.37, 0.62, 0.63, 1.0),
    "chartreuse": (0.5, 1.0, 0.0, 1.0),
    "chocolate": (0.82, 0.41, 0.12, 1.0),
    "clear": (0.0, 0.0, 0.0, 0.0),
    "coral": (1.0, 0.5, 0.31, 1.0),
    "cornflowerblue": (0.39, 0.58, 0.93, 1.0),
    "cornsilk": (1.0, 0.97, 0.86, 1.0),
    "crimson": (0.86, 0.08, 0.24, 1.0),
    "cyan": (0.0, 1.0, 1.0, 1.0),
    "darkblue": (0.0, 0.0, 0.55, 1.0),
    "darkcyan": (0.0, 0.55, 0.55, 1.0),
    "darkgoldenrod": (0.72, 0.53, 0.04, 1.0),
    "darkgray": (0.66, 0.66, 0.66, 1.0),
    "darkgreen": (0.0, 0.39, 0.0, 1.0),
    "darkgrey": (0.66, 0.66, 0.66, 1.0),
    "darkkhaki": (0.74, 0.72, 0.42, 1.0),
    "darkmagenta": (0.55, 0.0, 0.55, 1.0),
    "darkolivegreen": (0.33, 0.42, 0.18, 1.0),
    "darkorange": (1.0, 0.55, 0.0, 1.0),
    "darkorchid": (0.6, 0.2, 0.8, 1.0),
    "darkred": (0.55, 0.0, 0.0, 1.0),
    "darksalmon": (0.91, 0.59, 0.48, 1.0),
    "darkseagreen": (0.56, 0.74, 0.56, 1.0),
    "darkslateblue": (0.28, 0.24, 0.55, 1.0),
    "darkslategray": (0.18, 0.31, 0.31, 1.0),
    "darkslategrey": (0.18, 0.31, 0.31, 1.0),
    "darkturquoise": (0.0, 0.81, 0.82, 1.0),
    "darkviolet": (0.58, 0.0, 0.83, 1.0),
    "deeppink": (1.0, 0.08, 0.58, 1.0),
    "deepskyblue": (0.0, 0.75, 1.0, 1.0),
    "dimgray": (0.41, 0.41, 0.41, 1.0),
    "dimgrey": (0.41, 0.41, 0.41, 1.0),
    "dodgerblue": (0.12, 0.56, 1.0, 1.0),
    "firebrick": (0.7, 0.13, 0.13, 1.0),
    "floralwhite": (1.0, 0.98, 0.94, 1.0),
    "forestgreen": (0.13, 0.55, 0.13, 1.0),
    "fuchsia": (1.0, 0.0, 1.0, 1.0),
    "gainsboro": (0.86, 0.86, 0.86, 1.0),
    "ghostwhite": (0.97, 0.97, 1.0, 1.0),
    "gold": (1.0, 0.84, 0.0, 1.0),
    "goldenrod": (0.85, 0.65, 0.13, 1.0),
    "gray": (0.5, 0.5, 0.5, 1.0),
    "green": (0.0, 0.5, 0.0, 1.0),
    "greenyellow": (0.68, 1.0, 0.18, 1.0),
    "grey": (0.5, 0.5, 0.5, 1.0),
    "honeydew": (0.94, 1.0, 0.94, 1.0),
    "hotpink": (1.0, 0.41, 0.71, 1.0),
    "indianred": (0.8, 0.36, 0.36, 1.0),
    "indigo": (0.29, 0.0, 0.51, 1.0),
    "ivory": (1.0, 1.0, 0.94, 1.0),
    "khaki": (0.94, 0.9, 0.55, 1.0),
    "lavender": (0.9, 0.9, 0.98, 1.0),
    "lavenderblush": (1.0, 0.94, 0.96, 1.0),
    "lawngreen": (0.49, 0.99, 0.0, 1.0),
    "lemonchiffon": (1.0, 0.98, 0.8, 1.0),
    "lightblue": (0.68, 0.85, 0.9, 1.0),
    "lightcoral": (0.94, 0.5, 0.5, 1.0),
    "lightcyan": (0.88, 1.0, 1.0, 1.0),
    "lightgoldenrodyellow": (0.98, 0.98, 0.82, 1.0),
    "lightgray": (0.83, 0.83, 0.83, 1.0),
    "lightgreen": (0.56, 0.93, 0.56, 1.0),
    "lightgrey": (0.83, 0.83, 0.83, 1.0),
    "lightpink": (1.0, 0.71, 0.76, 1.0),
    "lightsalmon": (1.0, 0.63, 0.48, 1.0),
    "lightseagreen": (0.13, 0.7, 0.67, 1.0),
    "lightskyblue": (0.53, 0.81, 0.98, 1.0),
    "lightslategray": (0.47, 0.53, 0.6, 1.0),
    "lightslategrey": (0.47, 0.53, 0.6, 1.0),
    "lightsteelblue": (0.69, 0.77, 0.87, 1.0),
    "lightyellow": (1.0, 1.0, 0.88, 1.0),
    "lime": (0.0, 1.0, 0.0, 1.0),
    "limegreen": (0.2, 0.8, 0.2, 1.0),
    "linen": (0.98, 0.94, 0.9, 1.0),
    "magenta": (1.0, 0.0, 1.0, 1.0),
    "maroon": (0.5, 0.0, 0.0, 1.0),
    "mediumaquamarine": (0.4, 0.8, 0.67, 1.0),
    "mediumblue": (0.0, 0.0, 0.8, 1.0),
    "mediumorchid": (0.73, 0.33, 0.83, 1.0),
    "mediumpurple": (0.58, 0.44, 0.86, 1.0),
    "mediumseagreen": (0.24, 0.7, 0.44, 1.0),
    "mediumslateblue": (0.48, 0.41, 0.93, 1.0),
    "mediumspringgreen": (0.0, 0.98, 0.6, 1.0),
    "mediumturquoise": (0.28, 0.82, 0.8, 1.0),
    "mediumvioletred": (0.78, 0.08, 0.52, 1.0),
    "midnightblue": (0.1, 0.1, 0.44, 1.0),
    "mintcream": (0.96, 1.0, 0.98, 1.0),
    "mistyrose": (1.0, 0.89, 0.88, 1.0),
    "moccasin": (1.0, 0.89, 0.71, 1.0),
    "navajowhite": (1.0, 0.87, 0.68, 1.0),
    "navy": (0.0, 0.0, 0.5, 1.0),
    "oldlace": (0.99, 0.96, 0.9, 1.0),
    "olive": (0.5, 0.5, 0.0, 1.0),
    "olivedrab": (0.42, 0.56, 0.14, 1.0),
    "orange": (1.0, 0.65, 0.0, 1.0),
    "orangered": (1.0, 0.27, 0.0, 1.0),
    "orchid": (0.85, 0.44, 0.84, 1.0),
    "palegoldenrod": (0.93, 0.91, 0.67, 1.0),
    "palegreen": (0.6, 0.98, 0.6, 1.0),
    "paleturquoise": (0.69, 0.93, 0.93, 1.0),
    "palevioletred": (0.86, 0.44, 0.58, 1.0),
    "papayawhip": (1.0, 0.94, 0.84, 1.0),
    "peachpuff": (1.0, 0.85, 0.73, 1.0),
    "peru": (0.8, 0.52, 0.25, 1.0),
    "pink": (1.0, 0.75, 0.8, 1.0),
    "plum": (0.87, 0.63, 0.87, 1.0),
    "powderblue": (0.69, 0.88, 0.9, 1.0),
    "purple": (0.5, 0.0, 0.5, 1.0),
    "rebeccapurple": (0.4, 0.2, 0.6, 1.0),
    "red": (1.0, 0.0, 0.0, 1.0),
    "rosybrown": (0.74, 0.56, 0.56, 1.0),
    "royalblue": (0.25, 0.41, 0.88, 1.0),
    "saddlebrown": (0.55, 0.27, 0.07, 1.0),
    "salmon": (0.98, 0.5, 0.45, 1.0),
    "sandybrown": (0.96, 0.64, 0.38, 1.0),
    "seagreen": (0.18, 0.55, 0.34, 1.0),
    "seashell": (1.0, 0.96, 0.93, 1.0),
    "sienna": (0.63, 0.32, 0.18, 1.0),
    "silver": (0.75, 0.75, 0.75, 1.0),
    "skyblue": (0.53, 0.81, 0.92, 1.0),
    "slateblue": (0.42, 0.35, 0.8, 1.0),
    "slategray": (0.44, 0.5, 0.56, 1.0),
    "slategrey": (0.44, 0.5, 0.56, 1.0),
    "snow": (1.0, 0.98, 0.98, 1.0),
    "springgreen": (0.0, 1.0, 0.5, 1.0),
    "steelblue": (0.27, 0.51, 0.71, 1.0),
    "tan": (0.82, 0.71, 0.55, 1.0),
    "teal": (0.0, 0.5, 0.5, 1.0),
    "thistle": (0.85, 0.75, 0.85, 1.0),
    "tomato": (1.0, 0.39, 0.28, 1.0),
    "transparent": (0.0, 0.0, 0.0, 0.0),
    "turquoise": (0.25, 0.88, 0.82, 1.0),
    "violet": (0.93, 0.51, 0.93, 1.0),
    "wheat": (0.96, 0.87, 0.7, 1.0),
    "white": (1.0, 1.0, 1.0, 1.0),
    "whitesmoke": (0.96, 0.96, 0.96, 1.0),
    "yellow": (1.0, 1.0, 0.0, 1.0),
    "yellowgreen": (0.6, 0.8, 0.2, 1.0),
}


_UIKIT_SYSTEM_COLORS: dict[str, _RGBA] = {
    "systemblue": (0.0, 0.48, 1.0, 1.0),
    "systemgreen": (0.2, 0.78, 0.35, 1.0),
    "systemindigo": (0.35, 0.34, 0.84, 1.0),
    "systemorange": (1.0, 0.58, 0.0, 1.0),
    "systempink": (1.0, 0.18, 0.33, 1.0),
    "systempurple": (0.69, 0.32, 0.87, 1.0),
    "systemred": (1.0, 0.23, 0.19, 1.0),
    "systemteal": (0.19, 0.69, 0.78, 1.0),
    "systemyellow": (1.0, 0.8, 0.0, 1.0),
    "systemmint": (0.0, 0.78, 0.75, 1.0),
    "systemcyan": (0.2, 0.71, 0.9, 1.0),
    "systemgray": (0.56, 0.56, 0.58, 1.0),
    "systemgray2": (0.68, 0.68, 0.7, 1.0),
    "systemgray3": (0.78, 0.78, 0.8, 1.0),
    "systemgray4": (0.82, 0.82, 0.84, 1.0),
    "systemgray5": (0.89, 0.89, 0.91, 1.0),
    "systemgray6": (0.95, 0.95, 0.97, 1.0),
    "label": (0.0, 0.0, 0.0, 1.0),
    "secondarylabel": (0.24, 0.24, 0.26, 0.6),
    "tertiarylabel": (0.24, 0.24, 0.26, 0.3),
    "quaternarylabel": (0.24, 0.24, 0.26, 0.18),
    "systembackground": (1.0, 1.0, 1.0, 1.0),
    "secondarysystembackground": (0.95, 0.95, 0.97, 1.0),
    "tertiarysystembackground": (1.0, 1.0, 1.0, 1.0),
}

_COLORS: dict[str, _RGBA] = {}
_COLORS.update(_CSS_COLORS_STANDARD)
_COLORS.update(_CSS_COLORS_UIKIT)
_COLORS.update(_UIKIT_SYSTEM_COLORS)


@lru_cache(maxsize=256)
def parse_color(c: _ColorLike) -> _RGBA | None:
    r: float | int
    g: float | int
    b: float | int
    a: float | int

    if c is None:
        return None

    if isinstance(c, tuple):
        if len(c) == 4:
            return c
        if len(c) == 3:
            return (c[0], c[1], c[2], 1.0)

    if isinstance(c, (float, int)) and not isinstance(c, bool):
        if isinstance(c, float):
            # Scalar gray: 0.0–1.0
            g = max(0.0, min(1.0, c))
            return (g, g, g, 1.0)
        # int — hex color
        if c > 0xFFFFFF:
            r = (c >> 24) & 0xFF
            g = (c >> 16) & 0xFF
            b = (c >> 8) & 0xFF
            a = c & 0xFF
            return (r / 255, g / 255, b / 255, a / 255)
        r = (c >> 16) & 0xFF
        g = (c >> 8) & 0xFF
        b = c & 0xFF
        return (r / 255, g / 255, b / 255, 1.0)

    if isinstance(c, str):
        # CSS color name lookup
        named = _COLORS.get(re.sub(r"[^a-zA-Z0-9]", "", c).lower())
        if named is not None:
            return named

        hex_val = c.lstrip("#")

        if fullmatch(r"[A-Fa-f0-9]{6}", hex_val):
            r, g, b = [int(hex_val[i : i + 2], 16) / 255 for i in (0, 2, 4)]
            return (r, g, b, 1.0)

        if fullmatch(r"[A-Fa-f0-9]{8}", hex_val):
            r, g, b, a = [int(hex_val[i : i + 2], 16) / 255 for i in (0, 2, 4, 6)]
            return (r, g, b, a)

    return None


def set_color(c: _ColorLike):
    """Set the current fill and stroke color.
    Accepts any Color format (RGBA tuple, RGB tuple, hex string, hex int).
    """
    ctx = _get_draw_ctx()
    ctx.color = parse_color(c) or (0.0, 0.0, 0.0, 1.0)


def set_blend_mode(mode: _BlendMode):
    """Set the current blend mode
    (BlendMode.NORMAL = alpha-over, BlendMode.COPY = direct)."""
    ctx = _get_draw_ctx()
    ctx.blend_mode = mode


def concat_ctm(transform: Transform):
    """Adds a new transformation to the current state of the graphics context.
    Mathematically this is: NewCTM = CurrentCTM * IncomingTransform
    """
    ctx = _get_draw_ctx()

    if not hasattr(ctx, "ctm") or ctx.ctm is None:
        ctx.ctm = Transform()  # Identity matrix (1,0,0,1,0,0)

    ctx.ctm = ctx.ctm.concat(transform)
    _sync_ctm_to_rust(ctx)


def fill_rect(x: float, y: float, w: float, h: float):
    Path.rect(x, y, w, h).fill()


@pytoui_desktop_only
def _content_mode_transform(
    mode: _ContentMode,
    cw: float,
    ch: float,
    fw: float,
    fh: float,
) -> None:
    """Apply a CTM pre-transform so content originally drawn at (cw, ch) appears
    scaled/positioned within (fw, fh) according to *mode* (a CONTENT_* constant).

    Must be called inside an active drawing context (e.g. inside GState()).
    Does nothing when any dimension is non-positive.
    """
    if cw <= 0.0 or ch <= 0.0 or fw <= 0.0 or fh <= 0.0:
        return

    if mode == CONTENT_SCALE_TO_FILL:
        concat_ctm(Transform.scale(fw / cw, fh / ch))

    elif mode == CONTENT_SCALE_ASPECT_FIT:
        s = min(fw / cw, fh / ch)
        concat_ctm(Transform.translation((fw - cw * s) / 2.0, (fh - ch * s) / 2.0))
        concat_ctm(Transform.scale(s, s))

    elif mode == CONTENT_SCALE_ASPECT_FILL:
        s = max(fw / cw, fh / ch)
        concat_ctm(Transform.translation((fw - cw * s) / 2.0, (fh - ch * s) / 2.0))
        concat_ctm(Transform.scale(s, s))

    elif mode == CONTENT_CENTER:
        concat_ctm(Transform.translation((fw - cw) / 2.0, (fh - ch) / 2.0))

    elif mode == CONTENT_TOP:
        concat_ctm(Transform.translation((fw - cw) / 2.0, 0.0))

    elif mode == CONTENT_BOTTOM:
        concat_ctm(Transform.translation((fw - cw) / 2.0, fh - ch))

    elif mode == CONTENT_LEFT:
        concat_ctm(Transform.translation(0.0, (fh - ch) / 2.0))

    elif mode == CONTENT_RIGHT:
        concat_ctm(Transform.translation(fw - cw, (fh - ch) / 2.0))

    elif mode == CONTENT_TOP_LEFT:
        pass  # origin already at top-left, no transform needed

    elif mode == CONTENT_TOP_RIGHT:
        concat_ctm(Transform.translation(fw - cw, 0.0))

    elif mode == CONTENT_BOTTOM_LEFT:
        concat_ctm(Transform.translation(0.0, fh - ch))

    elif mode == CONTENT_BOTTOM_RIGHT:
        concat_ctm(Transform.translation(fw - cw, fh - ch))


def set_shadow(color: _ColorLike, offset_x: float, offset_y: float, blur_radius: float):
    """Configure a drop shadow for following drawing operations."""
    ctx = _get_draw_ctx()
    ctx.shadow = (parse_color(color), offset_x, offset_y, blur_radius)


@lru_cache(maxsize=512)
def _rgba_to_uint32(c: _RGBA) -> int:
    """Convert RGBA float tuple to 0xRRGGBBAA uint32."""
    r = int(c[0] * 255) & 0xFF
    g = int(c[1] * 255) & 0xFF
    b = int(c[2] * 255) & 0xFF
    a = int(c[3] * 255) & 0xFF
    return (r << 24) | (g << 16) | (b << 8) | a


# -- Font name → font_id (dynamic, cached via FrameBuffer._font_registry) -----


def _get_font_id(font_name: str, size: float) -> int:
    from pytoui._fonts import resolve_any_font
    from pytoui._osdbuf import FrameBuffer

    path = resolve_any_font(font_name, int(size))
    if path is None:
        fid = FrameBuffer.get_default_font()
        return fid if fid > 0 else 1
    try:
        return FrameBuffer.load_font_cached(str(path))
    except Exception:
        fid = FrameBuffer.get_default_font()
        return fid if fid > 0 else 1


# -- Text measurement and layout helpers ---------------------------------------


def draw_string(
    s: str,
    rect: _RectLike = (0, 0, 0, 0),
    font: tuple[str, float] = ("<system>", 17.0),
    color: _ColorLike | None = (0.0, 0.0, 0.0, 1.0),
    alignment: _Alignment = ALIGN_NATURAL,
    line_break_mode: _LineBrakeMode = LB_TRUNCATE_TAIL,
):
    ctx = _get_draw_ctx()
    fb = ctx.backend
    if fb is None:
        return

    ox, oy = ctx.origin
    m = ctx.ctm
    if not isinstance(rect, Rect):
        rect = Rect(*rect)

    # Transform coords (logical → physical via scale_factor)
    scale = getattr(fb, "scale_factor", 1.0)
    x = (m.a * rect.x + m.c * rect.y + m.tx + ox) * scale
    y = (m.b * rect.x + m.d * rect.y + m.ty + oy) * scale
    w, h = rect.w * scale, rect.h * scale

    font_name, font_size = font
    fid = _get_font_id(font_name, font_size)

    _color = parse_color(color)
    if _color is None:
        _color = ctx.color
    if ctx.alpha != 1.0:
        _color = (_color[0], _color[1], _color[2], _color[3] * ctx.alpha)
    c = _rgba_to_uint32(_color)

    fb.draw_string_core_graphics(
        s,
        x,
        y,
        w,
        h,
        size=font_size * scale,
        c=c,
        font_id=fid,
        alignment=alignment,
        line_break_mode=line_break_mode,
    )


def measure_string(
    s: str,
    max_width: float = 0,
    font: tuple[str, float] = ("<system>", 12.0),
    alignment: _Alignment = ALIGN_LEFT,
    line_break_mode: _LineBrakeMode = LB_WORD_WRAP,
) -> tuple[float, float]:
    backend = _get_draw_ctx().backend
    if not backend:
        return (0.0, 0.0)

    font_name, font_size = font
    fid = _get_font_id(font_name, font_size)

    return type(backend).measure_string_core_graphics(
        s,
        max_width,
        size=font_size,
        font_id=fid,
        line_break_mode=line_break_mode,
    )


@pytoui_desktop_only
def _screen_origin(view) -> tuple[float, float]:
    """Compute view's content origin in screen coordinates.

    Walks the superview chain: each ancestor contributes frame.xy - bounds.xy.
    """
    x = view.frame.x
    y = view.frame.y
    sv = view.superview
    while sv is not None:
        x += sv.frame.x - sv.bounds.x
        y += sv.frame.y - sv.bounds.y
        sv = sv.superview
    return x, y


def convert_point(
    point: _PointLike = (0, 0),
    from_view=None,
    to_view=None,
) -> Point:
    """Convert a point from one view's coordinate system to another.

    If from_view is None, point is treated as already in screen coordinates.
    If to_view is None, the result is in screen coordinates.
    """
    px, py = point
    if from_view is not None:
        ox, oy = _screen_origin(from_view)
        px += ox
        py += oy
    if to_view is not None:
        tx, ty = _screen_origin(to_view)
        px -= tx
        py -= ty
    return Point(px, py)


def convert_rect(
    rect: _RectLike = (0, 0, 0, 0),
    from_view=None,
    to_view=None,
) -> Rect:
    """Convert a rectangle from one view's coordinate system to another.

    If from_view is None, rect is treated as already in screen coordinates.
    If to_view is None, the result is in screen coordinates.
    Width and height are preserved (no rotation support).
    """
    rx, ry, rw, rh = rect
    origin = convert_point((rx, ry), from_view, to_view)
    return Rect(origin.x, origin.y, rw, rh)


# -- Path class ---------------------------------------------------------------


@_final_
class Path:
    """Pythonista-compatible Path backed by a Rust handle (osdbuf PathXxx FFI).

    Segments are stored in Rust; fill/stroke delegate directly to PathFill/PathStroke.
    """

    def __init__(self):
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        self._handle = type(backend).create_path()
        self._line_width: float = 1.0
        self._line_join_style: _LineJoinMode = LINE_JOIN_MITER
        self._line_cap_style: _LineCapStyle = LINE_CAP_BUTT
        self._has_segments: bool = False
        self._eo_fill_rule: bool = False

    def __del__(self):
        backend = _get_draw_ctx().backend
        if not backend:
            return

        h = getattr(self, "_handle", 0)
        try:
            type(backend).destroy_path(h)
        except Exception:
            pass

    # -- line style properties ------------------------------------------------

    @property
    def line_width(self) -> float:
        return self._line_width

    @line_width.setter
    def line_width(self, value: float):
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        self._line_width = float(value)
        type(backend).path_set_line_width(self._handle, value)

    @property
    def line_join_style(self) -> _LineJoinMode:
        return self._line_join_style

    @line_join_style.setter
    def line_join_style(self, value: _LineJoinMode):
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        self._line_join_style = cast(_LineJoinMode, int(value))
        type(backend).path_set_line_join_style(self._handle, value)

    @property
    def line_cap_style(self) -> _LineCapStyle:
        return self._line_cap_style

    @line_cap_style.setter
    def line_cap_style(self, value: _LineCapStyle):
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        self._line_cap_style = cast(_LineCapStyle, int(value))
        type(backend).path_set_line_cap_style(self._handle, value)

    @property
    def eo_fill_rule(self) -> bool:
        """If True, uses even-odd fill rule;
        if False (default), uses non-zero (winding) rule."""
        return self._eo_fill_rule

    @eo_fill_rule.setter
    def eo_fill_rule(self, value: bool):
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        self._eo_fill_rule = bool(value)
        type(backend).path_set_eo_fill_rule(self._handle, value)

    @property
    def bounds(self) -> Rect:
        """(readonly) The path's bounding rectangle as a Rect(x, y, w, h)."""
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        return Rect(*type(backend).path_get_bounds(self._handle))

    # -- Class method constructors --------------------------------------------

    @classmethod
    def rect(cls, x: float, y: float, w: float, h: float) -> Path:
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        p = cls()
        try:
            p._handle = type(backend).path_rect(x, y, w, h)
        except RuntimeError:
            p._handle = 0
        p._has_segments = True
        return p

    @classmethod
    def oval(cls, x: float, y: float, w: float, h: float) -> Path:
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        p = cls()
        try:
            p._handle = type(backend).path_oval(x, y, w, h)
        except RuntimeError:
            p._handle = 0
        p._has_segments = True
        return p

    @classmethod
    def rounded_rect(cls, x: float, y: float, w: float, h: float, r: float) -> Path:
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        p = cls()
        try:
            p._handle = type(backend).path_rounded_rect(x, y, w, h, r)
        except RuntimeError:
            p._handle = 0
        p._has_segments = True
        return p

    # -- Instance path construction -------------------------------------------

    def move_to(self, x: float, y: float) -> None:
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        type(backend).path_move_to(self._handle, x, y)
        self._has_segments = True

    def line_to(self, x: float, y: float) -> None:
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        type(backend).path_line_to(self._handle, x, y)
        self._has_segments = True

    def add_arc(
        self,
        cx: float,
        cy: float,
        r: float,
        start: float,
        end: float,
        clockwise: bool = True,
    ) -> None:
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        type(backend).path_add_arc(self._handle, cx, cy, r, start, end, clockwise)
        self._has_segments = True

    def add_curve(
        self,
        end_x: float,
        end_y: float,
        cp1_x: float,
        cp1_y: float,
        cp2_x: float,
        cp2_y: float,
    ) -> None:
        """Append a cubic Bézier curve.  Argument order matches Pythonista:
        end point first, then the two control points.
        """
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        type(backend).path_add_curve(
            self._handle,
            end_x,
            end_y,
            cp1_x,
            cp1_y,
            cp2_x,
            cp2_y,
        )
        self._has_segments = True

    def add_quad_curve(
        self, end_x: float, end_y: float, cp_x: float, cp_y: float
    ) -> None:
        """Append a quadratic Bézier curve.  Argument order matches Pythonista:
        end point first, then the control point.
        """
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        type(backend).path_add_quad_curve(self._handle, end_x, end_y, cp_x, cp_y)
        self._has_segments = True

    def close(self) -> None:
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        type(backend).path_close(self._handle)

    def append_path(self, other: Path) -> None:
        """Append all segments of other into this path."""
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        type(backend).path_append_path(self._handle, other._handle)
        self._has_segments = True

    def set_line_dash(self, sequence: Sequence[float], phase: float = 0.0) -> None:
        """Set dashed stroke pattern. Pass empty list to clear."""
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        type(backend).path_set_line_dash(self._handle, sequence, phase)

    def hit_test(self, x: float, y: float) -> bool:
        """Return True if (x, y) is inside the filled path."""
        backend = _get_draw_ctx().backend
        if not backend:
            raise RuntimeError("Invalid backend")

        return type(backend).path_hit_test(self._handle, x, y)

    # -- Drawing --------------------------------------------------------------

    def fill(self) -> None:
        """Fill the path using the current color."""
        ctx = _get_draw_ctx()
        fb = ctx.backend
        if fb is None or self._handle <= 0:
            return
        color = ctx.color
        if ctx.alpha != 1.0:
            color = (color[0], color[1], color[2], color[3] * ctx.alpha)
        c = _rgba_to_uint32(color)
        fb.path_fill(self._handle, c, ctx.blend_mode)  # type: ignore[arg-type]

    def stroke(self) -> None:
        """Stroke the path outline using the current color."""
        ctx = _get_draw_ctx()
        fb = ctx.backend
        if fb is None or self._handle <= 0:
            return
        color = ctx.color
        if ctx.alpha != 1.0:
            color = (color[0], color[1], color[2], color[3] * ctx.alpha)
        c = _rgba_to_uint32(color)
        fb.path_stroke(self._handle, c, ctx.blend_mode)  # type: ignore[arg-type]

    def add_clip(self) -> None:
        """Constrain the clipping region of the
        current graphics context to this path."""
        ctx = _get_draw_ctx()
        fb = ctx.backend
        if fb is None or self._handle <= 0:
            return
        fb.path_add_clip(self._handle)

    # -- Utility --------------------------------------------------------------

    def __bool__(self):
        return self._has_segments

    def __repr__(self):
        return f"<Path handle={self._handle}>"

    # ObjC-compat
    @property
    def objc_instance(self) -> None:
        return None

    @property
    def _objc_ptr(self) -> None:
        return None

    def _debug_quicklook_(self) -> str:
        return self.__repr__()


def get_screen_size() -> tuple[int, int]:
    from pytoui.ui._runtime import get_screen_size as _gss

    return _gss()


def get_window_size() -> tuple[int, int]:
    from pytoui.ui._runtime import get_window_size as _gws

    return _gws()


def get_ui_style() -> _UiStyle:
    from pytoui.ui._runtime import get_ui_style as _gus

    return _gus()


# ---------------------------------------------------------------------------
# Per-window animation context (thread-local)
# ---------------------------------------------------------------------------


@_final_
class _AnimatingContext:
    active: list
    pending_delays: list
    recording: bool
    records: list


_anim_local = cast("_AnimatingContext", local())


def _get_anim_ctx() -> _AnimatingContext:
    lc = _anim_local
    if not hasattr(lc, "active"):
        lc.active = []
        lc.pending_delays = []
        lc.recording = False
        lc.records = []
    return lc


# ---------------------------------------------------------------------------
# Delay / cancel_delays / in_background
# ---------------------------------------------------------------------------


def delay(func: Callable, seconds: float) -> None:
    """Call func after the given number of seconds."""
    _get_anim_ctx().pending_delays.append((time.time() + seconds, func))


def cancel_delays() -> None:
    """Cancel all pending delay() invocations."""
    _get_anim_ctx().pending_delays.clear()


@pytoui_desktop_only
def _tick_delays(now: float) -> None:
    """Called by the runtime each frame to fire ready delays."""
    ctx = _get_anim_ctx()
    ready = [(t, f) for t, f in ctx.pending_delays if now >= t]
    ctx.pending_delays = [(t, f) for t, f in ctx.pending_delays if now < t]
    for _, func in ready:
        func()


def in_background(fn: Callable) -> Callable:
    """Decorator that runs fn in a background thread.

    Usage::

        @ui.in_background
        def button_tapped(sender):
            # long-running work here; UI stays responsive
            ...
    """
    import functools
    import threading

    def new_fn(*args, **kwargs):
        threading.Thread(
            target=functools.partial(fn, *args, **kwargs),
            daemon=True,
        ).start()

    return new_fn


# (animation state is now per-thread — see _get_anim_ctx())


# ---------------------------------------------------------------------------
# Interpolation
# ---------------------------------------------------------------------------


def _ease_in_out(t: float) -> float:
    """Smooth-step: 3t² - 2t³"""
    return t * t * (3.0 - 2.0 * t)


def _lerp(a, b, t: float):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + (b - a) * t
    if isinstance(a, tuple) and isinstance(b, tuple):
        return tuple(ai + (bi - ai) * t for ai, bi in zip(a, b))
    if isinstance(a, Rect) and isinstance(b, Rect):
        return Rect(
            a.x + (b.x - a.x) * t,
            a.y + (b.y - a.y) * t,
            a.w + (b.w - a.w) * t,
            a.h + (b.h - a.h) * t,
        )
    if isinstance(a, (Point, Size)) and type(a) is type(b):
        return type(a)(
            a.x + (b.x - a.x) * t,
            a.y + (b.y - a.y) * t,
        )
    return b if t >= 1.0 else a


# ---------------------------------------------------------------------------
# Animation object
# ---------------------------------------------------------------------------


@_final_
class _Anim:
    __slots__ = (
        "attr",
        "completion",
        "done",
        "duration",
        "end",
        "start",
        "start_t",
        "view",
    )

    def __init__(
        self,
        view,
        attr: str,
        start,
        end,
        start_t: float,
        duration: float,
        completion,
    ):
        self.view = view
        self.attr = attr
        self.start = start
        self.end = end
        self.start_t = start_t
        self.duration = duration
        self.completion = completion
        self.done = False

    def tick(self, now: float) -> bool:
        """Advance animation. Returns True when finished."""
        elapsed = now - self.start_t
        if elapsed < 0:
            return False  # Delay not yet expired

        t = (elapsed / self.duration) if self.duration > 0 else 1.0
        if t >= 1.0:
            t = 1.0
            self.done = True

        setattr(self.view, self.attr, _lerp(self.start, self.end, _ease_in_out(t)))

        if self.done and self.completion:
            self.completion()

        return self.done


# ---------------------------------------------------------------------------
# Public API called by View setters
# ---------------------------------------------------------------------------


@pytoui_desktop_only
def _record(view, attr: str, start, end) -> bool:
    """Called from animated View property setters.

    Returns True if we are inside animate() — the setter should skip applying
    the change (it will be applied by the animation engine instead).
    """
    ctx = _get_anim_ctx()
    if ctx.recording:
        ctx.records.append((view, attr, start, end))
        return True
    return False


# ---------------------------------------------------------------------------
# Runtime hook — call once per frame
# ---------------------------------------------------------------------------


def _tick(now: float | None = None) -> None:
    """Advance all active animations. Must be called by the runtime each frame."""
    ctx = _get_anim_ctx()
    if not ctx.active:
        return
    if now is None:
        now = time.time()
    snapshot = ctx.active
    ctx.active = []  # completions can append safely
    remaining = [a for a in snapshot if not a.tick(now)]
    ctx.active = remaining + ctx.active  # new anims go to end


def animate(
    animation: Callable,
    duration: float = 0.25,
    delay: float = 0.0,
    completion: Callable | None = None,
) -> None:
    """Animate changes to View attributes.

    Call this with a function that modifies view properties; those changes
    will be smoothly interpolated over *duration* seconds.

    Example::

        def anim():
            v.alpha = 0.0


        ui.animate(anim, duration=0.5, completion=lambda: print("done"))
    """
    ctx = _get_anim_ctx()
    ctx.recording = True
    ctx.records = []
    try:
        animation()
    finally:
        ctx.recording = False

    records = ctx.records
    ctx.records = []

    if duration <= 0:
        for view, attr, _, end in records:
            setattr(view, attr, end)
        if completion:
            completion()
        return

    if not records:
        if completion:
            completion()
        return

    start_t = time.time() + delay
    n = len(records)
    remaining = [n]

    def _completion_once():
        remaining[0] -= 1
        if remaining[0] == 0 and completion:
            completion()

    cb = _completion_once if completion else None
    keys = {(view, attr) for view, attr, _, _ in records}
    ctx.active = [a for a in ctx.active if (a.view, a.attr) not in keys]
    for view, attr, start, end in records:
        ctx.active.append(_Anim(view, attr, start, end, start_t, duration, cb))


# ---------------------------------------------------------------------------
# Pythonista compatibility shim
# When running inside Pythonista, replace desktop implementations with the
# native ui-module equivalents.  Internal helpers (_set_origin, _tick, …)
# become no-ops since the desktop runtime is never started on iOS.
# ---------------------------------------------------------------------------

from pytoui._platform import IS_PYTHONISTA, pytoui_desktop_only

if IS_PYTHONISTA:
    from ui import (  # type: ignore[import-not-found,no-redef,assignment]
        GState,
        ImageContext,
        Path,
        Transform,
        animate,
        cancel_delays,
        concat_ctm,
        convert_point,
        convert_rect,
        delay,
        draw_string,
        fill_rect,
        get_screen_size,
        get_ui_style,
        get_window_size,
        in_background,
        measure_string,
        parse_color,
        set_blend_mode,
        set_color,
        set_shadow,
    )
