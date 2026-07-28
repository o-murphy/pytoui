from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from pytoui._platform import IS_PYTHONISTA
from pytoui.hid import (
    KEY_INPUT_BACKSPACE,
    KEY_INPUT_DELETE,
    KEY_INPUT_DOWN,
    KEY_INPUT_END,
    KEY_INPUT_ESC,
    KEY_INPUT_HOME,
    KEY_INPUT_LEFT,
    KEY_INPUT_RETURN,
    KEY_INPUT_RIGHT,
    KEY_INPUT_UP,
)
from pytoui.ui._draw import (
    draw_string,
    fill_rect,
    measure_string,
    parse_color,
    set_color,
)
from pytoui.ui._internals import _final_
from pytoui.ui._scroll_view import _ScrollView, _ScrollViewDelegate
from pytoui.ui._text_editing import (
    char_index_at_x,
    delete_backward,
    delete_forward,
    insert_text,
    replace_range as _replace_range_helper,
    wrap_lines,
)

if TYPE_CHECKING:
    from pytoui.ui._types import (
        _RGBA,
        Touch,
        _Alignment,
        _CapitalizationType,
        _ColorLike,
        _Font,
        _KeyboardType,
    )


__all__ = ("TextView", "_TextViewDelegate")

_H_PAD = 6.0
_V_PAD = 4.0


class _TextViewDelegate(_ScrollViewDelegate, Protocol):
    def textview_should_begin_editing(self, textview) -> bool:
        return True

    def textview_did_begin_editing(self, textview): ...
    def textview_did_end_editing(self, textview): ...
    def textview_should_change(self, textview, range, replacement) -> bool:
        return True

    def textview_did_change(self, textview): ...
    def textview_did_change_selection(self, textview): ...


