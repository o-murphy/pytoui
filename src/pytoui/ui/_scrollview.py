from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pytoui.ui._types import Point, Size
from pytoui.ui._view import View

if TYPE_CHECKING:
    from pytoui.ui._types import _PointLike, _SizeLike


_ScrollIndicatorStyle = Literal["default", "white", "black"]

__all__ = ("ScrollView", "_ScrollIndicatorStyle")


class ScrollView(View):
    _final_ = True
    __slots__ = (
        "_always_bounce_horizontal",
        "_always_bounce_vertical",
        "_bounces",
        "_content_inset",
        "_content_offset",
        "_content_size",
        "_decelerating",
        "_delegate",
        "_directional_lock_enabled",
        "_dragging",
        "_indicator_style",
        "_paging_enabled",
        "_scroll_enabled",
        "_scroll_indicator_insets",
        "_shows_horizontal_scroll_indicator",
        "_shows_vertical_scroll_indicator",
        "_tracking",
    )

    def __init__(self):
        self._always_bounce_horizontal: bool = False
        self._always_bounce_vertical: bool = False
        self._bounces: bool = True
        self._content_inset: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
        self._content_offset: Point = Point(0.0, 0.0)
        self._content_size: Size = Size(0.0, 0.0)
        self._decelerating: bool = False
        self._delegate: Any | None = None
        self._directional_lock_enabled: bool = False
        self._dragging: bool = False
        self._indicator_style: _ScrollIndicatorStyle = "default"
        self._paging_enabled: bool = False
        self._scroll_enabled: bool = True
        self._scroll_indicator_insets: tuple[float, float, float, float] = (
            0.0,
            0.0,
            0.0,
            0.0,
        )
        self._shows_horizontal_scroll_indicator: bool = True
        self._shows_vertical_scroll_indicator: bool = True
        self._tracking: bool = False

    @property
    def always_bounce_horizontal(self) -> bool:
        """A boolean value that determines whether bouncing always occurs
        when vertical scrolling reaches the end of the content.
        If this attribute is set to True and bounces is True,
        vertical dragging is allowed even if the content is smaller
        than the bounds of the scroll view.
        The default value is False."""
        return self._always_bounce_horizontal

    @always_bounce_horizontal.setter
    def always_bounce_horizontal(self, value: bool):
        self._always_bounce_horizontal = bool(value)

    @property
    def always_bounce_vertical(self) -> bool:
        """A boolean value that determines whether bouncing always occurs
        when horizontal scrolling reaches the end of the content.
        If this attribute is set to True and bounces is True,
        horizontal dragging is allowed even if the content is smaller
        than the bounds of the scroll view.
        The default value is False."""
        return self._always_bounce_vertical

    @always_bounce_vertical.setter
    def always_bounce_vertical(self, value: bool):
        self._always_bounce_vertical = bool(value)

    @property
    def bounces(self) -> bool:
        """A boolean value that controls whether the scroll view bounces
        past the edge of content and back again."""
        return self._bounces

    @bounces.setter
    def bounces(self, value: bool):
        self._bounces = bool(value)

    @property
    def content_inset(self) -> tuple[float, float, float, float]:
        """The distance that the content view is inset from the enclosing scroll view,
        as a 4-tuple of (top, left, bottom right) insets."""
        return self._content_inset

    @content_inset.setter
    def content_inset(self, value: tuple[float, float, float, float]):
        self._content_inset = value

    @property
    def content_offset(self) -> Point:
        """The view’s scrolling position, as an offset from the top-left corner.
        This is represented as an (x, y) tuple."""
        return self._content_offset

    @content_offset.setter
    def content_offset(self, value: _PointLike):
        self._content_offset = Point(*value)

    @property
    def content_size(self) -> Size:
        """The size of the content (as a (width, height) tuple).
        This determines how far the view can scroll in each direction."""
        return self._content_size

    @content_size.setter
    def content_size(self, value: _SizeLike):
        self._content_size = Size(*value)

    @property
    def decelerating(self) -> bool:
        """(readonly) True if user isn’t dragging the content
        but scrolling is still occurring."""
        return self._decelerating

    @property
    def delegate(self) -> Any | None:
        """
        The delegate is an object that is notified about scrolling events that occur in
        the scroll view with the callback defined below.

        Please see About Actions and Delegates for more information
        about the concept of delegates in general.

        class MyScrollViewDelegate (object):
            def scrollview_did_scroll(self, scrollview):
                # You can use the content_offset attribute
                # to determine the current scroll position
                pass
        """
        return self._delegate

    @delegate.setter
    def delegate(self, value: Any | None):
        self._delegate = value

    @property
    def directional_lock_enabled(self) -> bool:
        """If this attribute is False, scrolling is permitted in both horizontal
        and vertical directions, otherwise, if the user begins dragging
        in one general direction (horizontally or vertically),
        the scroll view disables scrolling in the other direction.
        If the drag direction is diagonal, then scrolling will not be locked
        and the user can drag in any direction until the drag completes.
        The default value is False."""
        return self._directional_lock_enabled

    @directional_lock_enabled.setter
    def directional_lock_enabled(self, value: bool):
        self._directional_lock_enabled = bool(value)

    @property
    def dragging(self) -> bool:
        """(readonly) A boolean value that indicates
        whether the user has started scrolling the content."""
        return self._dragging

    @property
    def indicator_style(self) -> _ScrollIndicatorStyle:
        """The style of the scroll indicators ('default', 'white', or 'black')."""
        return self._indicator_style

    @indicator_style.setter
    def indicator_style(self, value: _ScrollIndicatorStyle):
        self._indicator_style = value

    @property
    def paging_enabled(self) -> bool:
        """If the value of this attribute is True,
        the scroll view stops on multiples of the scroll view’s bounds
        when the user scrolls.
        The default value is False."""
        return self._paging_enabled

    @paging_enabled.setter
    def paging_enabled(self, value: bool):
        self._paging_enabled = bool(value)

    @property
    def scroll_enabled(self) -> bool:
        """If the value of this attribute is True, scrolling is enabled,
        and if it is False, scrolling is disabled. The default is True."""
        return self._scroll_enabled

    @scroll_enabled.setter
    def scroll_enabled(self, value: bool):
        self._scroll_enabled = bool(value)

    @property
    def scroll_indicator_insets(self) -> tuple[float, float, float, float]:
        """
        The distance the scroll indicators are inset from the edges of the scroll view.
        The value is a 4-tuple (top, left, bottom, right), the default is (0, 0, 0, 0).
        """
        return self._scroll_indicator_insets

    @scroll_indicator_insets.setter
    def scroll_indicator_insets(self, value: tuple[float, float, float, float]):
        self._scroll_indicator_insets = value

    @property
    def shows_horizontal_scroll_indicator(self) -> bool:
        """A Boolean value that controls whether the vertical
        scroll indicator is visible."""
        return self._shows_horizontal_scroll_indicator

    @shows_horizontal_scroll_indicator.setter
    def shows_horizontal_scroll_indicator(self, value: bool):
        """A Boolean value that controls whether the horizontal
        scroll indicator is visible."""
        self._shows_horizontal_scroll_indicator = bool(value)

    @property
    def shows_vertical_scroll_indicator(self) -> bool:
        return self._shows_vertical_scroll_indicator

    @shows_vertical_scroll_indicator.setter
    def shows_vertical_scroll_indicator(self, value: bool):
        self._shows_vertical_scroll_indicator = bool(value)

    @property
    def tracking(self) -> bool:
        """(readonly) Whether the user has touched the content to initiate scrolling."""
        return self._tracking
