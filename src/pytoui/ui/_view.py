from __future__ import annotations

import time
from collections.abc import Sequence
from threading import Event
from typing import (
    TYPE_CHECKING,
    Callable,
    cast,
)
from uuid import uuid4

from pytoui._platform import _UI_DISABLE_ANIMATIONS, IS_PYTHONISTA
from pytoui.ui._button_item import ButtonItem
from pytoui.ui._constants import (
    CONTENT_REDRAW,
    CONTENT_SCALE_TO_FILL,
)
from pytoui.ui._draw import (
    GState,
    Path,
    Transform,
    _content_mode_transform,
    _get_draw_ctx,
    _record,
    _screen_origin,
    _set_origin,
    _sync_ctm_to_rust,
    fill_rect,
    parse_color,
    set_alpha,
    set_color,
)
from pytoui.ui._internals import _get_system_tint, _getset_descriptor
from pytoui.ui._types import Rect, Size

if not IS_PYTHONISTA:
    from pytoui._osdbuf import FrameBuffer as _FrameBuffer

if TYPE_CHECKING:
    from pytoui.ui._navigation_view import _NavigationView, _NavigationViewInternals
    from pytoui.ui._types import (
        _RGBA,
        MouseEvent,
        MouseWheel,
        Point,
        Touch,
        _ColorLike,
        _ContentMode,
        _PointLike,
        _PresentOrientation,
        _PresentStyle,
        _RectLike,
        _ViewFlex,
    )

__all__ = (
    "View",
    "_View",
    "_ViewInternals",
    "_RenderContext",
    "_RenderLoop",
)


class _RenderContext:
    """Context manager for rendering a view to a framebuffer.

    Saves and restores the drawing context state, similar to ImageContext.
    """

    def __init__(self, view: _ViewInternals, fb):
        self.view = view
        self.fb = fb
        self._prev_backend = None
        self._prev_origin = None

    def __enter__(self):
        ctx = _get_draw_ctx()

        # Save previous state
        self._prev_backend = ctx.backend
        self._prev_origin = ctx.origin

        # Set new backend
        ctx.backend = self.fb
        ctx.origin = (0.0, 0.0)  # Render at origin

        # Sync state to Rust
        _sync_ctm_to_rust(ctx)

        return self

    def __exit__(self, *args):
        ctx = _get_draw_ctx()

        # Restore previous state
        ctx.backend = self._prev_backend
        ctx.origin = self._prev_origin

        # Sync restored state
        _sync_ctm_to_rust(ctx)


class _RenderLoop:
    """Helper for animation and rendering loop."""

    def __init__(self, view: _ViewInternals, animated: bool = True):
        self.view = view
        self.animated = animated and not _UI_DISABLE_ANIMATIONS
        self.start_time = None
        self.anim_duration = 0.25

    def __call__(self, fb):
        with _RenderContext(self.view, fb):
            if self.animated:
                self._animate_frame()
            self.view.pytoui_render()
        # pytoui_render() clears _pytoui_needsDisplay; re-set it so the next
        # frame is scheduled while the fade-in animation is still running.
        if self.animated and self.view._alpha < 1.0:
            self.view._needsDisplay = True

    def _animate_frame(self):
        if self.start_time is None:
            self.start_time = time.time()
            self.view._alpha = 0.0

        elapsed = time.time() - self.start_time
        if elapsed < self.anim_duration:
            p = elapsed / self.anim_duration
            p = p * p * (3.0 - 2.0 * p)  # smoothstep
            self.view._alpha = p
        elif self.view._alpha < 1.0:
            self.view._alpha = 1.0


