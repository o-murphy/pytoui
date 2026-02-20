"""
Pythonista-compatible drawing API.

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
from functools import lru_cache
from re import fullmatch
from threading import local
import time
from typing import Any, Callable, cast, TYPE_CHECKING

from pytoui.ui._constants import (
    ALIGN_CENTER,
    ALIGN_LEFT,
    ALIGN_NATURAL,
    ALIGN_RIGHT,
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
    LB_CHAR_WRAP,
    LB_CLIP,
    LB_TRUNCATE_HEAD,
    LB_TRUNCATE_MIDDLE,
    LB_TRUNCATE_TAIL,
    LB_WORD_WRAP,
    LINE_CAP_BUTT,
    LINE_JOIN_MITER,
)
from pytoui.ui._types import (
    Point,
    Rect,
    Size,
)

if TYPE_CHECKING:
    from pytoui.ui._types import _RGBA, _RectLike, _ColorLike


__all__ = (
    "GState",
    "ImageContext",
    "parse_color",
    "set_color",
    "set_blend_mode",
    "set_shadow",
    "fill_rect",
    "concat_ctm",
    "begin_path",
    "draw_string",
    "measure_string",
    "convert_point",
    "convert_rect",
    "animate",
    "delay",
    "cancel_delays",
    "in_background",
    "Path",
    "Transform",
    "_set_origin",
    "_content_mode_transform",
    "_tick",
    "_tick_delays",
    "_record",
)


# -- Drawing context (thread-local) ------------------------------------------


class ImageContext:
    """Context manager for offscreen drawing into an Image.

    Usage::

        with ui.ImageContext(100, 100) as ctx:
            ui.set_color('red')
            ui.Path.oval(0, 0, 100, 100).fill()
            img = ctx.get_image()
    """

    def __init__(self, width: float, height: float, scale: float = 1.0):
        self.width = width
        self.height = height
        self.scale = scale
        self._fb = None
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

    def __exit__(self, *args):
        ctx = _get_draw_ctx()
        ctx.backend = self._prev_backend
        ctx.origin = self._prev_origin
        ctx._image_context = None
        if self._fb is not None:
            try:
                self._fb._lib.DestroyFrameBuffer(self._fb._handle)
                self._fb._handle = 0
            except Exception:
                pass
            self._fb = None

    def get_image(self):
        """Create an Image from the current drawing."""
        from pytoui.ui._image import Image

        if self._buf is None:
            return Image()
        # FrameBuffer stores pixels as ARGB8888 → BGRA bytes on little-endian.
        # Convert to RGBA so Image._data and blit() use consistent byte order.
        raw = bytearray(self._buf)
        # FrameBuffer fills pixels as RGBA8888 (same order as BlitRGBA expects),
        # so no byte-swap is needed here.
        return Image(
            width=self.width, height=self.height, scale=self.scale, data=bytes(raw)
        )


def _get_rust_lib():
    """Return the loaded osdbuf Rust library, or None if not yet available."""
    try:
        from pytoui._osdbuf import FrameBuffer

        return FrameBuffer._lib
    except (ImportError, AttributeError):
        return None


class Transform:
    """Thin wrapper around a Rust-side Transform handle.

    Python fields (a, b, c, d, tx, ty) are kept in sync as a local cache
    so that _sync_ctm_to_rust and repr work without a Rust round-trip.
    The Rust handle is created lazily on first use.
    """

    __slots__ = ("a", "b", "c", "d", "tx", "ty", "_handle")

    def __init__(self, a=1.0, b=0.0, c=0.0, d=1.0, tx=0.0, ty=0.0):
        self.a = float(a)
        self.b = float(b)
        self.c = float(c)
        self.d = float(d)
        self.tx = float(tx)
        self.ty = float(ty)
        self._handle: int = 0  # lazily created

    def __del__(self):
        h = getattr(self, "_handle", 0)
        if h > 0:
            lib = _get_rust_lib()
            if lib:
                try:
                    lib.DestroyTransform(h)
                except Exception:
                    pass

    def _ensure_handle(self) -> int:
        if self._handle <= 0:
            lib = _get_rust_lib()
            if lib:
                import ctypes

                self._handle = lib.CreateTransform(
                    ctypes.c_float(self.a),
                    ctypes.c_float(self.b),
                    ctypes.c_float(self.c),
                    ctypes.c_float(self.d),
                    ctypes.c_float(self.tx),
                    ctypes.c_float(self.ty),
                )
        return self._handle

    @classmethod
    def _from_handle(cls, handle: int) -> "Transform":
        """Wrap an existing Rust handle; reads values back via TransformGet."""
        import ctypes

        obj = cls.__new__(cls)
        object.__setattr__(obj, "_handle", handle)
        object.__setattr__(obj, "a", 0.0)
        object.__setattr__(obj, "b", 0.0)
        object.__setattr__(obj, "c", 0.0)
        object.__setattr__(obj, "d", 0.0)
        object.__setattr__(obj, "tx", 0.0)
        object.__setattr__(obj, "ty", 0.0)
        lib = _get_rust_lib()
        if lib and handle > 0:
            a = ctypes.c_float()
            b = ctypes.c_float()
            c = ctypes.c_float()
            d = ctypes.c_float()
            tx = ctypes.c_float()
            ty = ctypes.c_float()
            lib.TransformGet(
                handle,
                ctypes.byref(a),
                ctypes.byref(b),
                ctypes.byref(c),
                ctypes.byref(d),
                ctypes.byref(tx),
                ctypes.byref(ty),
            )
            obj.a, obj.b, obj.c, obj.d = a.value, b.value, c.value, d.value
            obj.tx, obj.ty = tx.value, ty.value
        return obj

    @classmethod
    def rotation(cls, rad: float) -> "Transform":
        import ctypes

        lib = _get_rust_lib()
        if lib:
            h = lib.TransformRotation(ctypes.c_float(rad))
            if h > 0:
                return cls._from_handle(h)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        return cls(cos_a, sin_a, -sin_a, cos_a, 0.0, 0.0)

    @classmethod
    def scale(cls, sx: float, sy: float) -> "Transform":
        import ctypes

        lib = _get_rust_lib()
        if lib:
            h = lib.TransformScale(ctypes.c_float(sx), ctypes.c_float(sy))
            if h > 0:
                return cls._from_handle(h)
        return cls(sx, 0.0, 0.0, sy, 0.0, 0.0)

    @classmethod
    def translation(cls, tx: float, ty: float) -> "Transform":
        import ctypes

        lib = _get_rust_lib()
        if lib:
            h = lib.TransformTranslation(ctypes.c_float(tx), ctypes.c_float(ty))
            if h > 0:
                return cls._from_handle(h)
        return cls(1.0, 0.0, 0.0, 1.0, tx, ty)

    def concat(self, other: "Transform") -> "Transform":
        lib = _get_rust_lib()
        ha = self._ensure_handle()
        hb = other._ensure_handle()
        if lib and ha > 0 and hb > 0:
            h = lib.TransformConcat(ha, hb)
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

    def invert(self) -> "Transform":
        lib = _get_rust_lib()
        h = self._ensure_handle()
        if lib and h > 0:
            ih = lib.TransformInvert(h)
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


class _DrawingContext:
    """Description of the context structure for static analysis."""

    color: tuple[float, float, float, float]
    blend_mode: int
    backend: Any
    clip: Rect | None
    origin: tuple[float, float]
    shadow: tuple[_RGBA | None, float, float, float] | None
    ctm: Transform
    alpha: float
    _stack: list[dict]


_draw_ctx = cast(_DrawingContext, local())


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
        }
    )


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


class GState:
    """Context manager that saves/restores the current drawing state.

    Saves and restores Python-side state (color, blend_mode, alpha, origin,
    shadow, ctm). On restore, CTM is synced to Rust via _sync_ctm_to_rust.

    Usage::

        with ui.GState():
            ui.set_color('red')
            ui.concat_ctm(ui.Transform.rotation(0.5))
            # ... draw ...
        # state is restored here
    """

    def __enter__(self):
        _save_gstate()

    def __exit__(self, exc_type, exc_val, exc_tb):
        _restore_gstate()


def _sync_ctm_to_rust(ctx) -> None:
    """Push the current Python CTM (composed with origin translation) to the Rust backend.

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
    # T(ox, oy).concat(m) = (m.a, m.b, m.c, m.d, m.tx + ox, m.ty + oy)
    fb.set_ctm(m.a, m.b, m.c, m.d, m.tx + ox, m.ty + oy)


