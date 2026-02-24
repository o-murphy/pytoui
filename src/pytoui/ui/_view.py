from __future__ import annotations
from typing import (
    TYPE_CHECKING,
    Generic,
    Sequence,
    Type,
    TypeVar,
    cast,
    overload,
)

import time
from uuid import uuid4
from threading import Event

from pytoui._platform import _UI_DISABLE_ANIMATIONS, IS_PYTHONISTA, pytoui_desktop_only
from pytoui.ui._constants import (
    CONTENT_REDRAW,
    CONTENT_SCALE_TO_FILL,
)
from pytoui.ui._types import (
    _PresentOrientation,
    Rect,
    Point,
    Size,
    _ColorLike,
)
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
        _PointLike,
    )

__all__ = ("View",)

__ClassT = TypeVar("__ClassT")
__PropT = TypeVar("__PropT")


class _getset_descriptor(Generic[__ClassT, __PropT]):
    def __init__(self, name: str):
        self._public_name = name
        self._mangled_name: str = f"__{name}"

    def __set_name__(self, owner: Type[__ClassT], name: str):
        self._mangled_name = f"_{owner.__name__.lstrip('_')}__{name.lstrip('_')}"

    @overload
    def __get__(
        self, obj: None, objtype: Type[__ClassT]
    ) -> _getset_descriptor[__ClassT, __PropT]: ...

    @overload
    def __get__(self, obj: __ClassT, objtype: Type[__ClassT]) -> __PropT: ...

    def __get__(
        self, obj: __ClassT | None, objtype: Type[__ClassT] | None = None
    ) -> __PropT:
        if obj is None:
            return self
        val = getattr(obj, self._mangled_name, None)
        if val is None:
            objtype_name = objtype.__name__ if objtype is not None else None
            raise AttributeError(
                f"State not initialized for {objtype_name}. "
                "Did you forget to call super().__new__ or use the metaclass?"
            )
        return val

    def __set__(self, obj: __ClassT, value: __PropT):
        setattr(obj, self._mangled_name, value)

    def __delete__(self, obj: __ClassT):
        raise AttributeError(f"Can't delete {self._public_name} attribute")


class _view_state:
    SYSTEM_TINT: _RGBA = (0.0, 0.478, 1.0, 1.0)

    __slots__ = (
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
        # pytoui
        "pytoui_presented",
        "pytoui_close_event",
        "pytoui_needs_display",
        "pytoui_last_update_t",
        "pytoui_content_draw_size",
        "pytoui_animations_disabled",
    )

    def __init__(self):
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
        self.subviews: list[_view] = []
        self.superview: _view | None = None
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
        self.pytoui_animations_disabled: bool = False


class _view_meta(type):
    def __new__(mcls, name, bases, namespace, **kwargs):
        for base in bases:
            if getattr(base, "__final__", False):
                raise TypeError(f"{base.__name__} cannot be subclassed")
        return super().__new__(mcls, name, bases, namespace, **kwargs)

    def __call__(cls, *args, **kwargs):
        instance = cls.__new__(cls, *args, **kwargs)

        if hasattr(cls, "_pytoui_st") and isinstance(instance, _view):
            state = _view_state()
            _view._pytoui_st.__set__(instance, state)

            state.content_mode = (
                CONTENT_REDRAW if cls is not _view else CONTENT_SCALE_TO_FILL
            )

        if isinstance(instance, cls):
            instance.__init__(*args, **kwargs)

        return instance


