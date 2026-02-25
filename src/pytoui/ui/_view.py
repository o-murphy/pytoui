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

from pytoui._platform import _UI_DISABLE_ANIMATIONS, IS_PYTHONISTA, pytoui_desktop_only
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
        "ref",
        # attributes
        "alpha",
        "background_color",
        "bg_color",
        "border_color",
        "border_width",
        "content_mode",
        "corner_radius",
        "flex",
        "autoresizing",
        "hidden",
        "name",
        "tint_color",
        "transform",
        "update_interval",
        "touch_enabled",
        "multitouch_enabled",
        "frame",
        "bounds",
        "on_screen",
        "subviews",
        "superview",
        # pytoui internal attributes
        "pytoui_presented",
        "pytoui_close_event",
        "pytoui_needs_display",
        "pytoui_last_update_t",
        "pytoui_content_draw_size",
    )

    def __init__(self, view: _View):
        self.ref: _View = view
        self.alpha: float = 1.0
        self.background_color: _RGBA | None = (0.0, 0.0, 0.0, 0.0)
        self.border_color: _RGBA | None = (0.0, 0.0, 0.0, 1.0)
        self.border_width: float = 0.0
        self.bounds: Rect = Rect(0.0, 0.0, 100.0, 100.0)
        self.content_mode: int = CONTENT_SCALE_TO_FILL
        self.corner_radius: float = 0.0
        self.flex: _ViewFlex = ""
        self.frame: Rect = Rect(0.0, 0.0, 100.0, 100.0)
        self.hidden: bool = False
        self.name: str = str(uuid4())
        self.subviews: list[_ViewInternals] = []
        self.superview: _ViewInternals | None = None
        self.tint_color: _RGBA | None = None
        self.transform: Transform | None = None
        self.update_interval: float = 0.0
        self.on_screen: bool = False
        self.touch_enabled: bool = True
        self.multitouch_enabled: bool = False

        # CUSTOM
        self.pytoui_presented: bool = False
        self.pytoui_close_event: Event = Event()
        self.pytoui_needs_display: bool = True
        self.pytoui_last_update_t: float = 0.0
        self.pytoui_content_draw_size: Size = Size(0.0, 0.0)

    @property
    def pytoui_touch_began(self) -> Callable[[Touch], None] | None:
        return getattr(self.ref, "touch_began", None)

    @property
    def pytoui_touch_moved(self) -> Callable[[Touch], None] | None:
        return getattr(self.ref, "touch_moved", None)

    @property
    def pytoui_touch_ended(self) -> Callable[[Touch], None] | None:
        return getattr(self.ref, "touch_ended", None)

    def pytoui_did_become_first_responder(self): ...
    def pytoui_did_resign_first_responder(self): ...

    def pytoui_update(self):
        if hasattr(self.ref, "update"):
            self.ref.update()

    def pytoui_apply_autoresizing(self, old_w: float, old_h: float):
        """Resize subviews based on their flex flags after this view's size changed."""
        bw, bh = self.bounds.size
        dw = bw - old_w
        dh = bh - old_h
        if dw == 0.0 and dh == 0.0:
            return
        for sv in self.subviews:
            flex = sv.flex
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
        if self.hidden:
            return None
        ox, oy = _screen_origin(self.ref)
        fw, fh = self.frame.size
        if not (ox <= x < ox + fw and oy <= y < oy + fh):
            return None
        for child in reversed(self.subviews):
            target = child.pytoui_hit_test(x, y)
            if target is not None and target.touch_enabled:
                return target
        return self if self.touch_enabled else None

    # ── rendering ─────────────────────────────────────────────────────────────

    def pytoui_render(self):
        self.pytoui_needs_display = False
        if self.hidden:
            return

        ox, oy = _screen_origin(self)
        fw, fh = self.frame.size
        cr = self.corner_radius

        with GState():
            _set_origin(ox, oy)
            set_alpha(self.alpha)

            bg = self.background_color
            if bg and bg[3] > 0:
                set_color(bg)
                if cr > 0:
                    Path.rounded_rect(0, 0, fw, fh, cr).fill()
                else:
                    fill_rect(0, 0, fw, fh)

            if self.border_width > 0 and self.border_color is not None:
                set_color(self.border_color)
                p = (
                    Path.rounded_rect(0, 0, fw, fh, cr)
                    if cr > 0
                    else Path.rect(0, 0, fw, fh)
                )
                p.line_width = self.border_width
                p.stroke()

            cm = self.content_mode
            draw = getattr(self.ref, "draw", lambda: False)
            if cm == CONTENT_REDRAW:
                draw()
            else:
                cw, ch = self.pytoui_content_draw_size.as_tuple()
                if cw <= 0.0 or ch <= 0.0:
                    # First render — record the size draw() was called at
                    self.pytoui_content_draw_size = Size(fw, fh)
                    draw()
                else:
                    with GState():
                        _content_mode_transform(cm, cw, ch, fw, fh)
                        draw()

        for sv in self.subviews:
            sv.pytoui_render()

    def __getitem__(self, name: str) -> _ViewInternals:
        for view in self.subviews:
            if view.name == name:
                return view
        raise KeyError(name)

    def add_subview(self, view: _ViewInternals):
        """Add another view as a child of this view."""
        vst = view
        if vst.superview is self.ref:
            return
        if vst.superview is not None:
            vst.superview.remove_subview(view)
        self.subviews.append(view)
        vst.superview = self

    def remove_subview(self, view: _ViewInternals):
        """Remove a child view."""
        self.subviews.remove(view)
        view.superview = None

    def bring_to_front(self):
        """Show the view on top of its sibling views."""
        sv = self.superview
        if sv is None:
            return
        siblings = self.subviews
        siblings.remove(self)
        siblings.append(self)

    def send_to_back(self):
        """Put the view behind its sibling views."""
        sv = self.superview
        if sv is None:
            return
        siblings = self.subviews
        siblings.remove(self)
        siblings.insert(0, self)

    def set_need_display(self):
        self.pytoui_needs_display = True

    def size_to_fit(self):
        """Resize to enclose all subviews."""
        if not self.subviews:
            return
        max_w = max(sv.frame.x + sv.frame.w for sv in self.subviews)
        max_h = max(sv.frame.y + sv.frame.h for sv in self.subviews)
        self.frame = Rect(self.frame.x, self.frame.y, max_w, max_h)

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
        if self.pytoui_presented:
            raise RuntimeError("View is already presented")
        self.pytoui_presented = True
        self.on_screen = True
        self.pytoui_close_event.clear()
        self.pytoui_needs_display = True

        from pytoui.ui._runtime import launch_runtime

        if animated and not _UI_DISABLE_ANIMATIONS:
            self.alpha = 0.0
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
                    self.alpha = p
                elif self.alpha < 1.0:
                    self.alpha = 1.0
                set_backend(fb)
                self.pytoui_render()
                set_backend(None)
                if animating:
                    self.pytoui_needs_display = (
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
        if not self.pytoui_presented:
            return
        if hasattr(self.ref, "will_close"):
            self.will_close()
        self.on_screen = False
        self.pytoui_presented = False
        self.pytoui_close_event.set()

    def wait_modal(self):
        """Block until the view is dismissed."""
        if not self.on_screen:
            return
        self.pytoui_close_event.wait()


class _View:
    __slots__ = ("__internals_",)

    _final_ = False
    _internals_: _getset_descriptor["_View", "_ViewInternals"] = _getset_descriptor(
        "internals_", factory=lambda obj: _ViewInternals(obj), readonly=True
    )

    # ── overridable hooks ─────────────────────────────────────────────────────

    # did_load: Callable[[], None]
    # will_close: Callable[[], None]
    # layout: Callable[[], None]
    # draw: _Callable[[], None]
    # touch_began: Callable[[Touch], None]
    # touch_moved: Callable[[Touch], None]
    # touch_ended: Callable[[Touch], None]
    # keyboard_frame_will_change: Callable[[Rect], None]
    # keyboard_frame_did_change: Callable[[Rect], None]

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
        st = self._internals_
        if _record(self, "alpha", st.alpha, value):
            return
        st.alpha = float(value)
        self.set_needs_display()

    @property
    def background_color(self) -> _RGBA | None:
        """The view's background color, defaults to None (transparent)."""
        return parse_color(self._internals_.background_color)

    @background_color.setter
    def background_color(self, value: _ColorLike):
        parsed = parse_color(value)
        st = self._internals_
        if _record(self, "background_color", st.background_color, parsed):
            return
        st.background_color = parsed
        self.set_needs_display()

    # bg_color as alias
    bg_color = background_color

    @property
    def border_color(self) -> _RGBA | None:
        """The view's border color (only has effect if border_width > 0)."""
        return parse_color(self._internals_.border_color)

    @border_color.setter
    def border_color(self, value: _ColorLike):
        self._internals_.border_color = parse_color(value)
        self.set_needs_display()

    @property
    def border_width(self) -> float:
        """The view's border width, defaults to zero (no border)."""
        return self._internals_.border_width

    @border_width.setter
    def border_width(self, value: float):
        self._internals_.border_width = float(value)
        self.set_needs_display()

    @property
    def bounds(self) -> Rect:
        """The view's location and size in its own coordinate system."""
        return self._internals_.bounds

    @bounds.setter
    def bounds(self, value: _RectLike):
        new_bounds = Rect(*value)
        st = self._internals_
        old_w, old_h = st.bounds.size
        st.bounds = new_bounds
        new_w, new_h = new_bounds.size
        if new_w != old_w or new_h != old_h:
            st.frame = Rect(st.frame.x, st.frame.y, new_w, new_h)
            st.pytoui_apply_autoresizing(old_w, old_h)
            if hasattr(self, "layout"):
                self.layout()
        self.set_needs_display()

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
        st = self._internals_
        st.content_mode = value
        st.pytoui_content_draw_size = Size(0.0, 0.0)
        self.set_needs_display()

    @property
    def corner_radius(self) -> float:
        """The view's corner radius."""
        return self._internals_.corner_radius

    @corner_radius.setter
    def corner_radius(self, value: float):
        self._internals_.corner_radius = float(value)
        self.set_needs_display()

    @property
    def flex(self) -> _ViewFlex:
        """The autoresizing behavior of the view."""
        return self._internals_.flex

    @flex.setter
    def flex(self, value: _ViewFlex):
        self._internals_.flex = value
        self.set_needs_display()

    autoresizing = flex

    @property
    def frame(self) -> Rect:
        """The view's position and size in the coordinate system of its superview."""
        return self._internals_.frame

    @frame.setter
    def frame(self, value: _RectLike):
        new_frame = Rect(*value)
        st = self._internals_
        old_frame = st.frame
        if _record(self, "frame", old_frame, new_frame):
            return
        old_w, old_h = old_frame.size
        st.frame = new_frame
        new_w, new_h = new_frame.size
        if new_w != old_w or new_h != old_h:
            st.bounds = Rect(st.bounds.x, st.bounds.y, new_w, new_h)
            st.pytoui_apply_autoresizing(old_w, old_h)
            if hasattr(self, "layout"):
                self.layout()
        self.set_needs_display()

    @property
    def hidden(self) -> bool:
        """Determines if the view is hidden."""
        return self._internals_.hidden

    @hidden.setter
    def hidden(self, value: bool):
        self._internals_.hidden = value
        self.set_needs_display()

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
        v: _View | None = self
        while v is not None:
            st = v._internals_
            if st.tint_color is not None:
                return st.tint_color
            if st.superview is not None:
                v = st.superview.ref
        return st.SYSTEM_TINT

    @tint_color.setter
    def tint_color(self, value: _ColorLike):
        self._internals_.tint_color = parse_color(value)
        self.set_needs_display()

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
        self._internals_.multitouch_enabled = bool(value)

    @property
    def transform(self) -> Transform | None:
        """The transform applied to the view relative to the center of its bounds."""
        return self._internals_.transform

    @transform.setter
    def transform(self, value: Transform | None):
        st = self._internals_
        if _record(self, "transform", st.transform, value):
            return
        st.transform = value
        self.set_needs_display()

    @property
    def update_interval(self) -> float:
        """Interval between update() calls in seconds. 0 disables updates."""
        return self._internals_.update_interval

    @update_interval.setter
    def update_interval(self, value: float):
        st = self._internals_
        st.update_interval = float(value)
        if value > 0.0:
            st.pytoui_last_update_t = time.time()

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
        self._internals_.set_need_display()

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

    def update(self): ...


class View(_View):
    pass


if IS_PYTHONISTA:
    import ui  # type: ignore[import-not-found]

    class View(ui.View):  # type: ignore[no-redef]
        # Proxy to the native properties so that subclass
        # __init__ assignments (e.g. self.frame = Rect(...)) immediately update
        # the native frame and reads always reflect the current geometry.

        @property
        @pytoui_desktop_only
        def _internals(self) -> _ViewInternals:
            raise NotImplementedError

        @_internals.setter
        @pytoui_desktop_only
        def _internals(self, value: _ViewInternals):
            raise NotImplementedError


if __name__ == "__main__":
    v = View()
    print(v.__dict__)
