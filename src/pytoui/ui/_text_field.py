from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Protocol

from pytoui._platform import IS_PYTHONISTA
from pytoui.hid import (
    KEY_INPUT_BACKSPACE,
    KEY_INPUT_DELETE,
    KEY_INPUT_END,
    KEY_INPUT_ESC,
    KEY_INPUT_HOME,
    KEY_INPUT_LEFT,
    KEY_INPUT_RETURN,
    KEY_INPUT_RIGHT,
)
from pytoui.ui._constants import ALIGN_LEFT, LB_CLIP
from pytoui.ui._draw import (
    Path,
    draw_string,
    fill_rect,
    measure_string,
    parse_color,
    set_color,
)
from pytoui.ui._internals import _final_
from pytoui.ui._text_editing import (
    char_index_at_x,
    delete_backward,
    delete_forward,
    insert_text,
)
from pytoui.ui._types import Rect, Touch
from pytoui.ui._view import View

if TYPE_CHECKING:
    from pytoui.ui._types import (
        _RGBA,
        _Action,
        _CapitalizationType,
        _ColorLike,
        _Font,
        _KeyboardType,
    )


__all__ = ("TextField", "_TextField", "_TextFieldDelegate")

_TEXT_INSET = 6.0
_BORDER_COLOR: tuple[float, float, float, float] = (0.78, 0.78, 0.82, 1.0)
_FILL_COLOR: tuple[float, float, float, float] = (0.94, 0.94, 0.96, 1.0)
_PLACEHOLDER_COLOR: tuple[float, float, float, float] = (0.6, 0.6, 0.6, 1.0)


class _TextFieldDelegate(Protocol):
    def textfield_should_begin_editing(self, textfield) -> bool:
        return True

    def textfield_did_begin_editing(self, textfield: TextField): ...
    def textfield_did_end_editing(self, textfield: TextField): ...
    def textfield_should_return(self, textfield: TextField) -> bool:
        textfield.end_editing()
        return True

    def textfield_should_change(self, textfield: TextField, range, replacement) -> bool:
        return True

    def textfield_did_change(self, textfield: TextField): ...


