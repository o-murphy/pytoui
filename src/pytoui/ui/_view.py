from __future__ import annotations
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Sequence,
    Type,
    TypeVar,
    cast,
    NoReturn,
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
    _SizeLike,
    Rect,
    Point,
    Size,
    Touch,
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
__GetT = TypeVar("__GetT")
__SetT = TypeVar("__SetT")


class getset_descriptor(Generic[__ClassT, __GetT, __SetT]):
    def __init__(self, name: str, default_value: __GetT | None = None):
        self.public_name: str | None = name
        self.default_value: __GetT = default_value
        self.mangled_name: str | None = None
        self._getter: Callable[[__ClassT], __GetT] | None = None
        self._setter: Callable[[__ClassT, __SetT], None] | None = None

    def __set_name__(self, owner: Type[__ClassT], name: str):
        class_name = owner.__name__.lstrip("_")
        self.mangled_name = f"_{class_name}__{name}"

    @overload
    def __get__(
        self, obj: None, objtype: Type[__ClassT]
    ) -> getset_descriptor[__ClassT, __GetT, __SetT]: ...

    @overload
    def __get__(self, obj: __ClassT, objtype: Type[__ClassT]) -> __GetT: ...

    def __get__(
        self, obj: __ClassT | None, objtype: Type[__ClassT] | None = None
    ) -> __GetT:
        if obj is None:
            return self
        if self._getter is not None:
            return self._getter(obj)

        return getattr(obj, self.mangled_name, self.default_value)

    def __set__(self, obj: __ClassT, value: __SetT):
        if self._setter is not None:
            self._setter(obj, value)
        else:
            raise AttributeError(f"property '{self.public_name}' has no setter")

    def __delete__(self, obj: __ClassT):
        raise AttributeError(f"Can't delete {self.public_name} attribute")

    def _get_raw(self, obj: __ClassT) -> __GetT:
        """Повертає 'сире' значення зі слота або default_value типу V_get."""
        return getattr(obj, self.mangled_name, self.default_value)

    def _set_raw(self, obj: __ClassT, value: __GetT):
        """Записує значення безпосередньо в слот. Очікує тип V_get."""
        setattr(obj, self.mangled_name, value)

    def getter(self, func: Callable[[__ClassT], __GetT]) -> None:
        self._getter = func

    def setter(self, func: Callable[[__ClassT, __SetT], None]) -> None:
        self._setter = func


class _ViewMeta(type):
    def __new__(mcls, name, bases, namespace, **kwargs):
        for base in bases:
            if getattr(base, "__final__", False):
                raise TypeError(f"{base.__name__} cannot be subclassed")
        return super().__new__(mcls, name, bases, namespace, **kwargs)


_GD = getset_descriptor

