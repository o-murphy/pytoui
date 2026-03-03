from __future__ import annotations

import time
from collections.abc import Sequence
from typing import TYPE_CHECKING

from pytoui._platform import _UI_DISABLE_ANIMATIONS, IS_PYTHONISTA
from pytoui.ui._constants import ALIGN_CENTER, LB_TRUNCATE_TAIL
from pytoui.ui._draw import Path, draw_string, measure_string, set_color
from pytoui.ui._types import Rect, Touch
from pytoui.ui._view import View

if TYPE_CHECKING:
    from pytoui.ui._types import _Action


__all__ = ("SegmentedControl",)


class SegmentedControl(View):
    _final_ = True

    __slots__ = (
        "_action",
        "_anim_index",
        "_enabled",
        "_last_time",
        "_press_scale",
        "_press_start_time",
        "_segments",
        "_selected_index",
        "_tracked",
        "_tracking_index",
        "_anim_disabled",
    )

    _DEFAULT_MARGIN = 2.0
    _TEXT_INSET = 4.0  # Horizontal inset for text within segment
    _IOS_GRAY_BG = (0.89, 0.89, 0.91, 1.0)
    _IOS_WHITE_SEL = (1.0, 1.0, 1.0, 1.0)
    _TEXT_COLOR = (0.0, 0.0, 0.0, 1.0)
    _FONT_SIZE = 15.0

    def __init__(self):
        self._action: _Action | None = None
        self._enabled: bool = True
        self._segments: Sequence[str] = []
        self._selected_index = 0
        self._tracking_index = 0.0
        self._anim_index = 0.0
        # overridable
        self._anim_disabled = _UI_DISABLE_ANIMATIONS

        # Press scale animation
        self._press_scale = 1.0
        self._press_start_time = 0.0

        self._last_time = time.time()
        self._tracked = False

        self.frame = Rect(0.00, 0.00, 120.0, 32.0)
        if not IS_PYTHONISTA:
            self.mouse_scroll_enabled = True

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
            self._tracking_index = float(new_index)
            if self._anim_disabled:
                self._anim_index = float(self._selected_index)
            else:
                self._last_time = time.time()
                self.update_interval = 1.0 / 60.0
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
        self._tracking_index = float(self._selected_index)
        self._anim_index = float(self._selected_index)
        self.set_needs_display()

    def update(self):
        """Driven by update_interval for smooth transitions."""
        now = time.time()
        # dt clamping for stability during lag
        dt = min(now - self._last_time, 0.05)
        self._last_time = now

        if self._anim_disabled:
            self._anim_index = float(self._tracking_index)
            self._press_scale = 1.0
            self.update_interval = 0
            self.set_needs_display()
            return

        lerp_speed = 1.0 - (0.00005**dt)
        done = True

        # Slider animation - follows _tracking_index
        target_idx = float(self._tracking_index)
        diff_idx = target_idx - self._anim_index
        if abs(diff_idx) > 0.001:
            self._anim_index += diff_idx * lerp_speed
            done = False
        else:
            self._anim_index = target_idx

        # Scale animation
        if self._tracked:
            elapsed = now - self._press_start_time
            target_scale = 0.95 if elapsed > 0.03 else 1.0
        else:
            target_scale = 1.0

        diff_scale = target_scale - self._press_scale
        if abs(diff_scale) > 0.001:
            self._press_scale += diff_scale * lerp_speed
            done = False
        else:
            self._press_scale = target_scale

        self.set_needs_display()

        if done and not self._tracked:
            self.update_interval = 0

    def draw(self):
        segments = self.segments
        count = len(segments)
        if count == 0:
            return

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

        # Calculate vertical center of the pill
        pill_center_y = h / 2

        for i, string in enumerate(segments):
            seg_x = i * segment_width
            r, g, b, a = self._TEXT_COLOR
            # Smoother text fading if disabled
            alpha = a if self.enabled else a * 0.3

            # Measure text to get actual dimensions
            max_text_width = segment_width - 2 * self._TEXT_INSET
            try:
                text_width, text_height = measure_string(
                    string,
                    max_width=max_text_width,
                    font=("<system>", self._FONT_SIZE),
                    alignment=ALIGN_CENTER,
                    line_break_mode=LB_TRUNCATE_TAIL,
                )
            except Exception:
                text_width = max_text_width
                text_height = self._FONT_SIZE

            # Calculate horizontal position to center text within segment
            text_x = seg_x + (segment_width - text_width) / 2

            # Position text so that its center aligns with the pill's center
            # Baseline is approximately at 2/3 of the text height from the top
            baseline_y = pill_center_y - text_height / 2  # + self._FONT_SIZE * 0.7

            # if text_height <= scaled_sh:
            # Draw text
            draw_string(
                string,
                rect=(text_x, baseline_y, text_width, text_height),
                font=("<system>", self._FONT_SIZE),
                color=(r, g, b, alpha),
                alignment=ALIGN_CENTER,
                line_break_mode=LB_TRUNCATE_TAIL,
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

        self._tracked = True
        self._press_start_time = time.time()
        self._last_time = self._press_start_time

        # Initialize tracking index at current selection
        self._tracking_index = float(self._selected_index)

        if not self._anim_disabled:
            self.update_interval = 1.0 / 60.0
        self.set_needs_display()

    def touch_moved(self, touch: Touch):
        if not (self._tracked and self.enabled):
            return

        # Update tracking index so animation follows the finger
        new_idx = self._get_index_at_location(touch.location[0])
        if new_idx != -1:
            self._tracking_index = float(new_idx)
            if self.update_interval == 0 and not self._anim_disabled:
                self._last_time = time.time()
                self.update_interval = 1.0 / 60.0

        self.set_needs_display()

    def mouse_wheel(self, touch):
        if not self.enabled:
            return
        count = len(self._segments)
        if count == 0:
            return
        # Dominant axis: dy up (+) = prev segment, dx right (+) = next segment
        if abs(touch.scroll_dy) >= abs(touch.scroll_dx):
            delta = -1 if touch.scroll_dy > 0 else (1 if touch.scroll_dy < 0 else 0)
        else:
            delta = 1 if touch.scroll_dx > 0 else (-1 if touch.scroll_dx < 0 else 0)
        if delta == 0:
            return
        new_index = max(0, min(self._selected_index + delta, count - 1))
        if new_index != self._selected_index:
            self.selected_index = new_index
            self._ensure_action_and_call(self)

    def touch_ended(self, touch: Touch):
        if not (self._tracked and self.enabled):
            return

        if touch.phase == "ended":
            # Change actual value and call action ONLY on release
            new_index = self._get_index_at_location(touch.location[0])
            if new_index != -1:
                # selected_index setter will also sync tracking_index
                self.selected_index = new_index
                self._ensure_action_and_call(self)
            else:
                # Reset tracking to actual selection if released outside
                self._tracking_index = float(self._selected_index)

        self._tracked = False
        # Ensure scale and position return to final states
        if not self._anim_disabled:
            self._last_time = time.time()
            self.update_interval = 1.0 / 60.0
        self.set_needs_display()

    def _ensure_action_and_call(self, sender=None):
        action = getattr(self, "action", None)
        if action is None:
            return
        import inspect

        if len(inspect.signature(action).parameters) > 0:
            action(sender if sender is not None else self)
        else:
            action()
