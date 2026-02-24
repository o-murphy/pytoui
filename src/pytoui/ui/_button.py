from __future__ import annotations
from typing import TYPE_CHECKING

import time

from pytoui.ui._view import View
from pytoui.ui._types import (
    Rect,
    Size,
    Touch,
)
from pytoui.ui._image import Image
from pytoui.ui._draw import draw_string, measure_string
from pytoui.ui._constants import ALIGN_CENTER, LB_TRUNCATE_TAIL


if TYPE_CHECKING:
    from pytoui.ui._types import _Action, _RGBA, _Font

__all__ = ("Button",)


class Button(View):
    __final__ = True

    __slots__ = (
        "_action",
        "_enabled",
        "_background_image",
        "_image",
        "_title",
        "_font",
        "_text_color",
        "_anim_alpha",
        "_target_alpha",
        "_tracked",
        "_content_insets",
        "_last_time",
    )

    # Authentic iOS system blue color
    _IOS_BLUE: _RGBA = (0.0, 122 / 255, 1.0, 1.0)
    _WHITE: _RGBA = (1.0, 1.0, 1.0, 1.0)

    def __init__(self):
        self._action: _Action | None = None
        self._enabled: bool = True
        self._background_image: Image | None = None
        self._image: Image | None = None
        self._title: str | None = None
        self._font: _Font = ("<system>", 17.0)
        self._text_color: _RGBA | None = None  # None means auto-detect

        # Opacity animation state
        self._anim_alpha = 1.0
        self._target_alpha = 1.0
        self._tracked = False
        self._last_time = time.time()

        # Default iOS content insets (top, left, bottom, right)
        self._content_insets: Size = Size(8.0, 8.0)

        self.frame = Rect(0.0, 0.0, 80.0, 44.0)

    def _get_contrast_text_color(self) -> _RGBA:
        """Determines the best text color based on background brightness."""
        bg = self.background_color

        # If no background color or it's fully transparent, use system blue
        if bg is None or bg[3] <= 0.01:
            return self._IOS_BLUE

        # Calculate perceived luminance (standard W3C formula)
        # 0.299*R + 0.587*G + 0.114*B
        r, g, b = bg[0], bg[1], bg[2]
        luminance = (0.299 * r) + (0.587 * g) + (0.114 * b)

        # If background is dark, text should be white.
        # If light, use system blue
        return self._WHITE if luminance < 0.6 else self._IOS_BLUE

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
        self._target_alpha = 1.0 if value else 0.3
        if self._pytoui_animations_disabled:
            self._anim_alpha = self._target_alpha
        else:
            self._last_time = time.time()
            self.update_interval = 1.0 / 60.0
        self.set_needs_display()

    @property
    def title(self) -> str | None:
        return self._title

    @title.setter
    def title(self, value: str | None):
        self._title = value
        self.set_needs_display()

    def update(self):
        now = time.time()
        dt = min(now - self._last_time, 0.05)
        self._last_time = now

        # --- ANIMATION ---
        if self._pytoui_animations_disabled:
            self._anim_alpha = self._target_alpha
            self.update_interval = 0
            self.set_needs_display()
            return

        lerp_speed = 1.0 - (0.00005**dt)
        diff = self._target_alpha - self._anim_alpha

        if abs(diff) > 0.001:
            self._anim_alpha += diff * lerp_speed
            self.set_needs_display()
        else:
            self._anim_alpha = self._target_alpha

            if not self._tracked:
                self.update_interval = 0
            self.set_needs_display()

    def draw(self):
        if not self._title:
            return

        # --- AUTOMATIC TEXT COLOR SELECTION ---
        if not self.enabled:
            base_color = (0.7, 0.7, 0.7, 1.0)  # disabled gray
        else:
            # If user manually set text color, use it. Otherwise, adapt.
            base_color = self._text_color or self._get_contrast_text_color()

        # Apply animated opacity
        r, g, b, a = base_color
        current_color = (r, g, b, a * self._anim_alpha)

        # Apply content insets to get the drawing rectangle
        inset_rect = self.bounds.inset(self._content_insets.x, self._content_insets.y)

        _, font_size = self._font
        # Measure text to get actual dimensions
        try:
            _, text_height = measure_string(
                self._title,
                max_width=inset_rect.w,
                font=self._font,
                alignment=ALIGN_CENTER,
                line_break_mode=LB_TRUNCATE_TAIL,
            )
        except Exception:
            text_height = font_size

        title_rect = inset_rect.inset(0, (inset_rect.height - text_height) / 2)

        # Draw text centered
        draw_string(
            self._title,
            rect=title_rect,
            font=self._font,
            color=current_color,
            alignment=ALIGN_CENTER,
            line_break_mode=LB_TRUNCATE_TAIL,
        )

    def touch_began(self, touch: Touch):
        if not self.enabled:
            return
        self._tracked = True
        self._last_time = time.time()
        # In iOS, the button becomes semi-transparent immediately upon touch
        self._target_alpha = 0.25
        if self._pytoui_animations_disabled:
            self._anim_alpha = 0.25
        else:
            self.update_interval = 1.0 / 60.0
        self.set_needs_display()

    def touch_moved(self, touch: Touch):
        if self._tracked and self.enabled:
            # Check if finger is within button bounds
            inside = (
                0 <= touch.location[0] <= self.width
                and 0 <= touch.location[1] <= self.height
            )
            # If finger leaves bounds, restore brightness (cancel highlight)
            new_target = 0.25 if inside else 1.0

            if new_target != self._target_alpha:
                self._target_alpha = new_target
                if self.update_interval == 0 and not self._pytoui_animations_disabled:
                    self._last_time = time.time()
                    self.update_interval = 1.0 / 60.0
                self.set_needs_display()

    def touch_ended(self, touch: Touch):
        if self._tracked:
            self._target_alpha = 1.0 if self.enabled else 0.3

            # Execute action only if released within button bounds
            inside = (
                0 <= touch.location[0] <= self.width
                and 0 <= touch.location[1] <= self.height
            )

            if self.enabled and touch.phase == "ended" and inside:
                self._ensure_action_and_call(self)  # type: ignore[attr-defined]

            if not self._pytoui_animations_disabled:
                self._last_time = time.time()
                self.update_interval = 1.0 / 60.0
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
