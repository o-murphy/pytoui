# osdbuf.py
import ctypes
from enum import IntEnum
from pathlib import Path
from typing import Protocol


_OSDBUF_PATH = str(Path(__file__).parent / "libosdbuf.so")


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


class _OsdBufLibFunc(Protocol):
    def __call__(self, *args) -> object: ...


class _OsdBufLib(ctypes.CDLL):
    CreateFrameBuffer: _OsdBufLibFunc
    DestroyFrameBuffer: _OsdBufLibFunc
    LoadFont: _OsdBufLibFunc
    UnloadFont: _OsdBufLibFunc
    GetDefaultFont: _OsdBufLibFunc
    GetFontCount: _OsdBufLibFunc
    GetFontIDs: _OsdBufLibFunc
    Fill: _OsdBufLibFunc
    FillOver: _OsdBufLibFunc
    SetPixel: _OsdBufLibFunc
    GetPixel: _OsdBufLibFunc
    CSetPixel: _OsdBufLibFunc
    CGetPixel: _OsdBufLibFunc
    BlitRGBA: _OsdBufLibFunc
    Scroll: _OsdBufLibFunc
    SetAntiAlias: _OsdBufLibFunc
    GetAntiAlias: _OsdBufLibFunc
    Line: _OsdBufLibFunc
    HLine: _OsdBufLibFunc
    VLine: _OsdBufLibFunc
    Rect: _OsdBufLibFunc
    FillRect: _OsdBufLibFunc
    FillRectOver: _OsdBufLibFunc
    RoundedRect: _OsdBufLibFunc
    FillRoundedRect: _OsdBufLibFunc
    FillRoundedRectOver: _OsdBufLibFunc
    Circle: _OsdBufLibFunc
    FillCircle: _OsdBufLibFunc
    Ellipse: _OsdBufLibFunc
    FillEllipse: _OsdBufLibFunc
    EllipseArc: _OsdBufLibFunc
    DrawText: _OsdBufLibFunc
    MeasureText: _OsdBufLibFunc
    GetTextHeight: _OsdBufLibFunc
    GetTextMetrics: _OsdBufLibFunc
    ApplyYUV422Compensation: _OsdBufLibFunc
    LineStroke: _OsdBufLibFunc
    RectStroke: _OsdBufLibFunc
    StrokeRoundedRect: _OsdBufLibFunc
    EllipseStroke: _OsdBufLibFunc
    FillPath: _OsdBufLibFunc
    StrokePath: _OsdBufLibFunc
    SetCTM: _OsdBufLibFunc
    # GState
    GStatePush: _OsdBufLibFunc
    GStatePop: _OsdBufLibFunc
    # Transform
    CreateTransform: _OsdBufLibFunc
    DestroyTransform: _OsdBufLibFunc
    TransformRotation: _OsdBufLibFunc
    TransformScale: _OsdBufLibFunc
    TransformTranslation: _OsdBufLibFunc
    TransformConcat: _OsdBufLibFunc
    TransformInvert: _OsdBufLibFunc
    TransformGet: _OsdBufLibFunc
    # Path
    CreatePath: _OsdBufLibFunc
    DestroyPath: _OsdBufLibFunc
    PathMoveTo: _OsdBufLibFunc
    PathLineTo: _OsdBufLibFunc
    PathAddCurve: _OsdBufLibFunc
    PathAddQuadCurve: _OsdBufLibFunc
    PathAddArc: _OsdBufLibFunc
    PathClose: _OsdBufLibFunc
    PathAppend: _OsdBufLibFunc
    PathRect: _OsdBufLibFunc
    PathOval: _OsdBufLibFunc
    PathRoundedRect: _OsdBufLibFunc
    PathSetLineWidth: _OsdBufLibFunc
    PathSetLineCap: _OsdBufLibFunc
    PathSetLineJoin: _OsdBufLibFunc
    PathSetLineDash: _OsdBufLibFunc
    PathFill: _OsdBufLibFunc
    PathStroke: _OsdBufLibFunc
    PathHitTest: _OsdBufLibFunc
    PathSetEoFillRule: _OsdBufLibFunc
    PathGetBounds: _OsdBufLibFunc
    PathAddClip: _OsdBufLibFunc
    # TESTING ONLY
    DrawCheckerBoard: _OsdBufLibFunc


