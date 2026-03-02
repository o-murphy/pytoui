from __future__ import annotations

import time
from collections.abc import Sequence
from threading import Event
from typing import (
    TYPE_CHECKING,
    Callable,
    Generic,
    TypeVar,
    Union,
    cast,
    overload,
)
from uuid import uuid4

from pytoui._platform import _UI_DISABLE_ANIMATIONS, IS_PYTHONISTA
from pytoui.ui._constants import (
    CONTENT_REDRAW,
    CONTENT_SCALE_TO_FILL,
)
from pytoui.ui._draw import (
    GState,
    Path,
    Transform,
    _content_mode_transform,
    _record,
    _screen_origin,
    _set_origin,
    fill_rect,
    parse_color,
    set_alpha,
    set_backend,
    set_color,
)
from pytoui.ui._types import Rect, Size, _ColorLike, _PresentOrientation

if TYPE_CHECKING:
    from pytoui.ui._types import (
        _RGBA,
        MouseEvent,
        MouseWheel,
        Point,
        Touch,
        _PointLike,
        _PresentStyle,
        _RectLike,
        _ViewFlex,
    )

__all__ = ("View", "_getset_descriptor", "_View", "_ViewInternals")

__ClassT = TypeVar("__ClassT")
__PropT = TypeVar("__PropT")


class _getset_descriptor(Generic[__ClassT, __PropT]):
    def __init__(
        self,
        name: str,
        factory: Callable[[__ClassT], __PropT] | None = None,
        readonly: bool = True,
    ):
        self._public_name = name
        self._mangled_name: str = f"__{name}"
        self._factory = factory
        self._readonly: bool = readonly

    def __set_name__(self, owner: type[__ClassT], name: str):
        self._mangled_name = (
            f"_{owner.__name__.lstrip('_')}__{self._public_name.lstrip('_')}"
        )

    @overload
    def __get__(
        self, obj: None, objtype: type[__ClassT] | None = None
    ) -> _getset_descriptor[__ClassT, __PropT]: ...

    @overload
    def __get__(
        self, obj: __ClassT, objtype: type[__ClassT] | None = None
    ) -> __PropT: ...

    def __get__(
        self, obj: __ClassT | None, objtype: type[__ClassT] | None = None
    ) -> Union["_getset_descriptor"[__ClassT, __PropT], __PropT]:
        if obj is None:
            return self
        if not hasattr(obj, self._mangled_name):
            if self._factory is None:
                raise AttributeError(f"{self._public_name} not initialized")
            setattr(obj, self._mangled_name, self._factory(obj))
        return getattr(obj, self._mangled_name)

    def __set__(self, obj: __ClassT, value: __PropT):
        if self._readonly:
            raise AttributeError()
        setattr(obj, self._mangled_name, value)

    def __delete__(self, obj: __ClassT):
        raise AttributeError(f"Can't delete {self._public_name} attribute")


