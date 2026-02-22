from __future__ import annotations
from typing import TYPE_CHECKING

from pytoui.ui._constants import (
    ALIGN_NATURAL,
    LB_TRUNCATE_TAIL,
    LB_CLIP,
)
from pytoui.ui._view import View
from pytoui.ui._types import Rect
from pytoui.ui._draw import (
    draw_string,
    measure_string,
    parse_color,
    _layout_lines,
    _font_id,
    _get_draw_ctx,
)

if TYPE_CHECKING:
    from pytoui.ui._types import (
        _RGBA,
        _ColorLike,
        _Font,
    )


__all__ = ("Label",)


class Label(View):
    __final__ = True

    __slots__ = (
        "_alignment",
        "_font",
        "_line_break_mode",
        "_number_of_lines",
        "_scales_font",
        "_min_font_scale",
        "_text",
        "_text_color",
    )

    def __init__(self):
        # Basic text properties
        self._text: str | None = None
        self._font: _Font = ("<system>", 17.0)
        self._text_color: _RGBA | None = (0.0, 0.0, 0.0, 1.0)
        self._alignment: int = ALIGN_NATURAL
        self._line_break_mode: int = LB_TRUNCATE_TAIL
        self._number_of_lines: int = 1

        # Automatic scaling (iOS Auto-shrink)
        self._scales_font: bool = False
        self._min_font_scale: float = 0.0  # 0.0 means use system default

        self._frame = Rect(0.0, 0.0, 100.0, 20.0)

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
    def text_color(self) -> _RGBA | None:
        """The label's text color."""
        return parse_color(self._text_color)

    @text_color.setter
    def text_color(self, value: _ColorLike):
        self._text_color = parse_color(value)
        self.set_needs_display()

    @property
    def alignment(self) -> int:
        """Text alignment (ALIGN_NATURAL, ALIGN_CENTER, ALIGN_RIGHT)."""
        return self._alignment

    @alignment.setter
    def alignment(self, value: int):
        self._alignment = value
        self.set_needs_display()

    def draw(self):
        if not self._text or self._text_color is None:
            return

        font_name, font_size = self._font
        w, h = self.width, self.height

        # iOS Auto-shrink logic (single-line only)
        if self._scales_font and self._number_of_lines == 1:
            min_scale = self._min_font_scale if self._min_font_scale > 0 else 0.5
            min_size = font_size * min_scale

            while font_size > min_size:
                tw, _ = measure_string(self._text, font=(font_name, font_size))
                if tw <= w:
                    break
                font_size -= 0.5
            font_size = max(font_size, min_size)

        if self._number_of_lines == 1:
            draw_string(
                self._text,
                rect=(0, 0, w, h),
                font=(font_name, font_size),
                color=self._text_color,
                alignment=self._alignment,
                line_break_mode=self._line_break_mode,
            )
        else:
            # Multi-line: lay out all lines then draw each one in its own row
            ctx = _get_draw_ctx()
            fb = ctx.backend
            if fb is None:
                return
            fid = _font_id(font_name)
            lines = _layout_lines(
                self._text,
                int(w),
                font_size,
                fid,
                self._line_break_mode,
                self._number_of_lines,
            )
            line_h = type(fb).get_text_height(size=font_size, font_id=fid)
            for i, line in enumerate(lines):
                y_off = i * line_h
                if y_off + line_h > h:
                    break
                draw_string(
                    line,
                    rect=(0, y_off, w, line_h),
                    font=(font_name, font_size),
                    color=self._text_color,
                    alignment=self._alignment,
                    line_break_mode=LB_CLIP,
                )

    def size_to_fit(self):
        """Resizes the label to perfectly fit its text content."""
        if not self._text:
            return

        tw, th = measure_string(
            self._text,
            font=self._font,
            max_width=self._frame.w if self._number_of_lines != 1 else 0,
        )
        self.frame = Rect(self._frame.x, self._frame.y, tw, th)
