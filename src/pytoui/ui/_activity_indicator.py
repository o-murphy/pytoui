from __future__ import annotations

import math

from pytoui.ui._draw import GState, Path, Transform, concat_ctm, set_color
from pytoui.ui._types import Rect
from pytoui.ui._view import View
from pytoui.ui._constants import (
    ACTIVITY_INDICATOR_STYLE_GRAY,
    ACTIVITY_INDICATOR_STYLE_WHITE,
    ACTIVITY_INDICATOR_STYLE_WHITE_LARGE,
    _UI_DISABLE_ANIMATIONS,
)


class ActivityIndicator(View):
    __final__ = True

    __slots__ = (
        "_style",
        "_hides_when_stopped",
        "_anim_step",
        "_is_animating",
        "_last_static_update",
        "__animations_disabled",
    )

    def __init__(self):
        self._style: int = ACTIVITY_INDICATOR_STYLE_WHITE
        self._hides_when_stopped = True
        self._anim_step = 0
        self._is_animating = False
        self._last_static_update = 0.0
        self.__animations_disabled: bool = False

        # default size for standard style; frame is user-settable and must not
        # change automatically when style changes
        self._frame = Rect(0.0, 0.0, 20.0, 20.0)
        self._bounds = Rect(0.0, 0.0, 20.0, 20.0)

    @property
    def style(self) -> int:
        return self._style

    @style.setter
    def style(self, value: int):
        self._style = value
        self.set_needs_display()

    @property
    def hides_when_stopped(self) -> bool:
        return self._hides_when_stopped

    @hides_when_stopped.setter
    def hides_when_stopped(self, value: bool):
        self._hides_when_stopped = value
        self.hidden = self._hides_when_stopped if not self._is_animating else False

    def start(self):
        if not self._is_animating:
            self._is_animating = True
            if self._animations_disabled:
                self.update_interval = 0.5
            else:
                self.update_interval = 1.0 / 12.0
            self.hidden = False
            # advance one step immediately so the first visible frame is
            # already mid-animation (avoids a visually "frozen" initial frame)
            self.update()

    def stop(self):
        self._is_animating = False
        self.update_interval = 0
        if self._hides_when_stopped:
            self.hidden = True
        self.set_needs_display()

    def update(self):
        if self._is_animating:
            self._anim_step = (self._anim_step + 1) % 12
            self.set_needs_display()

            curr = self.superview
            while curr:
                curr.set_needs_display()
                curr = curr.superview

    def draw(self):
        if self._hides_when_stopped and not self._is_animating:
            return

        num_lines = 12
        # center within the (possibly user-resized) frame
        cx, cy = self.width / 2, self.height / 2

        # fixed pixel geometry per style — frame size does NOT affect petal size
        if self._style == ACTIVITY_INDICATOR_STYLE_WHITE_LARGE:
            radius = 9.25
            line_len = 9.25
            line_width = 4.5
        else:
            radius = 4.4
            line_len = 5.6
            line_width = 2.0

        if self._style == ACTIVITY_INDICATOR_STYLE_GRAY:
            base_color = (0.6, 0.6, 0.6)
        else:
            base_color = (1.0, 1.0, 1.0)

        for i in range(num_lines):
            angle = i * (2.0 * math.pi / num_lines)
            dist = (i - self._anim_step) % num_lines

            if self._animations_disabled:
                if dist == 0:
                    alpha = 1.0
                elif dist == 1:
                    alpha = 0.7
                elif dist == 2:
                    alpha = 0.4
                else:
                    alpha = 0.2
            else:
                alpha = max(0.15, 1.0 - (dist * 0.7 / num_lines))

            with GState():
                concat_ctm(Transform.translation(cx, cy))
                concat_ctm(Transform.rotation(angle))
                set_color((*base_color, alpha))
                p = Path.rounded_rect(
                    -line_width / 2,
                    -(radius + line_len),
                    line_width,
                    line_len,
                    line_width / 2,
                )
                p.fill()

    # ── animation ─────────────────────────────────────────────────────────────

    @property
    def _animations_disabled(self) -> bool:
        return self.__animations_disabled or _UI_DISABLE_ANIMATIONS

    @_animations_disabled.setter
    def _animations_disabled(self, value: bool) -> None:
        self.__animations_disabled = value