class _ViewInternals:
    SYSTEM_TINT: _RGBA = (0.0, 0.478, 1.0, 1.0)

    __slots__ = (
        # view ref
        "_ref",
        # attributes
        "_alpha",
        "_background_color",
        "_border_color",
        "_border_width",
        "_content_mode",
        "_corner_radius",
        "_flex",
        "_hidden",
        "_name",
        "_tint_color",
        "_transform",
        "_update_interval",
        "_touch_enabled",
        "_multitouch_enabled",
        "_frame",
        "_bounds",
        "_on_screen",
        "_subviews",
        "_superview",
        # pytoui attributes
        "_pytoui_presented",
        "_pytoui_needs_display",
        "_pytoui_last_update_time",
        "_pytoui_mouse_scroll_enabled",
        "_pytoui_close_event",
        "_pytoui_content_draw_size",
        # System-level overlay draw functions called after subviews.
        # Each entry is a zero-argument callable rendered in the current GState
        # (clipped to this view's bounds). Used by ScrollView for indicators.
        "_pytoui_system_subviews",
    )

    def __init__(self, view: _View):
        self._ref: _View = view
        self._alpha: float = 1.0
        self._background_color: _RGBA | None = (0.0, 0.0, 0.0, 0.0)
        self._border_color: _RGBA | None = (0.0, 0.0, 0.0, 1.0)
        self._border_width: float = 0.0
        self._bounds: Rect = Rect(0.0, 0.0, 100.0, 100.0)
        self._content_mode: int = CONTENT_SCALE_TO_FILL
        self._corner_radius: float = 0.0
        self._flex: _ViewFlex = ""
        self._frame: Rect = Rect(0.0, 0.0, 100.0, 100.0)
        self._hidden: bool = False
        self._name: str = str(uuid4())
        self._subviews: list[_ViewInternals] = []
        self._superview: _ViewInternals | None = None
        self._tint_color: _RGBA | None = None
        self._transform: Transform | None = None
        self._update_interval: float = 0.0
        self._on_screen: bool = False
        self._touch_enabled: bool = True
        self._multitouch_enabled: bool = False
        self._pytoui_mouse_scroll_enabled: bool = False

        # CUSTOM
        self._pytoui_presented: bool = False
        self._pytoui_needs_display: bool = True
        self._pytoui_last_update_time: float = 0.0

        # INTERNAL ONLY
        self._pytoui_close_event: Event = Event()
        self._pytoui_content_draw_size: Size = Size(0.0, 0.0)
        self._pytoui_system_subviews: list = []

    @property
    def ref(self) -> _View:
        # READONLY
        return self._ref

    @property
    def pytoui_presented(self) -> bool:
        # READONLY
        return self._pytoui_presented

    @property
    def pytoui_needs_display(self) -> bool:
        # READONLY
        return self._pytoui_needs_display

    @property
    def pytoui_last_update_time(self) -> float:
        return self._pytoui_last_update_time

    @pytoui_last_update_time.setter
    def pytoui_last_update_time(self, value: float):
        self._pytoui_last_update_time = float(value)

    @property
    def alpha(self) -> float:
        """The view's alpha value as a float in the range 0.0 to 1.0."""
        return self._alpha

    @alpha.setter
    def alpha(self, value: float):
        if _record(self, "alpha", self.alpha, value):
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
    def content_mode(self) -> int:
        """Determines how a view lays out its content when its bounds change."""
        return self._content_mode

    @content_mode.setter
    def content_mode(self, value: int):
        self._content_mode = value
        self._pytoui_content_draw_size = Size(0.0, 0.0)
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
        self.set_needs_display()

    autoresizing = flex

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
        """(readonly) Whether the view is part of
        a view hierarchy currently on screen."""
        return self._on_screen

    @property
    def subviews(self) -> list[_ViewInternals]:
        """(readonly) A tuple of the view's children."""
        return self._subviews

    @property
    def superview(self) -> _ViewInternals | None:
        """(readonly) The view's parent view."""
        sv = self._superview
        if sv is not None:
            return sv
        return None

    @property
    def touch_enabled(self) -> bool:
        return self._touch_enabled

    @touch_enabled.setter
    def touch_enabled(self, value: bool):
        self._touch_enabled = bool(value)

    @property
    def multitouch_enabled(self) -> bool:
        """If True, the view receives all simultaneous touches.
        If False (default), only the first touch is tracked."""
        return self._multitouch_enabled

    @multitouch_enabled.setter
    def multitouch_enabled(self, value: bool):
        self._multitouch_enabled = bool(value)

    @property
    def mouse_scroll_enabled(self) -> bool:
        """If False, the view ignores mouse wheel / scroll events."""
        return self._pytoui_mouse_scroll_enabled

    @mouse_scroll_enabled.setter
    def mouse_scroll_enabled(self, value: bool):
        self._pytoui_mouse_scroll_enabled = bool(value)

    @property
    def frame(self) -> Rect:
        """The view's position and size in the coordinate system of its superview."""
        return self._frame

    @frame.setter
    def frame(self, value: _RectLike):
        new_frame = Rect(*value)
        old_frame = self._frame
        if _record(self, "frame", old_frame, new_frame):
            return
        old_w, old_h = old_frame.size
        self._frame = new_frame
        new_w, new_h = new_frame.size
        if new_w != old_w or new_h != old_h:
            self._bounds = Rect(self._bounds.x, self._bounds.y, new_w, new_h)
            self._pytoui_content_draw_size = Size(0.0, 0.0)
            self.pytoui_apply_autoresizing(old_w, old_h)
            if hasattr(self._ref, "layout"):
                self._ref.layout()
        self.set_needs_display()

    @property
    def bounds(self) -> Rect:
        """The view's location and size in its own coordinate system."""
        return self._bounds

    @bounds.setter
    def bounds(self, value: _RectLike):
        new_bounds = Rect(*value)
        old_w, old_h = self._bounds.size
        self._bounds = new_bounds
        new_w, new_h = new_bounds.size
        if new_w != old_w or new_h != old_h:
            self._frame = Rect(self._frame.x, self._frame.y, new_w, new_h)
            self.pytoui_apply_autoresizing(old_w, old_h)
            if hasattr(self._ref, "layout"):
                self._ref.layout()
        self.set_needs_display()

    @property
    def tint_color(self) -> _RGBA:
        """The view's tint color, inherited from superview if None."""
        v: _ViewInternals | None = self
        while v is not None:
            if self._tint_color is not None:
                return self._tint_color
            if self._superview is not None:
                v = self._superview
        return self.SYSTEM_TINT

    @tint_color.setter
    def tint_color(self, value: _ColorLike):
        self._tint_color = parse_color(value)
        self.set_needs_display()

    @property
    def transform(self) -> Transform | None:
        """The transform applied to the view relative to the center of its bounds."""
        return self._transform

    @transform.setter
    def transform(self, value: Transform | None):
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
            self.pytoui_last_update_time = time.time()

    @property
    def pytoui_touch_began(self) -> Callable[[Touch], None] | None:
        return getattr(self._ref, "touch_began", None)

    @property
    def pytoui_touch_moved(self) -> Callable[[Touch], None] | None:
        return getattr(self._ref, "touch_moved", None)

    @property
    def pytoui_touch_ended(self) -> Callable[[Touch], None] | None:
        return getattr(self._ref, "touch_ended", None)

    @property
    def pytoui_mouse_down(self) -> Callable[[MouseEvent], None] | None:
        cb = getattr(self._ref, "mouse_down", None)
        if cb is None:
            return getattr(self._ref, "touch_began", None)
        return cb

    @property
    def pytoui_mouse_up(self) -> Callable[[MouseEvent], None] | None:
        cb = getattr(self._ref, "mouse_up", None)
        if cb is None:
            return getattr(self._ref, "touch_ended", None)
        return cb

    @property
    def pytoui_mouse_dragged(self) -> Callable[[MouseEvent], None] | None:
        cb = getattr(self._ref, "mouse_dragged", None)
        if cb is None:
            return getattr(self._ref, "touch_moved", None)
        return cb

    @property
    def pytoui_mouse_moved(self) -> Callable[[MouseEvent], None] | None:
        return getattr(self._ref, "mouse_moved", None)

    @property
    def pytoui_mouse_wheel(self) -> Callable[[MouseWheel], None] | None:
        return getattr(self._ref, "mouse_wheel", None)

    def pytoui_get_key_commands(self) -> list[dict]:
        fn = getattr(self._ref, "get_key_commands", None)
        if fn is None:
            return []
        return fn() or []

    @property
    def pytoui_key_command(self) -> Callable[[dict], None] | None:
        return getattr(self._ref, "key_command", None)

    def pytoui_did_become_first_responder(self): ...
    def pytoui_did_resign_first_responder(self): ...

    def pytoui_update(self):
        if hasattr(self._ref, "update"):
            self._ref.update()

    def pytoui_apply_autoresizing(self, old_w: float, old_h: float):
        """Resize subviews based on their flex flags after this view's size changed."""
        bw, bh = self._bounds.size
        dw = bw - old_w
        dh = bh - old_h
        if dw == 0.0 and dh == 0.0:
            return
        for sv in self._subviews:
            flex = sv._flex
            if not flex:
                continue
            f = sv.frame
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
            sv.frame = Rect(x, y, w, h)  # bypass setter to avoid recursion

    def pytoui_hit_test(self, x: float, y: float) -> _ViewInternals | None:
        """Recursively searches for the highest Z-index View
        that supports touch at the specified coordinates.
        """
        if self._hidden:
            return None
        ox, oy = _screen_origin(self._ref)
        fw, fh = self._frame.size
        if not (ox <= x < ox + fw and oy <= y < oy + fh):
            return None
        for child in reversed(self._subviews):
            target = child.pytoui_hit_test(x, y)
            if target is not None and target._touch_enabled:
                return target
        return self if self._touch_enabled else None

    def pytoui_scroll_hit_test(self, x: float, y: float) -> _ViewInternals | None:
        """Like pytoui_hit_test but filters by mouse_scroll_enabled.

        A view with scroll_enabled=False is transparent to scroll events
        (the event passes through to the parent), independently of touch_enabled.
        """
        if self._hidden:
            return None
        ox, oy = _screen_origin(self._ref)
        fw, fh = self._frame.size
        if not (ox <= x < ox + fw and oy <= y < oy + fh):
            return None
        for child in reversed(self._subviews):
            target = child.pytoui_scroll_hit_test(x, y)
            if target is not None and getattr(
                target, "_pytoui_mouse_scroll_enabled", False
            ):
                return target
        return self if getattr(self, "_pytoui_mouse_scroll_enabled", False) else None

    # ── rendering ─────────────────────────────────────────────────────────────

    def _clear_dirty_tree(self) -> None:
        """Recursively clear needs_display without rendering (used for culled views)."""
        self._pytoui_needs_display = False
        for sv in self._subviews:
            sv._clear_dirty_tree()

    def pytoui_render(self):
        self._pytoui_needs_display = False
        if self._hidden:
            return

        ox, oy = _screen_origin(self)
        fw, fh = self._frame.size
        if fw <= 0 or fh <= 0:
            return
        cr = self._corner_radius

        with GState():
            _set_origin(ox, oy)
            set_alpha(self._alpha)

            clip_path = (
                Path.rounded_rect(0, 0, fw, fh, cr)
                if cr > 0
                else Path.rect(0, 0, fw, fh)
            )
            clip_path.add_clip()

            bg = self._background_color
            if bg and bg[3] > 0:
                set_color(bg)
                if cr > 0:
                    clip_path.fill()
                else:
                    fill_rect(0, 0, fw, fh)

            if self._border_width > 0 and self._border_color is not None:
                set_color(self._border_color)
                p = clip_path if cr > 0 else Path.rect(0, 0, fw, fh)
                p.line_width = self._border_width
                p.stroke()

            cm = self._content_mode
            draw = getattr(self._ref, "draw", lambda: False)
            if cm == CONTENT_REDRAW:
                draw()
            else:
                cw, ch = self._pytoui_content_draw_size.as_tuple()
                if cw <= 0.0 or ch <= 0.0:
                    # First render — record the size draw() was called at
                    self._pytoui_content_draw_size = Size(fw, fh)
                    draw()
                else:
                    with GState():
                        _content_mode_transform(cm, cw, ch, fw, fh)
                        draw()

            bx, by = self._bounds.x, self._bounds.y
            for sv in self._subviews:
                sf = sv._frame
                if (
                    sf.x + sf.w <= bx
                    or sf.x >= bx + fw
                    or sf.y + sf.h <= by
                    or sf.y >= by + fh
                ):
                    sv._clear_dirty_tree()
                    continue
                sv.pytoui_render()

            # System subviews: drawn on top of all regular subviews,
            # within the same clip. Each entry is a zero-arg callable.
            for fn in self._pytoui_system_subviews:
                fn()

    def __getitem__(self, name: str) -> _ViewInternals:
        for view in self._subviews:
            if view._name == name:
                return view
        raise KeyError(name)

    def add_subview(self, view: _ViewInternals):
        """Add another view as a child of this view."""
        if view._superview is self._ref:
            return
        if view._superview is not None:
            view._superview.remove_subview(view)
        self._subviews.append(view)
        view._superview = self

    def remove_subview(self, view: _ViewInternals):
        """Remove a child view."""
        self._subviews.remove(view)
        view._superview = None

    def bring_to_front(self):
        """Show the view on top of its sibling views."""
        sv = self._superview
        if sv is None:
            return
        siblings = self._subviews
        siblings.remove(self)
        siblings.append(self)

    def send_to_back(self):
        """Put the view behind its sibling views."""
        sv = self._superview
        if sv is None:
            return
        siblings = self._subviews
        siblings.remove(self)
        siblings.insert(0, self)

    def set_needs_display(self):
        self._pytoui_needs_display = True

    def size_to_fit(self):
        """Resize to enclose all subviews."""
        if not self._subviews:
            return
        max_w = max(sv.frame.x + sv.frame.w for sv in self._subviews)
        max_h = max(sv.frame.y + sv.frame.h for sv in self._subviews)
        self.frame = Rect(self._frame.x, self._frame.y, max_w, max_h)

    def present(
        self,
        style: _PresentStyle = "default",
        animated: bool = True,
        popover_location: _PointLike | None = None,
        hide_title_bar: bool = False,
        title_bar_color: _ColorLike = None,
        title_color: _ColorLike = None,
        orientations: Sequence[_PresentOrientation] | None = None,
        hide_close_button: bool = False,
    ):
        """Present the view on screen."""
        if self._pytoui_presented:
            raise RuntimeError("View is already presented")
        self._pytoui_presented = True
        self._on_screen = True
        self._pytoui_close_event.clear()
        self._pytoui_needs_display = True

        from pytoui.ui._runtime import launch_runtime

        if animated and not _UI_DISABLE_ANIMATIONS:
            self._alpha = 0.0
            _ANIM_DUR = 0.25
            _start: list[float | None] = [None]

            def _render_frame(fb) -> None:
                t = time.time()
                if _start[0] is None:
                    _start[0] = t
                elapsed = t - cast("float", _start[0])
                animating = elapsed < _ANIM_DUR
                if animating:
                    p = elapsed / _ANIM_DUR
                    p = p * p * (3.0 - 2.0 * p)  # smoothstep
                    self._alpha = p
                elif self._alpha < 1.0:
                    self._alpha = 1.0
                set_backend(fb)
                self.pytoui_render()
                set_backend(None)
                if animating:
                    self._pytoui_needs_display = (
                        True  # after _render() so it's not cleared
                    )
        else:

            def _render_frame(fb) -> None:
                set_backend(fb)
                self.pytoui_render()
                set_backend(None)

        launch_runtime(self, _render_frame)

    def close(self):
        """Close a view that was presented via View.present()."""
        if not self._pytoui_presented:
            return
        if hasattr(self._ref, "will_close"):
            self.will_close()
        self._on_screen = False
        self._pytoui_presented = False
        self._pytoui_close_event.set()

    def wait_modal(self):
        """Block until the view is dismissed."""
        if not self._on_screen:
            return
        self._pytoui_close_event.wait()


