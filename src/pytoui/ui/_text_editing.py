from __future__ import annotations

from typing import TYPE_CHECKING

from pytoui.ui._constants import ALIGN_LEFT, LB_CLIP
from pytoui.ui._draw import measure_string

if TYPE_CHECKING:
    from pytoui.ui._types import _Font

__all__ = (
    "char_index_at_x",
    "delete_backward",
    "delete_forward",
    "insert_text",
    "replace_range",
    "wrap_lines",
)


def insert_text(text: str, cursor: int, insertion: str) -> tuple[str, int]:
    return text[:cursor] + insertion + text[cursor:], cursor + len(insertion)


def replace_range(text: str, start: int, end: int, replacement: str) -> tuple[str, int]:
    return text[:start] + replacement + text[end:], start + len(replacement)


def delete_backward(text: str, cursor: int) -> tuple[str, int]:
    if cursor <= 0:
        return text, cursor
    return text[: cursor - 1] + text[cursor:], cursor - 1


def delete_forward(text: str, cursor: int) -> tuple[str, int]:
    if cursor >= len(text):
        return text, cursor
    return text[:cursor] + text[cursor + 1 :], cursor


def _text_width(text: str, font: _Font) -> float:
    return measure_string(
        text, font=font, alignment=ALIGN_LEFT, line_break_mode=LB_CLIP
    )[0]


def char_index_at_x(text: str, x: float, font: _Font) -> int:
    """Return the character index whose caret position is closest to `x`.

    Assumes LTR text with a non-decreasing prefix-width function (true for
    the Latin/left-aligned rendering pytoui's fontdue backend supports).
    """
    if x <= 0 or not text:
        return 0
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _text_width(text[:mid], font) <= x:
            lo = mid
        else:
            hi = mid - 1
    if lo < len(text):
        w_lo = _text_width(text[:lo], font)
        w_next = _text_width(text[: lo + 1], font)
        if x - w_lo > w_next - x:
            return lo + 1
    return lo


def wrap_lines(text: str, max_width: float, font: _Font) -> list[tuple[int, int]]:
    """Greedy word-wrap `text` into a list of (start, end) char-offset spans."""
    if not text:
        return [(0, 0)]

    lines: list[tuple[int, int]] = []
    pos = 0
    length = len(text)
    while True:
        nl = text.find("\n", pos)
        para_end = nl if nl != -1 else length
        lines.extend(_wrap_paragraph(text, pos, para_end, max_width, font))
        if nl == -1:
            break
        pos = nl + 1
    return lines


def _wrap_paragraph(
    text: str, start: int, end: int, max_width: float, font: _Font
) -> list[tuple[int, int]]:
    if start == end:
        return [(start, end)]

    spans: list[tuple[int, int]] = []
    line_start = start
    pos = start
    while pos < end:
        space = text.find(" ", pos, end)
        word_end = space + 1 if space != -1 else end

        if _text_width(text[line_start:word_end], font) <= max_width:
            pos = word_end
            continue

        if pos == line_start:
            # A single word alone exceeds max_width: force a mid-word break.
            break_at = max(
                1, char_index_at_x(text[line_start:word_end], max_width, font)
            )
            spans.append((line_start, line_start + break_at))
            line_start += break_at
            pos = line_start
        else:
            spans.append((line_start, pos))
            line_start = pos

    if line_start < end or not spans:
        spans.append((line_start, end))
    return spans