def set_backend(backend):
    """Set the active drawing backend (e.g. osdbuf.FrameBuffer instance).
    Called by the render loop before View.draw()."""
    ctx = _get_draw_ctx()
    ctx.backend = backend
    _sync_ctm_to_rust(ctx)


def _set_origin(x: float, y: float):
    """Set the coordinate origin for subsequent draw calls.
    Called by the render loop to translate to the view's absolute position.
    Internal only — not part of the Pythonista public API."""
    ctx = _get_draw_ctx()
    ctx.origin = (x, y)
    _sync_ctm_to_rust(ctx)


def set_alpha(alpha: float):
    """Set a global alpha multiplier applied to all subsequent drawing operations.
    Internal only — not part of the Pythonista public API.
    Used by View._render() to apply view.alpha to the entire view's drawing."""
    ctx = _get_draw_ctx()
    ctx.alpha = max(0.0, min(1.0, float(alpha)))


# -- Public Pythonista-compatible API -----------------------------------------

_CSS_COLORS: dict[str, _RGBA] = {
    "clear": (0.0, 0.0, 0.0, 0.0),
    "transparent": (0.0, 0.0, 0.0, 0.0),
    "black": (0.0, 0.0, 0.0, 1.0),
    "white": (1.0, 1.0, 1.0, 1.0),
    "red": (1.0, 0.0, 0.0, 1.0),
    "green": (0.0, 0.5, 0.0, 1.0),
    "lime": (0.0, 1.0, 0.0, 1.0),
    "blue": (0.0, 0.0, 1.0, 1.0),
    "yellow": (1.0, 1.0, 0.0, 1.0),
    "cyan": (0.0, 1.0, 1.0, 1.0),
    "aqua": (0.0, 1.0, 1.0, 1.0),
    "magenta": (1.0, 0.0, 1.0, 1.0),
    "fuchsia": (1.0, 0.0, 1.0, 1.0),
    "orange": (1.0, 0.65, 0.0, 1.0),
    "purple": (0.5, 0.0, 0.5, 1.0),
    "brown": (0.6, 0.4, 0.2, 1.0),
    "pink": (1.0, 0.75, 0.8, 1.0),
    "gray": (0.5, 0.5, 0.5, 1.0),
    "grey": (0.5, 0.5, 0.5, 1.0),
    "lightgray": (0.83, 0.83, 0.83, 1.0),
    "lightgrey": (0.83, 0.83, 0.83, 1.0),
    "darkgray": (0.33, 0.33, 0.33, 1.0),
    "darkgrey": (0.33, 0.33, 0.33, 1.0),
    "silver": (0.75, 0.75, 0.75, 1.0),
    "navy": (0.0, 0.0, 0.5, 1.0),
    "teal": (0.0, 0.5, 0.5, 1.0),
    "maroon": (0.5, 0.0, 0.0, 1.0),
    "olive": (0.5, 0.5, 0.0, 1.0),
}


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
        else:
            r = (c >> 16) & 0xFF
            g = (c >> 8) & 0xFF
            b = c & 0xFF
            return (r / 255, g / 255, b / 255, 1.0)

    if isinstance(c, str):
        # CSS color name lookup
        named = _CSS_COLORS.get(c.lower().replace(" ", ""))
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
    Accepts any Color format (RGBA tuple, RGB tuple, hex string, hex int)."""
    ctx = _get_draw_ctx()
    ctx.color = parse_color(c) or (0.0, 0.0, 0.0, 1.0)


def set_blend_mode(mode: int):
    """Set the current blend mode (BlendMode.NORMAL = alpha-over, BlendMode.COPY = direct)."""
    ctx = _get_draw_ctx()
    ctx.blend_mode = mode


def concat_ctm(transform: Transform):
    """
    Adds a new transformation to the current state of the graphics context.
    Mathematically this is: NewCTM = CurrentCTM * IncomingTransform
    """
    ctx = _get_draw_ctx()

    if not hasattr(ctx, "ctm") or ctx.ctm is None:
        ctx.ctm = Transform()  # Identity matrix (1,0,0,1,0,0)

    ctx.ctm = ctx.ctm.concat(transform)
    _sync_ctm_to_rust(ctx)


def begin_path():
    """Begin a new empty path. Returns a new Path."""
    return Path()


def fill_rect(x: float, y: float, w: float, h: float):
    Path.rect(x, y, w, h).fill()


def _content_mode_transform(
    mode: int, cw: float, ch: float, fw: float, fh: float
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


# -- Font name → font_id mapping ----------------------------------------------

_FONT_MAP = {
    "<system>": 1,
    "<system-bold>": 2,
}


def _font_id(font_name: str) -> int:
    return _FONT_MAP.get(font_name, 1)


# -- Text measurement and layout helpers ---------------------------------------


def measure_string(
    s: str,
    max_width: float = 0,
    font: tuple[str, float] = ("<system>", 12.0),
    alignment: int = ALIGN_LEFT,
    line_break_mode: int = LB_WORD_WRAP,
) -> tuple[float, float]:
    """Return the dimensions (width, height) of a string as if drawn with draw_string().

    When max_width is 0, the text is not constrained (single line).
    """
    ctx = _get_draw_ctx()
    fb = ctx.backend
    if fb is None:
        return (0.0, 0.0)
    font_name, font_size = font
    fid = _font_id(font_name)
    line_h = type(fb).get_text_height(size=font_size, font_id=fid)

    fb_cls = type(fb)
    if max_width <= 0:
        # Single line, unconstrained width
        w = _measure(fb_cls, s, font_size, fid)  # type: ignore[arg-type]
        return (float(w), float(line_h))

    # Multi-line: layout with max_width constraint
    lines = _layout_lines(s, int(max_width), font_size, fid, line_break_mode, 0)
    total_h = line_h * len(lines)
    max_w = 0.0
    for line in lines:
        lw = _measure(fb_cls, line, font_size, fid)  # type: ignore[arg-type]
        if lw > max_w:
            max_w = lw
    return (float(max_w), float(total_h))


@lru_cache(maxsize=2048)
def _measure(fb_cls, text: str, size: float, font_id: int) -> int:
    """Measure text width via fb class method. Cached — result is deterministic for given inputs."""
    return fb_cls.measure_text(text, size=size, font_id=font_id)


def _truncate_tail(fb_cls, text: str, max_w: float, size: float, font_id: int) -> str:
    if _measure(fb_cls, text, size, font_id) <= max_w:
        return text
    ellipsis = "..."
    ew = _measure(fb_cls, ellipsis, size, font_id)
    for i in range(len(text), 0, -1):
        if _measure(fb_cls, text[:i], size, font_id) + ew <= max_w:
            return text[:i] + ellipsis
    return ellipsis


def _truncate_head(fb_cls, text: str, max_w: float, size: float, font_id: int) -> str:
    if _measure(fb_cls, text, size, font_id) <= max_w:
        return text
    ellipsis = "\u2026"
    ew = _measure(fb_cls, ellipsis, size, font_id)
    for i in range(len(text)):
        if _measure(fb_cls, text[i:], size, font_id) + ew <= max_w:
            return ellipsis + text[i:]
    return ellipsis


def _truncate_middle(fb_cls, text: str, max_w: float, size: float, font_id: int) -> str:
    if _measure(fb_cls, text, size, font_id) <= max_w:
        return text
    ellipsis = "\u2026"
    n = len(text)
    for cut in range(1, n):
        left = n // 2 - (cut + 1) // 2
        right = n // 2 + cut // 2
        if left < 0:
            break
        candidate = text[:left] + ellipsis + text[right:]
        if _measure(fb_cls, candidate, size, font_id) <= max_w:
            return candidate
    return ellipsis


def _wrap_word(fb_cls, text: str, max_w: float, size: float, font_id: int) -> list[str]:
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if _measure(fb_cls, trial, size, font_id) <= max_w or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _wrap_char(fb_cls, text: str, max_w: float, size: float, font_id: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for ch in text:
        trial = current + ch
        if _measure(fb_cls, trial, size, font_id) <= max_w or not current:
            current = trial
        else:
            lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines or [""]


def _layout_lines(
    text: str,
    w: float,
    font_size: float,
    font_id: int,
    mode: int,
    max_lines: int,
) -> list[str]:
    """Break text into lines respecting line_break_mode and number_of_lines.

    Uses ctx.backend automatically; returns [''] if no backend is active.
    """
    fb = _get_draw_ctx().backend
    if fb is None:
        return [""]
    fb_cls = type(fb)

    if mode in (
        LB_TRUNCATE_TAIL,
        LB_TRUNCATE_HEAD,
        LB_TRUNCATE_MIDDLE,
        LB_CLIP,
    ):
        if max_lines <= 1:
            if mode == LB_TRUNCATE_TAIL:
                return [_truncate_tail(fb_cls, text, w, font_size, font_id)]
            elif mode == LB_TRUNCATE_HEAD:
                return [_truncate_head(fb_cls, text, w, font_size, font_id)]
            elif mode == LB_TRUNCATE_MIDDLE:
                return [_truncate_middle(fb_cls, text, w, font_size, font_id)]
            else:
                return [text]

    if mode == LB_CHAR_WRAP:
        lines = _wrap_char(fb_cls, text, w, font_size, font_id)
    else:
        lines = _wrap_word(fb_cls, text, w, font_size, font_id)

    if max_lines > 0 and len(lines) > max_lines:
        lines = lines[:max_lines]
        if mode != LB_CLIP:
            lines[-1] = _truncate_tail(fb_cls, lines[-1], w, font_size, font_id)

    return lines


def _alignment_to_anchor(alignment: int) -> int:
    """Map TextAlignment to osdbuf TextAnchor bit flags."""
    CENTER = 0
    LEFT = 4
    RIGHT = 8  # noqa: E702
    if alignment in (ALIGN_LEFT, ALIGN_NATURAL):
        return LEFT
    elif alignment == ALIGN_RIGHT:
        return RIGHT
    elif alignment == ALIGN_CENTER:
        return CENTER
    return LEFT


def draw_string(
    s: str,
    rect: _RectLike = (0, 0, 0, 0),
    font: tuple[str, float] = ("<system>", 17.0),
    color: _ColorLike | None = None,
    alignment: int = ALIGN_NATURAL,
    line_break_mode: int = LB_TRUNCATE_TAIL,
    number_of_lines: int = 1,
):
    """Draw a string in the given rectangle.

    Pythonista-compatible. Coordinates are relative to the current view origin.
    """
    ctx = _get_draw_ctx()
    fb = ctx.backend
    if fb is None:
        return

    # NOTE: text rendering does not apply CTM rotation — backend fb.text() does not support it.
    # However, we do apply the full transform (translation + scale) to the text anchor position.
    ox, oy = ctx.origin
    m = ctx.ctm
    if not isinstance(rect, Rect):
        rect = Rect(*rect)
    x = m.a * rect.x + m.c * rect.y + m.tx + ox
    y = m.b * rect.x + m.d * rect.y + m.ty + oy
    w, h = rect.w, rect.h

    font_name, font_size = font
    fid = _font_id(font_name)

    _color = parse_color(color)
    _color = _color if _color is not None else ctx.color
    if ctx.alpha != 1.0:
        _color = (_color[0], _color[1], _color[2], _color[3] * ctx.alpha)
    c = _rgba_to_uint32(_color)

    lines = _layout_lines(s, w, font_size, fid, line_break_mode, number_of_lines)
    line_h = type(fb).get_text_height(size=font_size, font_id=fid)
    total_h = line_h * len(lines)
    start_y = y + (h - total_h) // 2

    anchor = _alignment_to_anchor(alignment)

    for i, line in enumerate(lines):
        if alignment in (ALIGN_LEFT, ALIGN_NATURAL):
            tx = x
        elif alignment == ALIGN_RIGHT:
            tx = x + w
        elif alignment == ALIGN_CENTER:
            tx = x + w // 2
        else:
            tx = x

        ty = start_y + i * line_h + line_h // 2
        if ty < y or ty >= y + h:
            continue
        fb.text(line, tx, ty, c=c, size=font_size, font_id=fid, anchor=anchor)


def _screen_origin(view) -> tuple[float, float]:
    """Compute view's content origin in screen coordinates.

    Walks the superview chain: each ancestor contributes frame.xy - bounds.xy.
    """
    x = view._frame.x
    y = view._frame.y
    sv = view._superview
    while sv is not None:
        x += sv._frame.x - sv._bounds.x
        y += sv._frame.y - sv._bounds.y
        sv = sv._superview
    return x, y


def convert_point(
    point=(0, 0),
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
    rect=(0, 0, 0, 0),
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


class Path:
    """Pythonista-compatible Path backed by a Rust handle (osdbuf PathXxx FFI).

    Segments are stored in Rust; fill/stroke delegate directly to PathFill/PathStroke.
    """

    def __init__(self):
        lib = _get_rust_lib()
        self._handle: int = lib.CreatePath() if lib else 0
        self._line_width: float = 1.0
        self._line_join_style: int = LINE_JOIN_MITER
        self._line_cap_style: int = LINE_CAP_BUTT
        self._has_segments: bool = False
        self._eo_fill_rule: bool = False

    def __del__(self):
        h = getattr(self, "_handle", 0)
        if h > 0:
            lib = _get_rust_lib()
            if lib:
                try:
                    lib.DestroyPath(h)
                except Exception:
                    pass

    # -- line style properties ------------------------------------------------

    @property
    def line_width(self) -> float:
        return self._line_width

    @line_width.setter
    def line_width(self, value: float):
        self._line_width = float(value)
        if self._handle > 0:
            lib = _get_rust_lib()
            if lib:
                import ctypes

                lib.PathSetLineWidth(self._handle, ctypes.c_float(value))

    @property
    def line_join_style(self) -> int:
        return self._line_join_style

    @line_join_style.setter
    def line_join_style(self, value: int):
        self._line_join_style = int(value)
        if self._handle > 0:
            lib = _get_rust_lib()
            if lib:
                lib.PathSetLineJoin(self._handle, value)

    @property
    def line_cap_style(self) -> int:
        return self._line_cap_style

    @line_cap_style.setter
    def line_cap_style(self, value: int):
        self._line_cap_style = int(value)
        if self._handle > 0:
            lib = _get_rust_lib()
            if lib:
                lib.PathSetLineCap(self._handle, value)

    @property
    def eo_fill_rule(self) -> bool:
        """If True, uses even-odd fill rule; if False (default), uses non-zero (winding) rule."""
        return self._eo_fill_rule

    @eo_fill_rule.setter
    def eo_fill_rule(self, value: bool):
        self._eo_fill_rule = bool(value)
        if self._handle > 0:
            lib = _get_rust_lib()
            if lib:
                lib.PathSetEoFillRule(self._handle, 1 if value else 0)

    @property
    def bounds(self):
        """(readonly) The path's bounding rectangle as a Rect(x, y, w, h)."""
        if self._handle <= 0:
            from pytoui.ui._types import Rect

            return Rect(0.0, 0.0, 0.0, 0.0)
        lib = _get_rust_lib()
        if not lib:
            from pytoui.ui._types import Rect

            return Rect(0.0, 0.0, 0.0, 0.0)
        import ctypes

        x = ctypes.c_float(0.0)
        y = ctypes.c_float(0.0)
        w = ctypes.c_float(0.0)
        h = ctypes.c_float(0.0)
        if lib.PathGetBounds(
            self._handle,
            ctypes.byref(x),
            ctypes.byref(y),
            ctypes.byref(w),
            ctypes.byref(h),
        ):
            from pytoui.ui._types import Rect

            return Rect(x.value, y.value, w.value, h.value)
        from pytoui.ui._types import Rect

        return Rect(0.0, 0.0, 0.0, 0.0)

    # -- Class method constructors --------------------------------------------

    @classmethod
    def rect(cls, x: float, y: float, w: float, h: float) -> "Path":
        lib = _get_rust_lib()
        p = cls.__new__(cls)
        if lib:
            p._handle = lib.PathRect(x, y, w, h)
        else:
            p._handle = 0
        p._line_width = 1.0
        p._line_join_style = LINE_JOIN_MITER
        p._line_cap_style = LINE_CAP_BUTT
        p._has_segments = True
        p._eo_fill_rule = False
        return p

    @classmethod
    def oval(cls, x: float, y: float, w: float, h: float) -> "Path":
        lib = _get_rust_lib()
        p = cls.__new__(cls)
        if lib:
            p._handle = lib.PathOval(x, y, w, h)
        else:
            p._handle = 0
        p._line_width = 1.0
        p._line_join_style = LINE_JOIN_MITER
        p._line_cap_style = LINE_CAP_BUTT
        p._has_segments = True
        p._eo_fill_rule = False
        return p

    @classmethod
    def rounded_rect(cls, x: float, y: float, w: float, h: float, r: float) -> "Path":
        lib = _get_rust_lib()
        p = cls.__new__(cls)
        if lib:
            p._handle = lib.PathRoundedRect(x, y, w, h, r)
        else:
            p._handle = 0
        p._line_width = 1.0
        p._line_join_style = LINE_JOIN_MITER
        p._line_cap_style = LINE_CAP_BUTT
        p._has_segments = True
        p._eo_fill_rule = False
        return p

    # -- Instance path construction -------------------------------------------

    def move_to(self, x: float, y: float):
        if self._handle > 0:
            lib = _get_rust_lib()
            if lib:
                import ctypes

                lib.PathMoveTo(self._handle, ctypes.c_float(x), ctypes.c_float(y))
                self._has_segments = True

    def line_to(self, x: float, y: float):
        if self._handle > 0:
            lib = _get_rust_lib()
            if lib:
                import ctypes

                lib.PathLineTo(self._handle, ctypes.c_float(x), ctypes.c_float(y))
                self._has_segments = True

    def add_arc(
        self,
        cx: float,
        cy: float,
        r: float,
        start: float,
        end: float,
        clockwise: bool = True,
    ):
        if self._handle > 0:
            lib = _get_rust_lib()
            if lib:
                import ctypes

                lib.PathAddArc(
                    self._handle,
                    ctypes.c_float(cx),
                    ctypes.c_float(cy),
                    ctypes.c_float(r),
                    ctypes.c_float(start),
                    ctypes.c_float(end),
                    ctypes.c_int(1 if clockwise else 0),
                )
                self._has_segments = True

    def add_curve(
        self,
        end_x: float,
        end_y: float,
        cp1_x: float,
        cp1_y: float,
        cp2_x: float,
        cp2_y: float,
    ):
        """Append a cubic Bézier curve.  Argument order matches Pythonista:
        end point first, then the two control points."""
        if self._handle > 0:
            lib = _get_rust_lib()
            if lib:
                import ctypes

                lib.PathAddCurve(
                    self._handle,
                    ctypes.c_float(cp1_x),
                    ctypes.c_float(cp1_y),
                    ctypes.c_float(cp2_x),
                    ctypes.c_float(cp2_y),
                    ctypes.c_float(end_x),
                    ctypes.c_float(end_y),
                )
                self._has_segments = True

    def add_quad_curve(self, end_x: float, end_y: float, cp_x: float, cp_y: float):
        """Append a quadratic Bézier curve.  Argument order matches Pythonista:
        end point first, then the control point."""
        if self._handle > 0:
            lib = _get_rust_lib()
            if lib:
                import ctypes

                lib.PathAddQuadCurve(
                    self._handle,
                    ctypes.c_float(cp_x),
                    ctypes.c_float(cp_y),
                    ctypes.c_float(end_x),
                    ctypes.c_float(end_y),
                )
                self._has_segments = True

    def close(self):
        if self._handle > 0:
            lib = _get_rust_lib()
            if lib:
                lib.PathClose(self._handle)

    def append_path(self, other: "Path"):
        """Append all segments of other into this path."""
        if self._handle > 0 and other._handle > 0:
            lib = _get_rust_lib()
            if lib:
                lib.PathAppend(self._handle, other._handle)
                self._has_segments = True

    def set_line_dash(self, sequence: list[float], phase: float = 0.0):
        """Set dashed stroke pattern. Pass empty list to clear."""
        if self._handle <= 0:
            return
        lib = _get_rust_lib()
        if not lib:
            return
        import ctypes

        if not sequence:
            lib.PathSetLineDash(self._handle, None, 0, ctypes.c_float(0.0))
        else:
            arr = (ctypes.c_float * len(sequence))(*sequence)
            lib.PathSetLineDash(self._handle, arr, len(sequence), ctypes.c_float(phase))

    def hit_test(self, x: float, y: float) -> bool:
        """Return True if (x, y) is inside the filled path."""
        if self._handle <= 0:
            return False
        lib = _get_rust_lib()
        if not lib:
            return False
        import ctypes

        return lib.PathHitTest(self._handle, ctypes.c_float(x), ctypes.c_float(y)) != 0

    # -- Drawing --------------------------------------------------------------

    def fill(self):
        """Fill the path using the current color."""
        ctx = _get_draw_ctx()
        fb = ctx.backend
        if fb is None or self._handle <= 0:
            return
        color = ctx.color
        if ctx.alpha != 1.0:
            color = (color[0], color[1], color[2], color[3] * ctx.alpha)
        c = _rgba_to_uint32(color)
        fb.path_fill(self._handle, c, ctx.blend_mode)

    def stroke(self):
        """Stroke the path outline using the current color."""
        ctx = _get_draw_ctx()
        fb = ctx.backend
        if fb is None or self._handle <= 0:
            return
        color = ctx.color
        if ctx.alpha != 1.0:
            color = (color[0], color[1], color[2], color[3] * ctx.alpha)
        c = _rgba_to_uint32(color)
        fb.path_stroke(self._handle, c, ctx.blend_mode)

    def add_clip(self):
        """Constrain the clipping region of the current graphics context to this path."""
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