class _view(metaclass=_view_meta):
    __final__ = False

    __slots__ = ("__pytoui_st",)

    _pytoui_st: _getset_descriptor[_view, _view_state] = _getset_descriptor("pytoui_st")

    # ── descriptor ────────────────────────────────────────────────────────────
    def __init__(self):
        pass

    # ── properties ────────────────────────────────────────────────────────────

    @property
    def alpha(self) -> float:
        """The view's alpha value as a float in the range 0.0 to 1.0."""
        return self._pytoui_st.alpha

    @alpha.setter
    def alpha(self, value: float):
        st = self._pytoui_st
        if _record(self, "alpha", st.alpha, value):
            return
        st.alpha = float(value)
        self.set_needs_display()

    @property
    def background_color(self) -> _RGBA | None:
        """The view's background color, defaults to None (transparent)."""
        return parse_color(self._pytoui_st.background_color)

    @background_color.setter
    def background_color(self, value: _ColorLike):
        parsed = parse_color(value)
        st = self._pytoui_st
        if _record(self, "background_color", st.background_color, parsed):
            return
        st.background_color = parsed
        self.set_needs_display()

    # bg_color as alias
    bg_color = background_color

    @property
    def border_color(self) -> _RGBA | None:
        """The view's border color (only has effect if border_width > 0)."""
        return parse_color(self._pytoui_st.border_color)

    @border_color.setter
    def border_color(self, value: _ColorLike):
        self._pytoui_st.border_color = parse_color(value)
        self.set_needs_display()

    @property
    def border_width(self) -> float:
        """The view's border width, defaults to zero (no border)."""
        return self._pytoui_st.border_width

    @border_width.setter
    def border_width(self, value: float):
        self._pytoui_st.border_width = float(value)
        self.set_needs_display()

    @property
    def bounds(self) -> Rect:
        """The view's location and size in its own coordinate system."""
        return self._pytoui_st.bounds

    @bounds.setter
    def bounds(self, value: _RectLike):
        new_bounds = Rect(*value)
        st = self._pytoui_st
        old_w, old_h = st.bounds.size
        st.bounds = new_bounds
        new_w, new_h = new_bounds.size
        if new_w != old_w or new_h != old_h:
            st.frame = Rect(st.frame.x, st.frame.y, new_w, new_h)
            self._pytoui_apply_autoresizing(old_w, old_h)
            if hasattr(self, "layout"):
                self.layout()
        self.set_needs_display()

    @property
    def center(self) -> Point:
        """The center of the view's frame as a Point."""
        return self._pytoui_st.frame.center()

    @center.setter
    def center(self, value: _PointLike):
        cx, cy = value
        w, h = self._pytoui_st.frame.size
        self.frame = Rect(cx - w / 2, cy - h / 2, w, h)

    @property
    def x(self) -> float:
        """Shortcut for the x component of the view's frame."""
        return self._pytoui_st.frame.x

    @x.setter
    def x(self, value: float):
        f = self._pytoui_st.frame
        self.frame = Rect(value, f.y, f.w, f.h)

    @property
    def y(self) -> float:
        """Shortcut for the y component of the view's frame."""
        return self._pytoui_st.frame.y

    @y.setter
    def y(self, value: float):
        f = self._pytoui_st.frame
        self.frame = Rect(f.x, value, f.w, f.h)

    @property
    def width(self) -> float:
        """Shortcut for the width component of the view's frame."""
        return self._pytoui_st.frame.w

    @width.setter
    def width(self, value: float):
        f = self._pytoui_st.frame
        self.frame = Rect(f.x, f.y, value, f.h)

    @property
    def height(self) -> float:
        """Shortcut for the height component of the view's frame."""
        return self._pytoui_st.frame.h

    @height.setter
    def height(self, value: float):
        f = self._pytoui_st.frame
        self.frame = Rect(f.x, f.y, f.w, value)

    @property
    def content_mode(self) -> int:
        """Determines how a view lays out its content when its bounds change."""
        return self._pytoui_st.content_mode

    @content_mode.setter
    def content_mode(self, value: int):
        st = self._pytoui_st
        st.content_mode = value
        st.pytoui_content_draw_size = Size(0.0, 0.0)
        self.set_needs_display()

    @property
    def corner_radius(self) -> float:
        """The view's corner radius."""
        return self._pytoui_st.corner_radius

    @corner_radius.setter
    def corner_radius(self, value: float):
        self._pytoui_st.corner_radius = float(value)
        self.set_needs_display()

    @property
    def flex(self) -> _ViewFlex:
        """The autoresizing behavior of the view."""
        return self._pytoui_st.flex

    @flex.setter
    def flex(self, value: _ViewFlex):
        self._pytoui_st.flex = value
        self.set_needs_display()

    autoresizing = flex

    @property
    def frame(self) -> Rect:
        """The view's position and size in the coordinate system of its superview."""
        return self._pytoui_st.frame

    @frame.setter
    def frame(self, value: _RectLike):
        new_frame = Rect(*value)
        st = self._pytoui_st
        old_frame = st.frame
        if _record(self, "frame", old_frame, new_frame):
            return
        old_w, old_h = old_frame.size
        st.frame = new_frame
        new_w, new_h = new_frame.size
        if new_w != old_w or new_h != old_h:
            st.bounds = Rect(st.bounds.x, st.bounds.y, new_w, new_h)
            self._pytoui_apply_autoresizing(old_w, old_h)
            if hasattr(self, "layout"):
                self.layout()
        self.set_needs_display()

    @property
    def hidden(self) -> bool:
        """Determines if the view is hidden."""
        return self._pytoui_st.hidden

    @hidden.setter
    def hidden(self, value: bool):
        self._pytoui_st.hidden = value
        self.set_needs_display()

    @property
    def name(self) -> str:
        """A string that identifies the view."""
        return self._pytoui_st.name

    @name.setter
    def name(self, value: str):
        self._pytoui_st.name = value

    @property
    def on_screen(self) -> bool:
        """(readonly) Whether the view is part of a view hierarchy currently on screen."""
        return self._pytoui_st.on_screen

    @property
    def subviews(self) -> tuple[_view, ...]:
        """(readonly) A tuple of the view's children."""
        return tuple(self._pytoui_st.subviews)

    @property
    def superview(self) -> _view | None:
        """(readonly) The view's parent view."""
        return self._pytoui_st.superview

    @property
    def tint_color(self) -> _RGBA:
        """The view's tint color, inherited from superview if None."""
        v: _view | None = self
        while v is not None:
            st = v._pytoui_st
            if st.tint_color is not None:
                return st.tint_color
            v = st.superview
        return st.SYSTEM_TINT

    @tint_color.setter
    def tint_color(self, value: _ColorLike):
        self._pytoui_st.tint_color = parse_color(value)
        self.set_needs_display()

    @property
    def touch_enabled(self) -> bool:
        return self._pytoui_st.touch_enabled

    @touch_enabled.setter
    def touch_enabled(self, value: bool):
        self._pytoui_st.touch_enabled = value

    @property
    def multitouch_enabled(self) -> bool:
        """If True, the view receives all simultaneous touches. If False (default), only the first touch is tracked."""
        return self._pytoui_st.multitouch_enabled

    @multitouch_enabled.setter
    def multitouch_enabled(self, value: bool):
        self._pytoui_st.multitouch_enabled = bool(value)

    @property
    def transform(self) -> Transform | None:
        """The transform applied to the view relative to the center of its bounds."""
        return self._pytoui_st.transform

    @transform.setter
    def transform(self, value: Transform | None):
        st = self._pytoui_st
        if _record(self, "transform", st.transform, value):
            return
        st.transform = value
        self.set_needs_display()

    @property
    def update_interval(self) -> float:
        """Interval between update() calls in seconds. 0 disables updates."""
        return self._pytoui_st.update_interval

    @update_interval.setter
    def update_interval(self, value: float):
        st = self._pytoui_st
        st.update_interval = float(value)
        if value > 0.0:
            st.pytoui_last_update_t = time.time()

    # ── subview management ────────────────────────────────────────────────────

    def __getitem__(self, name: str) -> _view:
        for view in self._pytoui_st.subviews:
            if view.name == name:
                return view
        raise KeyError(name)

    def add_subview(self, view: _view):
        """Add another view as a child of this view."""
        vst = view._pytoui_st
        if vst.superview is self:
            return
        if vst.superview is not None:
            vst.superview.remove_subview(view)
        self._pytoui_st.subviews.append(view)
        vst.superview = self

    def remove_subview(self, view: _view):
        """Remove a child view."""
        self._pytoui_st.subviews.remove(view)
        view._pytoui_st.superview = None

    def bring_to_front(self):
        """Show the view on top of its sibling views."""
        st = self._pytoui_st
        sv = st.superview
        if sv is None:
            return
        siblings = st.subviews
        siblings.remove(self)
        siblings.append(self)

    def send_to_back(self):
        """Put the view behind its sibling views."""
        st = self._pytoui_st
        sv = st.superview
        if sv is None:
            return
        siblings = st.subviews
        siblings.remove(self)
        siblings.insert(0, self)

    # ── layout ────────────────────────────────────────────────────────────────

    def _pytoui_apply_autoresizing(self, old_w: float, old_h: float):
        """Resize subviews based on their flex flags after this view's size changed."""
        st = self._pytoui_st
        bw, bh = st.bounds.size
        dw = bw - old_w
        dh = bh - old_h
        if dw == 0.0 and dh == 0.0:
            return
        for sv in st.subviews:
            flex = sv._pytoui_st.flex
            if not flex:
                continue
            f = sv._pytoui_st.frame
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

    def set_needs_display(self):
        """Mark the view as needing to be redrawn."""
        self._pytoui_st.pytoui_needs_display = True

    def size_to_fit(self):
        """Resize to enclose all subviews."""
        st = self._pytoui_st
        if not st.subviews:
            return
        max_w = max(sv._pytoui_st.frame.x + sv._pytoui_st.frame.w for sv in st.subviews)
        max_h = max(sv._pytoui_st.frame.y + sv._pytoui_st.frame.h for sv in st.subviews)
        self.frame = Rect(st.frame.x, st.frame.y, max_w, max_h)

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
        st = self._pytoui_st
        if st.pytoui_presented:
            raise RuntimeError("View is already presented")
        st.pytoui_presented = True
        st.on_screen = True
        st.pytoui_close_event.clear()
        st.pytoui_needs_display = True

        from pytoui.ui._runtime import launch_runtime

        if animated and not _UI_DISABLE_ANIMATIONS:
            st.alpha = 0.0
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
                    st.alpha = p
                elif st.alpha < 1.0:
                    st.alpha = 1.0
                set_backend(fb)
                self._pytoui_render()
                set_backend(None)
                if animating:
                    st.pytoui_needs_display = (
                        True  # after _render() so it's not cleared
                    )
        else:

            def _render_frame(fb) -> None:
                set_backend(fb)
                self._pytoui_render()
                set_backend(None)

        launch_runtime(self, _render_frame)

    def close(self):
        """Close a view that was presented via View.present()."""
        st = self._pytoui_st
        if not st.pytoui_presented:
            return
        if hasattr(self, "will_close"):
            self.will_close()
        st.on_screen = False
        st.pytoui_presented = False
        st.pytoui_close_event.set()

    def wait_modal(self):
        """Block until the view is dismissed."""
        st = self._pytoui_st
        if not st.on_screen:
            return
        st.pytoui_close_event.wait()

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

    # ── overridable hooks ─────────────────────────────────────────────────────

    # def did_load(self): ...
    # def will_close(self): ...
    # def draw(self): ...
    # def layout(self): ...
    def update(self): ...

    # def touch_began(self, touch: Touch): ...
    # def touch_moved(self, touch: Touch): ...
    # def touch_ended(self, touch: Touch): ...
    # def keyboard_frame_will_change(self, frame): ...
    # def keyboard_frame_did_change(self, frame): ...

    # ── CUSOM INTERNALS ─────────────────────────────────────────────────────────────

    @property
    def _pytoui_animations_disabled(self) -> bool:
        return bool(
            self._pytoui_st.pytoui_animations_disabled or _UI_DISABLE_ANIMATIONS
        )

    @_pytoui_animations_disabled.setter
    def _pytoui_animations_disabled(self, value: bool):
        self._pytoui_st.pytoui_animations_disabled = value

    def _pytoui_hit_test(self, x: float, y: float) -> _view | None:
        """
        Recursively searches for the highest Z-index View
        that supports touch at the specified coordinates.
        """
        if self.hidden:
            return None
        ox, oy = _screen_origin(self)
        fw, fh = self.frame.size
        if not (ox <= x < ox + fw and oy <= y < oy + fh):
            return None
        for child in reversed(self.subviews):
            target = child._pytoui_hit_test(x, y)
            if target is not None and target.touch_enabled:
                return target
        return self if self.touch_enabled else None

    def _pytoui_did_become_first_responder(self): ...
    def _pytoui_did_resign_first_responder(self): ...

    # ── rendering ─────────────────────────────────────────────────────────────

    def _pytoui_render(self):
        st = self._pytoui_st
        st.pytoui_needs_display = False
        if st.hidden:
            return

        ox, oy = _screen_origin(self)
        fw, fh = st.frame.size
        cr = st.corner_radius

        with GState():
            _set_origin(ox, oy)
            set_alpha(st.alpha)

            bg = st.background_color
            if bg and bg[3] > 0:
                set_color(bg)
                if cr > 0:
                    Path.rounded_rect(0, 0, fw, fh, cr).fill()
                else:
                    fill_rect(0, 0, fw, fh)

            if st.border_width > 0 and st.border_color is not None:
                set_color(st.border_color)
                p = (
                    Path.rounded_rect(0, 0, fw, fh, cr)
                    if cr > 0
                    else Path.rect(0, 0, fw, fh)
                )
                p.line_width = st.border_width
                p.stroke()

            cm = st.content_mode
            draw = getattr(self, "draw", lambda: False)
            if cm == CONTENT_REDRAW:
                draw()
            else:
                cw, ch = st.pytoui_content_draw_size.as_tuple()
                if cw <= 0.0 or ch <= 0.0:
                    # First render — record the size draw() was called at
                    st.pytoui_content_draw_size = Size(fw, fh)
                    draw()
                else:
                    with GState():
                        _content_mode_transform(cm, cw, ch, fw, fh)
                        draw()

        for sv in st.subviews:
            sv._pytoui_render()


