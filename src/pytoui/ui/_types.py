from __future__ import annotations
from typing import Literal, Callable, Any, Union


__all__ = (
    "Rect",
    "_RectLike",
    "_PointLike",
    "_RGBA",
    "_RGB",
    "_HEX",
    "_ColorLike",
    "_Font",
    "_Action",
    "_SizeLike",
    "_TouchPhase",
    "_ViewFlex",
    "_PresentStyle",
    "_PresentOrientation",
    "Vector2",
    "Size",
    "Point",
    "Touch",
    "autoreleasepool",
)

_RGB = tuple[float, float, float]
_RGBA = tuple[float, float, float, float]
_HEX = str | int
_ColorLike = _RGB | _RGBA | _HEX | None

_Action = Callable[[Any], None] | Callable[[], None]

_Font = tuple[str, float]
_ViewFlex = Literal["", "W", "H", "L", "R", "T", "B"]
_TouchPhase = Literal["began", "ended", "moved", "stationary", "cancelled"]
_PresentStyle = Literal["full_screen", "sheet", "popover", "panel"]
_PresentOrientation = Literal[
    "portrait", "portrait-upside-down", "landscape", "landscape-left", "landscape-right"
]


# ── Vector2 ───────────────────────────────────────────────────────────────────


class Vector2:
    """Base class for 2D vectors with x and y components.

    Supports basic arithmetic and sequence protocol.
    """

    __slots__ = ("_x", "_y")

    _x: float
    _y: float

    def __init__(self, *args) -> None:
        if len(args) == 2:
            x, y = args
        elif len(args) == 1:
            x, y = args[0]
        else:
            raise TypeError(
                f"{type(self).__name__}() takes 1 or 2 arguments ({len(args)} given)"
            )
        object.__setattr__(self, "_x", float(x))
        object.__setattr__(self, "_y", float(y))

    def __setattr__(self, name, value):
        raise AttributeError(f"{type(self).__name__} is immutable")

    @property
    def x(self) -> float:
        return self._x

    @property
    def y(self) -> float:
        return self._y

    def __len__(self) -> int:
        return 2

    def __getitem__(self, index: int) -> float:
        return self.as_tuple()[index]

    def __iter__(self):
        return iter(self.as_tuple())

    def __eq__(self, other) -> bool:
        if isinstance(other, (Vector2, tuple, list)):
            try:
                ox, oy = other
                return self._x == float(ox) and self._y == float(oy)
            except (TypeError, ValueError):
                pass
        return NotImplemented

    def __add__(self, other) -> Vector2:
        ox, oy = other
        return type(self)(self._x + ox, self._y + oy)

    def __sub__(self, other) -> Vector2:
        ox, oy = other
        return type(self)(self._x - ox, self._y - oy)

    def __mul__(self, scalar: float) -> Vector2:
        return type(self)(self._x * scalar, self._y * scalar)

    def __rmul__(self, scalar: float) -> Vector2:
        return self.__mul__(scalar)

    def __neg__(self) -> Vector2:
        return type(self)(-self._x, -self._y)

    def __str__(self) -> str:
        return f"({self._x:g}, {self._y:g})"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._x:g}, {self._y:g})"

    def as_tuple(self) -> tuple[float, float]:
        """Return the vector as an (x, y) tuple."""
        return (self._x, self._y)


# ── Point ─────────────────────────────────────────────────────────────────────


class Point(Vector2):
    """A 2D point with x and y coordinates.

    Examples::

        Point(10, 20)
        Point((10, 20))
    """

    # def __add__(self, other) -> Point:
    #     """Return a new Point offset by other (Point or tuple)."""
    #     return super().__add__(other)


# ── Size ──────────────────────────────────────────────────────────────────────


