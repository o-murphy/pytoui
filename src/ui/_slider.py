from __future__ import annotations
import os
from typing import TYPE_CHECKING

import time

try:
    from ui import View, Touch, Rect, set_color, Path
except ImportError:
    from ui._view import View
    from ui._types import Touch, Rect
    from ui._draw import set_color, Path

if TYPE_CHECKING:
    from ui._types import _Action

__all__ = ("Slider",)

_UI_DISABLE_ANIMATIONS = os.environ.get(
    "UI_DISABLE_ANIMATIONS", "0"
).strip().strip().lower() in (
    "true",
    "1",
    "yes",
    "y",
)


class Slider(View):
    __final__ = True

    __slots__ = (
        "_action",
        "_enabled",
        "_value",
        "_continuous",
        "_tracked",
        "_anim_value",
        "_thumb_scale",
        "_last_time",
        "__animations_disabled",
    )

    _IOS_BLUE = (0.0, 0.48, 1.0, 1.0)
    _IOS_TRACK = (0.85, 0.85, 0.85, 1.0)
    _LOGICAL_HEIGHT = 31.0

    def __init__(self):
        self._action: _Action | None = None
        self._enabled: bool = True
        self._value: float = 0.0
        self._continuous: bool = True

        # Animation states
        self._anim_value = 0.0
        self._thumb_scale = 1.0
        self._tracked = False
        self._last_time = time.time()

        # Standard iOS slider size
        self.frame = Rect(0, 0, 200, 31)

        self.__animations_disabled: bool = False

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
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, val: float):
        new_val = max(0.0, min(1.0, float(val)))
        if self._value != new_val:
            self._value = new_val
            # If animations are disabled, sync visual value instantly
            if self._animations_disabled:
                self._anim_value = self._value
            self.set_needs_display()

    @property
    def continuous(self) -> bool:
        return self._continuous

    @continuous.setter
    def continuous(self, value: bool):
        self._continuous = value

    def draw(self):
        now = time.time()
        dt = now - self._last_time
        self._last_time = now

        dt = min(max(dt, 0.001), 0.033)

        needs_redraw = False

        if self._animations_disabled:
            self._anim_value = self._value
            self._thumb_scale = 1.15 if self._tracked else 1.0
        else:
            if self._tracked:
                self._anim_value = self._value
            else:
                lerp_factor = 1.0 - (0.00005**dt)
                val_diff = self._value - self._anim_value
                if abs(val_diff) > 0.0005:
                    self._anim_value += val_diff * lerp_factor
                    needs_redraw = True
                else:
                    self._anim_value = self._value

            target_scale = 1.15 if self._tracked else 1.0
            scale_speed = 0.0001 if self._tracked else 0.01
            scale_lerp = 1.0 - (scale_speed**dt)

            scale_diff = target_scale - self._thumb_scale
            if abs(scale_diff) > 0.002:
                self._thumb_scale += scale_diff * scale_lerp
                needs_redraw = True
            else:
                self._thumb_scale = target_scale

        if needs_redraw:
            self.set_needs_display()

        # 🔹 LOGICAL HEIGHT
        h = self._LOGICAL_HEIGHT
        oy = (self.height - h) * 0.5
        mid_y = oy + h * 0.5

        track_h = 4.0
        thumb_radius = 14.0 * self._thumb_scale

        margin = 15.0
        available_width = self.width - (margin * 2)
        pos_x = margin + (available_width * self._anim_value)

        # 1️⃣ Background track
        set_color(self._IOS_TRACK)
        Path.rounded_rect(
            margin,
            mid_y - track_h / 2,
            available_width,
            track_h,
            track_h / 2,
        ).fill()

        # 2️⃣ Active track
        set_color(self._IOS_BLUE)
        Path.rounded_rect(
            margin,
            mid_y - track_h / 2,
            pos_x - margin,
            track_h,
            track_h / 2,
        ).fill()

        # 3️⃣ Thumb

        # Drop shadow
        set_color((0, 0, 0, 0.15))
        Path.oval(
            pos_x - thumb_radius,
            mid_y - thumb_radius + 2.0,
            thumb_radius * 2,
            thumb_radius * 2,
        ).fill()

        # Ambient shadow
        set_color((0, 0, 0, 0.06))
        Path.oval(
            pos_x - thumb_radius - 0.5,
            mid_y - thumb_radius - 0.5,
            (thumb_radius + 0.5) * 2,
            (thumb_radius + 0.5) * 2,
        ).fill()

        # White body
        set_color("white")
        Path.oval(
            pos_x - thumb_radius,
            mid_y - thumb_radius,
            thumb_radius * 2,
            thumb_radius * 2,
        ).fill()

        # Border
        set_color((0, 0, 0, 0.04))
        p = Path.oval(
            pos_x - thumb_radius,
            mid_y - thumb_radius,
            thumb_radius * 2,
            thumb_radius * 2,
        )
        p.line_width = 0.5
        p.stroke()

    def _update_value_from_touch(self, touch: Touch):
        margin = 15.0
        available_width = self.width - (margin * 2)
        if available_width <= 0:
            return

        local_x = touch.location[0] - margin
        self.value = max(0.0, min(1.0, local_x / available_width))

    def touch_began(self, touch: Touch):
        if not self.enabled:
            return

        x, y = touch.location

        if not self._point_inside_slider(x, y):
            return

        self._tracked = True
        self._last_time = time.time()
        self._update_value_from_touch(touch)  # type: ignore[attr-defined]

        if self.continuous:
            self._ensure_action_and_call(self)  # type: ignore[attr-defined]

        self.set_needs_display()

    def touch_moved(self, touch: Touch):
        if self._tracked and self.enabled:
            self._update_value_from_touch(touch)
            if self.continuous:
                self._ensure_action_and_call(self)  # type: ignore[attr-defined]

    def touch_ended(self, touch: Touch):
        if self._tracked:
            self._tracked = False
            if self.enabled:
                self._update_value_from_touch(touch)
                self._ensure_action_and_call(self)  # type: ignore[attr-defined]
            self.set_needs_display()

    def _slider_bounds(self):
        h = self._LOGICAL_HEIGHT
        oy = (self.height - h) * 0.5
        return oy, h

    def _point_inside_slider(self, x: float, y: float) -> bool:
        oy, h = self._slider_bounds()
        return oy <= y <= oy + h

    def _ensure_action_and_call(self, sender=None):
        action = getattr(self, "action", None)
        if action is None:
            return
        import inspect

        if len(inspect.signature(action).parameters) > 0:
            action(sender if sender is not None else self)
        else:
            action()

    # ── animation ─────────────────────────────────────────────────────────────

    @property
    def _animations_disabled(self) -> bool:
        return self.__animations_disabled or _UI_DISABLE_ANIMATIONS

    @_animations_disabled.setter
    def _animations_disabled(self, value: bool) -> None:
        self.__animations_disabled = value
