# osdbuf.py
import ctypes
import sys
from collections.abc import Sequence
from enum import IntEnum, IntFlag
from pathlib import Path
from typing import Any


def _lib_filename(name: str) -> str:
    if sys.platform.startswith("linux"):
        return f"lib{name}.so"
    elif sys.platform == "darwin":
        return f"lib{name}.dylib"
    elif sys.platform == "win32":
        return f"{name}.dll"
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")


_LIB_PATH = str(Path(__file__).parent / _lib_filename("osdbuf"))


class LineCapStyle(IntEnum):
    BUTT = 0
    ROUND = 1
    SQUARE = 2


class LineJoinStyle(IntEnum):
    MITER = 0
    ROUND = 1
    BEVEL = 2


class BlendMode(IntEnum):
    NORMAL = 0  # SourceOver (default)
    MULTIPLY = 1
    SCREEN = 2
    OVERLAY = 3
    DARKEN = 4
    LIGHTEN = 5
    COLOR_DODGE = 6
    COLOR_BURN = 7
    SOFT_LIGHT = 8
    HARD_LIGHT = 9
    DIFFERENCE = 10
    EXCLUSION = 11
    HUE = 12
    SATURATION = 13
    COLOR = 14
    LUMINOSITY = 15
    CLEAR = 16
    COPY = 17  # Source (replace, no blend)
    SOURCE_IN = 18
    SOURCE_OUT = 19
    SOURCE_ATOP = 20
    DESTINATION_OVER = 21
    DESTINATION_IN = 22
    DESTINATION_OUT = 23
    DESTINATION_ATOP = 24
    XOR = 25
    PLUS_DARKER = 26  # Modulate approximation
    PLUS_LIGHTER = 27  # Plus


class TextAnchor(IntFlag):
    CENTER = 0
    TOP = 1 << 0  # 1
    BOTTOM = 1 << 1  # 2
    LEFT = 1 << 2  # 4
    RIGHT = 1 << 3  # 8

    @classmethod
    def normalize(cls, value: int) -> int:
        """Excludes conflicting flags: TOP+BOTTOM or LEFT+RIGHT."""
        if (value & cls.TOP) and (value & cls.BOTTOM):
            value &= ~(cls.TOP | cls.BOTTOM)
        if (value & cls.LEFT) and (value & cls.RIGHT):
            value &= ~(cls.LEFT | cls.RIGHT)
        return value