@_final_
class _TextField(View):
    __slots__ = (
        "_action",
        "_autocapitalization_type",
        "_autocorrection_type",
        "_bordered",
        "_clear_button_mode",
        "_cursor",
        "_cursor_visible",
        "_delegate",
        "_enabled",
        "_font",
        "_is_editing",
        "_keyboard_type",
        "_placeholder",
        "_preedit_range",
        "_preedit_text",
        "_scroll_x",
        "_secure",
        "_spellchecking_type",
        "_text",
        "_text_color",
    )

    def __init__(self, *args, **kwargs):
        self._action: _Action | None = None
        self._autocapitalization_type: _CapitalizationType = 0
        self._autocorrection_type: Any = None
        self._bordered: bool = True
        self._clear_button_mode: int = 0
        self._delegate: _TextFieldDelegate | None = None
        self._enabled: bool = True
        self._font: _Font = ("<system>", 17.0)
        self._keyboard_type: _KeyboardType = 0
        self._placeholder: str = ""
        self._secure: bool = False
        self._spellchecking_type: Any = None
        self._text: str = ""
        self._text_color: _RGBA = (0.0, 0.0, 0.0, 1.0)

        self._cursor: int = 0
        self._is_editing: bool = False
        self._cursor_visible: bool = False
        self._scroll_x: float = 0.0
        self._preedit_text: str = ""
        self._preedit_range: tuple[int, int] | None = None

        self.frame = Rect(0.0, 0.0, 200.0, 32.0)

        super().__init__(*args, **kwargs)

    # -- properties -----------------------------------------------------------

    @property
    def action(self) -> _Action | None:
        return self._action

    @action.setter
    def action(self, value: _Action | None):
        self._action = value

    @property
    def autocapitalization_type(self) -> _CapitalizationType:
        return self._autocapitalization_type

    @autocapitalization_type.setter
    def autocapitalization_type(self, value: _CapitalizationType):
        self._autocapitalization_type = value

    @property
    def autocorrection_type(self) -> Any:
        return self._autocorrection_type

    @autocorrection_type.setter
    def autocorrection_type(self, value: Any):
        self._autocorrection_type = value

    @property
    def bordered(self) -> bool:
        return self._bordered

    @bordered.setter
    def bordered(self, value: bool):
        self._bordered = value
        self.set_needs_display()

    @property
    def clear_button_mode(self) -> int:
        return self._clear_button_mode

    @clear_button_mode.setter
    def clear_button_mode(self, value: int):
        self._clear_button_mode = value
        self.set_needs_display()

    @property
    def delegate(self) -> _TextFieldDelegate | None:
        return self._delegate

    @delegate.setter
    def delegate(self, value: _TextFieldDelegate | None):
        self._delegate = value

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        if not value:
            self.end_editing()
        self.set_needs_display()

    @property
    def font(self) -> _Font:
        return self._font

    @font.setter
    def font(self, value: _Font):
        self._font = value
        self._update_scroll_to_cursor()
        self.set_needs_display()

    @property
    def keyboard_type(self) -> _KeyboardType:
        return self._keyboard_type

    @keyboard_type.setter
    def keyboard_type(self, value: _KeyboardType):
        self._keyboard_type = value

    @property
    def placeholder(self) -> str:
        return self._placeholder

    @placeholder.setter
    def placeholder(self, value: str):
        self._placeholder = value
        self.set_needs_display()

    @property
    def secure(self) -> bool:
        return self._secure

    @secure.setter
    def secure(self, value: bool):
        self._secure = value
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
        self._update_scroll_to_cursor()
        self.set_needs_display()

    @property
    def text_color(self) -> _RGBA:
        return self._text_color

    @text_color.setter
    def text_color(self, value: _ColorLike):
        self._text_color = parse_color(value)
        self.set_needs_display()

    # -- display helpers --------------------------------------------------

    def _display_text(self) -> str:
        return ("•" * len(self._text)) if self._secure else self._text

    def _composed_text(self) -> str:
        """Display text with any in-progress IME composition inserted at cursor."""
        display = self._display_text()
        if not self._preedit_text:
            return display
        return display[: self._cursor] + self._preedit_text + display[self._cursor :]

    def _caret_index(self) -> int:
        """Index into _composed_text() where the caret should be drawn."""
        if self._preedit_text:
            offset = (
                self._preedit_range[0]
                if self._preedit_range
                else len(self._preedit_text)
            )
            return self._cursor + offset
        return self._cursor

    # -- drawing ---------------------------------------------------------------

    def draw(self):
        w, h = self.width, self.height

        if self._bordered:
            set_color(_FILL_COLOR)
            Path.rounded_rect(0.0, 0.0, w, h, 6.0).fill()
            set_color(_BORDER_COLOR)
            Path.rounded_rect(
                0.5, 0.5, max(w - 1.0, 0.0), max(h - 1.0, 0.0), 6.0
            ).stroke()

        composed = self._composed_text()
        _, text_height = measure_string(
            composed or " ",
            font=self._font,
            alignment=ALIGN_LEFT,
            line_break_mode=LB_CLIP,
        )
        baseline_y = h / 2 - text_height / 2

        if not composed:
            if self._placeholder and not self._is_editing:
                draw_string(
                    self._placeholder,
                    rect=(_TEXT_INSET, baseline_y, w - 2 * _TEXT_INSET, text_height),
                    font=self._font,
                    color=_PLACEHOLDER_COLOR,
                    alignment=ALIGN_LEFT,
                    line_break_mode=LB_CLIP,
                )
        else:
            text_width, _ = measure_string(
                composed, font=self._font, alignment=ALIGN_LEFT, line_break_mode=LB_CLIP
            )
            draw_string(
                composed,
                rect=(
                    _TEXT_INSET - self._scroll_x,
                    baseline_y,
                    text_width,
                    text_height,
                ),
                font=self._font,
                color=self._text_color,
                alignment=ALIGN_LEFT,
                line_break_mode=LB_CLIP,
            )

        if self._preedit_text:
            pre_start = self._cursor
            pre_end = self._cursor + len(self._preedit_text)
            x0, _ = measure_string(
                composed[:pre_start],
                font=self._font,
                alignment=ALIGN_LEFT,
                line_break_mode=LB_CLIP,
            )
            x1, _ = measure_string(
                composed[:pre_end],
                font=self._font,
                alignment=ALIGN_LEFT,
                line_break_mode=LB_CLIP,
            )
            set_color(self._text_color)
            fill_rect(
                _TEXT_INSET - self._scroll_x + x0, h / 2 + text_height / 2, x1 - x0, 1.0
            )

        if self._is_editing and self._cursor_visible:
            caret_x, _ = measure_string(
                composed[: self._caret_index()],
                font=self._font,
                alignment=ALIGN_LEFT,
                line_break_mode=LB_CLIP,
            )
            set_color(self._text_color)
            fill_rect(
                _TEXT_INSET - self._scroll_x + caret_x, 4.0, 1.5, max(h - 8.0, 0.0)
            )

    # -- focus / editing lifecycle --------------------------------------------

    def begin_editing(self) -> None:
        if self._is_editing or not self._enabled:
            return
        if not self._should_begin_editing():
            return
        self.become_first_responder()

    def end_editing(self) -> None:
        if self._is_editing:
            self._internals_.resignFirstResponder()

    def did_become_first_responder(self):
        self._is_editing = True
        self._cursor = len(self._text)
        self._cursor_visible = True
        self.update_interval = 0.5
        self._update_scroll_to_cursor()
        self._notify("textfield_did_begin_editing", self)
        self.set_needs_display()

    def did_resign_first_responder(self):
        self._is_editing = False
        self._preedit_text = ""
        self._preedit_range = None
        self.update_interval = 0.0
        self._notify("textfield_did_end_editing", self)
        self.set_needs_display()

    def update(self):
        self._cursor_visible = not self._cursor_visible
        self.set_needs_display()

    # -- touch -------------------------------------------------------------

    def touch_began(self, touch: Touch):
        if not self._enabled:
            return
        self.begin_editing()
        if not self._is_editing:
            return
        local_x = touch.location.x - _TEXT_INSET + self._scroll_x
        self._cursor = char_index_at_x(self._display_text(), local_x, self._font)
        self._cursor_visible = True
        self._update_scroll_to_cursor()
        self.set_needs_display()

    # -- keyboard: control keys only (no printable-char branch — see Phase 0b) --

    def _pytoui_key_input(self, key_input: str, modifiers: frozenset[str]) -> bool:
        if not (self._is_editing and self._enabled):
            return False

        if key_input == KEY_INPUT_RETURN:
            self._should_return()
            return True
        if key_input == KEY_INPUT_ESC:
            self.end_editing()
            return True
        if key_input == KEY_INPUT_BACKSPACE:
            if self._cursor > 0 and self._should_change(
                (self._cursor - 1, self._cursor), ""
            ):
                self._text, self._cursor = delete_backward(self._text, self._cursor)
                self._after_edit()
            return True
        if key_input == KEY_INPUT_DELETE:
            if self._cursor < len(self._text) and self._should_change(
                (self._cursor, self._cursor + 1), ""
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
            self._cursor = 0
            self._after_move()
            return True
        if key_input == KEY_INPUT_END:
            self._cursor = len(self._text)
            self._after_move()
            return True
        return False

    # -- native text input / IME (Phase 0b) -----------------------------------

    def _pytoui_text_commit(self, text: str) -> bool:
        if not (self._is_editing and self._enabled):
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
        self._update_scroll_to_cursor()
        self._notify("textfield_did_change", self)
        self.set_needs_display()

    def _after_move(self):
        self._cursor_visible = True
        self._update_scroll_to_cursor()
        self.set_needs_display()

    def _update_scroll_to_cursor(self):
        display_text = self._display_text()
        caret_x, _ = measure_string(
            display_text[: self._cursor],
            font=self._font,
            alignment=ALIGN_LEFT,
            line_break_mode=LB_CLIP,
        )
        visible_w = max(self.width - 2 * _TEXT_INSET, 0.0)
        if caret_x - self._scroll_x < 0:
            self._scroll_x = caret_x
        elif caret_x - self._scroll_x > visible_w:
            self._scroll_x = caret_x - visible_w

    # -- delegate dispatch -------------------------------------------------

    def _should_begin_editing(self) -> bool:
        fn = getattr(self._delegate, "textfield_should_begin_editing", None)
        return True if fn is None else bool(fn(self))

    def _should_return(self) -> bool:
        fn = getattr(self._delegate, "textfield_should_return", None)
        if fn is None:
            self.end_editing()
            self._ensure_action_and_call(self)
            return True
        return bool(fn(self))

    def _should_change(self, rng: tuple[int, int], replacement: str) -> bool:
        fn = getattr(self._delegate, "textfield_should_change", None)
        return True if fn is None else bool(fn(self, rng, replacement))

    def _notify(self, name: str, *call_args):
        fn = getattr(self._delegate, name, None)
        if fn is not None:
            fn(*call_args)

    def _ensure_action_and_call(self, sender=None):
        action = getattr(self, "action", None)
        if action is None:
            return
        if len(inspect.signature(action).parameters) > 0:
            action(sender if sender is not None else self)
        else:
            action()


if not IS_PYTHONISTA:
    TextField = _TextField
else:
    import ui

    TextField = ui.TextField  # type: ignore[misc,assignment]