class _ViewInternals:
    __slots__ = (
        # view ref
        "_ref",
        # attributes
        "_alpha",
        "_backgroundColor",
        "_contentMode",
        "_cornerRadius_",
        "_isHidden",
        "_name",
        "_tintColor",
        "_transform",
        "_isMultipleTouchEnabled",
        "_frame",
        "_bounds",
        "_subviews",
        "_superview",
        "_needsDisplay",
        "_needsLayout",
        # pytoui attributes
        "_pytoui_borderColor",
        "_pytoui_borderWidth",
        "_pytoui_flex",
        "_pytoui_updateInterval",
        "_pytoui_navigationView",
        "_pytoui_isTouchEnabled",
        "_pytoui_isOnScreen",
        "_pytoui_isPresented",
        "_pytoui_lastUpdateTime",
        "_pytoui_isMouseWheelEnabled",
        "_pytoui_isScrollContainer",
        "_pytoui_leftButtonItems",
        "_pytoui_rightButtonItems",
        "_pytoui_closeEvent",
        "_pytoui_contentDrawSize",
        "_pytoui_hasInitialFrame",
        # System-level overlay draw function called after subviews.
        # Each entry is a zero-argument callable rendered in the current GState
        # (clipped to this view's bounds). Used by ScrollView for indicators.
        "_pytoui_internalSubviews",
        "_pytoui_drawOverlay",
        "_pytoui_layer",  # per-view owned FrameBuffer (None = not yet created)
    )

    def __init__(self, view: _View):
        self._ref: _View = view
        # view props
        self._alpha: float = 1.0
        self._backgroundColor: _RGBA = (0.0, 0.0, 0.0, 0.0)
        self._bounds: Rect = Rect(0.0, 0.0, 100.0, 100.0)
        self._contentMode: _ContentMode = CONTENT_SCALE_TO_FILL
        self._cornerRadius_: float = 0.0
        self._frame: Rect = Rect(0.0, 0.0, 100.0, 100.0)
        self._isHidden: bool = False
        self._name: str = str(uuid4())
        self._subviews: list[_ViewInternals] = []
        self._superview: _ViewInternals | None = None
        self._tintColor: _RGBA | None = None
        self._transform: Transform | None = None
        self._isMultipleTouchEnabled: bool = False
        self._needsDisplay: bool = True
        self._needsLayout: bool = True

        # CUSTOM
        self._pytoui_borderColor: _RGBA = (0.0, 0.0, 0.0, 1.0)
        self._pytoui_borderWidth: float = 0.0
        self._pytoui_flex: _ViewFlex = ""
        self._pytoui_updateInterval: float = 0.0
        self._pytoui_isOnScreen: bool = False
        self._pytoui_navigationView: _NavigationViewInternals | None = None
        self._pytoui_isTouchEnabled: bool = True
        self._pytoui_isPresented: bool = False
        self._pytoui_lastUpdateTime: float = 0.0
        self._pytoui_isMouseWheelEnabled: bool = False
        self._pytoui_isScrollContainer: bool = False
        self._pytoui_leftButtonItems: tuple[ButtonItem, ...] | None = None
        self._pytoui_rightButtonItems: tuple[ButtonItem, ...] | None = None

        # INTERNAL ONLY
        self._pytoui_closeEvent: Event = Event()
        self._pytoui_contentDrawSize: Size = Size(0.0, 0.0)
        self._pytoui_hasInitialFrame: bool = False

        # CUSTOM RENDER LAYERS
        self._pytoui_internalSubviews: list[_ViewInternals] = []
        self._pytoui_drawOverlay: Callable[[], None] | None = None
        self._pytoui_layer: _FrameBuffer | None = None

    def ref(self) -> _View:
        # READONLY
        return self._ref

    def pytoui_isPresented(self) -> bool:
        # READONLY
        return self._pytoui_isPresented

    def pytoui_borderColor(self) -> _RGBA:
        """The view's border color (only has effect if border_width > 0)."""
        return self._pytoui_borderColor

    def pytoui_setBorderColor_(self, value: _ColorLike):
        self._pytoui_borderColor = parse_color(value)
        self.setNeedsDisplay()

    def pytoui_borderWidth(self) -> float:
        """The view's border width, defaults to zero (no border)."""
        return self._pytoui_borderWidth

    def pytoui_setBorderWidth_(self, value: float):
        self._pytoui_borderWidth = float(value)
        self.setNeedsDisplay()

    def pytoui_lastUpdateTime(self) -> float:
        return self._pytoui_lastUpdateTime

    def pytoui_setLastUpdateTime_(self, value: float):
        self._pytoui_lastUpdateTime = float(value)

    def pytoui_flex(self) -> _ViewFlex:
        """The autoresizing behavior of the view."""
        return self._pytoui_flex

    def pytoui_setFlex_(self, value: _ViewFlex):
        self._pytoui_flex = value
        self.setNeedsDisplay()

    def pytoui_isOnScreen(self) -> bool:
        """(readonly) Whether the view is part of
        a view hierarchy currently on screen."""
        return self._pytoui_isOnScreen

    def pytoui_updateInterval(self) -> float:
        """Interval between update() calls in seconds. 0 disables updates."""
        return self._pytoui_updateInterval

    def pytoui_setUpdateInterval_(self, value: float):
        self._pytoui_updateInterval = float(value)
        if value > 0.0:
            self.pytoui_setLastUpdateTime_(time.time())

    def pytoui_internalSubviews(self) -> list[_ViewInternals]:
        """(readonly) A tuple of the view's children."""
        return self._pytoui_internalSubviews

    def pytoui_navigationView(self) -> _NavigationViewInternals | None:
        """(readonly) The view's navigation_view view."""
        sv = self._pytoui_navigationView
        if sv is not None:
            return sv
        return None

    def pytoui_leftButtonItems(self) -> tuple[ButtonItem, ...] | None:
        items = self._pytoui_leftButtonItems
        if items:
            return tuple(items)
        return None

    def pytoui_setLeftButtonItems_(self, value: Sequence[ButtonItem] | None):
        self._pytoui_leftButtonItems = tuple(value) if value else None

    def pytoui_rightButtonItems(self) -> tuple[ButtonItem, ...] | None:
        items = self._pytoui_rightButtonItems
        if items:
            return tuple(items)
        return None

    def pytoui_setRightButtonItems_(self, value: Sequence[ButtonItem] | None):
        self._pytoui_rightButtonItems = tuple(value) if value else None

    def pytoui_isTouchEnabled(self) -> bool:
        return self._pytoui_isTouchEnabled

    def pytoui_setTouchEnabled_(self, value: bool):
        self._pytoui_isTouchEnabled = bool(value)

    def pytoui_isMouseWheelEnabled(self) -> bool:
        """If False, the view ignores mouse wheel / scroll events."""
        return self._pytoui_isMouseWheelEnabled

    def pytoui_setMouseWheelEnabled_(self, value: bool):
        self._pytoui_isMouseWheelEnabled = bool(value)

    def needsDisplay(self) -> bool:
        return self._needsDisplay

    def setNeedsDisplay(self):
        self._needsDisplay = True
        # Bubble dirty up so parent layers know to re-render and recomposite
        sv = self._superview
        while sv is not None:
            if sv._needsDisplay:
                break  # chain already dirty above this point
            sv._needsDisplay = True
            sv = sv._superview

    def needsLayout(self) -> bool:
        return self._needsLayout

    def setNeedsLayout(self):
        self._needsLayout = True
        self.setNeedsDisplay()

    def alpha(self) -> float:
        """The view's alpha value as a float in the range 0.0 to 1.0."""
        return self._alpha

    def setAlpha_(self, value: float):
        if _record(self, "alpha", self._alpha, value):
            return
        self._alpha = float(value)
        self.setNeedsDisplay()

    def backgroundColor(self) -> _RGBA:
        """The view's background color, defaults to None (transparent)."""
        return self._backgroundColor

    def setBackgroundColor_(self, value: _ColorLike):
        parsed = parse_color(value)
        if _record(self, "background_color", self._backgroundColor, parsed):
            return
        self._backgroundColor = parsed
        self.setNeedsDisplay()

    def contentMode(self) -> _ContentMode:
        """Determines how a view lays out its content when its bounds change."""
        return self._contentMode

    def setContentMode_(self, value: _ContentMode):
        self._contentMode = value
        self._pytoui_contentDrawSize = Size(0.0, 0.0)
        self.setNeedsDisplay()

    def _cornerRadius(self) -> float:
        """The view's corner radius."""
        return self._cornerRadius_

    def _setCornerRadius_(self, value: float):
        self._cornerRadius_ = float(value)
        self.setNeedsDisplay()

    def isHidden(self) -> bool:
        """Determines if the view is hidden."""
        return self._isHidden

    def setHidden_(self, value: bool):
        self._isHidden = bool(value)
        self.setNeedsDisplay()

    def name(self) -> str:
        """A string that identifies the view."""
        return self._name

    def setName_(self, value: str):
        self._name = value

    def subviews(self) -> list[_ViewInternals]:
        """(readonly) A tuple of the view's children."""
        return self._subviews

    def superview(self) -> _ViewInternals | None:
        """(readonly) The view's parent view."""
        sv = self._superview
        if sv is not None:
            return sv
        return None

    def isMultipleTouchEnabled(self) -> bool:
        """If True, the view receives all simultaneous touches.
        If False (default), only the first touch is tracked."""
        return self._isMultipleTouchEnabled

    def setMultipleTouchEnabled_(self, value: bool):
        self._isMultipleTouchEnabled = bool(value)

    def frame(self) -> Rect:
        """The view's position and size in the coordinate system of its superview."""
        return self._frame

    def setFrame_(self, value: _RectLike):
        new_frame = Rect(*value)
        old_frame = self._frame
        if _record(self, "frame", old_frame, new_frame):
            return
        old_w, old_h = old_frame.size
        self._frame = new_frame
        new_w, new_h = new_frame.size
        if new_w != old_w or new_h != old_h:
            self._bounds = Rect(self._bounds.x, self._bounds.y, new_w, new_h)
            self._pytoui_contentDrawSize = Size(0.0, 0.0)
            self.pytoui_applyAutoresizing(old_w, old_h)
        self._pytoui_hasInitialFrame = True
        self.setNeedsLayout()

    def bounds(self) -> Rect:
        """The view's location and size in its own coordinate system."""
        return self._bounds

    def setBounds_(self, value: _RectLike):
        new_bounds = Rect(*value)
        old_w, old_h = self._bounds.size
        self._bounds = new_bounds
        new_w, new_h = new_bounds.size
        if new_w != old_w or new_h != old_h:
            self._frame = Rect(self._frame.x, self._frame.y, new_w, new_h)
            self.pytoui_applyAutoresizing(old_w, old_h)
        self._pytoui_hasInitialFrame = True
        self.setNeedsLayout()

    def tintColor(self) -> _RGBA:
        """The view's tint color, inherited from superview if None."""
        v: _ViewInternals | None = self
        while v is not None:
            if v._tintColor is not None:
                return v._tintColor
            v = v._superview
        return _get_system_tint()

    def setTintColor_(self, value: _ColorLike):
        if value is None:
            self._tintColor = None
        else:
            self._tintColor = parse_color(value)
        self.setNeedsDisplay()

    def transform(self) -> Transform | None:
        """The transform applied to the view relative to the center of its bounds."""
        return self._transform

    def setTransform_(self, value: Transform | None):
        if _record(self, "transform", self._transform, value):
            return
        self._transform = value
        self.setNeedsDisplay()

    def pytoui_touchBeganCallback(self) -> Callable[[Touch], None] | None:
        # touchesBeganWithEvent_
        return getattr(self._ref, "touch_began", None)

    def pytoui_touchMovedCallback(self) -> Callable[[Touch], None] | None:
        # touchesMovedWithEvent_
        return getattr(self._ref, "touch_moved", None)

    def pytoui_touchEndedCallback(self) -> Callable[[Touch], None] | None:
        # touchesEndedWithEvent_
        # touchesCanceledWithEvent_
        return getattr(self._ref, "touch_ended", None)

    def pytoui_mouseDownCallback(self) -> Callable[[MouseEvent], None] | None:
        cb = getattr(self._ref, "mouse_down", None)
        if cb is None:
            return getattr(self._ref, "touch_began", None)
        return cb

    def pytoui_mouseUpCallback(self) -> Callable[[MouseEvent], None] | None:
        cb = getattr(self._ref, "mouse_up", None)
        if cb is None:
            return getattr(self._ref, "touch_ended", None)
        return cb

    def pytoui_mouseDraggedCallback(self) -> Callable[[MouseEvent], None] | None:
        cb = getattr(self._ref, "mouse_dragged", None)
        if cb is None:
            return getattr(self._ref, "touch_moved", None)
        return cb

    def pytoui_mouseMovedCallback(self) -> Callable[[MouseEvent], None] | None:
        return getattr(self._ref, "mouse_moved", None)

    def pytoui_mouseWheelCallback(self) -> Callable[[MouseWheel], None] | None:
        return getattr(self._ref, "mouse_wheel", None)

    def pytoui_getKeyCommands(self) -> list[dict[str, str]]:
        # keyCommands
        return self._ref.get_key_commands()

    def pytoui_keyCommand(self) -> Callable[[dict], None] | None:
        return getattr(self._ref, "key_command", None)

    def pytoui_didBecomeFirstResponder(self): ...
    def pytoui_didResignFirstResponder(self): ...

    def pytoui_update(self):
        if hasattr(self._ref, "update"):
            self._ref.update()

    def _apply_autoresizing_to_view(self, sv: _ViewInternals, dw: float, dh: float):
        flex = sv._pytoui_flex
        if not flex:
            return
        f = sv.frame()
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
        sv.setFrame_((x, y, w, h))

    def pytoui_applyAutoresizing(self, old_w: float, old_h: float):
        """Resize subviews based on their flex flags after this view's size changed."""
        bw, bh = self._bounds.size
        dw = bw - old_w
        dh = bh - old_h
        if dw == 0.0 and dh == 0.0:
            return

        for sv in self._subviews:
            self._apply_autoresizing_to_view(sv, dw, dh)

        for sv in self._pytoui_internalSubviews:
            self._apply_autoresizing_to_view(sv, dw, dh)

    def pytoui_hitTest(self, x: float, y: float) -> _ViewInternals | None:
        """Recursively searches for the highest Z-index View
        that supports touch at the specified coordinates.
        """
        if self._isHidden:
            return None
        ox, oy = _screen_origin(self._ref)
        fw, fh = self._frame.size
        if not (ox <= x < ox + fw and oy <= y < oy + fh):
            return None

        # 1. Overlay has not hit-test

        # 2. Public subviews
        for child in reversed(self._subviews):
            target = child.pytoui_hitTest(x, y)
            if target is not None and target._pytoui_isTouchEnabled:
                return target

        # 3. Internal subviews
        for child in reversed(self._pytoui_internalSubviews):
            target = child.pytoui_hitTest(x, y)
            if target and target._pytoui_isTouchEnabled:
                return target

        return self if self._pytoui_isTouchEnabled else None

    def pytoui_scrollHitTest(self, x: float, y: float) -> _ViewInternals | None:
        """Like pytoui_hit_test but filters by isMouseWheelEnabled.

        A view with scroll_enabled=False is transparent to scroll events
        (the event passes through to the parent), independently of touch_enabled.
        """
        if self._isHidden:
            return None
        ox, oy = _screen_origin(self._ref)
        fw, fh = self._frame.size
        if not (ox <= x < ox + fw and oy <= y < oy + fh):
            return None

        # 1. Overlay has not hit-test

        # 2. Public subviews
        for child in reversed(self._subviews):
            target = child.pytoui_scrollHitTest(x, y)
            if target is not None and getattr(
                target, "_pytoui_isMouseWheelEnabled", False
            ):
                # If the current view is a scroll container but the child is
                # not (e.g. Slider/SegmentedControl inside a ScrollView),
                # prefer the container — matches iOS where wheel events go to
                # the scroll view, not to inline controls inside it.
                if self._pytoui_isScrollContainer and not getattr(
                    target, "_pytoui_isScrollContainer", False
                ):
                    break
                return target

        # 3. Internal subviews
        for child in reversed(self._pytoui_internalSubviews):
            target = child.pytoui_scrollHitTest(x, y)
            if target is not None and getattr(
                target, "_pytoui_isMouseWheelEnabled", False
            ):
                # If the current view is a scroll container but the child is
                # not (e.g. Slider/SegmentedControl inside a ScrollView),
                # prefer the container — matches iOS where wheel events go to
                # the scroll view, not to inline controls inside it.
                if self._pytoui_isScrollContainer and not getattr(
                    target, "_pytoui_isScrollContainer", False
                ):
                    break
                return target

        return self if getattr(self, "_pytoui_isMouseWheelEnabled", False) else None

    # ── rendering ─────────────────────────────────────────────────────────────

    def _clear_dirty_tree(self) -> None:
        """Recursively clear needs_display without rendering (used for culled views)."""
        self._needsDisplay = False
        for sv in self._subviews:
            sv._clear_dirty_tree()
        for sv in self._pytoui_internalSubviews:
            sv._clear_dirty_tree()

    def _pytoui_renderSelf(self, fw: float, fh: float):
        cm = self._contentMode
        draw = getattr(self._ref, "draw", None)
        if callable(draw):
            if cm == CONTENT_REDRAW:
                draw()
            else:
                cw, ch = self._pytoui_contentDrawSize.as_tuple()
                if cw <= 0.0 or ch <= 0.0:
                    # First render — record the size draw() was called at
                    self._pytoui_contentDrawSize = Size(fw, fh)
                    draw()
                else:
                    with GState():
                        _content_mode_transform(cm, cw, ch, fw, fh)
                        draw()

    def _pytoui_renderBackground(
        self, clip_path: Path, fw: float, fh: float, cr: float
    ):
        bg = self._backgroundColor
        if bg and bg[3] > 0:
            set_color(bg)
            if cr > 0:
                clip_path.fill()
            else:
                fill_rect(0, 0, fw, fh)

        if self._pytoui_borderWidth > 0 and self._pytoui_borderColor is not None:
            set_color(self._pytoui_borderColor)
            p = clip_path if cr > 0 else Path.rect(0, 0, fw, fh)
            p.line_width = self._pytoui_borderWidth
            p.stroke()

    def _pytoui_renderOverlay(self):
        """
        System overlay: drawn on top of all regular subviews,
        within the same clip. Each entry is a zero-arg callable.
        """
        fn = self._pytoui_drawOverlay
        if callable(fn):
            fn()

    def pytoui_layout(self, force=False):
        if self._needsLayout or force:
            if hasattr(self._ref, "layout"):
                self._ref.layout()

    def pytoui_updateTree(self, now: float):
        """Update this view and propagate to all subviews (public and internal)."""
        # Update self if needed
        if self._pytoui_updateInterval > 0:
            if now - self._pytoui_lastUpdateTime >= self._pytoui_updateInterval:
                self.pytoui_update()
                self._pytoui_lastUpdateTime = now

        # Update public subviews
        for sv in self._subviews:
            sv.pytoui_updateTree(now)

        # Update internal subviews
        for sv in self._pytoui_internalSubviews:
            sv.pytoui_updateTree(now)

    def pytoui_drawSnapshot(self):
        self.pytoui_layout()
        if self._isHidden:
            return
        ox, oy = _screen_origin(self._ref)
        fw, fh = self._frame.size
        if fw <= 0 or fh <= 0:
            return
        cr = self._cornerRadius_

        _set_origin(ox, oy)
        set_alpha(self._alpha)

        clip_path = (
            Path.rounded_rect(0, 0, fw, fh, cr) if cr > 0 else Path.rect(0, 0, fw, fh)
        )
        clip_path.add_clip()

        self._pytoui_renderBackground(clip_path, fw, fh, cr)
        self._pytoui_renderSelf(fw, fh)

        # Pass current screen FB to subviews for compositing
        ctx = _get_draw_ctx()
        scale = ctx.backend.scale_factor if ctx.backend is not None else 1.0
        parent_layer = ctx.backend
        bx, by = self._bounds.x, self._bounds.y

        for sv in self._pytoui_internalSubviews:
            sf = sv._frame
            if (
                sf.x + sf.w <= bx
                or sf.x >= bx + fw
                or sf.y + sf.h <= by
                or sf.y >= by + fh
            ):
                sv._clear_dirty_tree()
                continue
            sv.pytoui_render(
                parent_layer, int((sf.x - bx) * scale), int((sf.y - by) * scale)
            )

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
            sv.pytoui_render(
                parent_layer, int((sf.x - bx) * scale), int((sf.y - by) * scale)
            )

        self._pytoui_renderOverlay()

    def pytoui_render(
        self, parent_layer: _FrameBuffer | None = None, px: int = 0, py: int = 0
    ):
        if parent_layer is None:
            # Root path: render directly into current ctx.backend (screen FB)
            self._needsDisplay = False
            self._needsLayout = False
            with GState():
                self.pytoui_drawSnapshot()
            return

        # Subview path: use own per-view layer
        if self._isHidden:
            return

        self.pytoui_layout()

        fw, fh = self._frame.size
        if fw <= 0 or fh <= 0:
            return

        scale = parent_layer.scale_factor
        pw = max(1, int(fw * scale))
        ph = max(1, int(fh * scale))

        layer = self._pytoui_layer
        if layer is None or layer._width != pw or layer._height != ph:
            layer = _FrameBuffer.create_owned(pw, ph)
            layer.scale_factor = scale
            self._pytoui_layer = layer
            self._needsDisplay = True

        if self._needsDisplay:
            self._needsDisplay = False
            self._needsLayout = False
            layer.clear()
            cr = self._cornerRadius_

            ctx = _get_draw_ctx()
            saved_backend = ctx.backend
            saved_origin = ctx.origin
            ctx.backend = layer
            ctx.origin = (0.0, 0.0)
            _sync_ctm_to_rust(ctx)

            try:
                set_alpha(1.0)  # alpha applied during compositing, not rendering
                cp = (
                    Path.rounded_rect(0, 0, fw, fh, cr)
                    if cr > 0
                    else Path.rect(0, 0, fw, fh)
                )
                self._pytoui_renderBackground(cp, fw, fh, cr)
                self._pytoui_renderSelf(fw, fh)

                bx, by = self._bounds.x, self._bounds.y

                for sv in self._pytoui_internalSubviews:
                    sf = sv._frame
                    if (
                        sf.x + sf.w <= bx
                        or sf.x >= bx + fw
                        or sf.y + sf.h <= by
                        or sf.y >= by + fh
                    ):
                        sv._clear_dirty_tree()
                        continue
                    sv.pytoui_render(
                        layer, int((sf.x - bx) * scale), int((sf.y - by) * scale)
                    )

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
                    sv.pytoui_render(
                        layer, int((sf.x - bx) * scale), int((sf.y - by) * scale)
                    )

                self._pytoui_renderOverlay()
            finally:
                ctx.backend = saved_backend
                ctx.origin = saved_origin
                _sync_ctm_to_rust(ctx)

        # Composite own layer into parent (rounded if corner_radius > 0)
        cr = self._cornerRadius_
        if cr > 0:
            layer.composite_into_rounded(parent_layer, px, py, self._alpha, cr * scale)
        else:
            layer.composite_into(parent_layer, px, py, self._alpha)

    def __getitem__(self, name: str) -> _ViewInternals:
        for view in self._subviews:
            if view._name == name:
                return view
        raise KeyError(name)

    def addSubview_(self, view: _ViewInternals):
        """Add another view as a child of this view."""
        if view._superview is self:
            return
        if view._superview is not None:
            view._superview.pytoui_removeSubview(view)
        self._subviews.append(view)
        view._superview = self
        view.setNeedsDisplay()

    def removeFromSuperview(self):
        """Remove this view from its superview."""
        sv = self._superview
        if sv is not None:
            if self in sv._subviews:
                sv.pytoui_removeSubview(self)
            if self in sv._pytoui_internalSubviews:
                sv.pytoui_removeInternalSubview(self)

    def pytoui_removeSubview(self, view: _ViewInternals):
        """Remove a child view."""
        if view in self._subviews:
            self._subviews.remove(view)
            view._superview = None
            view.setNeedsDisplay()

    def pytoui_AddInternalSubview_(self, view: _ViewInternals):
        """Add another view as a child of this view."""
        if view._superview is self:
            return
        if view._superview is not None:
            view._superview.pytoui_removeInternalSubview(view)
        self._pytoui_internalSubviews.append(view)
        view._superview = self
        view.setNeedsDisplay()

    def pytoui_removeInternalSubview(self, view: _ViewInternals):
        """Remove a child view."""
        if view in self._pytoui_internalSubviews:
            self._pytoui_internalSubviews.remove(view)
            view._superview = None
            view.setNeedsDisplay()

    def bringSubviewToFront_(self):
        """Show the view on top of its sibling views."""
        sv = self._superview
        if sv is None:
            return

        changed = False

        if self in sv._subviews:
            sv._subviews.remove(self)
            sv._subviews.append(self)
            changed = True
        elif self in sv._pytoui_internalSubviews:
            sv._pytoui_internalSubviews.remove(self)
            sv._pytoui_internalSubviews.append(self)
            changed = True

        if changed:
            sv.setNeedsDisplay()

    def sendSubviewToBack_(self):
        """Put the view behind its sibling views."""
        sv = self._superview
        if sv is None:
            return

        changed = False

        if self in sv._subviews:
            sv._subviews.remove(self)
            sv._subviews.insert(0, self)
            changed = True
        elif self in sv._pytoui_internalSubviews:
            sv._pytoui_internalSubviews.remove(self)
            sv._pytoui_internalSubviews.insert(0, self)
            changed = True

        if changed:
            sv.setNeedsDisplay()

    def sizeToFit(self):
        """Resize to enclose all subviews (including internal ones)."""
        if not self._subviews and not self._pytoui_internalSubviews:
            return

        max_w = 0.0
        max_h = 0.0

        for sv in self._subviews:
            max_w = max(max_w, sv.frame.x + sv.frame.w)
            max_h = max(max_h, sv.frame.y + sv.frame.h)

        for sv in self._pytoui_internalSubviews:
            max_w = max(max_w, sv.frame.x + sv.frame.w)
            max_h = max(max_h, sv.frame.y + sv.frame.h)

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
        if self._pytoui_isPresented:
            raise RuntimeError("View is already presented")

        from pytoui.ui._runtime import launch_runtime

        self._pytoui_isPresented = True
        self._pytoui_isOnScreen = True
        self._pytoui_closeEvent.clear()
        self._needsDisplay = True
        # Forse first resize
        self.pytoui_layout(force=True)

        # if frame was not redefined use size_to_fit()
        if not self._pytoui_hasInitialFrame:
            self.sizeToFit()

        animated = animated and not _UI_DISABLE_ANIMATIONS

        launch_runtime(self, _RenderLoop(self, animated))

    def close(self):
        """Close a view that was presented via View.present()."""
        if not self._pytoui_isPresented:
            return
        if hasattr(self._ref, "will_close"):
            self.will_close()
        self._pytoui_isOnScreen = False
        self._pytoui_isPresented = False
        self._pytoui_closeEvent.set()

    def wait_modal(self):
        """Block until the view is dismissed."""
        if not self._pytoui_isOnScreen:
            return
        self._pytoui_closeEvent.wait()

    def becomeFirstResponder(self) -> None:
        from pytoui.base_runtime import get_runtime_for_view

        rt = get_runtime_for_view(self)
        if rt is None:
            # return False
            return
        rt._set_first_responder(self)
        # return True