class FrameBuffer:
    """Pythonic wrapper for osdbuf framebuffer with TTF support"""

    _lib: Any = None

    @classmethod
    def _ensure_lib_loaded(cls, path: str | None = None):
        if cls._lib is None:
            target_path = str(path) if path else _LIB_PATH
            print(f"DEBUG: Loading CDLL into class from {target_path}...", flush=True)
            handle = ctypes.CDLL(target_path)
            cls._setup_argtypes_static(handle)
            cls._lib = handle
        return cls._lib

    @staticmethod
    def _setup_argtypes_static(lib) -> None:
        """Set up argtypes once"""
        L = lib

        # Lifecycle
        L.CreateFrameBuffer.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        L.CreateFrameBuffer.restype = ctypes.c_int

        L.DestroyFrameBuffer.argtypes = [ctypes.c_int]
        L.DestroyFrameBuffer.restype = None

        # Font management (global, not per-FB)
        L.LoadFont.argtypes = [ctypes.c_char_p]
        L.LoadFont.restype = ctypes.c_int

        L.UnloadFont.argtypes = [ctypes.c_int]
        L.UnloadFont.restype = ctypes.c_int

        L.GetDefaultFont.argtypes = []
        L.GetDefaultFont.restype = ctypes.c_int

        L.GetFontCount.argtypes = []
        L.GetFontCount.restype = ctypes.c_int

        L.GetFontIDs.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int]
        L.GetFontIDs.restype = ctypes.c_int

        # Basic fill operations (no blend param — Fill/FillOver use internal logic)
        L.Fill.argtypes = [ctypes.c_int, ctypes.c_uint32]
        L.Fill.restype = None

        L.FillOver.argtypes = [ctypes.c_int, ctypes.c_uint32]
        L.FillOver.restype = None

        # Pixel operations (handle, x, y, color)
        L.SetPixel.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint32,
        ]
        L.SetPixel.restype = None

        L.GetPixel.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        L.GetPixel.restype = ctypes.c_uint32

        L.BlitRGBA.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        L.BlitRGBA.restype = None

        L.BlitRGBAScaled.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        L.BlitRGBAScaled.restype = None

        L.Scroll.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        L.Scroll.restype = None

        # Antialiasing
        L.SetAntiAlias.argtypes = [ctypes.c_int, ctypes.c_int]
        L.SetAntiAlias.restype = None

        L.GetAntiAlias.argtypes = [ctypes.c_int]
        L.GetAntiAlias.restype = ctypes.c_int

        # Lines (handle, x0, y0, x1, y1, color, blend)
        L.Line.argtypes = (
            [ctypes.c_int] + [ctypes.c_int] * 4 + [ctypes.c_uint32, ctypes.c_uint8]
        )
        L.Line.restype = None

        L.HLine.argtypes = (
            [ctypes.c_int] + [ctypes.c_int] * 3 + [ctypes.c_uint32, ctypes.c_uint8]
        )
        L.HLine.restype = None

        L.VLine.argtypes = (
            [ctypes.c_int] + [ctypes.c_int] * 3 + [ctypes.c_uint32, ctypes.c_uint8]
        )
        L.VLine.restype = None

        # Rect outline (handle, x, y, w, h, color, blend)
        L.Rect.argtypes = (
            [ctypes.c_int] + [ctypes.c_int] * 4 + [ctypes.c_uint32, ctypes.c_uint8]
        )
        L.Rect.restype = None

        # FillRect (handle, x, y, w, h [f32], color, blend)
        L.FillRect.argtypes = [
            ctypes.c_int,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_uint32,
            ctypes.c_uint8,
        ]
        L.FillRect.restype = None

        # RoundedRect outline (handle, x, y, w, h, radius [i32], color, blend)
        L.RoundedRect.argtypes = (
            [ctypes.c_int] + [ctypes.c_int] * 5 + [ctypes.c_uint32, ctypes.c_uint8]
        )
        L.RoundedRect.restype = None

        # FillRoundedRect (handle, x, y, w, h, radius [f32], color, blend)
        _frr_args = [
            ctypes.c_int,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_uint32,
            ctypes.c_uint8,
        ]
        L.FillRoundedRect.argtypes = _frr_args
        L.FillRoundedRect.restype = None

        # Circle outline (handle, cx, cy, r [i32], color, blend)
        L.Circle.argtypes = (
            [ctypes.c_int] + [ctypes.c_int] * 3 + [ctypes.c_uint32, ctypes.c_uint8]
        )
        L.Circle.restype = None

        # FillCircle (handle, cx, cy, r [f32], color, blend)
        L.FillCircle.argtypes = [
            ctypes.c_int,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_uint32,
            ctypes.c_uint8,
        ]
        L.FillCircle.restype = None

        # Ellipse outline (handle, cx, cy, rx, ry [i32], color, blend)
        L.Ellipse.argtypes = (
            [ctypes.c_int] + [ctypes.c_int] * 4 + [ctypes.c_uint32, ctypes.c_uint8]
        )
        L.Ellipse.restype = None

        # FillEllipse (handle, cx, cy, rx, ry [f32], color, blend)
        L.FillEllipse.argtypes = [
            ctypes.c_int,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_uint32,
            ctypes.c_uint8,
        ]
        L.FillEllipse.restype = None

        # EllipseArc (handle, cx, cy, rx, ry [i32], start, end [f64], color, blend)
        L.EllipseArc.argtypes = (
            [ctypes.c_int]
            + [ctypes.c_int] * 4
            + [ctypes.c_double, ctypes.c_double]
            + [ctypes.c_uint32, ctypes.c_uint8]
        )
        L.EllipseArc.restype = None

        # Text (DrawText: fb_handle + font_id + fontSize; others: font_id + fontSize)
        L.DrawText.argtypes = [
            ctypes.c_int,  # fb_handle
            ctypes.c_int,  # font_handle
            ctypes.c_float,  # size
            ctypes.c_char_p,  # text
            ctypes.c_float,  # x
            ctypes.c_float,  # y
            ctypes.c_uint32,  # anchor
            ctypes.c_uint32,  # color
            ctypes.c_float,  # spacing
        ]
        L.DrawText.restype = ctypes.c_int

        L.MeasureText.argtypes = [
            ctypes.c_int,
            ctypes.c_float,
            ctypes.c_char_p,
            ctypes.c_float,
        ]
        L.MeasureText.restype = ctypes.c_int

        L.GetTextHeight.argtypes = [ctypes.c_int, ctypes.c_float]
        L.GetTextHeight.restype = ctypes.c_int

        L.GetTextMetrics.argtypes = [
            ctypes.c_int,
            ctypes.c_float,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
        ]
        L.GetTextMetrics.restype = ctypes.c_int

        # YUV Compensation
        L.ApplyYUV422Compensation.argtypes = [ctypes.c_int] + [ctypes.c_int] * 4
        L.ApplyYUV422Compensation.restype = None

        # Stroke primitives

        # LineStroke (handle, x0, y0, x1, y1, width [f32], cap, join [u8], color, blend)
        L.LineStroke.argtypes = [
            ctypes.c_int,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_uint8,
            ctypes.c_uint8,
            ctypes.c_uint32,
            ctypes.c_uint8,
        ]
        L.LineStroke.restype = None

        # RectStroke (handle, x, y, w, h, width [f32], join [u8], color, blend)
        L.RectStroke.argtypes = [
            ctypes.c_int,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_uint8,
            ctypes.c_uint32,
            ctypes.c_uint8,
        ]
        L.RectStroke.restype = None

        # StrokeRoundedRect
        # (handle, x, y, w, h, radius, bw [f32], join [u8], color, blend)
        L.StrokeRoundedRect.argtypes = [
            ctypes.c_int,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_uint8,
            ctypes.c_uint32,
            ctypes.c_uint8,
        ]
        L.StrokeRoundedRect.restype = None

        # EllipseStroke (handle, cx, cy, rx, ry, width [f32], color, blend)
        L.EllipseStroke.argtypes = [
            ctypes.c_int,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_uint32,
            ctypes.c_uint8,
        ]
        L.EllipseStroke.restype = None

        # SetCTM (handle, a, b, c, d, tx, ty [f32]) — sets current transform matrix
        L.SetCTM.argtypes = [
            ctypes.c_int,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
        ]
        L.SetCTM.restype = None

        # GState
        L.GStatePush.argtypes = [ctypes.c_int]
        L.GStatePush.restype = None
        L.GStatePop.argtypes = [ctypes.c_int]
        L.GStatePop.restype = None

        # Transform
        _tf6 = [ctypes.c_float] * 6
        L.CreateTransform.argtypes = _tf6
        L.CreateTransform.restype = ctypes.c_int
        L.DestroyTransform.argtypes = [ctypes.c_int]
        L.DestroyTransform.restype = ctypes.c_int
        L.TransformRotation.argtypes = [ctypes.c_float]
        L.TransformRotation.restype = ctypes.c_int
        L.TransformScale.argtypes = [ctypes.c_float, ctypes.c_float]
        L.TransformScale.restype = ctypes.c_int
        L.TransformTranslation.argtypes = [ctypes.c_float, ctypes.c_float]
        L.TransformTranslation.restype = ctypes.c_int
        L.TransformConcat.argtypes = [ctypes.c_int, ctypes.c_int]
        L.TransformConcat.restype = ctypes.c_int
        L.TransformInvert.argtypes = [ctypes.c_int]
        L.TransformInvert.restype = ctypes.c_int
        L.TransformGet.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
        ]
        L.TransformGet.restype = ctypes.c_int

        # Path
        L.CreatePath.argtypes = []
        L.CreatePath.restype = ctypes.c_int
        L.DestroyPath.argtypes = [ctypes.c_int]
        L.DestroyPath.restype = ctypes.c_int
        L.PathMoveTo.argtypes = [ctypes.c_int, ctypes.c_float, ctypes.c_float]
        L.PathMoveTo.restype = None
        L.PathLineTo.argtypes = [ctypes.c_int, ctypes.c_float, ctypes.c_float]
        L.PathLineTo.restype = None
        L.PathAddCurve.argtypes = [ctypes.c_int] + [ctypes.c_float] * 6
        L.PathAddCurve.restype = None
        L.PathAddQuadCurve.argtypes = [ctypes.c_int] + [ctypes.c_float] * 4
        L.PathAddQuadCurve.restype = None
        L.PathAddArc.argtypes = [ctypes.c_int] + [ctypes.c_float] * 5 + [ctypes.c_int]
        L.PathAddArc.restype = None
        L.PathClose.argtypes = [ctypes.c_int]
        L.PathClose.restype = None
        L.PathAppend.argtypes = [ctypes.c_int, ctypes.c_int]
        L.PathAppend.restype = None
        L.PathRect.argtypes = [ctypes.c_float] * 4
        L.PathRect.restype = ctypes.c_int
        L.PathOval.argtypes = [ctypes.c_float] * 4
        L.PathOval.restype = ctypes.c_int
        L.PathRoundedRect.argtypes = [ctypes.c_float] * 5
        L.PathRoundedRect.restype = ctypes.c_int
        L.PathSetLineWidth.argtypes = [ctypes.c_int, ctypes.c_float]
        L.PathSetLineWidth.restype = None
        L.PathSetLineCap.argtypes = [ctypes.c_int, ctypes.c_uint8]
        L.PathSetLineCap.restype = None
        L.PathSetLineJoin.argtypes = [ctypes.c_int, ctypes.c_uint8]
        L.PathSetLineJoin.restype = None
        L.PathSetLineDash.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_int,
            ctypes.c_float,
        ]
        L.PathSetLineDash.restype = None
        L.PathFill.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint32,
            ctypes.c_uint8,
        ]
        L.PathFill.restype = None
        L.PathStroke.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint32,
            ctypes.c_uint8,
        ]
        L.PathStroke.restype = None
        L.PathHitTest.argtypes = [ctypes.c_int, ctypes.c_float, ctypes.c_float]
        L.PathHitTest.restype = ctypes.c_int
        L.PathSetEoFillRule.argtypes = [ctypes.c_int, ctypes.c_int]
        L.PathSetEoFillRule.restype = None
        L.PathGetBounds.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
        ]
        L.PathGetBounds.restype = ctypes.c_int
        L.PathAddClip.argtypes = [ctypes.c_int, ctypes.c_int]
        L.PathAddClip.restype = None

        L.DrawCheckerBoard.argtypes = (
            ctypes.c_int,
            ctypes.c_int,  # size
        )
        L.DrawCheckerBoard.restype = None

        # Core Graphics text methods
        L.DrawStringCoreGraphics.argtypes = [
            ctypes.c_int,  # fb_handle
            ctypes.c_int,  # font_handle
            ctypes.c_char_p,  # text
            ctypes.c_float,  # x
            ctypes.c_float,  # y
            ctypes.c_float,  # w
            ctypes.c_float,  # h
            ctypes.c_float,  # size
            ctypes.c_uint32,  # color
            ctypes.c_uint32,  # alignment
            ctypes.c_uint32,  # line_break_mode
        ]
        L.DrawStringCoreGraphics.restype = ctypes.c_int

        L.MeasureStringCoreGraphics.argtypes = [
            ctypes.c_int,  # font_handle
            ctypes.c_char_p,  # text
            ctypes.c_float,  # max_width
            ctypes.c_float,  # size
            ctypes.c_uint32,  # line_break_mode
            ctypes.POINTER(ctypes.c_float),  # out_width
            ctypes.POINTER(ctypes.c_float),  # out_height
        ]
        L.MeasureStringCoreGraphics.restype = ctypes.c_int

    def __init__(self, osd_ptr, width, height, lib_path=_LIB_PATH):
        if not osd_ptr:
            raise ValueError("osd_ptr is NULL! Cannot create FrameBuffer.")

        self._handle = 0
        print("DEBUG: Load lib...", flush=True)

        self._lib = self._ensure_lib_loaded(lib_path)
        print("DEBUG: Lib loaded...", flush=True)

        print("DEBUG: Calling CreateFrameBuffer handle...", flush=True)

        addr = ctypes.cast(osd_ptr, ctypes.c_void_p)
        self._handle = self._lib.CreateFrameBuffer(addr, width, height)
        if self._handle <= 0:
            raise RuntimeError("Failed to create framebuffer")
        print(f"DEBUG: Handle received: {self._handle}", flush=True)

        self._width = width
        self._height = height
        self._cx = width // 2
        self._cy = height // 2

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.destroy()

    def __del__(self):
        if self._handle > 0:
            try:
                self._lib.DestroyFrameBuffer(self._handle)
            except Exception:
                pass

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def destroy(self):
        if self._handle > 0:
            self.fill(0)
            self._lib.DestroyFrameBuffer(self._handle)
            self._handle = 0

    # ============= Font API (global, class-level) =============

    _font_registry: dict[str, int] = {}  # path_str → rust font_id

    @classmethod
    def load_font(cls, font_path: str) -> int:
        """Load TTF/OTF font, returns font handle."""
        lib = cls._ensure_lib_loaded()
        fid = lib.LoadFont(font_path.encode("utf-8"))
        if fid <= 0:
            raise RuntimeError(f"Failed to load font: {font_path}")
        return fid

    @classmethod
    def load_font_cached(cls, path_str: str) -> int:
        """Load font if not already in registry; return font_id."""
        fid = cls._font_registry.get(path_str)
        if fid is not None:
            return fid
        fid = cls.load_font(path_str)
        cls._font_registry[path_str] = fid
        return fid

    @classmethod
    def unload_font(cls, font_id: int = 0) -> None:
        """Unload font by handle"""
        lib = cls._ensure_lib_loaded()
        if lib.UnloadFont(font_id) < 0:
            raise ValueError(f"Invalid font handle: {font_id}")

    @classmethod
    def get_default_font(cls) -> int:
        lib = cls._ensure_lib_loaded()
        return lib.GetDefaultFont()

    @classmethod
    def get_font_count(cls) -> int:
        lib = cls._ensure_lib_loaded()
        return lib.GetFontCount()

    @classmethod
    def list_fonts(cls) -> list[int]:
        lib = cls._ensure_lib_loaded()
        count = lib.GetFontCount()
        if count <= 0:
            return []
        buf = (ctypes.c_int * count)()
        n = lib.GetFontIDs(buf, count)
        return list(buf[:n])

    # ============= Drawing methods =============

    def fill(self, c: int = 0) -> None:
        self._lib.Fill(self._handle, c)

    def fill_over(self, c: int = 0) -> None:
        self._lib.FillOver(self._handle, c)

    def pixel(self, x: int, y: int, c: int | None = 0) -> int | None:
        """Absolute coordinates. c=None -> get, else set."""
        if c is None:
            return self._lib.GetPixel(self._handle, x, y)
        self._lib.SetPixel(self._handle, x, y, c)
        return None

    def line(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.Line(self._handle, x0, y0, x1, y1, c, int(blend))

    def hline(
        self,
        x: int,
        y: int,
        w: int,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.HLine(self._handle, x, y, w, c, int(blend))

    def vline(
        self,
        x: int,
        y: int,
        h: int,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.VLine(self._handle, x, y, h, c, int(blend))

    def rect(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.Rect(self._handle, x, y, w, h, c, int(blend))

    def fill_rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.FillRect(
            self._handle,
            float(x),
            float(y),
            float(w),
            float(h),
            int(c),
            int(blend),
        )

    def rounded_rect(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        r: int,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.RoundedRect(self._handle, x, y, w, h, r, c, int(blend))

    def fill_rounded_rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        r: float,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.FillRoundedRect(
            self._handle,
            float(x),
            float(y),
            float(w),
            float(h),
            float(r),
            int(c),
            int(blend),
        )

    def circle(
        self,
        cx: int,
        cy: int,
        r: int,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.Circle(self._handle, cx, cy, r, c, int(blend))

    def fill_circle(
        self,
        cx: float,
        cy: float,
        r: float,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.FillCircle(
            self._handle,
            float(cx),
            float(cy),
            float(r),
            int(c),
            int(blend),
        )

    def ellipse(
        self,
        cx: int,
        cy: int,
        rx: int,
        ry: int,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.Ellipse(self._handle, cx, cy, rx, ry, c, int(blend))

    def fill_ellipse(
        self,
        cx: float,
        cy: float,
        rx: float,
        ry: float,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.FillEllipse(
            self._handle,
            float(cx),
            float(cy),
            float(rx),
            float(ry),
            int(c),
            int(blend),
        )

    def ellipse_arc(
        self,
        cx: int,
        cy: int,
        rx: int,
        ry: int,
        startAngle: float,
        endAngle: float,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.EllipseArc(
            self._handle,
            cx,
            cy,
            rx,
            ry,
            startAngle,
            endAngle,
            c,
            int(blend),
        )

    # ============= Text =============

    def text(
        self,
        s: str,
        x: int,
        y: int,
        c: int = 0,
        size: float = 0.0,
        font_id: int = 0,
        anchor: TextAnchor = TextAnchor.LEFT | TextAnchor.TOP,
        spacing: float = 0.0,
    ) -> None:
        ret = self._lib.DrawText(
            self._handle,
            font_id,
            ctypes.c_float(size),
            s.encode("utf-8"),
            x,
            y,
            anchor,
            c,
            ctypes.c_float(spacing),
        )
        if ret == -1:
            raise ValueError("Invalid framebuffer handle")
        if ret == -2:
            raise ValueError(f"Invalid font handle: {font_id}")

    @classmethod
    def measure_text(
        cls,
        s: str,
        size: float = 0.0,
        font_id: int = 0,
        spacing: float = 0.0,
    ) -> int:
        lib = cls._ensure_lib_loaded()
        ret = lib.MeasureText(
            font_id,
            ctypes.c_float(size),
            s.encode("utf-8"),
            ctypes.c_float(spacing),
        )
        if ret == -1:
            raise ValueError(f"Invalid font handle: {font_id}")
        return ret

    @classmethod
    def get_text_height(cls, size: float = 0.0, font_id: int = 0) -> int:
        lib = cls._ensure_lib_loaded()
        ret = lib.GetTextHeight(font_id, ctypes.c_float(size))
        if ret == -1:
            raise ValueError(f"Invalid font handle: {font_id}")
        return ret

    @classmethod
    def get_text_metrics(
        cls,
        size: float = 0.0,
        font_id: int = 0,
    ) -> tuple[int, int, int]:
        lib = cls._ensure_lib_loaded()
        ascent = ctypes.c_int()
        descent = ctypes.c_int()
        height = ctypes.c_int()
        ret = lib.GetTextMetrics(
            font_id,
            ctypes.c_float(size),
            ctypes.byref(ascent),
            ctypes.byref(descent),
            ctypes.byref(height),
        )
        if ret == -1:
            raise ValueError(f"Invalid font handle: {font_id}")
        return ascent.value, descent.value, height.value

    # ============= Misc =============

    def scroll(self, dx: int, dy: int) -> None:
        self._lib.Scroll(self._handle, dx, dy)

    @property
    def antialias(self) -> bool:
        return self._lib.GetAntiAlias(self._handle) != 0

    @antialias.setter
    def antialias(self, enabled: bool) -> None:
        self._lib.SetAntiAlias(self._handle, int(enabled))

    def blit(
        self,
        src_data,  # ctypes.POINTER(ctypes.c_ubyte)
        src_width: int,
        src_height: int,
        dst_x: int,
        dst_y: int,
        blend: bool = True,
    ) -> None:
        self._lib.BlitRGBA(
            self._handle,
            src_data,
            src_width,
            src_height,
            dst_x,
            dst_y,
            1 if blend else 0,
        )

    def blit_scaled(
        self,
        src_data,  # ctypes.POINTER(ctypes.c_ubyte)
        src_width: int,
        src_height: int,
        dst_x: int,
        dst_y: int,
        dst_width: int,
        dst_height: int,
        blend: bool = True,
    ) -> None:
        self._lib.BlitRGBAScaled(
            self._handle,
            src_data,
            src_width,
            src_height,
            dst_x,
            dst_y,
            dst_width,
            dst_height,
            1 if blend else 0,
        )

    def apply_yuv_compensation(self, x: int, y: int, w: int, h: int) -> None:
        """Aligns chroma of neighboring pixels for correct display on YUV422."""
        self._lib.ApplyYUV422Compensation(self._handle, x, y, w, h)

    def apply_yuv_compensation_full(self) -> None:
        """Apply compensation to the entire buffer."""
        self._lib.ApplyYUV422Compensation(self._handle, 0, 0, self._width, self._height)

    # ============= Stroke primitives =============

    def line_stroke(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        width: float,
        cap: LineCapStyle = LineCapStyle.BUTT,
        join: LineJoinStyle = LineJoinStyle.MITER,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.LineStroke(
            self._handle,
            float(x0),
            float(y0),
            float(x1),
            float(y1),
            float(width),
            int(cap),
            int(join),
            int(c),
            int(blend),
        )

    def ellipse_stroke(
        self,
        cx: float,
        cy: float,
        rx: float,
        ry: float,
        width: float,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.EllipseStroke(
            self._handle,
            float(cx),
            float(cy),
            float(rx),
            float(ry),
            float(width),
            int(c),
            int(blend),
        )

    def rect_stroke(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        width: float,
        join: LineJoinStyle = LineJoinStyle.MITER,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.RectStroke(
            self._handle,
            float(x),
            float(y),
            float(w),
            float(h),
            float(width),
            int(join),
            int(c),
            int(blend),
        )

    def stroke_rounded_rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        radius: float,
        bw: float,
        join: LineJoinStyle = LineJoinStyle.ROUND,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.StrokeRoundedRect(
            self._handle,
            float(x),
            float(y),
            float(w),
            float(h),
            float(radius),
            float(bw),
            int(join),
            int(c),
            int(blend),
        )

    def set_ctm(
        self,
        a: float,
        b: float,
        c: float,
        d: float,
        tx: float,
        ty: float,
    ) -> None:
        """Set the current transformation matrix.

        Parameters map to the standard 2D affine matrix (a, b, c, d, tx, ty)
        matching the CoreGraphics / Pythonista Transform convention.
        Call after concat_ctm or set_origin to sync Python state to Rust.
        """
        self._lib.SetCTM(
            self._handle,
            ctypes.c_float(a),
            ctypes.c_float(b),
            ctypes.c_float(c),
            ctypes.c_float(d),
            ctypes.c_float(tx),
            ctypes.c_float(ty),
        )

    # ============= GState =============

    def gstate_push(self) -> None:
        self._lib.GStatePush(self._handle)

    def gstate_pop(self) -> None:
        self._lib.GStatePop(self._handle)

    # ============= Path (handle-based) =============

    def path_fill(
        self,
        pid: int,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.PathFill(self._handle, int(pid), int(c), int(blend))

    def path_stroke(
        self,
        pid: int,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.PathStroke(self._handle, int(pid), int(c), int(blend))

    def path_add_clip(self, pid: int) -> None:
        self._lib.PathAddClip(self._handle, int(pid))

    @classmethod
    def create_path(cls) -> int:
        if lib := cls._ensure_lib_loaded():
            pid = lib.CreatePath()
            if pid > 0:
                return pid
        raise RuntimeError("Failed to create path")

    @classmethod
    def destroy_path(cls, pid: int) -> bool:
        if pid > 0:
            if lib := cls._ensure_lib_loaded():
                return lib.DestroyPath(pid) == 0
        return False

    @classmethod
    def path_rect(cls, x: float, y: float, w: float, h: float) -> int:
        if lib := cls._ensure_lib_loaded():
            pid = lib.PathRect(x, y, w, h)
            if pid > 0:
                return pid
        raise RuntimeError("Failed to create path")

    @classmethod
    def path_oval(cls, x: float, y: float, w: float, h: float) -> int:
        if lib := cls._ensure_lib_loaded():
            pid = lib.PathOval(x, y, w, h)
            if pid > 0:
                return pid
        raise RuntimeError("Failed to create path")

    @classmethod
    def path_rounded_rect(cls, x: float, y: float, w: float, h: float, r: float) -> int:
        if lib := cls._ensure_lib_loaded():
            pid = lib.PathRoundedRect(x, y, w, h, r)
            if pid > 0:
                return pid
        raise RuntimeError("Failed to create path")

    @classmethod
    def path_set_line_width(cls, pid: int, value: float) -> None:
        if pid > 0:
            if lib := cls._ensure_lib_loaded():
                lib.PathSetLineWidth(pid, ctypes.c_float(value))

    @classmethod
    def path_set_line_join_style(cls, pid: int, value: int) -> None:
        if pid > 0:
            if lib := cls._ensure_lib_loaded():
                lib.PathSetLineJoin(pid, value)

    @classmethod
    def path_set_line_cap_style(cls, pid: int, value: int) -> None:
        if pid > 0:
            if lib := cls._ensure_lib_loaded():
                lib.PathSetLineCap(pid, value)

    @classmethod
    def path_set_eo_fill_rule(cls, pid: int, value: bool) -> None:
        if pid > 0:
            if lib := cls._ensure_lib_loaded():
                lib.PathSetEoFillRule(pid, 1 if value else 0)

    @classmethod
    def path_move_to(cls, pid: int, x: float, y: float) -> None:
        if pid > 0:
            if lib := cls._ensure_lib_loaded():
                lib.PathMoveTo(pid, ctypes.c_float(x), ctypes.c_float(y))

    @classmethod
    def path_line_to(cls, pid: int, x: float, y: float) -> None:
        if pid > 0:
            if lib := cls._ensure_lib_loaded():
                lib.PathLineTo(pid, ctypes.c_float(x), ctypes.c_float(y))

    @classmethod
    def path_add_arc(
        cls,
        pid: int,
        cx: float,
        cy: float,
        r: float,
        start: float,
        end: float,
        clockwise: bool = True,
    ) -> None:
        if pid > 0:
            if lib := cls._ensure_lib_loaded():
                lib.PathAddArc(
                    pid,
                    ctypes.c_float(cx),
                    ctypes.c_float(cy),
                    ctypes.c_float(r),
                    ctypes.c_float(start),
                    ctypes.c_float(end),
                    ctypes.c_int(1 if clockwise else 0),
                )

    @classmethod
    def path_add_curve(
        cls,
        pid: int,
        end_x: float,
        end_y: float,
        cp1_x: float,
        cp1_y: float,
        cp2_x: float,
        cp2_y: float,
    ) -> None:
        if pid > 0:
            if lib := cls._ensure_lib_loaded():
                lib.PathAddCurve(
                    pid,
                    ctypes.c_float(cp1_x),
                    ctypes.c_float(cp1_y),
                    ctypes.c_float(cp2_x),
                    ctypes.c_float(cp2_y),
                    ctypes.c_float(end_x),
                    ctypes.c_float(end_y),
                )

    @classmethod
    def path_add_quad_curve(
        cls,
        pid: int,
        end_x: float,
        end_y: float,
        cp_x: float,
        cp_y: float,
    ) -> None:
        if pid > 0:
            if lib := cls._ensure_lib_loaded():
                lib.PathAddQuadCurve(
                    pid,
                    ctypes.c_float(cp_x),
                    ctypes.c_float(cp_y),
                    ctypes.c_float(end_x),
                    ctypes.c_float(end_y),
                )

    @classmethod
    def path_close(cls, pid: int) -> None:
        if pid > 0:
            lib = cls._ensure_lib_loaded()
            lib.PathClose(pid)

    @classmethod
    def path_append_path(cls, pid: int, other_pid: int) -> None:
        if pid > 0 and other_pid > 0:
            if lib := cls._ensure_lib_loaded():
                lib.PathAppend(pid, other_pid)

    @classmethod
    def path_set_line_dash(
        cls,
        pid: int,
        sequence: Sequence[float],
        phase: float = 0.0,
    ) -> None:
        if pid > 0:
            if lib := cls._ensure_lib_loaded():
                if not sequence:
                    lib.PathSetLineDash(pid, None, 0, ctypes.c_float(0.0))
                else:
                    arr = (ctypes.c_float * len(sequence))(*sequence)
                    lib.PathSetLineDash(pid, arr, len(sequence), ctypes.c_float(phase))

    @classmethod
    def path_hit_test(cls, pid: int, x: float, y: float) -> bool:
        if pid > 0:
            if lib := cls._ensure_lib_loaded():
                return lib.PathHitTest(pid, ctypes.c_float(x), ctypes.c_float(y)) != 0
        return False

    @classmethod
    def path_get_bounds(cls, pid: int) -> tuple[float, float, float, float]:
        if pid > 0:
            if lib := cls._ensure_lib_loaded():
                x = ctypes.c_float(0.0)
                y = ctypes.c_float(0.0)
                w = ctypes.c_float(0.0)
                h = ctypes.c_float(0.0)
                ret = lib.PathGetBounds(
                    pid,
                    ctypes.byref(x),
                    ctypes.byref(y),
                    ctypes.byref(w),
                    ctypes.byref(h),
                )
                if ret == 0:
                    return x.value, y.value, w.value, h.value
        # FIXME: maybe should return None or identity, now it masks an error
        return 0.0, 0.0, 0.0, 0.0

    # ============= DEBUG ONLY =============
    def draw_checkerboard(self, size: int = 8):
        self._lib.DrawCheckerBoard(self._handle, size)

    # ============= CORE GRAPHICS =============
    def draw_string_core_graphics(
        self,
        s: str,
        x: float,
        y: float,
        w: float,
        h: float,
        size: float = 17.0,
        c: int = 0,
        font_id: int = 0,
        alignment: int = 0,  # ALIGN_LEFT
        line_break_mode: int = 4,  # LB_TRUNCATE_TAIL
    ) -> None:
        """CoreGraphics-compatible text drawing.

        Args:
            s: text to draw
            x, y, w, h: rectangle coordinates
            size: font size in points
            c: color as 0xRRGGBBAA
            font_id: font handle ID
            alignment: text alignment
                (0=LEFT, 1=CENTER, 2=RIGHT, 3=JUSTIFIED, 4=NATURAL)
            line_break_mode: line break mode
                (0=WORD_WRAP, 1=CHAR_WRAP, 2=CLIP,
                3=TRUNCATE_HEAD, 4=TRUNCATE_TAIL, 5=TRUNCATE_MIDDLE)

        """
        if hasattr(self._lib, "DrawStringCoreGraphics"):
            self._lib.DrawStringCoreGraphics(
                self._handle,
                font_id,
                s.encode("utf-8"),
                ctypes.c_float(x),
                ctypes.c_float(y),
                ctypes.c_float(w),
                ctypes.c_float(h),
                ctypes.c_float(size),
                int(c),
                alignment,
                line_break_mode,
            )

    @classmethod
    def measure_string_core_graphics(
        cls,
        s: str,
        max_width: float,
        size: float = 17.0,
        font_id: int = 0,
        line_break_mode: int = 4,
    ) -> tuple[float, float]:
        """Measure text dimensions.

        Args:
            s: text to measure
            max_width: maximum width constraint (0 for unlimited)
            size: font size in points
            font_id: font handle ID
            line_break_mode: line break mode (0=WORD_WRAP, 1=CHAR_WRAP, 2=CLIP,
                            3=TRUNCATE_HEAD, 4=TRUNCATE_TAIL, 5=TRUNCATE_MIDDLE)

        Returns:
            (width, height) in pixels

        """
        lib = cls._ensure_lib_loaded()

        width = ctypes.c_float()
        height = ctypes.c_float()

        ret = lib.MeasureStringCoreGraphics(
            font_id,
            s.encode("utf-8"),
            ctypes.c_float(max_width),
            ctypes.c_float(size),
            line_break_mode,
            ctypes.byref(width),
            ctypes.byref(height),
        )

        if ret == -1:
            raise ValueError(f"Invalid font handle: {font_id}")

        return (width.value, height.value)

    # ============= Transform (handle-based) =============

    @classmethod
    def create_transform(
        cls,
        a: float,
        b: float,
        c: float,
        d: float,
        tx: float,
        ty: float,
    ) -> int:
        if lib := cls._ensure_lib_loaded():
            tid = lib.CreateTransform(
                ctypes.c_float(a),
                ctypes.c_float(b),
                ctypes.c_float(c),
                ctypes.c_float(d),
                ctypes.c_float(tx),
                ctypes.c_float(ty),
            )
            if tid > 0:
                return tid
        raise RuntimeError(f"Failed to create transform: [{a, b, c, d, tx, ty}]")

    @classmethod
    def destroy_transform(cls, tid: int) -> bool:
        if tid > 0:
            if lib := cls._ensure_lib_loaded():
                return lib.DestroyTransform(tid) == 0
        return False

    @classmethod
    def transform_get(cls, tid: int) -> tuple[float, float, float, float, float, float]:
        if tid > 0:
            if lib := cls._ensure_lib_loaded():
                a = ctypes.c_float()
                b = ctypes.c_float()
                c = ctypes.c_float()
                d = ctypes.c_float()
                tx = ctypes.c_float()
                ty = ctypes.c_float()
                ret = lib.TransformGet(
                    tid,
                    ctypes.byref(a),
                    ctypes.byref(b),
                    ctypes.byref(c),
                    ctypes.byref(d),
                    ctypes.byref(tx),
                    ctypes.byref(ty),
                )
                if ret == 0:
                    return a.value, b.value, c.value, d.value, tx.value, ty.value
        # FIXME: maybe should return None or identity, now it masks an error
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    @classmethod
    def transform_rotation(cls, rad: float) -> int:
        if lib := cls._ensure_lib_loaded():
            return lib.TransformRotation(ctypes.c_float(rad))
        return 0

    @classmethod
    def transform_scale(cls, sx: float, sy: float) -> int:
        if lib := cls._ensure_lib_loaded():
            return lib.TransformScale(ctypes.c_float(sx), ctypes.c_float(sy))
        return 0

    @classmethod
    def transform_translation(cls, tx: float, ty: float) -> int:
        if lib := cls._ensure_lib_loaded():
            return lib.TransformTranslation(ctypes.c_float(tx), ctypes.c_float(ty))
        return 0

    @classmethod
    def transform_concat(cls, tid_a: int, tid_b: int) -> int:
        lib = cls._ensure_lib_loaded()
        if tid_a > 0 and tid_b > 0:
            return lib.TransformConcat(tid_a, tid_b)
        return 0

    @classmethod
    def transform_invert(cls, tid: int) -> int:
        if lib := cls._ensure_lib_loaded():
            return lib.TransformInvert(tid)
        return 0
