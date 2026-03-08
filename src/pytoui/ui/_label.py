from __future__ import annotations

from typing import TYPE_CHECKING

from pytoui.ui._constants import (
    ALIGN_NATURAL,
    LB_WORD_WRAP,
)
from pytoui.ui._draw import (
    draw_string,
    measure_string,
    parse_color,
)
from pytoui.ui._internals import _final_
from pytoui.ui._types import Rect
from pytoui.ui._view import View

if TYPE_CHECKING:
    from pytoui.ui._types import (
        _RGBA,
        _Alignment,
        _ColorLike,
        _Font,
        _LineBrakeMode,
    )


__all__ = ("Label",)


@_final_
class Label(View):
    __slots__ = (
        "_alignment",
        "_font",
        "_line_break_mode",
        "_min_font_scale",
        "_number_of_lines",
        "_scales_font",
        "_text",
        "_text_color",
    )

    def __init__(self, *args, **kwargs):
        # Basic text properties
        self._text: str | None = None
        self._font: _Font = ("<system>", 17.0)
        self._text_color: _RGBA = (0.0, 0.0, 0.0, 1.0)
        self._alignment: _Alignment = ALIGN_NATURAL
        self._line_break_mode: _LineBrakeMode = LB_WORD_WRAP
        self._number_of_lines: int = 1

        # Automatic scaling (iOS Auto-shrink)
        self._scales_font: bool = False
        self._min_font_scale: float = 0.0  # 0.0 means use system default

        self.frame = Rect(0.0, 0.0, 100.0, 20.0)
        self.touch_enabled = False

        super().__init__(*args, **kwargs)

    @property
    def text(self) -> str | None:
        """The label's text."""
        return self._text

    @text.setter
    def text(self, value: str | None):
        if self._text != value:
            self._text = value
            self.set_needs_display()

    @property
    def font(self) -> _Font:
        """The label's font (name, size)."""
        return self._font

    @font.setter
    def font(self, value: _Font):
        self._font = value
        self.set_needs_display()

    @property
    def text_color(self) -> _RGBA:
        """The label's text color."""
        return self._text_color

    @text_color.setter
    def text_color(self, value: _ColorLike):
        self._text_color = parse_color(value)
        self.set_needs_display()

    @property
    def alignment(self) -> _Alignment:
        """Text alignment (ALIGN_NATURAL, ALIGN_CENTER, ALIGN_RIGHT)."""
        return self._alignment

    @alignment.setter
    def alignment(self, value: _Alignment):
        self._alignment = value
        self.set_needs_display()

    @property
    def number_of_lines(self) -> int:
        return self._number_of_lines

    @number_of_lines.setter
    def number_of_lines(self, value: int):
        if self._number_of_lines != value:
            self._number_of_lines = value
            self.set_needs_display()

    def _get_text_metrics(self, font_size: float) -> tuple[float, float, float]:
        """Get font metrics for vertical centering using fallback values."""
        # Since we can't access fb directly, use approximate values
        # In a real implementation, these would come from the font metrics
        ascent = font_size * 0.8  # Approximate ascent
        descent = font_size * 0.2  # Approximate descent
        text_height = font_size
        return text_height, ascent, descent

    def draw(self):
        """Draw the label."""
        if not self._text or self._text_color is None:
            return

        font_name, font_size = self._font
        w, h = self.width, self.height

        # iOS Auto-shrink (only for single line)
        if self._scales_font and self._number_of_lines == 1:
            min_scale = self._min_font_scale if self._min_font_scale > 0 else 0.5
            min_size = font_size * min_scale
            current_size = font_size

            # Measure text width with current font size
            try:
                text_width, _ = measure_string(
                    self._text,
                    max_width=w,
                    font=(font_name, current_size),
                    alignment=self._alignment,
                    line_break_mode=self._line_break_mode,
                )
            except Exception:
                text_width = w

            # Reduce font size until it fits
            while text_width > w and current_size > min_size:
                current_size -= 0.5
                try:
                    text_width, _ = measure_string(
                        self._text,
                        max_width=w,
                        font=(font_name, current_size),
                        alignment=self._alignment,
                        line_break_mode=self._line_break_mode,
                    )
                except Exception:
                    text_width = w

            font_size = max(current_size, min_size)

        # Measure text to get actual dimensions with current font
        try:
            text_width, text_height = measure_string(
                self._text,
                max_width=w,
                font=(font_name, font_size),
                alignment=self._alignment,
                line_break_mode=self._line_break_mode,
            )
        except Exception:
            text_width = w
            text_height = font_size

        # Calculate vertical center of the label
        center_y = h / 2

        # Position text so that its center aligns with the label's center
        # Baseline is approximately at 2/3 of the text height from the top
        baseline_y = center_y - text_height / 2  # + font_size * 0.7

        # Calculate horizontal position based on alignment
        if self._alignment == ALIGN_NATURAL or self._alignment == 0:  # LEFT
            text_x = 0
            rect_width = text_width
        elif self._alignment == 2:  # RIGHT
            text_x = w - text_width
            rect_width = text_width
        else:  # CENTER
            text_x = (w - text_width) / 2
            rect_width = text_width

        # Draw text
        try:
            draw_string(
                self._text,
                rect=(text_x, baseline_y, rect_width, text_height),
                font=(font_name, font_size),
                color=self._text_color,
                alignment=self._alignment,
                line_break_mode=self._line_break_mode,
            )
        except Exception:
            pass  # Silently fail if drawing fails

    def size_to_fit(self):
        """Resize the label to perfectly fit its text content."""
        if not self._text:
            return

        # If number_of_lines == 1, max_width = 0 (unlimited)
        # If multiline, use current width as constraint
        max_width = 0.0 if self._number_of_lines == 1 else self.frame.w

        try:
            tw, th = measure_string(
                self._text,
                max_width=max_width,
                font=self._font,
                alignment=self._alignment,
                line_break_mode=self._line_break_mode,
            )
            self.frame = Rect(self.frame.x, self.frame.y, tw, th)
        except Exception:
            pass  # Silently fail if measurement fails