class Size(Vector2):
    """A 2D size with width and height.

    x and y are aliases for width and height respectively.

    Examples::

        Size(100, 50)
        Size((100, 50))
    """

    # def __add__(self, other) -> "Size":
    #     """Return a new Size with added dimensions."""
    #     return super().__add__(other)

    @property
    def width(self) -> float:
        """Width (same as x)."""
        return self._x

    @property
    def w(self) -> float:
        """Alias for width."""
        return self._x

    @property
    def height(self) -> float:
        """Height (same as y)."""
        return self._y

    @property
    def h(self) -> float:
        """Alias for height."""
        return self._y


# ── helpers ───────────────────────────────────────────────────────────────────

_RectLike = Union["Rect", tuple[float, float, float, float], list[float]]
_PointLike = Point | tuple[float, float]
_SizeLike = Size | tuple[float, float]


def _coerce_rect(r: _RectLike) -> Rect:
    if isinstance(r, Rect):
        return r
    return Rect(*r)


# ── Rect ──────────────────────────────────────────────────────────────────────


class Rect:
    """A rectangle defined by origin (x, y) and size (width, height).

    Compatible with Pythonista's ui.Rect. Accepts positional arguments or
    a single tuple/sequence of 4 values.

    Examples::

        Rect(0, 0, 100, 50)
        Rect((0, 0, 100, 50))
        Rect(Point(0, 0), Size(100, 50))
    """

    __slots__ = ("_x", "_y", "_w", "_h")

    _x: float
    _y: float
    _w: float
    _h: float

    def __init__(self, *args) -> None:
        if len(args) == 4:
            x, y, w, h = args
        elif len(args) == 1:
            x, y, w, h = args[0]
        elif len(args) == 2:
            x, y = args[0]
            w, h = args[1]
        else:
            raise TypeError(f"Rect() takes 1, 2, or 4 arguments ({len(args)} given)")
        object.__setattr__(self, "_x", float(x))
        object.__setattr__(self, "_y", float(y))
        object.__setattr__(self, "_w", float(w))
        object.__setattr__(self, "_h", float(h))

    def __setattr__(self, name, value):
        raise AttributeError("Rect is immutable")

    # ── sequence protocol ─────────────────────────────────────────────────────

    def __len__(self) -> int:
        """Always 4: (x, y, width, height)."""
        return 4

    def __getitem__(self, index: int) -> float:
        """Return x, y, width, or height by index 0–3."""
        return self.as_tuple()[index]

    def __iter__(self):
        return iter(self.as_tuple())

    def __eq__(self, other) -> bool:
        if isinstance(other, (Rect, tuple, list)):
            return self.as_tuple() == _coerce_rect(other).as_tuple()
        return NotImplemented

    # ── representation ────────────────────────────────────────────────────────

    def __str__(self) -> str:
        return f"({self._x:g}, {self._y:g}, {self._w:g}, {self._h:g})"

    def __repr__(self) -> str:
        return f"Rect({self._x:g}, {self._y:g}, {self._w:g}, {self._h:g})"

    # ── scalar attributes ─────────────────────────────────────────────────────

    @property
    def x(self) -> float:
        """Left edge."""
        return self._x

    @property
    def y(self) -> float:
        """Top edge."""
        return self._y

    @property
    def width(self) -> float:
        """Width of the rectangle."""
        return self._w

    @property
    def w(self) -> float:
        """Alias for width."""
        return self._w

    @property
    def height(self) -> float:
        """Height of the rectangle."""
        return self._h

    @property
    def h(self) -> float:
        """Alias for height."""
        return self._h

    @property
    def min_x(self) -> float:
        """Left edge (same as x)."""
        return self._x

    @property
    def min_y(self) -> float:
        """Top edge (same as y)."""
        return self._y

    @property
    def max_x(self) -> float:
        """Right edge (x + width)."""
        return self._x + self._w

    @property
    def max_y(self) -> float:
        """Bottom edge (y + height)."""
        return self._y + self._h

    # ── Point/Size attributes ─────────────────────────────────────────────────

    @property
    def origin(self) -> Point:
        """Top-left corner as a Point."""
        return Point(self._x, self._y)

    @property
    def size(self) -> Size:
        """Size of the rectangle as a Size."""
        return Size(self._w, self._h)

    # ── methods ───────────────────────────────────────────────────────────────

    def as_tuple(self) -> tuple[float, float, float, float]:
        """Return the rectangle as a (x, y, width, height) tuple."""
        return (self._x, self._y, self._w, self._h)

    def center(self) -> Point:
        """Return the center point of the rectangle as a Point."""
        return Point(self._x + self._w / 2, self._y + self._h / 2)

    def contains_point(self, point: tuple[float, float]) -> bool:
        """Return True if the given (x, y) point lies within the rectangle."""
        px, py = point
        return self._x <= px <= self.max_x and self._y <= py <= self.max_y

    def contains_rect(self, rect: _RectLike) -> bool:
        """Return True if the given rectangle is entirely within this rectangle."""
        r = _coerce_rect(rect)
        return (
            self._x <= r._x
            and self._y <= r._y
            and self.max_x >= r.max_x
            and self.max_y >= r.max_y
        )

    def inset(self, dx: float, dy: float) -> Rect:
        """Return a new rectangle inset by dx horizontally and dy vertically."""
        return Rect(self._x + dx, self._y + dy, self._w - 2 * dx, self._h - 2 * dy)

    def intersection(self, rect: _RectLike) -> Rect:
        """Return the intersection of this rectangle and the given rectangle.

        Returns Rect(0, 0, 0, 0) if there is no intersection.
        """
        r = _coerce_rect(rect)
        x = max(self._x, r._x)
        y = max(self._y, r._y)
        max_x = min(self.max_x, r.max_x)
        max_y = min(self.max_y, r.max_y)
        if max_x < x or max_y < y:
            return Rect(0, 0, 0, 0)
        return Rect(x, y, max_x - x, max_y - y)

    def intersects(self, rect: _RectLike) -> bool:
        """Return True if this rectangle intersects the given rectangle."""
        r = _coerce_rect(rect)
        return (
            self._x < r.max_x
            and self.max_x > r._x
            and self._y < r.max_y
            and self.max_y > r._y
        )

    def min(self) -> Point:
        """Return the top-left corner as a Point."""
        return Point(self._x, self._y)

    def max(self) -> Point:
        """Return the bottom-right corner as a Point."""
        return Point(self.max_x, self.max_y)

    def translate(self, dx: float, dy: float) -> Rect:
        """Return a new rectangle shifted by (dx, dy)."""
        return Rect(self._x + dx, self._y + dy, self._w, self._h)

    def union(self, rect: _RectLike) -> Rect:
        """Return the smallest rectangle that contains both rectangles."""
        r = _coerce_rect(rect)
        x = min(self._x, r._x)
        y = min(self._y, r._y)
        max_x = max(self.max_x, r.max_x)
        max_y = max(self.max_y, r.max_y)
        return Rect(x, y, max_x - x, max_y - y)


class Touch:
    """The location of the touch (x, y as a 2-tuple) in the coordinate system of the View that the touch belongs to."""

    __slots__ = (
        "location",
        "phase",
        "prev_location",
        "timestamp",  # ms since 1970
        "touch_id",
    )

    def __init__(
        self,
        location: _PointLike,
        phase: _TouchPhase,
        prev_location: _PointLike,
        timestamp: int,
        touch_id: int,
    ):
        self.location = Point(*location)
        self.phase = phase
        self.prev_location = Point(*prev_location)
        self.timestamp = timestamp
        self.touch_id = touch_id


class autoreleasepool:
    """No-op stub for Pythonista compatibility. ObjC memory management is not needed."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


# ── Pythonista shim ────────────────────────────────────────────────────────────

from pytoui._platform import IS_PYTHONISTA  # noqa: E402

if IS_PYTHONISTA:
    from ui import (  # type: ignore[import-not-found,no-redef]
        Vector2,
        Point,
        Size,
        Rect,
        Touch,
    )
