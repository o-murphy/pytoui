"""Base class for all UI runtimes.

Provides shared touch handling, view hit-testing, and first-responder
tracking so that SDLRuntime, WinitRuntime, and RawFrameBufferRuntime
do not duplicate logic.

Per-window first-responder
--------------------------
Each BaseRuntime instance tracks its own _first_responder.  View.become_first_responder()
walks up to the root view, looks up the owning runtime in _root_to_runtime, and
delegates to _set_first_responder().
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from pytoui.ui._draw import _screen_origin, convert_point
from pytoui.ui._types import Touch

if TYPE_CHECKING:
    from pytoui.ui._view import View

__all__ = ("BaseRuntime", "find_view_at", "_any_dirty", "CHECKER_SIZE")

CHECKER_SIZE = 8

# id(root_view) → runtime  (used by View.become_first_responder)
_root_to_runtime: dict[int, "BaseRuntime"] = {}


def _get_runtime_for_view(view: "View") -> "BaseRuntime | None":
    root = view
    while root._superview is not None:
        root = root._superview
    return _root_to_runtime.get(id(root))


def _any_dirty(view: "View") -> bool:
    """Return True if view or any descendant needs redrawing."""
    if view._needs_display:
        return True
    for sv in view._subviews:
        if _any_dirty(sv):
            return True
    return False


def find_view_at(view: "View", screen_x: float, screen_y: float) -> "View | None":
    """Return the topmost touch-enabled View at the given screen coordinates."""
    if view.hidden:
        return None
    ox, oy = _screen_origin(view)
    fw, fh = view._frame.w, view._frame.h
    if not (ox <= screen_x < ox + fw and oy <= screen_y < oy + fh):
        return None
    for child in reversed(view.subviews):
        target = find_view_at(child, screen_x, screen_y)
        if target is not None and target.touch_enabled:
            return target
    return view if view.touch_enabled else None


class BaseRuntime:
    """Shared base for all UI runtimes.

    Subclasses must implement _run(self) with the platform event loop and
    call self._unregister() when the window closes.
    """

    def __init__(self, root_view: "View", width: int, height: int, render_fn):
        self.root = root_view
        self.width = width
        self.height = height
        self.render_fn = render_fn

        # touch_id → tracked view / last screen position
        # touch_id == -1 is the mouse pointer; >= 0 are real touch fingers
        self._tracked: dict[int, "View"] = {}
        self._last_pos: dict[int, tuple[float, float]] = {}

        # Per-window first responder
        self._first_responder: "View | None" = None

        _root_to_runtime[id(root_view)] = self

    @property
    def current_size(self) -> tuple[int, int]:
        """Current window dimensions in pixels. Subclasses may override for live resize."""
        return (self.width, self.height)

    def _unregister(self) -> None:
        _root_to_runtime.pop(id(self.root), None)

    # ------------------------------------------------------------------
    # First responder
    # ------------------------------------------------------------------

    def _set_first_responder(self, view: "View | None") -> None:
        old = self._first_responder
        if old is view:
            return
        if old is not None:
            old._did_resign_first_responder()
        self._first_responder = view
        if view is not None:
            view._did_become_first_responder()

    # ------------------------------------------------------------------
    # Touch handling
    # ------------------------------------------------------------------

    def _create_touch(
        self, view: "View", screen_x, screen_y, phase, touch_id, prev_pos
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
        target = find_view_at(self.root, x, y)
        if target:
            if not target.multitouch_enabled and any(
                v is target for v in self._tracked.values()
            ):
                return
            self._tracked[touch_id] = target
            target.touch_began(
                self._create_touch(target, x, y, "began", touch_id, (x, y))
            )

    def _touch_move(self, x, y, touch_id):
        prev = self._last_pos.get(touch_id, (x, y))
        self._last_pos[touch_id] = (x, y)
        target = self._tracked.get(touch_id)
        if not target:
            return
        phase = "moved" if (x, y) != prev else "stationary"
        target.touch_moved(self._create_touch(target, x, y, phase, touch_id, prev))

    def _touch_up(self, x, y, touch_id):
        prev = self._last_pos.pop(touch_id, (x, y))
        target = self._tracked.pop(touch_id, None)
        if not target:
            return
        current = find_view_at(self.root, x, y)
        phase = "ended" if current is target else "cancelled"
        target.touch_ended(self._create_touch(target, x, y, phase, touch_id, prev))

    def _touch_cancel(self, touch_id):
        x, y = self._last_pos.pop(touch_id, (0.0, 0.0))
        target = self._tracked.pop(touch_id, None)
        if target:
            target.touch_ended(
                self._create_touch(target, x, y, "cancelled", touch_id, (x, y))
            )

    # ------------------------------------------------------------------
    # Update loop
    # ------------------------------------------------------------------

    def _update_hierarchy(self, view: "View", now: float):
        if view.update_interval > 0:
            if now - view._last_update_t >= view.update_interval:
                view.update()
                view._last_update_t = now
        for sv in view.subviews:
            self._update_hierarchy(sv, now)