class _view(metaclass=_ViewMeta):
    __final__ = False

    __slots__ = (
        "_bounds",
        "_frame",
        "_on_screen",
        "_subviews",
        "_superview",
        "_tint_color",
        "_transform",
        "_update_interval",
        "_touch_enabled",
        "_multitouch_enabled",
        # INTERNALS
        "_pytoui_needs_display",
        "_pytoui_presented",
        "_pytoui_close_event",
        "_pytoui_last_update_t",
        "_pytoui_content_draw_size",
        # VIEW ONLY SCOPE INTERNALS
        "__pytoui_animations_disabled",
    )

    alpha: _GD[_view, float, float] = _GD("alpha", 1.0)
    background_color: _GD[_view, _ColorLike, _RGBA] = _GD(
        "background_color", (0.0, 0.0, 0.0, 0.0)
    )
    border_color: _GD[_view, _ColorLike, _RGBA] = _GD(
        "border_color", (0.0, 0.0, 0.0, 1.0)
    )
    border_width: _GD[_view, float, float] = _GD(
        "border_width", 0.0
    )
    content_mode: _GD[_view, int, int] = _GD(
        "content_mode", CONTENT_REDRAW
    )
    corner_radius: _GD[_view, float, float] = _GD(
        "corner_radius", 0.0
    )
    flex: _GD[_view, _ViewFlex, _ViewFlex] = _GD("flex", "")
    hidden: _GD[_view, bool, bool] = _GD("hidden", False)
    name: _GD[_view, str, str] = _GD("name", "")
    tint_color: _GD[_view, _ColorLike, _RGBA] = _GD(
        "tint_color", None
    )
    touch_enabled: _GD[_view, bool, bool] = _GD(
        "touch_enabled", True
    )
    multitouch_enabled: _GD[_view, bool, bool] = _GD(
        "multitouch_enabled", False
    )
    transform: _GD[_view, Transform | None, Transform | None] = (
        _GD("transform", None)
    )
    update_interval: _GD[_view, float, float] = _GD(
        "update_interval", 0.0
    )

    on_screen: _GD[_view, bool, bool] = _GD(
        "on_screen", False
    )

    _SYSTEM_TINT: _RGBA = (0.0, 0.478, 1.0, 1.0)

    def __init__(self):
        self.alpha = 1.0
        self.background_color = (0.0, 0.0, 0.0, 0.0)
        self.border_color = (0.0, 0.0, 0.0, 1.0)
        self.border_width = 0.0
        self._bounds = Rect(0.0, 0.0, 100.0, 100.0)
        self.content_mode = (
            CONTENT_REDRAW if type(self) is not View else CONTENT_SCALE_TO_FILL
        )
        self.corner_radius: float = 0.0
        self.flex: _ViewFlex = ""
        self._frame: Rect = Rect(0.0, 0.0, 100.0, 100.0)
        self.hidden = False
        self.name: str = str(uuid4())
        self._subviews: list[View] = []
        self._superview: View | None = None
        self.tint_color: _RGBA | None = None
        self.transform: Transform | None = None
        self.update_interval: float = 0.0
        self.touch_enabled: bool = True
        self.multitouch_enabled: bool = False

        # _view.on_screen._set_raw(self, False)
        _view.on_screen._set_raw(self, False)

        # CUSTOM
        self._pytoui_presented: bool = False
        self._pytoui_close_event: Event = Event()
        self._pytoui_needs_display: bool = True
        self._pytoui_last_update_t: float = 0.0
        self._pytoui_content_draw_size: Size = Size(0.0, 0.0)
        self.__pytoui_animations_disabled: bool = False

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

    # @alpha.getter
    # def __alpha(self) -> float:
    #     """The view's alpha value as a float in the range 0.0 to 1.0."""
    #     return getattr(self, _view.alpha.mangled_name, _view.alpha.default_value)

    @alpha.setter
    def __alpha(self, value: float):
        current_value = _view.alpha._get_raw(self)

        if _record(self, "alpha", current_value, value):
            return

        _view.alpha._set_raw(self, float(value))

        self.set_needs_display()

    @background_color.getter
    def __background_color(self) -> _RGBA | None:
        """The view's background color, defaults to None (transparent)."""
        raw_val = _view.background_color._get_raw(self)
        return parse_color(raw_val)

    @background_color.setter
    def __background_color(self, value: _ColorLike):
        parsed = parse_color(value)

        current = _view.background_color._get_raw(self)

        if _record(self, "background_color", current, parsed):
            return

        _view.background_color._set_raw(self, parsed)

        self.set_needs_display()

    # bg_color as alias
    bg_color = background_color

    @border_color.getter
    def __border_color(self) -> _RGBA | None:
        """The view's background color, defaults to None (transparent)."""
        # Отримуємо сире значення зі слотів базового класу
        raw_val = _view.border_color._get_raw(self)
        return parse_color(raw_val)

    @border_color.setter
    def __border_color(self, value: _ColorLike):
        parsed = parse_color(value)
        _view.border_color._set_raw(self, parsed)
        self.set_needs_display()

    @border_width.getter
    def __border_width(self) -> float:
        """The view's border width, defaults to zero (no border)."""
        return _view.border_width._get_raw(self)

    @border_width.setter
    def __border_width(self, value: float):
        new_value = float(value)
        _view.border_width._set_raw(self, new_value)
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
            self._pytoui_apply_autoresizing(old_w, old_h)
            self.layout()
        self.set_needs_display()

    @property
    def center(self) -> Point:
        """The center of the view's frame as a Point."""
        return self.frame.center()

    @center.setter
    def center(self, value: _PointLike):
        cx, cy = value
        w, h = self.frame.size
        self.frame = Rect(cx - w / 2, cy - h / 2, w, h)

    @property
    def x(self) -> float:
        """Shortcut for the x component of the view's frame."""
        return self.frame.x

    @x.setter
    def x(self, value: float):
        f = self.frame
        self.frame = Rect(value, f.y, f.w, f.h)

    @property
    def y(self) -> float:
        """Shortcut for the y component of the view's frame."""
        return self.frame.y

    @y.setter
    def y(self, value: float):
        f = self.frame
        self.frame = Rect(f.x, value, f.w, f.h)

    @property
    def width(self) -> float:
        """Shortcut for the width component of the view's frame."""
        return self.frame.w

    @width.setter
    def width(self, value: float):
        f = self.frame
        self.frame = Rect(f.x, f.y, value, f.h)

    @property
    def height(self) -> float:
        """Shortcut for the height component of the view's frame."""
        return self.frame.h

    @height.setter
    def height(self, value: float):
        f = self.frame
        self.frame = Rect(f.x, f.y, f.w, value)

    @content_mode.getter
    def __content_mode(self) -> int:
        """Determines how a view lays out its content when its bounds change."""
        return _view.content_mode._get_raw(self)

    @content_mode.setter
    def __content_mode(self, value: int):
        _view.content_mode._set_raw(self, int(value))
        self._pytoui_content_draw_size = Size(0.0, 0.0)
        self.set_needs_display()

    @corner_radius.getter
    def __corner_radius(self) -> float:
        """The view's corner radius."""
        return _view.corner_radius._get_raw(self)

    @corner_radius.setter
    def __corner_radius(self, value: float):
        _view.corner_radius._set_raw(self, float(value))
        self.set_needs_display()

    @flex.getter
    def __flex(self) -> _ViewFlex:
        """The autoresizing behavior of the view."""
        return _view.flex._get_raw(self)

    @flex.setter
    def __flex(self, value: _ViewFlex):
        _view.flex._set_raw(self, value)
        self.set_needs_display()

    autoresizing = flex

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
            self._pytoui_apply_autoresizing(old_w, old_h)
            self.layout()
        self.set_needs_display()

    @hidden.getter
    def __hidden(self) -> bool:
        """Determines if the view is hidden."""
        return bool(
            getattr(self, _view.hidden.mangled_name, _view.hidden.default_value)
        )

    @hidden.setter
    def __hidden(self, value: bool):
        new_value = bool(value)
        _view.hidden._set_raw(self, new_value)
        self.set_needs_display()

    @name.getter
    def __name(self) -> str:
        return str(_view.name._get_raw(self))

    @name.setter
    def __name(self, value: str):
        _view.name._set_raw(self, str(value))

    @on_screen.getter
    def __on_screen(self) -> bool:
        """(readonly) Whether the view is part of a view hierarchy currently on screen."""
        return bool(_view.on_screen._get_raw(self))

    @property
    def subviews(self) -> tuple[View, ...]:
        """(readonly) A tuple of the view's children."""
        return tuple(self._subviews)

    @property
    def superview(self) -> View | None:
        """(readonly) The view's parent view."""
        return self._superview

    @tint_color.getter
    def __tint_color(self) -> _RGBA:
        """The view's tint color, inherited from superview if None."""
        v: View | None = self

        while v is not None:
            val = _view.tint_color._get_raw(self)

            if val is not None:
                return val
            v = getattr(v, "_superview", None)
        return self._SYSTEM_TINT

    @tint_color.setter
    def __tint_color(self, value: _ColorLike):
        parsed = parse_color(value)
        _view.tint_color._set_raw(self, parsed)
        self.set_needs_display()

    @touch_enabled.getter
    def __touch_enabled(self) -> bool:
        """Determines if the view responds to touch events."""
        return bool(_view.touch_enabled._get_raw(self))

    @touch_enabled.setter
    def __touch_enabled(self, value: bool):
        _view.touch_enabled._set_raw(self, bool(value))

    @multitouch_enabled.getter
    def __multitouch_enabled(self) -> bool:
        """If True, the view receives all simultaneous touches. If False, only the first is tracked."""
        return bool(_view.multitouch_enabled._get_raw(self))

    @multitouch_enabled.setter
    def __multitouch_enabled(self, value: bool):
        _view.multitouch_enabled._set_raw(self, bool(value))

    @transform.getter
    def __transform(self) -> Transform | None:
        """The transform applied to the view relative to the center of its bounds."""
        return _view.transform._get_raw(self)

    @transform.setter
    def __transform(self, value: Transform | None):
        current = _view.transform._get_raw(self)

        if _record(self, "transform", current, value):
            return

        _view.transform._set_raw(self, value)

        self.set_needs_display()

    @update_interval.getter
    def __update_interval(self) -> float:
        """Interval between update() calls in seconds. 0 disables updates."""
        return _view.update_interval._get_raw(self)

    @update_interval.setter
    def __update_interval(self, value: float):
        new_val = float(value)
        _view.update_interval._set_raw(self, new_val)

        if new_val > 0.0:
            self._pytoui_last_update_t = time.time()

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

    def _pytoui_apply_autoresizing(self, old_w: float, old_h: float):
        """Resize subviews based on their flex flags after this view's size changed."""
        dw = self.bounds.w - old_w
        dh = self.bounds.h - old_h
        if dw == 0.0 and dh == 0.0:
            return
        for sv in self._subviews:
            flex = sv.flex
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
            sv.frame = Rect(x, y, w, h)  # bypass setter to avoid recursion

    def set_needs_display(self):
        """Mark the view as needing to be redrawn."""
        self._pytoui_needs_display = True

    def size_to_fit(self):
        """Resize to enclose all subviews."""
        if not self._subviews:
            return
        max_w = max(sv._frame.x + sv._frame.w for sv in self._subviews)
        max_h = max(sv._frame.y + sv._frame.h for sv in self._subviews)
        self.frame = Rect(self.frame.x, self.frame.y, max_w, max_h)

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
        if self._pytoui_presented:
            raise RuntimeError("View is already presented")
        self._pytoui_presented = True
        _view.on_screen._set_raw(self, True)
        self._pytoui_close_event.clear()
        self._pytoui_needs_display = True

        from pytoui.ui._runtime import launch_runtime

        if animated and not _UI_DISABLE_ANIMATIONS:
            self.alpha = 0.0
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
                    self.alpha = p
                elif self.alpha < 1.0:
                    self.alpha = 1.0
                set_backend(fb)
                self._pytoui_render()
                set_backend(None)
                if animating:
                    self._pytoui_needs_display = (
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
        if not self._pytoui_presented:
            return
        self.will_close()
        _view.on_screen._set_raw(self, False)
        self._pytoui_presented = False
        self._pytoui_close_event.set()

    def wait_modal(self):
        """Block until the view is dismissed."""
        if not self.on_screen:
            return
        self._pytoui_close_event.wait()

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

    # ── CUSOM INTERNALS ─────────────────────────────────────────────────────────────

    @property
    def _pytoui_animations_disabled(self) -> bool:
        return bool(self.__pytoui_animations_disabled or _UI_DISABLE_ANIMATIONS)

    @_pytoui_animations_disabled.setter
    def _pytoui_animations_disabled(self, value: bool):
        self.__pytoui_animations_disabled = value

    def _pytoui_hit_test(self, x: float, y: float) -> View | None:
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
        self._pytoui_needs_display = False
        if self.hidden:
            return

        ox, oy = _screen_origin(self)
        fw, fh = self.frame.w, self.frame.h
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
            if cm == CONTENT_REDRAW:
                self.draw()
            else:
                cw, ch = self._pytoui_content_draw_size.as_tuple()
                if cw <= 0.0 or ch <= 0.0:
                    # First render — record the size draw() was called at
                    self._pytoui_content_draw_size = Size(fw, fh)
                    self.draw()
                else:
                    with GState():
                        _content_mode_transform(cm, cw, ch, fw, fh)
                        self.draw()

        for sv in self._subviews:
            sv._pytoui_render()


class View(_view):
    pass


if IS_PYTHONISTA:
    import ui  # type: ignore[import-not-found]  # noqa: F811

    class View(ui.View, metaclass=_ViewMeta):  # type: ignore[no-redef]
        # Proxy to the native properties so that subclass
        # __init__ assignments (e.g. self.frame = Rect(...)) immediately update
        # the native frame and reads always reflect the current geometry.

        def __init__(self):
            # disallow *args, **kwargs
            pass

        @property
        def _alpha(self) -> float:
            return self.alpha

        @_alpha.setter
        def _alpha(self, value: float):
            self.alpha = value

        @property
        def _background_color(self) -> _RGBA:
            return cast(_RGBA, self.background_color)

        @_background_color.setter
        def _background_color(self, value: _ColorLike):
            self.background_color = cast(_RGBA, value)

        @property
        def _border_color(self) -> _RGBA:
            return cast(_RGBA, self.border_color)

        @_border_color.setter
        def _border_color(self, value: _ColorLike):
            self.border_color = cast(_RGBA, value)

        @property
        def _border_width(self) -> float:
            return self.border_width

        @_border_width.setter
        def _border_width(self, value: float):
            self.border_width = value

        @property
        def _bounds(self) -> Rect:
            return cast(Rect, self.bounds)

        @_bounds.setter
        def _bounds(self, value: _RectLike):
            self.bounds = cast(ui.Rect, value)

        @property
        def _content_mode(self) -> int:
            return self.content_mode

        @_content_mode.setter
        def _content_mode(self, value: int):
            self.content_mode = value

        @property
        def _corner_radius(self) -> float:
            return self.corner_radius

        @_corner_radius.setter
        def _corner_radius(self, value: float):
            self.corner_radius = value

        @property
        def _flex(self) -> _ViewFlex:
            return self.flex

        @_flex.setter
        def _flex(self, value: _ViewFlex):
            self.flex = value

        _autoresizing = _flex

        @property
        def _frame(self) -> Rect:
            return cast(Rect, self.frame)

        @_frame.setter
        def _frame(self, value: _RectLike):
            self.frame = cast(ui.Rect, value)

        @property
        def _hidden(self) -> bool:
            return self.hidden

        @_hidden.setter
        def _hidden(self, value: bool):
            self.hidden = value

        @property
        def _name(self) -> str:
            return self.name

        @_name.setter
        def _name(self, value: str):
            self.name = value

        @property
        def _on_screen(self) -> bool:
            return self.on_screen

        @property
        def _subviews(self) -> tuple[View, ...]:
            return cast(tuple[View, ...], self.subviews)

        @property
        def _superview(self) -> View | None:
            return cast(View, self.superview)

        @_superview.setter
        def _superview(self, value: View | None):
            self.superview = cast(ui.View, value)

        @property
        def _tint_color(self) -> _RGBA | None:
            return cast(_RGBA, self.tint_color)

        @_tint_color.setter
        def _tint_color(self, value: _ColorLike):
            self.tint_color = cast(_RGBA, value)

        @property
        def _transform(self) -> Transform | None:
            return self.transform

        @_transform.setter
        def _transform(self, value: Transform | None):
            self.transform = value

        @property
        def _update_interval(self) -> float:
            return self.update_interval

        @_update_interval.setter
        def _update_interval(self, value: float):
            self.update_interval = value

        @property
        def _touch_enabled(self) -> bool:
            return self.touch_enabled

        @_touch_enabled.setter
        def _touch_enabled(self, value: bool):
            self.touch_enabled = value

        @property
        def _multitouch_enabled(self) -> bool:
            return self.multitouch_enabled

        @_multitouch_enabled.setter
        def _multitouch_enabled(self, value: bool):
            self.multitouch_enabled = value

        # CUSTOM
        @property
        @pytoui_desktop_only
        def _pytoui_presented(self) -> bool:
            raise NotImplementedError

        @_pytoui_presented.setter
        @pytoui_desktop_only
        def _pytoui_presented(self, value: bool):
            raise NotImplementedError

        @property
        @pytoui_desktop_only
        def _pytoui_close_event(self) -> Event:
            raise NotImplementedError

        @_pytoui_close_event.setter
        @pytoui_desktop_only
        def _pytoui_close_event(self, value: Event):
            raise NotImplementedError

        @property
        @pytoui_desktop_only
        def _pytoui_needs_display(self) -> bool:
            raise NotImplementedError

        @_pytoui_needs_display.setter
        @pytoui_desktop_only
        def _pytoui_needs_display(self, value: bool):
            raise NotImplementedError

        @property
        @pytoui_desktop_only
        def _pytoui_last_update_t(self) -> float:
            raise NotImplementedError

        @_pytoui_last_update_t.setter
        @pytoui_desktop_only
        def _pytoui_last_update_t(self, value: float):
            raise NotImplementedError

        @property
        @pytoui_desktop_only
        def _pytoui_content_draw_size(self) -> Size | NoReturn:
            raise NotImplementedError

        @_pytoui_content_draw_size.setter
        @pytoui_desktop_only
        def _pytoui_content_draw_size(self, value: _SizeLike):
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
