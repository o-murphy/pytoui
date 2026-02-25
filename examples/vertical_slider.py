from __future__ import annotations

import time
from typing import TYPE_CHECKING

from pytoui._platform import _UI_DISABLE_ANIMATIONS
from pytoui.ui._draw import Path, set_color
from pytoui.ui._types import Rect, Touch
from pytoui.ui._view import View

if TYPE_CHECKING:
    from pytoui.ui._types import _Action

__all__ = ("VerticalSlider",)


class VerticalSlider(View):
    """
    Вертикальна версія iOS-подібного слайдера.
    Значення 0.0 знаходиться внизу, 1.0 — вгорі.
    """
    _final_ = True

    __slots__ = (
        "_action",
        "_anim_value",
        "_continuous",
        "_enabled",
        "_last_time",
        "_thumb_scale",
        "_tracked",
        "_value",
        "_anim_disabled",
        "_progress_color",
        "_track_color",
    )

    _IOS_BLUE = (0.0, 0.48, 1.0, 1.0)
    _IOS_TRACK = (0.85, 0.85, 0.85, 1.0)
    _LOGICAL_WIDTH = 31.0

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

        # Overrides
        self._anim_disabled = _UI_DISABLE_ANIMATIONS
        self._progress_color = self._IOS_BLUE
        self._track_color = self._IOS_TRACK

        # Стандартний розмір для вертикального слайдера
        self.frame = Rect(0, 0, 31, 200)

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
            if self._anim_disabled:
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

        if self._anim_disabled:
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

        # 🔹 LOGICAL WIDTH (Центрування по горизонталі)
        w = self._LOGICAL_WIDTH
        ox = (self.width - w) * 0.5
        mid_x = ox + w * 0.5

        track_w = 4.0
        thumb_radius = 14.0 * self._thumb_scale

        margin = 15.0
        available_height = self.height - (margin * 2)
        # Розраховуємо Y: 0.0 внизу (height - margin), 1.0 вгорі (margin)
        pos_y = (self.height - margin) - (available_height * self._anim_value)

        # 1️⃣ Background track (весь шлях)
        set_color(self._track_color)
        Path.rounded_rect(
            mid_x - track_w / 2,
            margin,
            track_w,
            available_height,
            track_w / 2,
        ).fill()

        # 2️⃣ Active track (від низу до повзунка)
        set_color(self._progress_color)
        active_track_y = pos_y
        active_track_h = (self.height - margin) - pos_y
        Path.rounded_rect(
            mid_x - track_w / 2,
            active_track_y,
            track_w,
            active_track_h,
            track_w / 2,
        ).fill()

        # 3️⃣ Thumb
        # Тіні
        set_color((0, 0, 0, 0.15))
        Path.oval(
            mid_x - thumb_radius,
            pos_y - thumb_radius + 2.0,
            thumb_radius * 2,
            thumb_radius * 2,
        ).fill()

        set_color((0, 0, 0, 0.06))
        Path.oval(
            mid_x - thumb_radius - 0.5,
            pos_y - thumb_radius - 0.5,
            (thumb_radius + 0.5) * 2,
            (thumb_radius + 0.5) * 2,
        ).fill()

        # Тіло повзунка
        set_color("white")
        Path.oval(
            mid_x - thumb_radius,
            pos_y - thumb_radius,
            thumb_radius * 2,
            thumb_radius * 2,
        ).fill()

        # Обводка
        set_color((0, 0, 0, 0.04))
        p = Path.oval(
            mid_x - thumb_radius,
            pos_y - thumb_radius,
            thumb_radius * 2,
            thumb_radius * 2,
        )
        p.line_width = 0.5
        p.stroke()

    def _update_value_from_touch(self, touch: Touch):
        margin = 15.0
        available_height = self.height - (margin * 2)
        if available_height <= 0:
            return

        # Інвертуємо Y, щоб рух вгору збільшував значення
        local_y = (self.height - margin) - touch.location[1]
        self.value = max(0.0, min(1.0, local_y / available_height))

    def touch_began(self, touch: Touch):
        if not self.enabled:
            return

        x, y = touch.location
        if not self._point_inside_slider(x, y):
            return

        self._tracked = True
        self._last_time = time.time()
        self._update_value_from_touch(touch)

        if self.continuous:
            self._ensure_action_and_call(self)
        self.set_needs_display()

    def touch_moved(self, touch: Touch):
        if self._tracked and self.enabled:
            self._update_value_from_touch(touch)
            if self.continuous:
                self._ensure_action_and_call(self)

    def touch_ended(self, touch: Touch):
        if self._tracked:
            self._tracked = False
            if self.enabled:
                self._update_value_from_touch(touch)
                self._ensure_action_and_call(self)
            self.set_needs_display()

    def _slider_bounds(self):
        w = self._LOGICAL_WIDTH
        ox = (self.width - w) * 0.5
        return ox, w

    def _point_inside_slider(self, x: float, y: float) -> bool:
        # Перевірка, чи потрапляє дотик у горизонтальні межі слайдера
        ox, w = self._slider_bounds()
        return ox <= x <= ox + w

    def _ensure_action_and_call(self, sender=None):
        action = getattr(self, "action", None)
        if action is None:
            return
        import inspect
        if len(inspect.signature(action).parameters) > 0:
            action(sender if sender is not None else self)
        else:
            action()


from pytoui import ui

def main():
    value = 0.3

    label = ui.Label()
    label.text = f"{value:.2f}"
    label.frame = (0, 0, 100, 50)
    label.center = (300, 300)
    label.flex = "W"
    label.alignment = ui.ALIGN_CENTER
    label.text_color = "black"
    label.background_color = "white"
    label.corner_radius = 16

    def action(sender: ui.VerticalSlider):
        label.text = f"{sender.value:.2f}"

    slider = VerticalSlider()
    slider.value = 0.3
    slider.frame = (0, 0, 50, 300)
    slider.center = (200, 300)
    slider.flex = "W"
    slider.background_color = "white"
    slider.corner_radius = 16
    slider.action = action

    root = ui.View()
    root.frame = (0, 0, 400, 600)
    root.background_color = "black"
    root.name = f"Demo: {slider.__class__.name}"
    root.add_subview(slider)
    root.add_subview(label)
    root.present("fullscreen")


if __name__ == "__main__":
    main()