class _View:
    """Base class for all views.

    # Overridable hooks:

    ## Basic lifecycle
    - did_load() - Called after view is loaded
    - will_close() - Called before view closes
    - layout() - Called when view needs layout
    - draw() - Called to draw the view
    - update() - Called at update_interval

    ## Touch events
    - touch_began(touch) - Touch started
    - touch_moved(touch) - Touch moved
    - touch_ended(touch) - Touch ended

    ## Mouse events (desktop)
    - mouse_down(event) - Mouse button pressed
    - mouse_up(event) - Mouse button released
    - mouse_moved(event) - Mouse moved (without button)
    - mouse_dragged(event) - Mouse moved with button down
    - mouse_wheel(event) - Mouse wheel scrolled

    ## Keyboard (desktop only)
    - keyboard_frame_will_change(rect) - Keyboard about to change
    - keyboard_frame_did_change(rect) - Keyboard changed

    ## Responder chain (desktop only)
    - did_become_first_responder() - Became first responder
    - did_resign_first_responder() - Resigned first responder

    ## Keyboard shortcuts (hardware keyboard)
    - key_command(sender) - Shortcut triggered
        Called when a registered keyboard shortcut is triggered.
        sender – the dict returned by get_key_commands() that matched.
    """

    __slots__ = ("__internals_",)

    _internals_: _getset_descriptor["_View", "_ViewInternals"] = _getset_descriptor(
        "internals_", factory=lambda obj: _ViewInternals(obj), readonly=True
    )

    # ── overridable hooks ─────────────────────────────────────────────────────

    # Basic lifecycle
    did_load: Callable[[], None]  # Called after view is loaded
    will_close: Callable[[], None]  # Called before view closes
    layout: Callable[[], None]  # Called when view needs layout
    draw: Callable[[], None]  # Called to draw the view
    # NOTE: View.update() is an implicit behaviour
    update: Callable[[], None]  # Called at update_interval

    # Touch events
    touch_began: Callable[[Touch], None]  # Touch started
    touch_moved: Callable[[Touch], None]  # Touch moved
    touch_ended: Callable[[Touch], None]  # Touch ended

    # Mouse events (desktop)
    mouse_down: Callable[[MouseEvent], None]  # Mouse button pressed
    mouse_up: Callable[[MouseEvent], None]  # Mouse button released
    mouse_moved: Callable[[MouseEvent], None]  # Mouse moved (without button)
    mouse_dragged: Callable[[MouseEvent], None]  # Mouse moved with button down
    mouse_wheel: Callable[[MouseWheel], None]  # Mouse wheel scrolled

    # Keyboard (desktop only)
    keyboard_frame_will_change: Callable[[Rect], None]  # Keyboard about to change
    keyboard_frame_did_change: Callable[[Rect], None]  # Keyboard changed

    # Responder chain (desktop only)
    did_become_first_responder: Callable[[], None]  # Became first responder
    did_resign_first_responder: Callable[[], None]  # Resigned first responder

    # Keyboard commands (for hardware keyboard)
    key_command: Callable[[dict], None]  # Shortcut triggered

    # ── initialization ────────────────────────────────────────────────────────────
    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    # ── properties ────────────────────────────────────────────────────────────

    @property
    def alpha(self) -> float:
        """The view's alpha value as a float in the range 0.0 to 1.0."""
        return self._internals_.alpha()

    @alpha.setter
    def alpha(self, value: float):
        self._internals_.setAlpha_(value)

    @property
    def background_color(self) -> _RGBA:
        """The view's background color, defaults to None (transparent)."""
        return self._internals_.backgroundColor()

    @background_color.setter
    def background_color(self, value: _ColorLike):
        self._internals_.setBackgroundColor_(value)

    # bg_color as alias
    bg_color = background_color

    @property
    def border_color(self) -> _RGBA:
        """The view's border color (only has effect if border_width > 0)."""
        return self._internals_.pytoui_borderColor()

    @border_color.setter
    def border_color(self, value: _ColorLike):
        self._internals_.pytoui_setBorderColor_(value)

    @property
    def border_width(self) -> float:
        """The view's border width, defaults to zero (no border)."""
        return self._internals_.pytoui_borderWidth()

    @border_width.setter
    def border_width(self, value: float):
        self._internals_.pytoui_setBorderWidth_(value)

    @property
    def bounds(self) -> Rect:
        """The view's location and size in its own coordinate system."""
        return self._internals_.bounds()

    @bounds.setter
    def bounds(self, value: _RectLike):
        self._internals_.setBounds_(value)

    @property
    def center(self) -> Point:
        """The center of the view's frame as a Point."""
        return self._internals_.frame().center()

    @center.setter
    def center(self, value: _PointLike):
        cx, cy = value
        w, h = self._internals_.frame().size
        self.frame = Rect(cx - w / 2, cy - h / 2, w, h)

    @property
    def x(self) -> float:
        """Shortcut for the x component of the view's frame."""
        return self._internals_.frame().x

    @x.setter
    def x(self, value: float):
        f = self._internals_.frame()
        self.frame = Rect(value, f.y, f.w, f.h)

    @property
    def y(self) -> float:
        """Shortcut for the y component of the view's frame."""
        return self._internals_.frame().y

    @y.setter
    def y(self, value: float):
        f = self._internals_.frame()
        self.frame = Rect(f.x, value, f.w, f.h)

    @property
    def width(self) -> float:
        """Shortcut for the width component of the view's frame."""
        return self._internals_.frame().w

    @width.setter
    def width(self, value: float):
        f = self._internals_.frame()
        self.frame = Rect(f.x, f.y, value, f.h)

    @property
    def height(self) -> float:
        """Shortcut for the height component of the view's frame."""
        return self._internals_.frame().h

    @height.setter
    def height(self, value: float):
        f = self._internals_.frame()
        self.frame = Rect(f.x, f.y, f.w, value)

    @property
    def content_mode(self) -> _ContentMode:
        """Determines how a view lays out its content when its bounds change."""
        return self._internals_.contentMode()

    @content_mode.setter
    def content_mode(self, value: _ContentMode):
        self._internals_.setContentMode_(value)

    @property
    def corner_radius(self) -> float:
        """The view's corner radius."""
        return self._internals_._cornerRadius()

    @corner_radius.setter
    def corner_radius(self, value: float):
        self._internals_._setCornerRadius_(value)

    @property
    def flex(self) -> _ViewFlex:
        """The autoresizing behavior of the view."""
        return self._internals_.pytoui_flex()

    @flex.setter
    def flex(self, value: _ViewFlex):
        self._internals_.pytoui_setFlex_(value)

    autoresizing = flex

    @property
    def frame(self) -> Rect:
        """The view's position and size in the coordinate system of its superview."""
        return self._internals_.frame()

    @frame.setter
    def frame(self, value: _RectLike):
        self._internals_.setFrame_(value)

    @property
    def hidden(self) -> bool:
        """Determines if the view is hidden."""
        return self._internals_.isHidden()

    @hidden.setter
    def hidden(self, value: bool):
        self._internals_.setHidden_(value)

    @property
    def name(self) -> str:
        """A string that identifies the view."""
        return self._internals_.name()

    @name.setter
    def name(self, value: str):
        self._internals_.setName_(value)

    @property
    def on_screen(self) -> bool:
        """(readonly) Whether the view is part of
        a view hierarchy currently on screen."""
        return self._internals_.pytoui_isOnScreen()

    @property
    def subviews(self) -> tuple[_View, ...]:
        """(readonly) A tuple of the view's children."""
        return tuple(sv.ref() for sv in self._internals_.subviews())

    @property
    def superview(self) -> _View | None:
        """(readonly) The view's parent view."""
        sv = self._internals_.superview()
        if sv is not None:
            return sv.ref()
        return None

    @property
    def navigation_view(self) -> _NavigationView | None:
        """(readonly) The view's navigation_view view."""
        sv = self._internals_.pytoui_navigationView()
        if sv is not None:
            return cast(_NavigationView, sv.ref())
        return None

    @property
    def tint_color(self) -> _RGBA:
        """The view's tint color, inherited from superview if None."""
        return self._internals_.tintColor()

    @tint_color.setter
    def tint_color(self, value: _ColorLike):
        self._internals_.setTintColor_(value)

    @property
    def left_button_items(self) -> tuple[ButtonItem, ...] | None:
        return self._internals_.pytoui_leftButtonItems()

    @left_button_items.setter
    def left_button_items(self, value: Sequence[ButtonItem] | None):
        self._internals_.pytoui_setLeftButtonItems_(value)

    @property
    def right_button_items(self) -> tuple[ButtonItem, ...] | None:
        return self._internals_.pytoui_rightButtonItems()

    @right_button_items.setter
    def right_button_items(self, value: Sequence[ButtonItem] | None):
        self._internals_.pytoui_setRightButtonItems_(value)

    @property
    def touch_enabled(self) -> bool:
        return self._internals_.pytoui_isTouchEnabled()

    @touch_enabled.setter
    def touch_enabled(self, value: bool):
        self._internals_.pytoui_setTouchEnabled_(value)

    @property
    def multitouch_enabled(self) -> bool:
        """If True, the view receives all simultaneous touches.
        If False (default), only the first touch is tracked."""
        return self._internals_.isMultipleTouchEnabled()

    @multitouch_enabled.setter
    def multitouch_enabled(self, value: bool):
        self._internals_.setMultipleTouchEnabled_(value)

    @property
    def mouse_wheel_enabled(self) -> bool:
        """Alias for scroll_enabled."""
        return self._internals_.pytoui_isMouseWheelEnabled()

    @mouse_wheel_enabled.setter
    def mouse_wheel_enabled(self, value: bool):
        self._internals_.pytoui_setMouseWheelEnabled_(value)

    @property
    def transform(self) -> Transform | None:
        """The transform applied to the view relative to the center of its bounds."""
        return self._internals_.transform()

    @transform.setter
    def transform(self, value: Transform | None):
        self._internals_.setTransform_(value)

    @property
    def update_interval(self) -> float:
        """Interval between update() calls in seconds. 0 disables updates."""
        return self._internals_.pytoui_updateInterval()

    @update_interval.setter
    def update_interval(self, value: float):
        self._internals_.pytoui_setUpdateInterval_(value)

    # ── subview management ────────────────────────────────────────────────────

    def __getitem__(self, name: str) -> _View:
        return self._internals_[name].ref()

    def add_subview(self, view: _View):
        """Add another view as a child of this view."""
        self._internals_.addSubview_(view._internals_)

    def remove_subview(self, view: _View):
        """Remove a child view."""
        self._internals_.pytoui_removeSubview(view._internals_)

    def bring_to_front(self):
        """Show the view on top of its sibling views."""
        self._internals_.bringSubviewToFront_()

    def send_to_back(self):
        """Put the view behind its sibling views."""
        self._internals_.sendSubviewToBack_()

    # ── layout ────────────────────────────────────────────────────────────────

    def set_needs_display(self):
        """Mark the view as needing to be redrawn."""
        self._internals_.setNeedsDisplay()

    def size_to_fit(self):
        """Resize to enclose all subviews."""
        self._internals_.sizeToFit()

    def draw_snapshot(self):
        self._internals_.pytoui_drawSnapshot()

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

    def become_first_responder(self) -> None:
        """Ask the owning window to make this view the first responder.

        Returns True if the runtime was found and the request was accepted,
        False if the view is not attached to any window.
        When this view becomes the first responder the previous one
        automatically loses it (resign is implicit, no public resign call).
        """
        self._internals_.becomeFirstResponder()

    def get_key_commands(self) -> list[dict[str, str]]:
        """Return keyboard shortcuts

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

    # ObjC-compat
    @property
    def objc_instance(self) -> _ViewInternals:
        return self._internals_

    @property
    def _objc_ptr(self) -> int:
        return id(self._internals_)

    def _debug_quicklook_(self):
        return self._internals_.__repr__()


if not IS_PYTHONISTA:

    class View(_View):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
else:
    import ui

    View = ui.View  # type: ignore[assignment,misc]