@_final_
class _TextView(_ScrollView):
    __slots__ = (
        "_alignment",
        "_auto_content_inset",
        "_autocapitalization_type",
        "_autocorrection_type",
        "_cursor",
        "_cursor_visible",
        "_editable",
        "_font",
        "_is_editing",
        "_keyboard_type",
        "_lines",
        "_lines_key",
        "_preedit_range",
        "_preedit_text",
        "_selectable",
        "_spellchecking_type",
        "_text",
        "_text_color",
        "_touch_start_time",
        "_touch_start_xy",
    )

    def __init__(self, *args, **kwargs):
        self._alignment: _Alignment = 0
        self._auto_content_inset: Any = True
        self._autocapitalization_type: _CapitalizationType = 0
        self._autocorrection_type: bool = True
        self._editable: bool = True
        self._font: _Font = ("<system>", 17.0)
        self._keyboard_type: _KeyboardType = 0
        self._selectable: bool = True
        self._spellchecking_type: Any = None
        self._text: str = ""
        self._text_color: _RGBA = (0.0, 0.0, 0.0, 1.0)

        self._cursor: int = 0
        self._is_editing: bool = False
        self._cursor_visible: bool = False
        self._preedit_text: str = ""
        self._preedit_range: tuple[int, int] | None = None
        self._lines: list[tuple[int, int]] = [(0, 0)]
        self._lines_key: tuple = ()
        self._touch_start_xy: tuple[float, float] = (0.0, 0.0)
        self._touch_start_time: int = 0

        super().__init__(*args, **kwargs)

    # -- properties ------------------------------------------------------------

    @property
    def alignment(self) -> _Alignment:
        return self._alignment

    @alignment.setter
    def alignment(self, value: _Alignment):
        self._alignment = value
        self.set_needs_display()

    @property
    def auto_content_inset(self) -> Any:
        return self._auto_content_inset

    @auto_content_inset.setter
    def auto_content_inset(self, value: Any):
        self._auto_content_inset = value

    @property
    def autocapitalization_type(self) -> _CapitalizationType:
        return self._autocapitalization_type

    @autocapitalization_type.setter
    def autocapitalization_type(self, value: _CapitalizationType):
        self._autocapitalization_type = value

    @property
    def autocorrection_type(self) -> bool:
        return self._autocorrection_type

    @autocorrection_type.setter
    def autocorrection_type(self, value: bool):
        self._autocorrection_type = value

    @property
    def editable(self) -> bool:
        return self._editable

    @editable.setter
    def editable(self, value: bool):
        self._editable = value
        if not value:
            self.end_editing()

    @property
    def font(self) -> _Font:
        return self._font

    @font.setter
    def font(self, value: _Font):
        self._font = value
        self._lines_key = ()
        self.set_needs_display()

    @property
    def keyboard_type(self) -> _KeyboardType:
        return self._keyboard_type

    @keyboard_type.setter
    def keyboard_type(self, value: _KeyboardType):
        self._keyboard_type = value

    @property
    def selectable(self) -> bool:
        return self._selectable

    @selectable.setter
    def selectable(self, value: bool):
        self._selectable = value
        if not value:
            self.end_editing()

    @property
    def selected_range(self) -> tuple[int, int]:
        return (self._cursor, self._cursor)

    @selected_range.setter
    def selected_range(self, value: tuple[int, int]):
        self._cursor = max(0, min(len(self._text), value[1]))
        self.set_needs_display()

    @property
    def spellchecking_type(self) -> Any:
        return self._spellchecking_type

    @spellchecking_type.setter
    def spellchecking_type(self, value: Any):
        self._spellchecking_type = value

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str | None):
        self._text = value or ""
        self._cursor = min(self._cursor, len(self._text))
        self._lines_key = ()
        self.set_needs_display()

    @property
    def text_color(self) -> _RGBA:
        return self._text_color

    @text_color.setter
    def text_color(self, value: _ColorLike):
        self._text_color = parse_color(value)
        self.set_needs_display()

    # -- layout ------------------------------------------------------------

    def _line_height(self) -> float:
        return measure_string(" ", font=self._font)[1]

    def layout(self):
        key = (self._text, self._font, self.bounds.w)
        if key == self._lines_key:
            return
        avail_w = max(1.0, self.bounds.w - 2 * _H_PAD)
        self._lines = wrap_lines(self._text, avail_w, self._font)
        self._lines_key = key
        line_h = self._line_height()
        self.content_size = (self.bounds.w, len(self._lines) * line_h + 2 * _V_PAD)

    def _line_and_col_for_cursor(self) -> tuple[int, int]:
        for i, (s, e) in enumerate(self._lines):
            if s <= self._cursor <= e:
                return i, self._cursor - s
        last = len(self._lines) - 1
        return last, self._cursor - self._lines[last][0]

    # -- drawing -------------------------------------------------------------

    def draw(self):
        self.layout()
        ox, oy = self.content_offset
        line_h = self._line_height()
        cursor_line, cursor_col = self._line_and_col_for_cursor()

        for i, (s, e) in enumerate(self._lines):
            y = _V_PAD + i * line_h - oy
            if not (-line_h <= y <= self.height):
                continue
            line_text = self._text[s:e]
            if self._preedit_text and i == cursor_line:
                line_text = (
                    line_text[:cursor_col] + self._preedit_text + line_text[cursor_col:]
                )
            draw_string(
                line_text,
                rect=(_H_PAD - ox, y, self.bounds.w, line_h),
                font=self._font,
                color=self._text_color,
                alignment=self._alignment,
            )

        if self._preedit_text:
            s, e = self._lines[cursor_line]
            base_text = self._text[s:e]
            pre_x0, _ = measure_string(base_text[:cursor_col], font=self._font)
            pre_x1, _ = measure_string(
                base_text[:cursor_col] + self._preedit_text, font=self._font
            )
            y = _V_PAD + cursor_line * line_h - oy
            set_color(self._text_color)
            fill_rect(_H_PAD - ox + pre_x0, y + line_h - 2, pre_x1 - pre_x0, 1.0)

        if self._is_editing and self._cursor_visible:
            s, e = self._lines[cursor_line]
            base_text = self._text[s:e]
            caret_col = cursor_col
            if self._preedit_text:
                offset = (
                    self._preedit_range[0]
                    if self._preedit_range
                    else len(self._preedit_text)
                )
                caret_col += offset
                base_text = (
                    base_text[:cursor_col] + self._preedit_text + base_text[cursor_col:]
                )
            caret_x, _ = measure_string(base_text[:caret_col], font=self._font)
            y = _V_PAD + cursor_line * line_h - oy
            set_color(self._text_color)
            fill_rect(_H_PAD - ox + caret_x, y, 1.5, line_h)

    # -- focus / editing lifecycle --------------------------------------------

    def begin_editing(self) -> None:
        if self._is_editing or not (self._editable or self._selectable):
            return
        if not self._should_begin_editing():
            return
        self.become_first_responder()

    def end_editing(self) -> None:
        if self._is_editing:
            self._internals_.resignFirstResponder()

    def did_become_first_responder(self):
        self._is_editing = True
        self._cursor_visible = True
        self.update_interval = 0.5
        self._notify("textview_did_begin_editing", self)
        self.set_needs_display()

    def did_resign_first_responder(self):
        self._is_editing = False
        self._preedit_text = ""
        self._preedit_range = None
        self.update_interval = 0.0
        self._notify("textview_did_end_editing", self)
        self.set_needs_display()

    def update(self):
        self._cursor_visible = not self._cursor_visible
        self.set_needs_display()

    # -- touch -----------------------------------------------------------------

    def touch_began(self, touch: Touch):
        super().touch_began(touch)
        self._touch_start_xy = (touch.location.x, touch.location.y)
        self._touch_start_time = touch.timestamp

    def touch_moved(self, touch: Touch):
        super().touch_moved(touch)

    def touch_ended(self, touch: Touch):
        dx = touch.location.x - self._touch_start_xy[0]
        dy = touch.location.y - self._touch_start_xy[1]
        was_tap = (dx * dx + dy * dy) <= 9.0
        super().touch_ended(touch)
        if not (was_tap and (self._editable or self._selectable)):
            return
        self.begin_editing()
        if not self._is_editing:
            return
        self.layout()
        ox, oy = self.content_offset
        line_h = self._line_height()
        y = touch.location.y + oy - _V_PAD
        line_idx = max(0, min(len(self._lines) - 1, int(y // line_h)))
        ls, le = self._lines[line_idx]
        x = touch.location.x + ox - _H_PAD
        self._cursor = ls + char_index_at_x(self._text[ls:le], x, self._font)
        self._cursor_visible = True
        self.set_needs_display()

    # -- keyboard: control keys only (no printable-char branch — see Phase 0b) --

    def _pytoui_key_input(self, key_input: str, modifiers: frozenset[str]) -> bool:
        if not self._is_editing:
            return False

        if key_input == KEY_INPUT_ESC:
            self.end_editing()
            return True
        if key_input == KEY_INPUT_RETURN:
            if self._editable and self._should_change(
                (self._cursor, self._cursor), "\n"
            ):
                self._text, self._cursor = insert_text(self._text, self._cursor, "\n")
                self._after_edit()
            return True
        if key_input == KEY_INPUT_BACKSPACE:
            if (
                self._editable
                and self._cursor > 0
                and self._should_change((self._cursor - 1, self._cursor), "")
            ):
                self._text, self._cursor = delete_backward(self._text, self._cursor)
                self._after_edit()
            return True
        if key_input == KEY_INPUT_DELETE:
            if (
                self._editable
                and self._cursor < len(self._text)
                and self._should_change((self._cursor, self._cursor + 1), "")
            ):
                self._text, self._cursor = delete_forward(self._text, self._cursor)
                self._after_edit()
            return True
        if key_input == KEY_INPUT_LEFT:
            self._cursor = max(0, self._cursor - 1)
            self._after_move()
            return True
        if key_input == KEY_INPUT_RIGHT:
            self._cursor = min(len(self._text), self._cursor + 1)
            self._after_move()
            return True
        if key_input == KEY_INPUT_HOME:
            self._cursor = self._lines[self._line_and_col_for_cursor()[0]][0]
            self._after_move()
            return True
        if key_input == KEY_INPUT_END:
            self._cursor = self._lines[self._line_and_col_for_cursor()[0]][1]
            self._after_move()
            return True
        if key_input == KEY_INPUT_UP:
            self._move_vertical(-1)
            return True
        if key_input == KEY_INPUT_DOWN:
            self._move_vertical(1)
            return True
        return False

    def _move_vertical(self, delta: int):
        self.layout()
        line_idx, col = self._line_and_col_for_cursor()
        s, _e = self._lines[line_idx]
        current_x, _ = measure_string(self._text[s : s + col], font=self._font)
        target_idx = max(0, min(len(self._lines) - 1, line_idx + delta))
        ts, te = self._lines[target_idx]
        self._cursor = ts + char_index_at_x(self._text[ts:te], current_x, self._font)
        self._after_move()

    # -- native text input / IME (Phase 0b) -----------------------------------

    def _pytoui_text_commit(self, text: str) -> bool:
        if not (self._is_editing and self._editable):
            return False
        if self._should_change((self._cursor, self._cursor), text):
            self._text, self._cursor = insert_text(self._text, self._cursor, text)
            self._after_edit()
        self._preedit_text = ""
        self._preedit_range = None
        return True

    def _pytoui_text_preedit(self, text: str, cursor: tuple[int, int] | None) -> bool:
        if not self._is_editing:
            return False
        self._preedit_text = text
        self._preedit_range = cursor
        self._cursor_visible = True
        self.set_needs_display()
        return True

    def _after_edit(self):
        self._cursor_visible = True
        self._lines_key = ()
        self._notify("textview_did_change", self)
        self.set_needs_display()

    def _after_move(self):
        self._cursor_visible = True
        self._notify("textview_did_change_selection", self)
        self.set_needs_display()

    # -- public API ------------------------------------------------------------

    def replace_range(self, start: int, end: int, text: str) -> None:
        if not self._should_change((start, end), text):
            return
        self._text, self._cursor = _replace_range_helper(self._text, start, end, text)
        self._lines_key = ()
        self._notify("textview_did_change", self)
        self.set_needs_display()

    # -- delegate dispatch -------------------------------------------------

    def _should_begin_editing(self) -> bool:
        fn = getattr(self.delegate, "textview_should_begin_editing", None)
        return True if fn is None else bool(fn(self))

    def _should_change(self, rng: tuple[int, int], replacement: str) -> bool:
        fn = getattr(self.delegate, "textview_should_change", None)
        return True if fn is None else bool(fn(self, rng, replacement))

    def _notify(self, name: str, *call_args):
        fn = getattr(self.delegate, name, None)
        if fn is not None:
            fn(*call_args)


if not IS_PYTHONISTA:
    TextView = _TextView
else:
    import ui

    TextView = ui.TextView  # type: ignore[misc,assignment]
