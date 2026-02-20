from __future__ import annotations

import time
from typing import Sequence, TYPE_CHECKING

from pytoui.ui._constants import ALIGN_CENTER, _UI_DISABLE_ANIMATIONS
from pytoui.ui._view import View
from pytoui.ui._types import Touch, Rect
from pytoui.ui._draw import Path, set_color, draw_string

if TYPE_CHECKING:
    from pytoui.ui._types import _Action


__all__ = ("SegmentedControl",)


class SegmentedControl(View):
    __final__ = True

    __slots__ = (
        "_action",
        "_enabled",
        "_segments",
        "_selected_index",
        "_anim_index",
        "_last_time",
        "_tracked",
        "_press_scale",
        "_target_scale",
        "_press_start_time",
        "__animations_disabled",
    )

    _DEFAULT_MARGIN = 2.0
    _IOS_GRAY_BG = (0.89, 0.89, 0.91, 1.0)
    _IOS_WHITE_SEL = (1.0, 1.0, 1.0, 1.0)
    _TEXT_COLOR = (0.0, 0.0, 0.0, 1.0)

    def __init__(self):
        self._action: _Action | None = None
        self._enabled: bool = True
        self._segments: Sequence[str] = []
        self._selected_index = 0
        self._anim_index = 0.0

        # Press scale animation
        self._press_scale = 1.0
        self._target_scale = 1.0
        self._press_start_time = 0.0

        self._last_time = time.time()
        self._tracked = False

        self._frame = Rect(0.00, 0.00, 120.0, 32.0)

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
    def selected_index(self) -> int:
        return self._selected_index

    @selected_index.setter
    def selected_index(self, value: int):
        count = len(self._segments)
        new_index = max(0, min(value, count - 1)) if count > 0 else -1
        if self._selected_index != new_index:
            self._selected_index = new_index
            if self._animations_disabled:
                self._anim_index = float(self._selected_index)
            self.set_needs_display()

    @property
    def segments(self) -> Sequence[str]:
        return self._segments

    @segments.setter
    def segments(self, segments: Sequence[str]):
        self._segments = segments
        self._selected_index = (
            max(0, min(self._selected_index, len(segments) - 1)) if segments else -1
        )
        self._anim_index = float(self._selected_index)
        self.set_needs_display()

    def draw(self):
        now = time.time()
        # dt clamping for stability during lag
        dt = min(now - self._last_time, 0.05)
        self._last_time = now

        segments = self.segments
        count = len(segments)
        if count == 0:
            return

        # --- ANIMATION ---
        needs_redraw = False

        if self._tracked:
            elapsed = now - self._press_start_time
            # Squeezing starts after 0.03s (iOS feel)
            self._target_scale = 0.95 if elapsed > 0.03 else 1.0
        else:
            self._target_scale = 1.0

        if self._animations_disabled:
            self._anim_index = float(self._selected_index)
            self._press_scale = self._target_scale
        else:
            # Use same formula as Switch/Button for consistency
            lerp_speed = 1.0 - (0.00005**dt)

            # Slider animation
            diff_idx = float(self._selected_index) - self._anim_index
            if abs(diff_idx) > 0.001:
                self._anim_index += diff_idx * lerp_speed
                needs_redraw = True
            else:
                self._anim_index = float(self._selected_index)

            # Scale animation
            diff_scale = self._target_scale - self._press_scale
            if abs(diff_scale) > 0.001:
                self._press_scale += diff_scale * lerp_speed
                needs_redraw = True
            else:
                self._press_scale = self._target_scale

        if needs_redraw:
            self.set_needs_display()

        # --- DRAWING ---
        w, h = self.width, self.height
        margin = self._DEFAULT_MARGIN
        segment_width = w / count
        radius = 8.0

        # 1. Container background
        set_color(self._IOS_GRAY_BG)
        Path.rounded_rect(0, 0, w, h, radius).fill()

        # 2. Selection slider (pill)
        sel_x = self._anim_index * segment_width

        # Pill geometry
        sw = segment_width - 2 * margin
        sh = h - 2 * margin

        # Calculate scaling relative to the segment center
        scaled_sw = sw * self._press_scale
        scaled_sh = sh * self._press_scale
        offset_x = (sw - scaled_sw) / 2
        offset_y = (sh - scaled_sh) / 2

        # Draw pill shadow and background
        set_color((0, 0, 0, 0.04))  # Subtle shadow
        Path.rounded_rect(
            sel_x + margin + offset_x,
            margin + offset_y + 0.5,
            scaled_sw,
            scaled_sh,
            radius - margin,
        ).fill()

        set_color(self._IOS_WHITE_SEL)
        Path.rounded_rect(
            sel_x + margin + offset_x,
            margin + offset_y,
            scaled_sw,
            scaled_sh,
            radius - margin,
        ).fill()

        # 3. Text labels
        for i, string in enumerate(segments):
            seg_x = i * segment_width
            r, g, b, a = self._TEXT_COLOR
            # Smoother text fading if disabled
            alpha = a if self.enabled else a * 0.3

            draw_string(
                string,
                rect=(seg_x, 0, segment_width, h),
                font=("<system>", 13.0),
                color=(r, g, b, alpha),
                alignment=ALIGN_CENTER,
            )

    def _get_index_at_location(self, x: float) -> int:
        count = len(self.segments)
        if count <= 0:
            return -1
        segment_width = self.width / count
        idx = int(x / segment_width)
        return max(0, min(idx, count - 1))

    def touch_began(self, touch: Touch):
        if not self.enabled:
            return

        x, y = touch.location
        # Start tracking only inside logical pill height
        if y < 0 or y > self.height:
            return

        self._tracked = True
        self._press_start_time = time.time()
        self._last_time = self._press_start_time
        self._target_scale = 1.0
        self.set_needs_display()

    def touch_moved(self, touch: Touch):
        if self._tracked and self.enabled:
            # Switch index during movement
            new_index = self._get_index_at_location(touch.location.x)
            if new_index != -1 and new_index != self._selected_index:
                self.selected_index = new_index
                self._ensure_action_and_call(self)  # type: ignore[attr-defined]

            # Bounds check to reset scale
            inside = (
                0 <= touch.location.x <= self.width
                and 0 <= touch.location.y <= self.height
            )
            if not inside:
                self._target_scale = 1.0

            self.set_needs_display()

    def touch_ended(self, touch: Touch):
        if self._tracked:
            self._target_scale = 1.0
            if self.enabled and touch.phase == "ended":
                new_index = self._get_index_at_location(touch.location.x)
                if new_index != -1 and new_index != self._selected_index:
                    self.selected_index = new_index
                    self._ensure_action_and_call(self)  # type: ignore[attr-defined]
            self.set_needs_display()
        self._tracked = False

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
