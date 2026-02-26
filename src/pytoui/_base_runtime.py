"""Base class for all UI runtimes.

Provides shared touch handling, view hit-testing, and first-responder
tracking so that SDLRuntime, WinitRuntime, and RawFrameBufferRuntime
do not duplicate logic.

Per-window first-responder
--------------------------
Each BaseRuntime instance tracks its own _first_responder.
View.become_first_responder()
walks up to the root view, looks up the owning runtime in _root_to_runtime, and
delegates to _set_first_responder().
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from pytoui.ui._draw import convert_point
from pytoui.ui._types import _MOUSE_LEFT_ID, Touch

if TYPE_CHECKING:
    from pytoui.ui._view import _View, _ViewInternals

__all__ = (
    "_CHECKER_SIZE",
    "BaseRuntime",
    "_any_dirty",
    "_get_runtime_for_view",
    "_SCROLL_LINE_PX",
)

_SCROLL_LINE_PX: float = 20.0  # pixels per scroll "line" (for LineDelta)

_CHECKER_SIZE = 8

# id(root_view) → runtime  (used by View.become_first_responder)
_root_to_runtime: dict[int, BaseRuntime] = {}


def _get_runtime_for_view(view: _ViewInternals) -> BaseRuntime | None:
    root = view
    while root.superview is not None:
        root = root.superview
    return _root_to_runtime.get(id(root))


def _any_dirty(view: _ViewInternals) -> bool:
    """Return True if view or any descendant needs redrawing."""
    if view.pytoui_needs_display:
        return True
    for sv in view._subviews:
        if _any_dirty(sv):
            return True
    return False


class BaseRuntime:
    """Shared base for all UI runtimes.

    Subclasses must implement _run(self) with the platform event loop and
    call self._unregister() when the window closes.
    """

    def __init__(self, root_view: _ViewInternals, width: int, height: int, render_fn):
        self.root = root_view
        self.width = width
        self.height = height
        self.render_fn = render_fn

        # touch_id → tracked view / last screen position
        # -1 = left mouse (MOUSE_LEFT_ID)
        # -2 = right mouse (MOUSE_RIGHT_ID)
        # -3 = middle mouse (MOUSE_MIDDLE_ID)
        # -4 = scroll wheel (SCROLL_TOUCH_ID, synthetic only)
        # >= 0 = real touch fingers
        self._tracked: dict[int, _ViewInternals] = {}
        self._last_pos: dict[int, tuple[float, float]] = {}
        self._held_mouse_buttons: set[int] = set()

        # Per-window first responder
        self._first_responder: _ViewInternals | None = None

        _root_to_runtime[id(root_view)] = self

    @property
    def current_size(self) -> tuple[int, int]:
        """Current window dimensions in pixels.
        Subclasses may override for live resize."""
        return (self.width, self.height)

    def _unregister(self) -> None:
        _root_to_runtime.pop(id(self.root), None)

    # ------------------------------------------------------------------
    # First responder
    # ------------------------------------------------------------------

    def _set_first_responder(self, view: _ViewInternals | None) -> None:
        old = self._first_responder
        if old is view:
            return
        if old is not None:
            old.pytoui_did_resign_first_responder()
        self._first_responder = view
        if view is not None:
            view.pytoui_did_become_first_responder()

    # ------------------------------------------------------------------
    # Touch handling
    # ------------------------------------------------------------------

    def _create_touch(
        self,
        view: _View,
        screen_x,
        screen_y,
        phase,
        touch_id,
        prev_pos,
    ) -> Touch:
        local = convert_point((screen_x, screen_y), to_view=view)
        prev_local = convert_point(prev_pos, to_view=view)
        return Touch(
            location=(local.x, local.y),
            phase=phase,
            prev_location=(prev_local.x, prev_local.y),
            timestamp=int(time.time() * 1000),
            touch_id=touch_id,
        )

    def _touch_down(self, x, y, touch_id):
        self._last_pos[touch_id] = (x, y)
        target = self.root.pytoui_hit_test(x, y)
        if not target:
            return
        touch_began = target.pytoui_touch_began
        if not touch_began:
            return

        if not target._multitouch_enabled and any(
            v is target for v in self._tracked.values()
        ):
            return
        self._tracked[touch_id] = target
        touch_began(self._create_touch(target, x, y, "began", touch_id, (x, y)))

    def _touch_move(self, x, y, touch_id):
        prev = self._last_pos.get(touch_id, (x, y))
        self._last_pos[touch_id] = (x, y)
        target = self._tracked.get(touch_id)
        if not target:
            return
        touch_moved = target.pytoui_touch_moved
        if not touch_moved:
            return
        phase = "moved" if (x, y) != prev else "stationary"
        touch_moved(self._create_touch(target, x, y, phase, touch_id, prev))

    def _touch_up(self, x, y, touch_id):
        prev = self._last_pos.pop(touch_id, (x, y))
        target = self._tracked.pop(touch_id, None)
        if not target:
            return
        touch_ended = target.pytoui_touch_ended
        if not touch_ended:
            return
        current = self.root.pytoui_hit_test(x, y)
        phase = "ended" if current is target else "cancelled"
        touch_ended(self._create_touch(target, x, y, phase, touch_id, prev))

    def _touch_cancel(self, touch_id):
        x, y = self._last_pos.pop(touch_id, (0.0, 0.0))
        target = self._tracked.pop(touch_id, None)
        if not target:
            return
        touch_ended = target.pytoui_touch_ended
        if not touch_ended:
            return
        touch_ended(
            self._create_touch(target, x, y, "cancelled", touch_id, (x, y)),
        )

    # ------------------------------------------------------------------
    # Mouse handling (desktop-only — never called on real Pythonista)
    # ------------------------------------------------------------------

    def _create_mouse_event(self, view, x, y, phase, button_id, prev, buttons):
        from pytoui.ui._types import MouseEvent

        local = convert_point((x, y), to_view=view)
        prev_local = convert_point(prev, to_view=view)
        return MouseEvent(
            location=(local.x, local.y),
            phase=phase,
            prev_location=(prev_local.x, prev_local.y),
            timestamp=int(time.time() * 1000),
            touch_id=button_id,
            buttons=buttons,
        )

    def _mouse_down(self, x, y, button_id: int):
        self._held_mouse_buttons.add(button_id)
        self._last_pos[button_id] = (x, y)
        target = self.root.pytoui_hit_test(x, y)
        if not target:
            return
        cb = target.pytoui_mouse_down
        if not cb:
            return
        self._tracked[button_id] = target
        cb(
            self._create_mouse_event(
                target,
                x,
                y,
                "began",
                button_id,
                (x, y),
                frozenset(self._held_mouse_buttons),
            )
        )

    def _mouse_up(self, x, y, button_id: int):
        self._held_mouse_buttons.discard(button_id)
        prev = self._last_pos.pop(button_id, (x, y))
        target = self._tracked.pop(button_id, None)
        if not target:
            return
        cb = target.pytoui_mouse_up
        if not cb:
            return
        current = self.root.pytoui_hit_test(x, y)
        phase = "ended" if current is target else "cancelled"
        cb(
            self._create_mouse_event(
                target,
                x,
                y,
                phase,
                button_id,
                prev,
                frozenset(self._held_mouse_buttons),
            )
        )

    def _mouse_dragged(self, x, y, button_id: int):
        prev = self._last_pos.get(button_id, (x, y))
        self._last_pos[button_id] = (x, y)
        target = self._tracked.get(button_id)
        if not target:
            return
        cb = target.pytoui_mouse_dragged
        if not cb:
            return
        phase = "moved" if (x, y) != prev else "stationary"
        cb(
            self._create_mouse_event(
                target,
                x,
                y,
                phase,
                button_id,
                prev,
                frozenset(self._held_mouse_buttons),
            )
        )

    def _mouse_moved(self, x, y):
        target = self.root.pytoui_hit_test(x, y)
        if not target:
            return
        cb = target.pytoui_mouse_moved
        if not cb:
            return
        cb(
            self._create_mouse_event(
                target,
                x,
                y,
                "moved",
                _MOUSE_LEFT_ID,
                (x, y),
                frozenset(),
            )
        )

    def _mouse_cancel(self, button_id: int):
        self._held_mouse_buttons.discard(button_id)
        x, y = self._last_pos.pop(button_id, (0.0, 0.0))
        target = self._tracked.pop(button_id, None)
        if not target:
            return
        cb = target.pytoui_mouse_up
        if not cb:
            return
        cb(
            self._create_mouse_event(
                target,
                x,
                y,
                "cancelled",
                button_id,
                (x, y),
                frozenset(self._held_mouse_buttons),
            )
        )

    def _scroll_event(
        self, cursor_x: float, cursor_y: float, dx: float, dy: float
    ) -> None:
        """Dispatch a MouseWheel event to the view under the cursor.

        cursor_x/y — screen coords of the mouse cursor (supplied by the runtime).
        dx/dy      — scroll delta in pixels (positive dy = scroll up).
        """
        from pytoui.ui._types import MouseWheel

        target = self.root.pytoui_hit_test(cursor_x, cursor_y)
        if not target:
            return
        cb = target.pytoui_mouse_wheel
        if not cb:
            return
        local = convert_point((cursor_x, cursor_y), to_view=target)
        cb(
            MouseWheel(
                location=(local.x, local.y),
                phase="moved",
                prev_location=(local.x, local.y),
                timestamp=int(time.time() * 1000),
                buttons=frozenset(self._held_mouse_buttons),
                scroll_dx=dx,
                scroll_dy=dy,
            )
        )

    # ------------------------------------------------------------------
    # Update loop
    # ------------------------------------------------------------------

    def _update_hierarchy(self, view: _ViewInternals, now: float):
        if view.update_interval > 0:
            if now - view.pytoui_last_update_time >= view.update_interval:
                view.pytoui_update()
                view.pytoui_last_update_time = now
        for sv in view._subviews:
            self._update_hierarchy(sv, now)
