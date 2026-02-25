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
from pytoui.ui._types import Touch

if TYPE_CHECKING:
    from pytoui.ui._view import _View, _ViewInternals

__all__ = ("CHECKER_SIZE", "BaseRuntime", "_any_dirty", "_get_runtime_for_view")

CHECKER_SIZE = 8

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
    for sv in view.subviews:
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
        # touch_id == -1 is the mouse pointer; >= 0 are real touch fingers
        self._tracked: dict[int, _ViewInternals] = {}
        self._last_pos: dict[int, tuple[float, float]] = {}

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

        if not target.multitouch_enabled and any(
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
    # Update loop
    # ------------------------------------------------------------------

    def _update_hierarchy(self, view: _ViewInternals, now: float):
        if view.update_interval > 0:
            if now - view.pytoui_last_update_t >= view.update_interval:
                view.pytoui_update()
                view.pytoui_last_update_t = now
        for sv in view.subviews:
            self._update_hierarchy(sv, now)
