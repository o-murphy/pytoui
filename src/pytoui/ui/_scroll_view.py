from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING, Protocol

from typing_extensions import override

from pytoui._platform import _UI_DISABLE_ANIMATIONS, IS_PYTHONISTA
from pytoui.ui._draw import Path, set_color
from pytoui.ui._internals import _final_, _getset_descriptor
from pytoui.ui._types import Point, Size
from pytoui.ui._view import _View, _ViewInternals

if TYPE_CHECKING:
    from pytoui.ui._types import (
        MouseWheel,
        Touch,
        _PointLike,
        _ScrollIndicatorStyle,
        _SizeLike,
    )

__all__ = ("ScrollView", "_ScrollView", "_ScrollViewDelegate", "_ScrollViewInternals")


class _ScrollViewDelegate(Protocol):
    def scrollview_did_scroll(self, scrollview: ScrollView):
        # You can use the content_offset attribute
        # to determine the current scroll position
        ...


class _ScrollViewInternals(_ViewInternals):
    __slots__ = (
        # Pythonista-compatible state
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
        # Internal drag/kinetics state
        "_vel_x",
        "_vel_y",
        "_locked_axis",
        "_drag_start_ox",
        "_drag_start_oy",
        "_drag_start_touch_x",
        "_drag_start_touch_y",
        "_last_touch_x",
        "_last_touch_y",
        "_last_touch_time",
        # Touch tracking: touch_id → original subview target
        "_tracked",
        # Flash indicator timer
        "_flash_until",
        # Paging debounce
        "_last_page_flip_time",
        # Paging slide animation
        "_page_anim_target",
        "_page_anim_start",
        "_page_anim_t0",
    )

    # Kinetic deceleration constants
    _DECEL_RATE: float = 0.95  # velocity multiplier per frame (≈60 fps)
    _MIN_VEL: float = 0.5  # px/frame threshold to stop deceleration
    _UPDATE_INTERVAL: float = 1.0 / 60.0
    _PAGE_ANIM_DUR: float = 0.30  # paging slide animation duration (seconds)

    def __init__(self, view: _ScrollView):
        super().__init__(view)
        # ── Pythonista-compatible defaults ────────────────────────────────────
        self._always_bounce_horizontal: bool = False
        self._always_bounce_vertical: bool = False
        self._bounces: bool = True
        self._content_inset: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
        self._content_offset: Point = Point(0.0, 0.0)
        self._content_size: Size = Size(0.0, 0.0)
        self._decelerating: bool = False
        self._delegate: _ScrollViewDelegate | None = None
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

        # ── Internal state ────────────────────────────────────────────────────
        self._vel_x: float = 0.0
        self._vel_y: float = 0.0
        self._locked_axis: str | None = None
        self._drag_start_ox: float = 0.0
        self._drag_start_oy: float = 0.0
        self._drag_start_touch_x: float = 0.0
        self._drag_start_touch_y: float = 0.0
        self._last_touch_x: float = 0.0
        self._last_touch_y: float = 0.0
        self._last_touch_time: float = 0.0
        self._tracked: dict = {}
        self._flash_until: float = 0.0
        self._last_page_flip_time: float = 0.0
        self._page_anim_target: tuple[float, float] | None = None
        self._page_anim_start: tuple[float, float] = (0.0, 0.0)
        self._page_anim_t0: float = 0.0

        self.pytoui_setUpdateInterval_(1 / 60)
        # ── pytoui setup (desktop only) ───────────────────────────────────────
        self.pytoui_setMouseWheelEnabled_(True)
        self._pytoui_isScrollContainer = True
        self._pytoui_drawOverlay = self._draw_scroll_indicators

    # ── Pythonista public API ──────────────────────────────────────────────────

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
        return self._always_bounce_vertical

    @always_bounce_vertical.setter
    def always_bounce_vertical(self, value: bool):
        self._always_bounce_vertical = bool(value)

    @property
    def bounces(self) -> bool:
        return self._bounces

    @bounces.setter
    def bounces(self, value: bool):
        self._bounces = bool(value)

    @property
    def content_inset(self) -> tuple[float, float, float, float]:
        return self._content_inset

    @content_inset.setter
    def content_inset(self, value: tuple[float, float, float, float]):
        self._content_inset = value

    @property
    def content_offset(self) -> Point:
        return self._content_offset

    @content_offset.setter
    def content_offset(self, value: _PointLike):
        self._set_offset(float(value[0]), float(value[1]), clamp=True)

    @property
    def content_size(self) -> Size:
        return self._content_size

    @content_size.setter
    def content_size(self, value: _SizeLike):
        self._content_size = Size(*value)
        self.setNeedsDisplay()

    @property
    def decelerating(self) -> bool:
        return self._decelerating

    @property
    def delegate(self) -> _ScrollViewDelegate | None:
        return self._delegate

    @delegate.setter
    def delegate(self, value: _ScrollViewDelegate | None):
        self._delegate = value

    @property
    def directional_lock_enabled(self) -> bool:
        return self._directional_lock_enabled

    @directional_lock_enabled.setter
    def directional_lock_enabled(self, value: bool):
        self._directional_lock_enabled = bool(value)

    @property
    def dragging(self) -> bool:
        return self._dragging

    @property
    def indicator_style(self) -> _ScrollIndicatorStyle:
        return self._indicator_style

    @indicator_style.setter
    def indicator_style(self, value: _ScrollIndicatorStyle):
        self._indicator_style = value

    @property
    def paging_enabled(self) -> bool:
        return self._paging_enabled

    @paging_enabled.setter
    def paging_enabled(self, value: bool):
        self._paging_enabled = bool(value)

    @property
    def scroll_enabled(self) -> bool:
        return self._scroll_enabled

    @scroll_enabled.setter
    def scroll_enabled(self, value: bool):
        self._scroll_enabled = bool(value)
        self.pytoui_setMouseWheelEnabled_(value)

    @override
    def pytoui_isMouseWheelEnabled(self) -> bool:
        return self._scroll_enabled and self._pytoui_isMouseWheelEnabled

    @override
    def pytoui_setMouseWheelEnabled_(self, value: bool):
        self._pytoui_isMouseWheelEnabled = bool(value) and self._scroll_enabled

    @property
    def scroll_indicator_insets(self) -> tuple[float, float, float, float]:
        return self._scroll_indicator_insets

    @scroll_indicator_insets.setter
    def scroll_indicator_insets(self, value: tuple[float, float, float, float]):
        self._scroll_indicator_insets = value

    @property
    def shows_horizontal_scroll_indicator(self) -> bool:
        return self._shows_horizontal_scroll_indicator

    @shows_horizontal_scroll_indicator.setter
    def shows_horizontal_scroll_indicator(self, value: bool):
        self._shows_horizontal_scroll_indicator = bool(value)

    @property
    def shows_vertical_scroll_indicator(self) -> bool:
        return self._shows_vertical_scroll_indicator

    @shows_vertical_scroll_indicator.setter
    def shows_vertical_scroll_indicator(self, value: bool):
        self._shows_vertical_scroll_indicator = bool(value)

    @property
    def tracking(self) -> bool:
        return self._tracking

    def _flash_scroll_indicators(self):
        """Briefly show the scroll indicators."""
        self._flash_until = time.monotonic() + 0.5
        if self.pytoui_updateInterval() <= 0:
            self.pytoui_setUpdateInterval_(self._UPDATE_INTERVAL)
        self.setNeedsDisplay()

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _min_offset(self) -> tuple[float, float]:
        inset_t, inset_l, _inset_b, _inset_r = self._content_inset
        return -inset_l, -inset_t

    def _max_offset(self) -> tuple[float, float]:
        inset_t, inset_l, inset_b, inset_r = self._content_inset
        fw, fh = self._frame.size
        cw, ch = self._content_size
        max_x = max(0.0, cw - fw + inset_r) - inset_l
        max_y = max(0.0, ch - fh + inset_b) - inset_t
        return max_x, max_y

    def _clamp_x(self, x: float) -> float:
        mn, _ = self._min_offset()
        mx, _ = self._max_offset()
        return max(mn, min(mx, x))

    def _clamp_y(self, y: float) -> float:
        _, mn = self._min_offset()
        _, mx = self._max_offset()
        return max(mn, min(mx, y))

    def _can_scroll_h(self) -> bool:
        if not self._scroll_enabled:
            return False
        mn, _ = self._min_offset()
        mx, _ = self._max_offset()
        return mx > mn or (self._bounces and self._always_bounce_horizontal)

    def _can_scroll_v(self) -> bool:
        if not self._scroll_enabled:
            return False
        _, mn = self._min_offset()
        _, mx = self._max_offset()
        return mx > mn or (self._bounces and self._always_bounce_vertical)

    def _set_offset(self, x: float, y: float, clamp: bool = True, notify: bool = True):
        """Update content_offset and sync bounds.origin (standard iOS mechanic)."""
        if clamp:
            x = self._clamp_x(x)
            y = self._clamp_y(y)
        self._content_offset = Point(x, y)
        # bounds.origin = content_offset: shifts the view's coordinate system
        # so _screen_origin correctly offsets all subviews.
        bw, bh = self.bounds().size
        self.setBounds_((x, y, bw, bh))
        self.needsDisplay()
        if notify:
            self._notify_delegate()

    def _notify_delegate(self):
        if self._delegate is not None:
            cb = getattr(self._delegate, "scrollview_did_scroll", None)
            if cb is not None:
                cb(self)

    # ── Desktop scroll (mouse wheel) ───────────────────────────────────────────

    def mouse_wheel(self, event: MouseWheel):
        if not self._scroll_enabled:
            return
        if self._paging_enabled:
            self._mouse_wheel_page(event)
            return
        ox, oy = self._content_offset
        new_x = ox - event.scroll_dx if self._can_scroll_h() else ox
        new_y = oy - event.scroll_dy if self._can_scroll_v() else oy
        self._set_offset(new_x, new_y)
        self._flash_scroll_indicators()

    def _mouse_wheel_page(self, event: MouseWheel):
        """Advance one page per wheel tick when paging_enabled."""
        now = time.monotonic()
        if now - self._last_page_flip_time < 0.35:
            return
        ox, oy = self._content_offset
        can_h = self._can_scroll_h()
        can_v = self._can_scroll_v()
        dx, dy = event.scroll_dx, event.scroll_dy
        if can_h and (not can_v or abs(dx) >= abs(dy)):
            fw = self._frame.width
            if fw <= 0:
                return
            cur = round(ox / fw)
            # dx>0 = "scroll right" (natural) = previous page (offset decreases)
            # when dx==0 (pure vertical wheel), use dy direction instead
            if dx != 0:
                step = -1 if dx > 0 else 1
            else:
                step = -1 if dy > 0 else 1
            self._start_page_anim((cur + step) * fw, oy)
        elif can_v:
            fh = self._frame.height
            if fh <= 0:
                return
            cur = round(oy / fh)
            # positive dy = scroll up = prev page
            step = -1 if dy > 0 else 1
            self._start_page_anim(ox, (cur + step) * fh)
        else:
            return
        self._last_page_flip_time = now

    # ── Touch drag scrolling ───────────────────────────────────────────────────

    def touch_began(self, touch: Touch):
        if not self._scroll_enabled:
            return
        # Cancel any running deceleration or page animation
        self._stop()

        self._tracking = True
        self._dragging = False
        self._locked_axis = None

        ox, oy = self._content_offset
        self._drag_start_ox = ox
        self._drag_start_oy = oy
        self._drag_start_touch_x = touch.location.x
        self._drag_start_touch_y = touch.location.y
        self._last_touch_x = touch.location.x
        self._last_touch_y = touch.location.y
        self._last_touch_time = touch.timestamp / 1000.0

    def touch_moved(self, touch: Touch):
        if not self._tracking:
            return

        tx = touch.location.x
        ty = touch.location.y
        now = touch.timestamp / 1000.0
        dt = now - self._last_touch_time

        # Drag delta from start (finger right → content scrolls left → offset increases)
        dx = self._drag_start_touch_x - tx
        dy = self._drag_start_touch_y - ty

        if not self._dragging:
            if abs(dx) > 3 or abs(dy) > 3:
                self._dragging = True
            else:
                return

        # Determine directional lock once
        if self._directional_lock_enabled and self._locked_axis is None:
            self._locked_axis = "x" if abs(dx) >= abs(dy) else "y"

        can_h = self._can_scroll_h()
        can_v = self._can_scroll_v()

        if self._locked_axis == "x":
            target_x = (self._drag_start_ox + dx) if can_h else self._drag_start_ox
            target_y = self._drag_start_oy
        elif self._locked_axis == "y":
            target_x = self._drag_start_ox
            target_y = (self._drag_start_oy + dy) if can_v else self._drag_start_oy
        else:
            target_x = (self._drag_start_ox + dx) if can_h else self._drag_start_ox
            target_y = (self._drag_start_oy + dy) if can_v else self._drag_start_oy

        # Track instantaneous velocity (px/sec, positive = finger moved right/down)
        if dt > 0.001:
            # negate: drag right → scroll left
            self._vel_x = -(tx - self._last_touch_x) / dt
            self._vel_y = -(ty - self._last_touch_y) / dt
        self._last_touch_x = tx
        self._last_touch_y = ty
        self._last_touch_time = now

        self._set_offset(target_x, target_y)

    def touch_ended(self, touch: Touch):
        if not self._tracking:
            return

        was_dragging = self._dragging
        self._tracking = False
        self._dragging = False

        if not was_dragging:
            return

        if self._paging_enabled:
            self._snap_to_page()
            self._flash_scroll_indicators()
            return

        # Start kinetic deceleration if there's meaningful velocity
        if abs(self._vel_x) > self._MIN_VEL or abs(self._vel_y) > self._MIN_VEL:
            self._decelerating = True
            self.pytoui_setUpdateInterval_(self._UPDATE_INTERVAL)
        else:
            self._vel_x = 0.0
            self._vel_y = 0.0
            self._flash_scroll_indicators()

    def _start_page_anim(self, tx: float, ty: float) -> None:
        """Smoothly slide content to page target (tx, ty)."""
        ox, oy = self._content_offset
        if _UI_DISABLE_ANIMATIONS or (ox == tx and oy == ty):
            self._set_offset(tx, ty)
            self._flash_scroll_indicators()
            return
        self._page_anim_start = (ox, oy)
        self._page_anim_target = (tx, ty)
        self._page_anim_t0 = time.monotonic()
        if self.pytoui_updateInterval() <= 0:
            self.pytoui_setUpdateInterval_(self._UPDATE_INTERVAL)

    def _snap_to_page(self):
        fw, fh = self.frame().size
        ox, oy = self._content_offset

        def nearest_page(offset: float, page_size: float, vel: float) -> float:
            if page_size <= 0:
                return offset
            page = offset / page_size
            if vel < -50:
                page = math.floor(page)
            elif vel > 50:
                page = math.ceil(page)
            else:
                page = round(page)
            return page * page_size

        new_x = nearest_page(ox, fw, self._vel_x) if self._can_scroll_h() else ox
        new_y = nearest_page(oy, fh, self._vel_y) if self._can_scroll_v() else oy
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._start_page_anim(new_x, new_y)

    def _stop(self) -> None:
        """Cancel any ongoing animation, deceleration or drag."""
        self._page_anim_target = None
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._decelerating = False
        self.pytoui_setUpdateInterval_(0.0)

    # ── Kinetic deceleration via update() ─────────────────────────────────────

    @override
    def pytoui_update(self):
        super().pytoui_update()
        now = time.monotonic()

        # Page animation has priority over deceleration
        if self._page_anim_target is not None:
            elapsed = now - self._page_anim_t0
            t = min(1.0, elapsed / self._PAGE_ANIM_DUR)
            e = 1.0 - (1.0 - t) ** 3  # cubic easeOut
            sx, sy = self._page_anim_start
            tx, ty = self._page_anim_target
            new_x = sx + (tx - sx) * e
            new_y = sy + (ty - sy) * e
            self._set_offset(new_x, new_y, notify=True)
            if t >= 1.0:
                self._page_anim_target = None
                self._flash_scroll_indicators()
            return  # don't run deceleration while page-animating

        if not self._decelerating:
            # Keep running while flash timer is active
            if self._flash_until > now:
                self.setNeedsDisplay()
            else:
                self.pytoui_setUpdateInterval_(0.0)
            return

        # Per-frame delta from velocity (px/sec → px/frame)
        dx = self._vel_x * self._UPDATE_INTERVAL
        dy = self._vel_y * self._UPDATE_INTERVAL

        ox, oy = self._content_offset
        new_x = (ox + dx) if self._can_scroll_h() else ox
        new_y = (oy + dy) if self._can_scroll_v() else oy

        # Apply friction
        self._vel_x *= self._DECEL_RATE
        self._vel_y *= self._DECEL_RATE

        self._set_offset(new_x, new_y)

        # Stop when slow and within bounds
        clamped_x = self._clamp_x(new_x)
        clamped_y = self._clamp_y(new_y)
        in_bounds = abs(new_x - clamped_x) < 0.5 and abs(new_y - clamped_y) < 0.5

        if (
            abs(self._vel_x) < self._MIN_VEL
            and abs(self._vel_y) < self._MIN_VEL
            and in_bounds
        ):
            self._vel_x = 0.0
            self._vel_y = 0.0
            self._decelerating = False
            # Keep update loop alive if flash is still active
            if self._flash_until <= now:
                self.pytoui_setUpdateInterval_(0.0)

    # ── Scroll indicators overlay ──────────────────────────────────────────────

    def _draw_scroll_indicators(self):
        """Draw scroll indicator bars on top of content."""
        fw, fh = self.frame().size
        now = time.monotonic()
        animating = self._page_anim_target is not None
        flashing = self._flash_until > now
        if not (self._dragging or self._decelerating or animating or flashing):
            return

        style = self._indicator_style
        if style == "white":
            color: tuple = (1.0, 1.0, 1.0, 0.7)
        elif style == "black":
            color = (0.0, 0.0, 0.0, 0.7)
        else:
            color = (0.0, 0.0, 0.0, 0.4)

        inset_t, inset_l, inset_b, inset_r = self._scroll_indicator_insets
        ox, oy = self._content_offset
        cw, ch = self._content_size

        BAR = 3.0
        MIN_LEN = 30.0
        MARGIN = 2.0

        show_v = self._shows_vertical_scroll_indicator and ch > fh
        show_h = self._shows_horizontal_scroll_indicator and cw > fw

        if show_v:
            avail_h = fh - inset_t - inset_b - MARGIN * 2
            if show_h:
                avail_h -= BAR + MARGIN
            bar_h = max(MIN_LEN, avail_h * fh / ch)
            travel = avail_h - bar_h
            t = max(0.0, min(1.0, oy / (ch - fh)))
            bar_y = inset_t + MARGIN + t * travel
            bar_x = fw - inset_r - BAR - MARGIN
            set_color(color)
            Path.rounded_rect(bar_x, bar_y, BAR, bar_h, BAR / 2).fill()

        if show_h:
            avail_w = fw - inset_l - inset_r - MARGIN * 2
            if show_v:
                avail_w -= BAR + MARGIN
            bar_w = max(MIN_LEN, avail_w * fw / cw)
            travel = avail_w - bar_w
            t = max(0.0, min(1.0, ox / (cw - fw)))
            bar_x = inset_l + MARGIN + t * travel
            bar_y = fh - inset_b - BAR - MARGIN
            set_color(color)
            Path.rounded_rect(bar_x, bar_y, bar_w, BAR, BAR / 2).fill()