class View(_view):
    pass


if IS_PYTHONISTA:
    import ui  # type: ignore[import-not-found]  # noqa: F811

    class View(ui.View):  # type: ignore[no-redef]
        # Proxy to the native properties so that subclass
        # __init__ assignments (e.g. self.frame = Rect(...)) immediately update
        # the native frame and reads always reflect the current geometry.

        @property
        @pytoui_desktop_only
        def _pytoui_st(self) -> _view_state:
            raise NotImplementedError
        
        @_pytoui_st.setter
        @pytoui_desktop_only
        def _pytoui_st(self, value: _view_state):
            raise NotImplementedError

        @property
        def _pytoui_animations_disabled(self) -> bool:
            return False or _UI_DISABLE_ANIMATIONS

        @_pytoui_animations_disabled.setter
        def _pytoui_animations_disabled(self, value: bool):
            from warnings import warn

            warn(
                "_pytoui_animations_disabled has no effect in Pythonista runtime",
                UserWarning,
            )

        @pytoui_desktop_only
        def _pytoui_render(self):
            raise NotImplementedError

        @pytoui_desktop_only
        def _pytoui_did_become_first_responder(self):
            raise NotImplementedError

        @pytoui_desktop_only
        def _pytoui_did_resign_first_responder(self):
            raise NotImplementedError

        @pytoui_desktop_only
        def _pytoui_apply_autoresizing(self, old_w: float, old_h: float):
            raise NotImplementedError

        @pytoui_desktop_only
        def _pytoui_hit_test(self, x: float, y: float) -> View | None:
            raise NotImplementedError


if __name__ == "__main__":
    v = View()
    print(v.__dict__)
