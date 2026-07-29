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
from pytoui.ui._internals import _final_, _getset_descriptor
from pytoui.ui._scroll_view import (
    _ScrollView,
    _ScrollViewDelegate,
    _ScrollViewInternals,
)
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


__all__ = ("TextView", "_TextView", "_TextViewDelegate", "_TextViewInternals")

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


class _TextViewInternals(_ScrollViewInternals):
    __slots__ = (
        # Pythonista-compatible state
        "_alignment",
        "_autoContentInset",
        "_autocapitalizationType",
        "_autocorrectionType",
        "_editable",
        "_font",
        "_keyboardType",
        "_selectable",
        "_spellcheckingType",
        "_text",
        "_textColor",
        # Internal editing/layout state
        "_pytoui_cursor",
        "_pytoui_isEditing",
        "_pytoui_cursorVisible",
        "_pytoui_preeditText",
        "_pytoui_preeditRange",
        "_pytoui_lines",
        "_pytoui_linesKey",
        "_pytoui_touchStartXY",
        "_pytoui_touchStartTime",
    )

    def __init__(self, view: _TextView):
        super().__init__(view)
        self._alignment: _Alignment = 0
        self._autoContentInset: Any = True
        self._autocapitalizationType: _CapitalizationType = 0
        self._autocorrectionType: bool = True
        self._editable: bool = True
        self._font: _Font = ("<system>", 17.0)
        self._keyboardType: _KeyboardType = 0
        self._selectable: bool = True
        self._spellcheckingType: Any = None
        self._text: str = ""
        self._textColor: _RGBA = (0.0, 0.0, 0.0, 1.0)

        self._pytoui_cursor: int = 0
        self._pytoui_isEditing: bool = False
        self._pytoui_cursorVisible: bool = False
        self._pytoui_preeditText: str = ""
        self._pytoui_preeditRange: tuple[int, int] | None = None
        self._pytoui_lines: list[tuple[int, int]] = [(0, 0)]
        self._pytoui_linesKey: tuple = ()
        self._pytoui_touchStartXY: tuple[float, float] = (0.0, 0.0)
        self._pytoui_touchStartTime: int = 0

    # -- Pythonista-compatible accessors ---------------------------------------

    def alignment(self) -> _Alignment:
        return self._alignment

    def setAlignment_(self, value: _Alignment):
        self._alignment = value
        self.setNeedsDisplay()

    def autoContentInset(self) -> Any:
        return self._autoContentInset

    def setAutoContentInset_(self, value: Any):
        self._autoContentInset = value

    def autocapitalizationType(self) -> _CapitalizationType:
        return self._autocapitalizationType

    def setAutocapitalizationType_(self, value: _CapitalizationType):
        self._autocapitalizationType = value

    def autocorrectionType(self) -> bool:
        return self._autocorrectionType

    def setAutocorrectionType_(self, value: bool):
        self._autocorrectionType = value

    def isEditable(self) -> bool:
        return self._editable

    def setEditable_(self, value: bool):
        self._editable = bool(value)
        if not value:
            self.end_editing()

    def font(self) -> _Font:
        return self._font

    def setFont_(self, value: _Font):
        self._font = value
        self._pytoui_linesKey = ()
        self.setNeedsDisplay()

    def keyboardType(self) -> _KeyboardType:
        return self._keyboardType

    def setKeyboardType_(self, value: _KeyboardType):
        self._keyboardType = value

    def isSelectable(self) -> bool:
        return self._selectable

    def setSelectable_(self, value: bool):
        self._selectable = bool(value)
        if not value:
            self.end_editing()

    def selectedRange(self) -> tuple[int, int]:
        return (self._pytoui_cursor, self._pytoui_cursor)

    def setSelectedRange_(self, value: tuple[int, int]):
        self._pytoui_cursor = max(0, min(len(self._text), value[1]))
        self.setNeedsDisplay()

    def spellcheckingType(self) -> Any:
        return self._spellcheckingType

    def setSpellcheckingType_(self, value: Any):
        self._spellcheckingType = value

    def text(self) -> str:
        return self._text

    def setText_(self, value: str | None):
        self._text = value or ""
        self._pytoui_cursor = min(self._pytoui_cursor, len(self._text))
        self._pytoui_linesKey = ()
        self.setNeedsDisplay()

    def textColor(self) -> _RGBA:
        return self._textColor

    def setTextColor_(self, value: _ColorLike):
        self._textColor = parse_color(value)
        self.setNeedsDisplay()

    # -- layout ------------------------------------------------------------

    def _line_height(self) -> float:
        return measure_string(" ", font=self._font)[1]

    def layout(self):
        bw = self.bounds().w
        key = (self._text, self._font, bw)
        if key == self._pytoui_linesKey:
            return
        avail_w = max(1.0, bw - 2 * _H_PAD)
        self._pytoui_lines = wrap_lines(self._text, avail_w, self._font)
        self._pytoui_linesKey = key
        line_h = self._line_height()
        self.setContentSize((bw, len(self._pytoui_lines) * line_h + 2 * _V_PAD))

    def _line_and_col_for_cursor(self) -> tuple[int, int]:
        cursor = self._pytoui_cursor
        for i, (s, e) in enumerate(self._pytoui_lines):
            if s <= cursor <= e:
                return i, cursor - s
        last = len(self._pytoui_lines) - 1
        return last, cursor - self._pytoui_lines[last][0]

    # -- drawing -------------------------------------------------------------

    def draw(self):
        self.layout()
        ox, oy = self._contentOffset
        w, h = self.frame().size
        line_h = self._line_height()
        cursor_line, cursor_col = self._line_and_col_for_cursor()

        for i, (s, e) in enumerate(self._pytoui_lines):
            y = _V_PAD + i * line_h - oy
            if not (-line_h <= y <= h):
                continue
            line_text = self._text[s:e]
            if self._pytoui_preeditText and i == cursor_line:
                line_text = (
                    line_text[:cursor_col]
                    + self._pytoui_preeditText
                    + line_text[cursor_col:]
                )
            draw_string(
                line_text,
                rect=(_H_PAD - ox, y, w, line_h),
                font=self._font,
                color=self._textColor,
                alignment=self._alignment,
            )

        if self._pytoui_preeditText:
            s, e = self._pytoui_lines[cursor_line]
            base_text = self._text[s:e]
            pre_x0, _ = measure_string(base_text[:cursor_col], font=self._font)
            pre_x1, _ = measure_string(
                base_text[:cursor_col] + self._pytoui_preeditText, font=self._font
            )
            y = _V_PAD + cursor_line * line_h - oy
            set_color(self._textColor)
            fill_rect(_H_PAD - ox + pre_x0, y + line_h - 2, pre_x1 - pre_x0, 1.0)

        if self._pytoui_isEditing and self._pytoui_cursorVisible:
            s, e = self._pytoui_lines[cursor_line]
            base_text = self._text[s:e]
            caret_col = cursor_col
            if self._pytoui_preeditText:
                offset = (
                    self._pytoui_preeditRange[0]
                    if self._pytoui_preeditRange
                    else len(self._pytoui_preeditText)
                )
                caret_col += offset
                base_text = (
                    base_text[:cursor_col]
                    + self._pytoui_preeditText
                    + base_text[cursor_col:]
                )
            caret_x, _ = measure_string(base_text[:caret_col], font=self._font)
            y = _V_PAD + cursor_line * line_h - oy
            set_color(self._textColor)
            fill_rect(_H_PAD - ox + caret_x, y, 1.5, line_h)

    # -- focus / editing lifecycle --------------------------------------------

    def begin_editing(self) -> None:
        if self._pytoui_isEditing or not (self._editable or self._selectable):
            return
        if not self._should_begin_editing():
            return
        self.becomeFirstResponder()

    def end_editing(self) -> None:
        if self._pytoui_isEditing:
            self.resignFirstResponder()

    def did_become_first_responder(self):
        self._pytoui_isEditing = True
        self._pytoui_cursorVisible = True
        self.pytoui_setUpdateInterval_(0.5)
        self._notify("textview_did_begin_editing", self.ref())
        self.setNeedsDisplay()

    def did_resign_first_responder(self):
        self._pytoui_isEditing = False
        self._pytoui_preeditText = ""
        self._pytoui_preeditRange = None
        self.pytoui_setUpdateInterval_(0.0)
        self._notify("textview_did_end_editing", self.ref())
        self.setNeedsDisplay()

    def update(self):
        self._pytoui_cursorVisible = not self._pytoui_cursorVisible
        self.setNeedsDisplay()

    # -- touch -----------------------------------------------------------------

    def touch_began(self, touch: Touch):
        super().touch_began(touch)
        self._pytoui_touchStartXY = (touch.location.x, touch.location.y)
        self._pytoui_touchStartTime = touch.timestamp

    def touch_ended(self, touch: Touch):
        dx = touch.location.x - self._pytoui_touchStartXY[0]
        dy = touch.location.y - self._pytoui_touchStartXY[1]
        was_tap = (dx * dx + dy * dy) <= 9.0
        super().touch_ended(touch)
        if not (was_tap and (self._editable or self._selectable)):
            return
        self.begin_editing()
        if not self._pytoui_isEditing:
            return
        self.layout()
        ox, oy = self._contentOffset
        line_h = self._line_height()
        y = touch.location.y + oy - _V_PAD
        line_idx = max(0, min(len(self._pytoui_lines) - 1, int(y // line_h)))
        ls, le = self._pytoui_lines[line_idx]
        x = touch.location.x + ox - _H_PAD
        self._pytoui_cursor = ls + char_index_at_x(self._text[ls:le], x, self._font)
        self._pytoui_cursorVisible = True
        self.setNeedsDisplay()

    # -- keyboard: control keys only (no printable-char branch — see Phase 0b) --

    def _pytoui_key_input(self, key_input: str, modifiers: frozenset[str]) -> bool:
        if not self._pytoui_isEditing:
            return False

        cursor = self._pytoui_cursor
        if key_input == KEY_INPUT_ESC:
            self.end_editing()
            return True
        if key_input == KEY_INPUT_RETURN:
            if self._editable and self._should_change((cursor, cursor), "\n"):
                self._text, self._pytoui_cursor = insert_text(self._text, cursor, "\n")
                self._after_edit()
            return True
        if key_input == KEY_INPUT_BACKSPACE:
            if (
                self._editable
                and cursor > 0
                and self._should_change((cursor - 1, cursor), "")
            ):
                self._text, self._pytoui_cursor = delete_backward(self._text, cursor)
                self._after_edit()
            return True
        if key_input == KEY_INPUT_DELETE:
            if (
                self._editable
                and cursor < len(self._text)
                and self._should_change((cursor, cursor + 1), "")
            ):
                self._text, self._pytoui_cursor = delete_forward(self._text, cursor)
                self._after_edit()
            return True
        if key_input == KEY_INPUT_LEFT:
            self._pytoui_cursor = max(0, cursor - 1)
            self._after_move()
            return True
        if key_input == KEY_INPUT_RIGHT:
            self._pytoui_cursor = min(len(self._text), cursor + 1)
            self._after_move()
            return True
        if key_input == KEY_INPUT_HOME:
            line_idx = self._line_and_col_for_cursor()[0]
            self._pytoui_cursor = self._pytoui_lines[line_idx][0]
            self._after_move()
            return True
        if key_input == KEY_INPUT_END:
            line_idx = self._line_and_col_for_cursor()[0]
            self._pytoui_cursor = self._pytoui_lines[line_idx][1]
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
        s, _e = self._pytoui_lines[line_idx]
        current_x, _ = measure_string(self._text[s : s + col], font=self._font)
        target_idx = max(0, min(len(self._pytoui_lines) - 1, line_idx + delta))
        ts, te = self._pytoui_lines[target_idx]
        self._pytoui_cursor = ts + char_index_at_x(
            self._text[ts:te], current_x, self._font
        )
        self._after_move()

    # -- native text input / IME (Phase 0b) -----------------------------------

    def _pytoui_text_commit(self, text: str) -> bool:
        if not (self._pytoui_isEditing and self._editable):
            return False
        cursor = self._pytoui_cursor
        if self._should_change((cursor, cursor), text):
            self._text, self._pytoui_cursor = insert_text(self._text, cursor, text)
            self._after_edit()
        self._pytoui_preeditText = ""
        self._pytoui_preeditRange = None
        return True

    def _pytoui_text_preedit(self, text: str, cursor: tuple[int, int] | None) -> bool:
        if not self._pytoui_isEditing:
            return False
        self._pytoui_preeditText = text
        self._pytoui_preeditRange = cursor
        self._pytoui_cursorVisible = True
        self.setNeedsDisplay()
        return True

    def _after_edit(self):
        self._pytoui_cursorVisible = True
        self._pytoui_linesKey = ()
        self._notify("textview_did_change", self.ref())
        self.setNeedsDisplay()

    def _after_move(self):
        self._pytoui_cursorVisible = True
        self._notify("textview_did_change_selection", self.ref())
        self.setNeedsDisplay()

    # -- public API ------------------------------------------------------------

    def replace_range(self, start: int, end: int, text: str) -> None:
        if not self._should_change((start, end), text):
            return
        self._text, self._pytoui_cursor = _replace_range_helper(
            self._text, start, end, text
        )
        self._pytoui_linesKey = ()
        self._notify("textview_did_change", self.ref())
        self.setNeedsDisplay()

    # -- delegate dispatch -------------------------------------------------

    def _should_begin_editing(self) -> bool:
        fn = getattr(self._delegate, "textview_should_begin_editing", None)
        return True if fn is None else bool(fn(self.ref()))

    def _should_change(self, rng: tuple[int, int], replacement: str) -> bool:
        fn = getattr(self._delegate, "textview_should_change", None)
        return True if fn is None else bool(fn(self.ref(), rng, replacement))

    def _notify(self, name: str, *call_args):
        fn = getattr(self._delegate, name, None)
        if fn is not None:
            fn(*call_args)


class _TextView(_ScrollView):
    _internals_: _getset_descriptor["_TextView", "_TextViewInternals"] = (
        _getset_descriptor(
            "internals_",
            factory=lambda obj: _TextViewInternals(obj),
            readonly=True,
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # -- properties ------------------------------------------------------------

    @property
    def alignment(self) -> _Alignment:
        return self._internals_.alignment()

    @alignment.setter
    def alignment(self, value: _Alignment):
        self._internals_.setAlignment_(value)

    @property
    def auto_content_inset(self) -> Any:
        return self._internals_.autoContentInset()

    @auto_content_inset.setter
    def auto_content_inset(self, value: Any):
        self._internals_.setAutoContentInset_(value)

    @property
    def autocapitalization_type(self) -> _CapitalizationType:
        return self._internals_.autocapitalizationType()

    @autocapitalization_type.setter
    def autocapitalization_type(self, value: _CapitalizationType):
        self._internals_.setAutocapitalizationType_(value)

    @property
    def autocorrection_type(self) -> bool:
        return self._internals_.autocorrectionType()

    @autocorrection_type.setter
    def autocorrection_type(self, value: bool):
        self._internals_.setAutocorrectionType_(value)

    @property
    def editable(self) -> bool:
        return self._internals_.isEditable()

    @editable.setter
    def editable(self, value: bool):
        self._internals_.setEditable_(value)

    @property
    def font(self) -> _Font:
        return self._internals_.font()

    @font.setter
    def font(self, value: _Font):
        self._internals_.setFont_(value)

    @property
    def keyboard_type(self) -> _KeyboardType:
        return self._internals_.keyboardType()

    @keyboard_type.setter
    def keyboard_type(self, value: _KeyboardType):
        self._internals_.setKeyboardType_(value)

    @property
    def selectable(self) -> bool:
        return self._internals_.isSelectable()

    @selectable.setter
    def selectable(self, value: bool):
        self._internals_.setSelectable_(value)

    @property
    def selected_range(self) -> tuple[int, int]:
        return self._internals_.selectedRange()

    @selected_range.setter
    def selected_range(self, value: tuple[int, int]):
        self._internals_.setSelectedRange_(value)

    @property
    def spellchecking_type(self) -> Any:
        return self._internals_.spellcheckingType()

    @spellchecking_type.setter
    def spellchecking_type(self, value: Any):
        self._internals_.setSpellcheckingType_(value)

    @property
    def text(self) -> str:
        return self._internals_.text()

    @text.setter
    def text(self, value: str | None):
        self._internals_.setText_(value)

    @property
    def text_color(self) -> _RGBA:
        return self._internals_.textColor()

    @text_color.setter
    def text_color(self, value: _ColorLike):
        self._internals_.setTextColor_(value)

    # -- overridable hooks (responder-chain dispatch looks these up on self) --

    def layout(self):
        self._internals_.layout()

    def draw(self):
        self._internals_.draw()

    def begin_editing(self) -> None:
        self._internals_.begin_editing()

    def end_editing(self) -> None:
        self._internals_.end_editing()

    def did_become_first_responder(self):
        self._internals_.did_become_first_responder()

    def did_resign_first_responder(self):
        self._internals_.did_resign_first_responder()

    def update(self):
        self._internals_.update()

    def touch_began(self, touch: Touch):
        self._internals_.touch_began(touch)

    def touch_ended(self, touch: Touch):
        self._internals_.touch_ended(touch)

    def _pytoui_key_input(self, key_input: str, modifiers: frozenset[str]) -> bool:
        return self._internals_._pytoui_key_input(key_input, modifiers)

    def _pytoui_text_commit(self, text: str) -> bool:
        return self._internals_._pytoui_text_commit(text)

    def _pytoui_text_preedit(self, text: str, cursor: tuple[int, int] | None) -> bool:
        return self._internals_._pytoui_text_preedit(text, cursor)

    # -- public API ------------------------------------------------------------

    def replace_range(self, start: int, end: int, text: str) -> None:
        self._internals_.replace_range(start, end, text)


if not IS_PYTHONISTA:

    @_final_
    class TextView(_TextView):
        pass

else:
    import ui

    TextView = ui.TextView  # type: ignore[misc,assignment]