# ---------------------------------------------------------------------------
# Per-window animation context (thread-local)
# ---------------------------------------------------------------------------


class _AnimatingContext:
    active: list
    pending_delays: list
    recording: bool
    records: list


_anim_local = cast(_AnimatingContext, local())


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
    import threading
    import functools

    def new_fn(*args, **kwargs):
        threading.Thread(
            target=functools.partial(fn, *args, **kwargs), daemon=True
        ).start()

    return new_fn


def get_screen_size() -> tuple[int, int]:
    from pytoui.ui._runtime import get_screen_size as _gss

    return _gss()


def get_window_size() -> tuple[int, int]:
    from pytoui.ui._runtime import get_window_size as _gws

    return _gws()


def get_ui_style() -> str:
    from pytoui.ui._runtime import get_ui_style as _gus

    return _gus()


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
    elif isinstance(a, tuple) and isinstance(b, tuple):
        return tuple(ai + (bi - ai) * t for ai, bi in zip(a, b))
    elif isinstance(a, Rect) and isinstance(b, Rect):
        return Rect(
            a.x + (b.x - a.x) * t,
            a.y + (b.y - a.y) * t,
            a.w + (b.w - a.w) * t,
            a.h + (b.h - a.h) * t,
        )
    elif isinstance(a, (Point, Size)) and type(a) is type(b):
        return type(a)(
            a.x + (b.x - a.x) * t,
            a.y + (b.y - a.y) * t,
        )
    return b if t >= 1.0 else a


# ---------------------------------------------------------------------------
# Animation object
# ---------------------------------------------------------------------------


class _Anim:
    __slots__ = (
        "view",
        "attr",
        "start",
        "end",
        "start_t",
        "duration",
        "completion",
        "done",
    )

    def __init__(
        self, view, attr: str, start, end, start_t: float, duration: float, completion
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
    ctx.active = [a for a in ctx.active if not a.tick(now)]


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
    for view, attr, start, end in records:
        ctx.active.append(_Anim(view, attr, start, end, start_t, duration, cb))