class _ScrollView(_View):
    _internals_: _getset_descriptor["_ScrollView", "_ScrollViewInternals"] = (
        _getset_descriptor(
            "internals_",
            factory=lambda obj: _ScrollViewInternals(obj),
            readonly=True,
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def always_bounce_horizontal(self) -> bool:
        """A boolean value that determines whether bouncing always occurs
        when vertical scrolling reaches the end of the content.
        If this attribute is set to True and bounces is True,
        vertical dragging is allowed even if the content is smaller
        than the bounds of the scroll view.
        The default value is False."""
        return self._internals_.always_bounce_horizontal

    @always_bounce_horizontal.setter
    def always_bounce_horizontal(self, value: bool):
        self._internals_.always_bounce_horizontal = value

    @property
    def always_bounce_vertical(self) -> bool:
        """A boolean value that determines whether bouncing always occurs
        when horizontal scrolling reaches the end of the content.
        If this attribute is set to True and bounces is True,
        horizontal dragging is allowed even if the content is smaller
        than the bounds of the scroll view.
        The default value is False."""
        return self._internals_.always_bounce_vertical

    @always_bounce_vertical.setter
    def always_bounce_vertical(self, value: bool):
        self._internals_.always_bounce_vertical = value

    @property
    def bounces(self) -> bool:
        """A boolean value that controls whether the scroll view bounces
        past the edge of content and back again."""
        return self._internals_.bounces

    @bounces.setter
    def bounces(self, value: bool):
        self._internals_.bounces = value

    @property
    def content_inset(self) -> tuple[float, float, float, float]:
        """The distance that the content view is inset from the enclosing scroll view,
        as a 4-tuple of (top, left, bottom right) insets."""
        return self._internals_.content_inset

    @content_inset.setter
    def content_inset(self, value: tuple[float, float, float, float]):
        self._internals_.content_inset = value

    @property
    def content_offset(self) -> Point:
        """The view’s scrolling position, as an offset from the top-left corner.
        This is represented as an (x, y) tuple."""
        return self._internals_._content_offset

    @content_offset.setter
    def content_offset(self, value: _PointLike):
        self._internals_._set_offset(float(value[0]), float(value[1]), clamp=True)

    @property
    def content_size(self) -> Size:
        """The size of the content (as a (width, height) tuple).
        This determines how far the view can scroll in each direction."""
        return self._internals_.content_size

    @content_size.setter
    def content_size(self, value: _SizeLike):
        self._internals_.content_size = value

    @property
    def decelerating(self) -> bool:
        """(readonly) True if user isn’t dragging the content
        but scrolling is still occurring."""
        return self._internals_.decelerating

    @property
    def delegate(self) -> _ScrollViewDelegate | None:
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
        return self._internals_.delegate

    @delegate.setter
    def delegate(self, value: _ScrollViewDelegate | None):
        self._internals_.delegate = value

    @property
    def directional_lock_enabled(self) -> bool:
        """If this attribute is False, scrolling is permitted in both horizontal
        and vertical directions, otherwise, if the user begins dragging
        in one general direction (horizontally or vertically),
        the scroll view disables scrolling in the other direction.
        If the drag direction is diagonal, then scrolling will not be locked
        and the user can drag in any direction until the drag completes.
        The default value is False."""
        return self._internals_.directional_lock_enabled

    @directional_lock_enabled.setter
    def directional_lock_enabled(self, value: bool):
        self._internals_.directional_lock_enabled = value

    @property
    def dragging(self) -> bool:
        """(readonly) A boolean value that indicates
        whether the user has started scrolling the content."""
        return self._internals_.dragging

    @property
    def indicator_style(self) -> _ScrollIndicatorStyle:
        """The style of the scroll indicators ('default', 'white', or 'black')."""
        return self._internals_.indicator_style

    @indicator_style.setter
    def indicator_style(self, value: _ScrollIndicatorStyle):
        self._internals_.indicator_style = value

    @property
    def paging_enabled(self) -> bool:
        """If the value of this attribute is True,
        the scroll view stops on multiples of the scroll view’s bounds
        when the user scrolls.
        The default value is False."""
        return self._internals_.paging_enabled

    @paging_enabled.setter
    def paging_enabled(self, value: bool):
        self._internals_.paging_enabled = value

    @property
    def scroll_enabled(self) -> bool:
        """If the value of this attribute is True, scrolling is enabled,
        and if it is False, scrolling is disabled. The default is True."""
        return self._internals_.scroll_enabled

    @scroll_enabled.setter
    def scroll_enabled(self, value: bool):
        self._internals_.scroll_enabled = value

    @property
    def mouse_wheel_enabled(self) -> bool:
        """mouse_wheel_enabled is tied to scroll_enabled on ScrollView."""
        return self._internals_.pytoui_isMouseWheelEnabled()

    @mouse_wheel_enabled.setter
    def mouse_wheel_enabled(self, value: bool):
        self._internals_.pytoui_setMouseWheelEnabled_(value)

    @property
    def scroll_indicator_insets(self) -> tuple[float, float, float, float]:
        """
        The distance the scroll indicators are inset from the edges of the scroll view.
        The value is a 4-tuple (top, left, bottom, right), the default is (0, 0, 0, 0).
        """
        return self._internals_.scroll_indicator_insets

    @scroll_indicator_insets.setter
    def scroll_indicator_insets(self, value: tuple[float, float, float, float]):
        self._internals_.scroll_indicator_insets = value

    @property
    def shows_horizontal_scroll_indicator(self) -> bool:
        """A Boolean value that controls whether the vertical
        scroll indicator is visible."""
        return self._internals_.shows_horizontal_scroll_indicator

    @shows_horizontal_scroll_indicator.setter
    def shows_horizontal_scroll_indicator(self, value: bool):
        """A Boolean value that controls whether the horizontal
        scroll indicator is visible."""
        self._internals_.shows_horizontal_scroll_indicator = value

    @property
    def shows_vertical_scroll_indicator(self) -> bool:
        return self._internals_.shows_vertical_scroll_indicator

    @shows_vertical_scroll_indicator.setter
    def shows_vertical_scroll_indicator(self, value: bool):
        self._internals_.shows_vertical_scroll_indicator = value

    @property
    def tracking(self) -> bool:
        """(readonly) Whether the user has touched the content to initiate scrolling."""
        return self._internals_.tracking

    def touch_began(self, touch: Touch):
        self._internals_.touch_began(touch)

    def touch_moved(self, touch: Touch):
        self._internals_.touch_moved(touch)

    def touch_ended(self, touch: Touch):
        self._internals_.touch_ended(touch)

    def mouse_wheel(self, event: MouseWheel):
        self._internals_.mouse_wheel(event)


if not IS_PYTHONISTA:

    @_final_
    class ScrollView(_ScrollView):
        pass

else:
    import ui

    ScrollView = ui.ScrollView  # type: ignore[assignment,misc,no-redef]
