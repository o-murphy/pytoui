from __future__ import annotations
from typing import TYPE_CHECKING, Sequence, cast

import time
from uuid import uuid4
from threading import Event

from pytoui.ui._constants import (
    CONTENT_REDRAW,
    CONTENT_SCALE_TO_FILL,
    _UI_DISABLE_ANIMATIONS,
)
from pytoui.ui._types import _PresentOrientation, Rect, Point, Touch
from pytoui.ui._draw import (
    GState,
    Path,
    Transform,
    _screen_origin,
    _content_mode_transform,
    _record,
    fill_rect,
    parse_color,
    set_color,
    set_backend,
    _set_origin,
    set_alpha,
)

if TYPE_CHECKING:
    from pytoui.ui._types import (
        _ViewFlex,
        _RectLike,
        _RGBA,
        _PresentStyle,
        _ColorLike,
        _PointLike,
    )

__all__ = ("View",)


class View:
    __final__ = False

    __slots__ = (
        "_alpha",
        "_background_color",
        "_border_color",
        "_border_width",
        "_bounds",
        "_content_mode",
        "_corner_radius",
        "_flex",
        "_frame",
        "_hidden",
        "_name",
        "_subviews",
        "_superview",
        "_tint_color",
        "_transform",
        "_update_interval",
        "_on_screen",
        "_needs_display",
        "_close_event",
        "_presented",
        "_touch_enabled",
        "_multitouch_enabled",
        # NOT FOR PYTHONISTA
        "_last_update_t",
        "_content_draw_w",
        "_content_draw_h",
        "__animations_disabled",
    )

    _SYSTEM_TINT: _RGBA = (0.0, 0.478, 1.0, 1.0)

    def __init__(self):
        self._alpha: float = 1.0
        self._background_color: _RGBA | None = (0.0, 0.0, 0.0, 0.0)
        self._border_color: _RGBA | None = (0.0, 0.0, 0.0, 1.0)
        self._border_width: float = 0.0
        self._bounds: Rect = Rect(0.0, 0.0, 100.0, 100.0)
        self._content_mode: int = (
            CONTENT_REDRAW if type(self) is not View else CONTENT_SCALE_TO_FILL
        )
        self._corner_radius: float = 0.0
        self._flex: _ViewFlex = ""
        self._frame: Rect = Rect(0.0, 0.0, 100.0, 100.0)
        self._hidden: bool = False
        self._name: str = str(uuid4())
        self._subviews: list[View] = []
        self._superview: View | None = None
        self._tint_color: _RGBA | None = None
        self._transform: Transform | None = None
        self._update_interval: float = 0.0
        self._on_screen: bool = False
        self._needs_display: bool = True
        self._close_event: Event = Event()
        self._presented: bool = False
        self._touch_enabled: bool = True
        self._multitouch_enabled: bool = False

        self._last_update_t: float = 0.0
        self._content_draw_w: float = 0.0
        self._content_draw_h: float = 0.0

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        for base in cls.__bases__:
            if getattr(base, "__final__", False):
                raise TypeError(f"{base.__name__} cannot be subclassed")

        original_init = cls.__dict__.get("__init__")
        if original_init is not None:

            def wrapped_init(self, *args, __orig=original_init, **kwargs):
                View.__init__(self)
                __orig(self, *args, **kwargs)

            cls.__init__ = wrapped_init

    # ── properties ────────────────────────────────────────────────────────────

    @property
    def alpha(self) -> float:
        """The view's alpha value as a float in the range 0.0 to 1.0."""
        return self._alpha

    @alpha.setter
    def alpha(self, value: float):
        if _record(self, "alpha", self._alpha, value):
            return
        self._alpha = float(value)
        self.set_needs_display()

    @property
    def background_color(self) -> _RGBA | None:
        """The view's background color, defaults to None (transparent)."""
        return parse_color(self._background_color)

    @background_color.setter
    def background_color(self, value: _ColorLike):
        parsed = parse_color(value)
        if _record(self, "background_color", self._background_color, parsed):
            return
        self._background_color = parsed
        self.set_needs_display()

    # bg_color as alias
    bg_color = background_color

    @property
    def border_color(self) -> _RGBA | None:
        """The view's border color (only has effect if border_width > 0)."""
        return parse_color(self._border_color)

    @border_color.setter
    def border_color(self, value: _ColorLike):
        self._border_color = parse_color(value)
        self.set_needs_display()

    @property
    def border_width(self) -> float:
        """The view's border width, defaults to zero (no border)."""
        return self._border_width

    @border_width.setter
    def border_width(self, value: float):
        self._border_width = float(value)
        self.set_needs_display()

    @property
    def bounds(self) -> Rect:
        """The view's location and size in its own coordinate system."""
        return self._bounds

    @bounds.setter
    def bounds(self, value: _RectLike):
        new_bounds = Rect(*value)
        old_w, old_h = self._bounds.w, self._bounds.h
        self._bounds = new_bounds
        new_w, new_h = new_bounds.w, new_bounds.h
        if new_w != old_w or new_h != old_h:
            self._frame = Rect(self._frame.x, self._frame.y, new_w, new_h)
            self._apply_autoresizing(old_w, old_h)
            self.layout()
        self.set_needs_display()

    @property
    def center(self) -> Point:
        """The center of the view's frame as a Point."""
        return self._frame.center()

    @center.setter
    def center(self, value: _PointLike):
        cx, cy = value
        w, h = self._frame.w, self._frame.h
        self.frame = Rect(cx - w / 2, cy - h / 2, w, h)

    @property
    def x(self) -> float:
        """Shortcut for the x component of the view's frame."""
        return self._frame.x

    @x.setter
    def x(self, value: float):
        f = self._frame
        self.frame = Rect(value, f.y, f.w, f.h)

    @property
    def y(self) -> float:
        """Shortcut for the y component of the view's frame."""
        return self._frame.y

    @y.setter
    def y(self, value: float):
        f = self._frame
        self.frame = Rect(f.x, value, f.w, f.h)

    @property
    def width(self) -> float:
        """Shortcut for the width component of the view's frame."""
        return self._frame.w

    @width.setter
    def width(self, value: float):
        f = self._frame
        self.frame = Rect(f.x, f.y, value, f.h)

    @property
    def height(self) -> float:
        """Shortcut for the height component of the view's frame."""
        return self._frame.h

    @height.setter
    def height(self, value: float):
        f = self._frame
        self.frame = Rect(f.x, f.y, f.w, value)

    @property
    def content_mode(self) -> int:
        """Determines how a view lays out its content when its bounds change."""
        return self._content_mode

    @content_mode.setter
    def content_mode(self, value: int):
        self._content_mode = value
        self._content_draw_w = 0.0
        self._content_draw_h = 0.0
        self.set_needs_display()

    @property
    def corner_radius(self) -> float:
        """The view's corner radius."""
        return self._corner_radius

    @corner_radius.setter
    def corner_radius(self, value: float):
        self._corner_radius = float(value)
        self.set_needs_display()

    @property
    def flex(self) -> _ViewFlex:
        """The autoresizing behavior of the view."""
        return self._flex

    @flex.setter
    def flex(self, value: _ViewFlex):
        self._flex = value

    @property
    def frame(self) -> Rect:
        """The view's position and size in the coordinate system of its superview."""
        return self._frame

    @frame.setter
    def frame(self, value: _RectLike):
        new_frame = Rect(*value)
        if _record(self, "frame", self._frame, new_frame):
            return
        old_w, old_h = self._frame.w, self._frame.h
        self._frame = new_frame
        new_w, new_h = new_frame.w, new_frame.h
        if new_w != old_w or new_h != old_h:
            self._bounds = Rect(self._bounds.x, self._bounds.y, new_w, new_h)
            self._apply_autoresizing(old_w, old_h)
            self.layout()
        self.set_needs_display()

    @property
    def hidden(self) -> bool:
        """Determines if the view is hidden."""
        return self._hidden

    @hidden.setter
    def hidden(self, value: bool):
        self._hidden = value
        self.set_needs_display()

    @property
    def name(self) -> str:
        """A string that identifies the view."""
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def on_screen(self) -> bool:
        """(readonly) Whether the view is part of a view hierarchy currently on screen."""
        return self._on_screen

    @property
    def subviews(self) -> tuple[View, ...]:
        """(readonly) A tuple of the view's children."""
        return tuple(self._subviews)

    @property
    def superview(self) -> View | None:
        """(readonly) The view's parent view."""
        return self._superview

    @property
    def tint_color(self) -> _RGBA:
        """The view's tint color, inherited from superview if None."""
        v: View | None = self
        while v is not None:
            if v._tint_color is not None:
                return v._tint_color
            v = v._superview
        return self._SYSTEM_TINT

    @tint_color.setter
    def tint_color(self, value: _ColorLike):
        self._tint_color = parse_color(value)
        self.set_needs_display()

    @property
    def touch_enabled(self) -> bool:
        return self._touch_enabled

    @touch_enabled.setter
    def touch_enabled(self, value: bool):
        self._touch_enabled = value

    @property
    def multitouch_enabled(self) -> bool:
        """If True, the view receives all simultaneous touches. If False (default), only the first touch is tracked."""
        return self._multitouch_enabled

    @multitouch_enabled.setter
    def multitouch_enabled(self, value: bool):
        self._multitouch_enabled = bool(value)

    @property
    def transform(self) -> Transform | None:
        """The transform applied to the view relative to the center of its bounds."""
        return self._transform

    @transform.setter
    def transform(self, value: Transform):
        if _record(self, "transform", self._transform, value):
            return
        self._transform = value
        self.set_needs_display()

    @property
    def update_interval(self) -> float:
        """Interval between update() calls in seconds. 0 disables updates."""
        return self._update_interval

    @update_interval.setter
    def update_interval(self, value: float):
        self._update_interval = float(value)
        if value > 0.0:
            self._last_update_t = time.time()

    # ── subview management ────────────────────────────────────────────────────

    def __getitem__(self, name: str) -> View:
        for view in self._subviews:
            if view.name == name:
                return view
        raise KeyError(name)

    def add_subview(self, view: View):
        """Add another view as a child of this view."""
        if view._superview is self:
            return
        if view._superview is not None:
            view._superview.remove_subview(view)
        self._subviews.append(view)
        view._superview = self

    def remove_subview(self, view: View):
        """Remove a child view."""
        self._subviews.remove(view)
        view._superview = None

    def bring_to_front(self):
        """Show the view on top of its sibling views."""
        sv = self._superview
        if sv is None:
            return
        siblings = sv._subviews
        siblings.remove(self)
        siblings.append(self)

    def send_to_back(self):
        """Put the view behind its sibling views."""
        sv = self._superview
        if sv is None:
            return
        siblings = sv._subviews
        siblings.remove(self)
        siblings.insert(0, self)

    # ── layout ────────────────────────────────────────────────────────────────

    def _apply_autoresizing(self, old_w: float, old_h: float):
        """Resize subviews based on their flex flags after this view's size changed."""
        dw = self._bounds.w - old_w
        dh = self._bounds.h - old_h
        if dw == 0.0 and dh == 0.0:
            return
        for sv in self._subviews:
            flex = sv._flex
            if not flex:
                continue
            f = sv._frame
            h_flexible = sum(c in flex for c in "LWR")
            if h_flexible:
                share = dw / h_flexible
                x = f.x + (share if "L" in flex else 0.0)
                w = f.w + (share if "W" in flex else 0.0)
            else:
                x, w = f.x, f.w
            v_flexible = sum(c in flex for c in "THB")
            if v_flexible:
                share = dh / v_flexible
                y = f.y + (share if "T" in flex else 0.0)
                h = f.h + (share if "H" in flex else 0.0)
            else:
                y, h = f.y, f.h
            sv._frame = Rect(x, y, w, h)  # bypass setter to avoid recursion

    def set_needs_display(self):
        """Mark the view as needing to be redrawn."""
        self._needs_display = True

    def size_to_fit(self):
        """Resize to enclose all subviews."""
        if not self._subviews:
            return
        max_w = max(sv._frame.x + sv._frame.w for sv in self._subviews)
        max_h = max(sv._frame.y + sv._frame.h for sv in self._subviews)
        self.frame = Rect(self._frame.x, self._frame.y, max_w, max_h)

    # ── presentation ──────────────────────────────────────────────────────────

    def present(
        self,
        style: _PresentStyle = "sheet",
        animated: bool = True,
        popover_location: _PointLike | None = None,
        hide_title_bar: bool = False,
        title_bar_color: _ColorLike = None,
        title_color: _ColorLike = None,
        orientations: Sequence[_PresentOrientation] | None = None,
        hide_close_button: bool = False,
    ):
        """Present the view on screen."""
        if self._presented:
            raise RuntimeError("View is already presented")
        self._presented = True
        self._on_screen = True
        self._close_event.clear()
        self._needs_display = True

        from pytoui.ui._runtime import launch_runtime

        if animated and not _UI_DISABLE_ANIMATIONS:
            self._alpha = 0.0
            _ANIM_DUR = 0.25
            _start: list[float | None] = [None]

            def _render_frame(fb) -> None:
                t = time.time()
                if _start[0] is None:
                    _start[0] = t
                elapsed = t - cast(float, _start[0])
                animating = elapsed < _ANIM_DUR
                if animating:
                    p = elapsed / _ANIM_DUR
                    p = p * p * (3.0 - 2.0 * p)  # smoothstep
                    self._alpha = p
                elif self._alpha < 1.0:
                    self._alpha = 1.0
                set_backend(fb)
                self._render()
                set_backend(None)
                if animating:
                    self._needs_display = True  # after _render() so it's not cleared
        else:

            def _render_frame(fb) -> None:
                set_backend(fb)
                self._render()
                set_backend(None)

        launch_runtime(self, _render_frame)

    def close(self):
        """Close a view that was presented via View.present()."""
        if not self._presented:
            return
        self.will_close()
        self._on_screen = False
        self._presented = False
        self._close_event.set()

    def wait_modal(self):
        """Block until the view is dismissed."""
        if not self._on_screen:
            return
        self._close_event.wait()

    # ── rendering ─────────────────────────────────────────────────────────────

    def _render(self):
        self._needs_display = False
        if self._hidden:
            return

        ox, oy = _screen_origin(self)
        fw, fh = self._frame.w, self._frame.h
        cr = self._corner_radius

        with GState():
            _set_origin(ox, oy)
            set_alpha(self._alpha)

            bg = self._background_color
            if bg and bg[3] > 0:
                set_color(bg)
                if cr > 0:
                    Path.rounded_rect(0, 0, fw, fh, cr).fill()
                else:
                    fill_rect(0, 0, fw, fh)

            if self._border_width > 0 and self._border_color is not None:
                set_color(self._border_color)
                p = (
                    Path.rounded_rect(0, 0, fw, fh, cr)
                    if cr > 0
                    else Path.rect(0, 0, fw, fh)
                )
                p.line_width = self._border_width
                p.stroke()

            cm = self._content_mode
            if cm == CONTENT_REDRAW:
                self.draw()
            else:
                cw = self._content_draw_w
                ch = self._content_draw_h
                if cw <= 0.0 or ch <= 0.0:
                    # First render — record the size draw() was called at
                    self._content_draw_w = fw
                    self._content_draw_h = fh
                    self.draw()
                else:
                    with GState():
                        _content_mode_transform(cm, cw, ch, fw, fh)
                        self.draw()

        for sv in self._subviews:
            sv._render()

    # ── overridable hooks ─────────────────────────────────────────────────────

    def did_load(self): ...
    def will_close(self): ...
    def draw(self): ...
    def layout(self): ...
    def update(self): ...
    def touch_began(self, touch: Touch): ...
    def touch_moved(self, touch: Touch): ...
    def touch_ended(self, touch: Touch): ...
    def keyboard_frame_will_change(self, frame): ...
    def keyboard_frame_did_change(self, frame): ...
    def _did_become_first_responder(self): ...
    def _did_resign_first_responder(self): ...

    def become_first_responder(self) -> bool:
        """Ask the owning window to make this view the first responder.

        Returns True if the runtime was found and the request was accepted,
        False if the view is not attached to any window.
        When this view becomes the first responder the previous one
        automatically loses it (resign is implicit, no public resign call).
        """
        from pytoui._base_runtime import _get_runtime_for_view

        rt = _get_runtime_for_view(self)
        if rt is None:
            return False
        rt._set_first_responder(self)
        return True
