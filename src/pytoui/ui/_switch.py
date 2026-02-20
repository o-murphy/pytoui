from __future__ import annotations

import time
from typing import TYPE_CHECKING

from pytoui.ui._view import View
from pytoui.ui._types import Touch, Rect
from pytoui.ui._draw import set_color, Path
from pytoui.ui._constants import _UI_DISABLE_ANIMATIONS

if TYPE_CHECKING:
    from pytoui.ui._types import _Action

__all__ = ("Switch",)


class Switch(View):
    __final__ = True

    __slots__ = (
        "_action",
        "_enabled",
        "_value",
        "_background_image",
        "_image",
        "_title_label",
        "_anim_alpha",
        "_target_alpha",
        "_tracked",
        "_last_time",
        "_anim_progress",
        "_target_progress",
        "_did_change_during_move",
        "_press_start_time",
        "_current_stretch",
        "__animations_disabled",
    )

    _IOS_GREEN = (0.2, 0.78, 0.35, 1.0)
    _IOS_GRAY = (0.85, 0.85, 0.85, 1.0)
    _LOGICAL_WIDTH = 51.0
    _LOGICAL_HEIGHT = 31.0

    def __init__(self):
        self._action: _Action | None = None
        self._enabled: bool = True
        self._value: bool = False

        self._anim_progress = 0.0
        self._target_progress = 0.0
        self._tracked = False
        self._did_change_during_move = False

        self._press_start_time = 0.0
        self._current_stretch = 0.0
        self._last_time = time.time()

        self.__animations_disabled: bool = False

        self.frame = Rect(0, 0, 51, 31)

    @property
    def action(self) -> _Action | None:
        return self._action

    @action.setter
    def action(self, value: _Action | None):
        self._action = value

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        self.set_needs_display()

    @property
    def value(self) -> bool:
        return self._value

    @value.setter
    def value(self, value: bool):
        if self._value != value:
            self._value = value
            self._target_progress = 1.0 if value else 0.0
            if self._animations_disabled:
                self._anim_progress = self._target_progress
            else:
                self._last_time = time.time()
                self.update_interval = 1.0 / 60.0
            self.set_needs_display()

    def update(self):
        """Animation tick — driven by update_interval."""
        now = time.time()
        dt = min(now - self._last_time, 0.05)
        self._last_time = now

        if self._animations_disabled:
            self._anim_progress = self._target_progress
            self._current_stretch = 8.0 if self._tracked else 0.0
            self.update_interval = 0
            self.set_needs_display()
            return

        lerp_speed = 1.0 - (0.00005**dt)
        done = True

        # Slider progress animation
        diff = self._target_progress - self._anim_progress
        if abs(diff) > 0.0001:
            self._anim_progress += diff * lerp_speed
            done = False
        else:
            self._anim_progress = self._target_progress

        # Stretching logic (visual pill expansion on press)
        if self._tracked:
            elapsed = now - self._press_start_time
            target_stretch = min(8.0, max(0.0, (elapsed - 0.03) * 65.0))
        else:
            target_stretch = 0.0

        stretch_diff = target_stretch - self._current_stretch
        if abs(stretch_diff) > 0.01:
            self._current_stretch += stretch_diff * lerp_speed
            done = False
        else:
            self._current_stretch = target_stretch

        self.set_needs_display()

        if done and not self._tracked:
            self.update_interval = 0

    def draw(self):
        # Pure rendering — all state is read-only here
        p = self._anim_progress
        stretch = self._current_stretch

        w = self._LOGICAL_WIDTH
        h = self._LOGICAL_HEIGHT

        # Anchored to top-left of bounds
        ox = 0.0
        oy = 0.0

        press_dim = 0.96 if self._tracked else 1.0

        # Background color interpolation
        bg_r = (
            self._IOS_GRAY[0] + (self._IOS_GREEN[0] - self._IOS_GRAY[0]) * p
        ) * press_dim
        bg_g = (
            self._IOS_GRAY[1] + (self._IOS_GREEN[1] - self._IOS_GRAY[1]) * p
        ) * press_dim
        bg_b = (
            self._IOS_GRAY[2] + (self._IOS_GREEN[2] - self._IOS_GRAY[2]) * p
        ) * press_dim

        set_color((bg_r, bg_g, bg_b, 1.0))
        Path.rounded_rect(ox, oy, w, h, h / 2).fill()

        margin = 2.0
        base_pin_size = h - (margin * 2)
        pin_w = base_pin_size + stretch

        max_x_shift = w - base_pin_size - (margin * 2)
        current_x = margin + max_x_shift * p
        draw_x = ox + current_x - (stretch * p)
        draw_y = oy + margin

        # Shadow drawing
        set_color((0, 0, 0, 0.08))
        Path.rounded_rect(
            draw_x, draw_y + 0.5, pin_w, base_pin_size, base_pin_size / 2
        ).fill()

        # White pin body
        set_color("white")
        Path.rounded_rect(
            draw_x, draw_y, pin_w, base_pin_size, base_pin_size / 2
        ).fill()

    def touch_began(self, touch: Touch):
        if not self.enabled:
            return

        x, y = touch.location
        if not self._point_inside_switch(x, y):
            return

        self._tracked = True
        self._did_change_during_move = False
        self._press_start_time = time.time()
        self._last_time = time.time()

        if not self._animations_disabled:
            self.update_interval = 1.0 / 60.0
        self.set_needs_display()

    def touch_moved(self, touch: Touch):
        if not (self._tracked and self.enabled):
            return

        # Handle sliding to change value
        new_value = touch.location[0] > self.width / 2
        if new_value != self.value:
            self.value = new_value
            self._did_change_during_move = True
            self._ensure_action_and_call(self)  # type: ignore[attr-defined]

    def touch_ended(self, touch: Touch):
        if not (self._tracked and self.enabled):
            return

        self._tracked = False
        if touch.phase == "ended":
            # If it was a simple tap (no slide), toggle value
            if not self._did_change_during_move:
                self.value = not self.value
                self._ensure_action_and_call(self)  # type: ignore[attr-defined]

        # Continue animating stretch retraction if needed
        if self._current_stretch > 0.01 and not self._animations_disabled:
            self._last_time = time.time()
            self.update_interval = 1.0 / 60.0
        self.set_needs_display()

    def _switch_rect(self):
        return 0.0, 0.0, self._LOGICAL_WIDTH, self._LOGICAL_HEIGHT

    def _point_inside_switch(self, x: float, y: float) -> bool:
        ox, oy, w, h = self._switch_rect()
        return ox <= x <= ox + w and oy <= y <= oy + h

    def _ensure_action_and_call(self, sender=None):
        action = getattr(self, "action", None)
        if action is None:
            return
        import inspect

        if len(inspect.signature(action).parameters) > 0:
            action(sender if sender is not None else self)
        else:
            action()

    # ── animation settings ──────────────────────────────────────────────────

    @property
    def _animations_disabled(self) -> bool:
        return self.__animations_disabled or _UI_DISABLE_ANIMATIONS

    @_animations_disabled.setter
    def _animations_disabled(self, value: bool) -> None:
        self.__animations_disabled = value