class TextAnchor(IntEnum):
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

    _lib: _OsdBufLib = None

    @classmethod
    def _ensure_lib_loaded(cls, path: str = None) -> object:
        if cls._lib is None:
            target_path = str(path) if path else _OSDBUF_PATH
            print(f"DEBUG: Loading CDLL into class from {target_path}...", flush=True)
            handle = ctypes.CDLL(target_path)
            cls._setup_argtypes_static(handle)
            cls._lib = handle
        return cls._lib

    @staticmethod
    def _setup_argtypes_static(lib: _OsdBufLib) -> None:
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

        L.CSetPixel.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint32,
        ]
        L.CSetPixel.restype = None

        L.CGetPixel.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        L.CGetPixel.restype = ctypes.c_uint32

        # Blit / Scroll
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

        L.FillRectOver.argtypes = [
            ctypes.c_int,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_uint32,
            ctypes.c_uint8,
        ]
        L.FillRectOver.restype = None

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

        L.FillRoundedRectOver.argtypes = _frr_args
        L.FillRoundedRectOver.restype = None

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

        # StrokeRoundedRect (handle, x, y, w, h, radius, bw [f32], join [u8], color, blend)
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

        # FillPath (handle, data, len [i32], color, blend)
        L.FillPath.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_int,
            ctypes.c_uint32,
            ctypes.c_uint8,
        ]
        L.FillPath.restype = None

        # StrokePath (handle, data, len [i32], width [f32], cap, join [u8], color, blend)
        L.StrokePath.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_int,
            ctypes.c_float,
            ctypes.c_uint8,
            ctypes.c_uint8,
            ctypes.c_uint32,
            ctypes.c_uint8,
        ]
        L.StrokePath.restype = None

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
        L.DestroyTransform.restype = None
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
        L.DestroyPath.restype = None
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

    def __init__(self, osd_ptr, width, height, lib_path=_OSDBUF_PATH):
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
        if self._handle > 0:
            self.fill(0)
            self._lib.DestroyFrameBuffer(self._handle)
            self._handle = 0

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

    # ============= Font API (global, class-level) =============

    @classmethod
    def load_font(cls, font_path: str) -> int:
        """Load TTF/OTF font, returns font handle."""
        lib = cls._ensure_lib_loaded()
        fid = lib.LoadFont(font_path.encode("utf-8"))
        if fid <= 0:
            raise RuntimeError(f"Failed to load font: {font_path}")
        return fid

    @classmethod
    def unload_font(cls, font_id: int = 0) -> None:
        """Unload font by handle"""
        lib = cls._ensure_lib_loaded()
        ret = lib.UnloadFont(font_id)
        if ret == -1:
            raise ValueError(f"Invalid font handle: {font_id}")
        if ret == -2:
            raise ValueError("Cannot unload default font")

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

    def pixel(self, x: int, y: int, c: int | None = 0) -> int:
        """Absolute coordinates. c=None -> get, else set."""
        if c is None:
            return self._lib.GetPixel(self._handle, x, y)
        self._lib.SetPixel(self._handle, x, y, c)

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
        self, x: int, y: int, w: int, c: int = 0, blend: BlendMode = BlendMode.NORMAL
    ) -> None:
        self._lib.HLine(self._handle, x, y, w, c, int(blend))

    def vline(
        self, x: int, y: int, h: int, c: int = 0, blend: BlendMode = BlendMode.NORMAL
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
            self._handle, float(x), float(y), float(w), float(h), int(c), int(blend)
        )

    def fill_rect_over(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.FillRectOver(
            self._handle, float(x), float(y), float(w), float(h), int(c), int(blend)
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

    def fill_rounded_rect_over(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        r: float,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.FillRoundedRectOver(
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
        self, cx: int, cy: int, r: int, c: int = 0, blend: BlendMode = BlendMode.NORMAL
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
            self._handle, float(cx), float(cy), float(r), int(c), int(blend)
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
            self._handle, float(cx), float(cy), float(rx), float(ry), int(c), int(blend)
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
            self._handle, cx, cy, rx, ry, startAngle, endAngle, c, int(blend)
        )

    # ============= Center-relative variants =============

    def c_pixel(self, x: int, y: int, c: int | None = 0) -> int:
        """Center-relative coordinates. c=None -> get, else set."""
        if c is None:
            return self._lib.CGetPixel(self._handle, x, y)
        self._lib.CSetPixel(self._handle, x, y, c)

    def c_line(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.Line(
            self._handle,
            x0 + self._cx,
            y0 + self._cy,
            x1 + self._cx,
            y1 + self._cy,
            c,
            int(blend),
        )

    def c_hline(
        self, x: int, y: int, w: int, c: int = 0, blend: BlendMode = BlendMode.NORMAL
    ) -> None:
        self._lib.HLine(self._handle, x + self._cx, y + self._cy, w, c, int(blend))

    def c_vline(
        self, x: int, y: int, h: int, c: int = 0, blend: BlendMode = BlendMode.NORMAL
    ) -> None:
        self._lib.VLine(self._handle, x + self._cx, y + self._cy, h, c, int(blend))

    def c_rect(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.Rect(self._handle, x + self._cx, y + self._cy, w, h, c, int(blend))

    def c_fill_rect(
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
            float(x + self._cx),
            float(y + self._cy),
            float(w),
            float(h),
            int(c),
            int(blend),
        )

    def c_fill_rect_over(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.FillRectOver(
            self._handle,
            float(x + self._cx),
            float(y + self._cy),
            float(w),
            float(h),
            int(c),
            int(blend),
        )

    def c_circle(
        self, cx: int, cy: int, r: int, c: int = 0, blend: BlendMode = BlendMode.NORMAL
    ) -> None:
        self._lib.Circle(self._handle, cx + self._cx, cy + self._cy, r, c, int(blend))

    def c_fill_circle(
        self,
        cx: float,
        cy: float,
        r: float,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.FillCircle(
            self._handle,
            float(cx + self._cx),
            float(cy + self._cy),
            float(r),
            int(c),
            int(blend),
        )

    def c_ellipse(
        self,
        cx: int,
        cy: int,
        rx: int,
        ry: int,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        self._lib.Ellipse(
            self._handle, cx + self._cx, cy + self._cy, rx, ry, c, int(blend)
        )

    def c_fill_ellipse(
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
            float(cx + self._cx),
            float(cy + self._cy),
            float(rx),
            float(ry),
            int(c),
            int(blend),
        )

    def c_ellipse_arc(
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
            cx + self._cx,
            cy + self._cy,
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

    def c_text(
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
            x + self._cx,
            y + self._cy,
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
        cls, s: str, size: float = 0.0, font_id: int = 0, spacing: float = 0.0
    ) -> int:
        lib = cls._ensure_lib_loaded()
        ret = lib.MeasureText(
            font_id, ctypes.c_float(size), s.encode("utf-8"), ctypes.c_float(spacing)
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
        cls, size: float = 0.0, font_id: int = 0
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

    def fill_path(
        self,
        path_data: bytes,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        """Fill an arbitrary path encoded as a byte buffer (see _draw._encode_path_segments)."""
        if not path_data:
            return
        buf = (ctypes.c_uint8 * len(path_data)).from_buffer_copy(path_data)
        self._lib.FillPath(self._handle, buf, len(path_data), int(c), int(blend))

    def stroke_path(
        self,
        path_data: bytes,
        width: float = 1.0,
        cap: LineCapStyle = LineCapStyle.BUTT,
        join: LineJoinStyle = LineJoinStyle.MITER,
        c: int = 0,
        blend: BlendMode = BlendMode.NORMAL,
    ) -> None:
        """Stroke an arbitrary path encoded as a byte buffer (see _draw._encode_path_segments)."""
        if not path_data:
            return
        buf = (ctypes.c_uint8 * len(path_data)).from_buffer_copy(path_data)
        self._lib.StrokePath(
            self._handle,
            buf,
            len(path_data),
            float(width),
            int(cap),
            int(join),
            int(c),
            int(blend),
        )

    # ============= GState =============

    def gstate_push(self) -> None:
        self._lib.GStatePush(self._handle)

    def gstate_pop(self) -> None:
        self._lib.GStatePop(self._handle)

    # ============= Path (handle-based) =============

    def path_fill(
        self, path_handle: int, c: int = 0, blend: BlendMode = BlendMode.NORMAL
    ) -> None:
        self._lib.PathFill(self._handle, int(path_handle), int(c), int(blend))

    def path_stroke(
        self, path_handle: int, c: int = 0, blend: BlendMode = BlendMode.NORMAL
    ) -> None:
        self._lib.PathStroke(self._handle, int(path_handle), int(c), int(blend))

    def path_add_clip(self, path_handle: int) -> None:
        self._lib.PathAddClip(self._handle, int(path_handle))

    # ============= DEBUG ONLY =============
    def draw_checkerboard(self, size: int = 8):
        self._lib.DrawCheckerBoard(self._handle, size)