class _View:
    __slots__ = ("__internals_",)

    _final_ = False
    _internals_: _getset_descriptor["_View", "_ViewInternals"] = _getset_descriptor(
        "internals_", factory=lambda obj: _ViewInternals(obj), readonly=True
    )

    # ── overridable hooks ─────────────────────────────────────────────────────

    did_load: Callable[[], None]
    will_close: Callable[[], None]
    layout: Callable[[], None]
    draw: Callable[[], None]
    touch_began: Callable[[Touch], None]
    touch_moved: Callable[[Touch], None]
    touch_ended: Callable[[Touch], None]
    keyboard_frame_will_change: Callable[[Rect], None]
    keyboard_frame_did_change: Callable[[Rect], None]

    # NOTE: View.update() is an implicit beahaviour
    update: Callable[[], None]

    # ── descriptor ────────────────────────────────────────────────────────────
    def __init__(self):
        pass

    # ── properties ────────────────────────────────────────────────────────────

    @property
    def alpha(self) -> float:
        """The view's alpha value as a float in the range 0.0 to 1.0."""
        return self._internals_.alpha

    @alpha.setter
    def alpha(self, value: float):
        self._internals_.alpha = value

    @property
    def background_color(self) -> _RGBA | None:
        """The view's background color, defaults to None (transparent)."""
        return self._internals_.background_color

    @background_color.setter
    def background_color(self, value: _ColorLike):
        self._internals_.background_color = value

    # bg_color as alias
    bg_color = background_color

    @property
    def border_color(self) -> _RGBA | None:
        """The view's border color (only has effect if border_width > 0)."""
        return self._internals_.border_color

    @border_color.setter
    def border_color(self, value: _ColorLike):
        self._internals_.border_color = value

    @property
    def border_width(self) -> float:
        """The view's border width, defaults to zero (no border)."""
        return self._internals_.border_width

    @border_width.setter
    def border_width(self, value: float):
        self._internals_.border_width = value

    @property
    def bounds(self) -> Rect:
        """The view's location and size in its own coordinate system."""
        return self._internals_.bounds

    @bounds.setter
    def bounds(self, value: _RectLike):
        self._internals_.bounds = value

    @property
    def center(self) -> Point:
        """The center of the view's frame as a Point."""
        return self._internals_.frame.center()

    @center.setter
    def center(self, value: _PointLike):
        cx, cy = value
        w, h = self._internals_.frame.size
        self.frame = Rect(cx - w / 2, cy - h / 2, w, h)

    @property
    def x(self) -> float:
        """Shortcut for the x component of the view's frame."""
        return self._internals_.frame.x

    @x.setter
    def x(self, value: float):
        f = self._internals_.frame
        self.frame = Rect(value, f.y, f.w, f.h)

    @property
    def y(self) -> float:
        """Shortcut for the y component of the view's frame."""
        return self._internals_.frame.y

    @y.setter
    def y(self, value: float):
        f = self._internals_.frame
        self.frame = Rect(f.x, value, f.w, f.h)

    @property
    def width(self) -> float:
        """Shortcut for the width component of the view's frame."""
        return self._internals_.frame.w

    @width.setter
    def width(self, value: float):
        f = self._internals_.frame
        self.frame = Rect(f.x, f.y, value, f.h)

    @property
    def height(self) -> float:
        """Shortcut for the height component of the view's frame."""
        return self._internals_.frame.h

    @height.setter
    def height(self, value: float):
        f = self._internals_.frame
        self.frame = Rect(f.x, f.y, f.w, value)

    @property
    def content_mode(self) -> int:
        """Determines how a view lays out its content when its bounds change."""
        return self._internals_.content_mode

    @content_mode.setter
    def content_mode(self, value: int):
        self._internals_.content_mode = value

    @property
    def corner_radius(self) -> float:
        """The view's corner radius."""
        return self._internals_.corner_radius

    @corner_radius.setter
    def corner_radius(self, value: float):
        self._internals_.corner_radius = value

    @property
    def flex(self) -> _ViewFlex:
        """The autoresizing behavior of the view."""
        return self._internals_.flex

    @flex.setter
    def flex(self, value: _ViewFlex):
        self._internals_.flex = value

    autoresizing = flex

    @property
    def frame(self) -> Rect:
        """The view's position and size in the coordinate system of its superview."""
        return self._internals_.frame

    @frame.setter
    def frame(self, value: _RectLike):
        self._internals_.frame = value

    @property
    def hidden(self) -> bool:
        """Determines if the view is hidden."""
        return self._internals_.hidden

    @hidden.setter
    def hidden(self, value: bool):
        self._internals_.hidden = value

    @property
    def name(self) -> str:
        """A string that identifies the view."""
        return self._internals_.name

    @name.setter
    def name(self, value: str):
        self._internals_.name = value

    @property
    def on_screen(self) -> bool:
        """(readonly) Whether the view is part of
        a view hierarchy currently on screen."""
        return self._internals_.on_screen

    @property
    def subviews(self) -> tuple[_View, ...]:
        """(readonly) A tuple of the view's children."""
        return tuple(sv.ref for sv in self._internals_.subviews)

    @property
    def superview(self) -> _View | None:
        """(readonly) The view's parent view."""
        sv = self._internals_.superview
        if sv is not None:
            return sv.ref
        return None

    @property
    def tint_color(self) -> _RGBA:
        """The view's tint color, inherited from superview if None."""
        return self._internals_.tint_color

    @tint_color.setter
    def tint_color(self, value: _ColorLike):
        self._internals_.tint_color = value

    @property
    def touch_enabled(self) -> bool:
        return self._internals_.touch_enabled

    @touch_enabled.setter
    def touch_enabled(self, value: bool):
        self._internals_.touch_enabled = value

    @property
    def multitouch_enabled(self) -> bool:
        """If True, the view receives all simultaneous touches.
        If False (default), only the first touch is tracked."""
        return self._internals_.multitouch_enabled

    @multitouch_enabled.setter
    def multitouch_enabled(self, value: bool):
        self._internals_.multitouch_enabled = value

    @property
    def mouse_scroll_enabled(self) -> bool:
        """Alias for scroll_enabled."""
        return self._internals_.mouse_scroll_enabled

    @mouse_scroll_enabled.setter
    def mouse_scroll_enabled(self, value: bool):
        self._internals_.mouse_scroll_enabled = value

    @property
    def transform(self) -> Transform | None:
        """The transform applied to the view relative to the center of its bounds."""
        return self._internals_.transform

    @transform.setter
    def transform(self, value: Transform | None):
        self._internals_.transform = value

    @property
    def update_interval(self) -> float:
        """Interval between update() calls in seconds. 0 disables updates."""
        return self._internals_.update_interval

    @update_interval.setter
    def update_interval(self, value: float):
        self._internals_.update_interval = value

    # ── subview management ────────────────────────────────────────────────────

    def __getitem__(self, name: str) -> _View:
        return self._internals_[name].ref

    def add_subview(self, view: _View):
        """Add another view as a child of this view."""
        self._internals_.add_subview(view._internals_)

    def remove_subview(self, view: _View):
        """Remove a child view."""
        self._internals_.remove_subview(view._internals_)

    def bring_to_front(self):
        """Show the view on top of its sibling views."""
        self._internals_.bring_to_front()

    def send_to_back(self):
        """Put the view behind its sibling views."""
        self._internals_.send_to_back()

    # ── layout ────────────────────────────────────────────────────────────────

    def set_needs_display(self):
        """Mark the view as needing to be redrawn."""
        self._internals_.set_needs_display()

    def size_to_fit(self):
        """Resize to enclose all subviews."""
        self._internals_.size_to_fit

    # ── presentation ──────────────────────────────────────────────────────────

    def present(
        self,
        style: _PresentStyle = "default",
        animated: bool = True,
        popover_location: _PointLike | None = None,
        hide_title_bar: bool = False,
        title_bar_color: _ColorLike = None,
        title_color: _ColorLike = None,
        orientations: Sequence[_PresentOrientation] | None = None,
        hide_close_button: bool = False,
    ):
        """Present the view on screen."""
        self._internals_.present(
            style,
            animated,
            popover_location,
            hide_title_bar,
            title_bar_color,
            title_color,
            orientations,
            hide_close_button,
        )

    def close(self):
        """Close a view that was presented via View.present()."""
        self._internals_.close()

    def wait_modal(self):
        """Block until the view is dismissed."""
        self._internals_.wait_modal()

    def become_first_responder(self) -> bool:
        """Ask the owning window to make this view the first responder.

        Returns True if the runtime was found and the request was accepted,
        False if the view is not attached to any window.
        When this view becomes the first responder the previous one
        automatically loses it (resign is implicit, no public resign call).
        """
        from pytoui._base_runtime import _get_runtime_for_view

        rt = _get_runtime_for_view(self._internals_)
        if rt is None:
            return False
        rt._set_first_responder(self._internals_)
        return True

    def get_key_commands(self) -> list[dict]:
        """Override to return hardware keyboard shortcuts for this view.

        Returns a list of dicts, each with:
          'input'     (required) – key string, e.g. 'a', KEY_INPUT_UP, KEY_INPUT_ESC
          'modifiers' (optional) – comma-separated modifier string, e.g. 'cmd,shift'
          'title'     (optional) – label shown in the keyboard shortcut HUD

        When the user presses a matching shortcut, key_command() is called
        with the matching dict as the sender argument.

        Example::

            def get_key_commands(self):
                return [
                    {"input": "n", "modifiers": "cmd", "title": "New"},
                    {"input": KEY_INPUT_ESC, "title": "Cancel"},
                ]
        """
        return []

    def key_command(self, sender: dict) -> None:
        """Called when a registered keyboard shortcut is triggered.

        sender – the dict returned by get_key_commands() that matched.
        """


if not IS_PYTHONISTA:
    View = _View
else:
    import ui  # type: ignore[import-not-found]

    View = ui.View  # type: ignore[assignment,misc]
