from __future__ import annotations
import os
from typing import TYPE_CHECKING

import time

from pytoui.ui._view import View
from pytoui.ui._types import (
    Rect,
    Touch,
)
from pytoui.ui._label import Label
from pytoui.ui._image import Image
from pytoui.ui._draw import draw_string
from pytoui.ui._constants import ALIGN_CENTER, LB_TRUNCATE_TAIL

if TYPE_CHECKING:
    from pytoui.ui._types import _Action, _RGBA

__all__ = ("Button",)


_UI_DISABLE_ANIMATIONS = os.environ.get(
    "UI_DISABLE_ANIMATIONS", "0"
).strip().strip().lower() in (
    "true",
    "1",
    "yes",
    "y",
)


class Button(View):
    __final__ = True

    __slots__ = (
        "_action",
        "_enabled",
        "_background_image",
        "_image",
        "_title_label",
        "_anim_alpha",
        "_target_alpha",
        "_tracked",
        "_last_time",
        "_content_insets",
        "__animations_disabled",
    )

    # Authentic iOS system blue color
    _IOS_BLUE: _RGBA = (0.0, 122 / 255, 1.0, 1.0)

    def __init__(self):
        self._action: _Action | None = None
        self._enabled: bool = True
        self._background_image: Image | None = None
        self._image: Image | None = None

        # Opacity animation state
        self._anim_alpha = 1.0
        self._target_alpha = 1.0
        self._tracked = False
        self._last_time = time.time()

        # Default iOS content insets (top, left, bottom, right)
        self._content_insets: tuple[float, float, float, float] = (4.0, 8.0, 4.0, 8.0)

        self._frame = Rect(0.0, 0.0, 80.0, 44.0)

        lbl = Label.__new__(Label)
        Label.__init__(lbl)
        lbl._font = ("<system>", 17)
        lbl._text_color = self._IOS_BLUE
        lbl._alignment = ALIGN_CENTER
        lbl._line_break_mode = LB_TRUNCATE_TAIL
        lbl._number_of_lines = 1

        self._title_label: Label = lbl

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
        self._target_alpha = 1.0 if value else 0.3
        if self._animations_disabled:
            self._anim_alpha = self._target_alpha
        self.set_needs_display()

    @property
    def title(self) -> str | None:
        return self._title_label._text

    @title.setter
    def title(self, value: str | None):
        self._title_label._text = value
        self.set_needs_display()

    # @property
    # def text_color(self) -> RGBA | None:
    #     return self._title_label._text_color

    # @text_color.setter
    # def text_color(self, value: ColorLike):
    #     self._title_label._text_color = parse_color(value)
    #     self.set_needs_display()

    def draw(self):
        now = time.time()
        dt = min(now - self._last_time, 0.1)
        self._last_time = now

        # --- ANIMATION ---
        if self._animations_disabled:
            self._anim_alpha = self._target_alpha
        else:
            # Fast and smooth interpolation similar to Switch
            lerp_speed = 1.0 - (0.00005**dt)
            diff = self._target_alpha - self._anim_alpha

            if abs(diff) > 0.001:
                self._anim_alpha += diff * lerp_speed
                self.set_needs_display()
            else:
                self._anim_alpha = self._target_alpha

        lbl = self._title_label
        if not lbl._text:
            return

        # --- AUTOMATIC TEXT COLOR SELECTION ---
        if not self.enabled:
            text_color = (0.7, 0.7, 0.7, 1.0)  # disabled gray
        elif self._tracked:
            text_color = (1.0, 1.0, 1.0, 1.0)  # highlighted (white)
        else:
            text_color = self._IOS_BLUE  # normal state

        # Apply animated opacity
        r, g, b, a = text_color
        current_color = (r, g, b, a * self._anim_alpha)

        it, il, ib, ir = self._content_insets
        draw_string(
            lbl.text,
            rect=(il, it, self.width - il - ir, self.height - it - ib),
            font=lbl.font,
            color=current_color,
            alignment=lbl._alignment,
            line_break_mode=lbl._line_break_mode,
            number_of_lines=lbl._number_of_lines,
        )

    def touch_began(self, touch: Touch):
        if not self.enabled:
            return
        self._tracked = True
        self._last_time = time.time()
        # In iOS, the button becomes semi-transparent immediately upon touch
        self._target_alpha = 0.25
        if self._animations_disabled:
            self._anim_alpha = 0.25
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
