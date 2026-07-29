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
from pytoui.ui._internals import _final_, _getset_descriptor
from pytoui.ui._text_editing import (
    char_index_at_x,
    delete_backward,
    delete_forward,
    insert_text,
)
from pytoui.ui._types import Rect, Touch
from pytoui.ui._view import _View, _ViewInternals

if TYPE_CHECKING:
    from pytoui.ui._types import (
        _RGBA,
        _Action,
        _CapitalizationType,
        _ColorLike,
        _Font,
        _KeyboardType,
    )


__all__ = ("TextField", "_TextField", "_TextFieldDelegate", "_TextFieldInternals")

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


class _TextFieldInternals(_ViewInternals):
    __slots__ = (
        # Pythonista-compatible state
        "_action",
        "_autocapitalizationType",
        "_autocorrectionType",
        "_bordered",
        "_clearButtonMode",
        "_delegate",
        "_enabled",
        "_font",
        "_keyboardType",
        "_placeholder",
        "_secure",
        "_spellcheckingType",
        "_text",
        "_textColor",
        # Internal editing state
        "_pytoui_cursor",
        "_pytoui_isEditing",
        "_pytoui_cursorVisible",
        "_pytoui_scrollX",
        "_pytoui_preeditText",
        "_pytoui_preeditRange",
    )

    def __init__(self, view: _TextField):
        super().__init__(view)
        self._action: _Action | None = None
        self._autocapitalizationType: _CapitalizationType = 0
        self._autocorrectionType: Any = None
        self._bordered: bool = True
        self._clearButtonMode: int = 0
        self._delegate: _TextFieldDelegate | None = None
        self._enabled: bool = True
        self._font: _Font = ("<system>", 17.0)
        self._keyboardType: _KeyboardType = 0
        self._placeholder: str = ""
        self._secure: bool = False
        self._spellcheckingType: Any = None
        self._text: str = ""
        self._textColor: _RGBA = (0.0, 0.0, 0.0, 1.0)

        self._pytoui_cursor: int = 0
        self._pytoui_isEditing: bool = False
        self._pytoui_cursorVisible: bool = False
        self._pytoui_scrollX: float = 0.0
        self._pytoui_preeditText: str = ""
        self._pytoui_preeditRange: tuple[int, int] | None = None

        self.setFrame_(Rect(0.0, 0.0, 200.0, 32.0))

    # -- Pythonista-compatible accessors ---------------------------------------

    def action(self) -> _Action | None:
        return self._action

    def setAction_(self, value: _Action | None):
        self._action = value

    def autocapitalizationType(self) -> _CapitalizationType:
        return self._autocapitalizationType

    def setAutocapitalizationType_(self, value: _CapitalizationType):
        self._autocapitalizationType = value

    def autocorrectionType(self) -> Any:
        return self._autocorrectionType

    def setAutocorrectionType_(self, value: Any):
        self._autocorrectionType = value

    def isBordered(self) -> bool:
        return self._bordered

    def setBordered_(self, value: bool):
        self._bordered = bool(value)
        self.setNeedsDisplay()

    def clearButtonMode(self) -> int:
        return self._clearButtonMode

    def setClearButtonMode_(self, value: int):
        self._clearButtonMode = value
        self.setNeedsDisplay()

    def delegate(self) -> _TextFieldDelegate | None:
        return self._delegate

    def setDelegate_(self, value: _TextFieldDelegate | None):
        self._delegate = value

    def isEnabled(self) -> bool:
        return self._enabled

    def setEnabled_(self, value: bool):
        self._enabled = bool(value)
        if not value:
            self.end_editing()
        self.setNeedsDisplay()

    def font(self) -> _Font:
        return self._font

    def setFont_(self, value: _Font):
        self._font = value
        self._update_scroll_to_cursor()
        self.setNeedsDisplay()

    def keyboardType(self) -> _KeyboardType:
        return self._keyboardType

    def setKeyboardType_(self, value: _KeyboardType):
        self._keyboardType = value

    def placeholder(self) -> str:
        return self._placeholder

    def setPlaceholder_(self, value: str):
        self._placeholder = value
        self.setNeedsDisplay()

    def isSecure(self) -> bool:
        return self._secure

    def setSecure_(self, value: bool):
        self._secure = bool(value)
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
        self._update_scroll_to_cursor()
        self.setNeedsDisplay()

    def textColor(self) -> _RGBA:
        return self._textColor

    def setTextColor_(self, value: _ColorLike):
        self._textColor = parse_color(value)
        self.setNeedsDisplay()

    # -- display helpers --------------------------------------------------

    def _display_text(self) -> str:
        return ("•" * len(self._text)) if self._secure else self._text

    def _composed_text(self) -> str:
        """Display text with any in-progress IME composition inserted at cursor."""
        display = self._display_text()
        if not self._pytoui_preeditText:
            return display
        cursor = self._pytoui_cursor
        return display[:cursor] + self._pytoui_preeditText + display[cursor:]

    def _caret_index(self) -> int:
        """Index into _composed_text() where the caret should be drawn."""
        if self._pytoui_preeditText:
            offset = (
                self._pytoui_preeditRange[0]
                if self._pytoui_preeditRange
                else len(self._pytoui_preeditText)
            )
            return self._pytoui_cursor + offset
        return self._pytoui_cursor

    # -- drawing ---------------------------------------------------------------

    def draw(self):
        w, h = self.frame().size

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
            if self._placeholder and not self._pytoui_isEditing:
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
                    _TEXT_INSET - self._pytoui_scrollX,
                    baseline_y,
                    text_width,
                    text_height,
                ),
                font=self._font,
                color=self._textColor,
                alignment=ALIGN_LEFT,
                line_break_mode=LB_CLIP,
            )

        if self._pytoui_preeditText:
            pre_start = self._pytoui_cursor
            pre_end = self._pytoui_cursor + len(self._pytoui_preeditText)
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
            set_color(self._textColor)
            fill_rect(
                _TEXT_INSET - self._pytoui_scrollX + x0,
                h / 2 + text_height / 2,
                x1 - x0,
                1.0,
            )

        if self._pytoui_isEditing and self._pytoui_cursorVisible:
            caret_x, _ = measure_string(
                composed[: self._caret_index()],
                font=self._font,
                alignment=ALIGN_LEFT,
                line_break_mode=LB_CLIP,
            )
            set_color(self._textColor)
            fill_rect(
                _TEXT_INSET - self._pytoui_scrollX + caret_x,
                4.0,
                1.5,
                max(h - 8.0, 0.0),
            )

    # -- focus / editing lifecycle --------------------------------------------

    def begin_editing(self) -> None:
        if self._pytoui_isEditing or not self._enabled:
            return
        if not self._should_begin_editing():
            return
        self.becomeFirstResponder()

    def end_editing(self) -> None:
        if self._pytoui_isEditing:
            self.resignFirstResponder()

    def did_become_first_responder(self):
        self._pytoui_isEditing = True
        self._pytoui_cursor = len(self._text)
        self._pytoui_cursorVisible = True
        self.pytoui_setUpdateInterval_(0.5)
        self._update_scroll_to_cursor()
        self._notify("textfield_did_begin_editing", self.ref())
        self.setNeedsDisplay()

    def did_resign_first_responder(self):
        self._pytoui_isEditing = False
        self._pytoui_preeditText = ""
        self._pytoui_preeditRange = None
        self.pytoui_setUpdateInterval_(0.0)
        self._notify("textfield_did_end_editing", self.ref())
        self.setNeedsDisplay()

    def update(self):
        self._pytoui_cursorVisible = not self._pytoui_cursorVisible
        self.setNeedsDisplay()

    # -- touch -------------------------------------------------------------

    def touch_began(self, touch: Touch):
        if not self._enabled:
            return
        self.begin_editing()
        if not self._pytoui_isEditing:
            return
        local_x = touch.location.x - _TEXT_INSET + self._pytoui_scrollX
        self._pytoui_cursor = char_index_at_x(self._display_text(), local_x, self._font)
        self._pytoui_cursorVisible = True
        self._update_scroll_to_cursor()
        self.setNeedsDisplay()

    # -- keyboard: control keys only (no printable-char branch — see Phase 0b) --

    def _pytoui_key_input(self, key_input: str, modifiers: frozenset[str]) -> bool:
        if not (self._pytoui_isEditing and self._enabled):
            return False

        if key_input == KEY_INPUT_RETURN:
            self._should_return()
            return True
        if key_input == KEY_INPUT_ESC:
            self.end_editing()
            return True
        if key_input == KEY_INPUT_BACKSPACE:
            cursor = self._pytoui_cursor
            if cursor > 0 and self._should_change((cursor - 1, cursor), ""):
                self._text, self._pytoui_cursor = delete_backward(self._text, cursor)
                self._after_edit()
            return True
        if key_input == KEY_INPUT_DELETE:
            cursor = self._pytoui_cursor
            if cursor < len(self._text) and self._should_change(
                (cursor, cursor + 1), ""
            ):
                self._text, self._pytoui_cursor = delete_forward(self._text, cursor)
                self._after_edit()
            return True
        if key_input == KEY_INPUT_LEFT:
            self._pytoui_cursor = max(0, self._pytoui_cursor - 1)
            self._after_move()
            return True
        if key_input == KEY_INPUT_RIGHT:
            self._pytoui_cursor = min(len(self._text), self._pytoui_cursor + 1)
            self._after_move()
            return True
        if key_input == KEY_INPUT_HOME:
            self._pytoui_cursor = 0
            self._after_move()
            return True
        if key_input == KEY_INPUT_END:
            self._pytoui_cursor = len(self._text)
            self._after_move()
            return True
        return False

    # -- native text input / IME (Phase 0b) -----------------------------------

    def _pytoui_text_commit(self, text: str) -> bool:
        if not (self._pytoui_isEditing and self._enabled):
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
        self._update_scroll_to_cursor()
        self._notify("textfield_did_change", self.ref())
        self.setNeedsDisplay()

    def _after_move(self):
        self._pytoui_cursorVisible = True
        self._update_scroll_to_cursor()
        self.setNeedsDisplay()

    def _update_scroll_to_cursor(self):
        display_text = self._display_text()
        caret_x, _ = measure_string(
            display_text[: self._pytoui_cursor],
            font=self._font,
            alignment=ALIGN_LEFT,
            line_break_mode=LB_CLIP,
        )
        visible_w = max(self.frame().width - 2 * _TEXT_INSET, 0.0)
        if caret_x - self._pytoui_scrollX < 0:
            self._pytoui_scrollX = caret_x
        elif caret_x - self._pytoui_scrollX > visible_w:
            self._pytoui_scrollX = caret_x - visible_w

    # -- delegate dispatch -------------------------------------------------

    def _should_begin_editing(self) -> bool:
        fn = getattr(self._delegate, "textfield_should_begin_editing", None)
        return True if fn is None else bool(fn(self.ref()))

    def _should_return(self) -> bool:
        fn = getattr(self._delegate, "textfield_should_return", None)
        if fn is None:
            self.end_editing()
            self._ensure_action_and_call()
            return True
        return bool(fn(self.ref()))

    def _should_change(self, rng: tuple[int, int], replacement: str) -> bool:
        fn = getattr(self._delegate, "textfield_should_change", None)
        return True if fn is None else bool(fn(self.ref(), rng, replacement))

    def _notify(self, name: str, *call_args):
        fn = getattr(self._delegate, name, None)
        if fn is not None:
            fn(*call_args)

    def _ensure_action_and_call(self):
        if self._action is None:
            return
        if len(inspect.signature(self._action).parameters) > 0:
            self._action(self.ref())
        else:
            self._action()


class _TextField(_View):
    _internals_: _getset_descriptor["_TextField", "_TextFieldInternals"] = (
        _getset_descriptor(
            "internals_",
            factory=lambda obj: _TextFieldInternals(obj),
            readonly=True,
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # -- properties -----------------------------------------------------------

    @property
    def action(self) -> _Action | None:
        return self._internals_.action()

    @action.setter
    def action(self, value: _Action | None):
        self._internals_.setAction_(value)

    @property
    def autocapitalization_type(self) -> _CapitalizationType:
        return self._internals_.autocapitalizationType()

    @autocapitalization_type.setter
    def autocapitalization_type(self, value: _CapitalizationType):
        self._internals_.setAutocapitalizationType_(value)

    @property
    def autocorrection_type(self) -> Any:
        return self._internals_.autocorrectionType()

    @autocorrection_type.setter
    def autocorrection_type(self, value: Any):
        self._internals_.setAutocorrectionType_(value)

    @property
    def bordered(self) -> bool:
        return self._internals_.isBordered()

    @bordered.setter
    def bordered(self, value: bool):
        self._internals_.setBordered_(value)

    @property
    def clear_button_mode(self) -> int:
        return self._internals_.clearButtonMode()

    @clear_button_mode.setter
    def clear_button_mode(self, value: int):
        self._internals_.setClearButtonMode_(value)

    @property
    def delegate(self) -> _TextFieldDelegate | None:
        return self._internals_.delegate()

    @delegate.setter
    def delegate(self, value: _TextFieldDelegate | None):
        self._internals_.setDelegate_(value)

    @property
    def enabled(self) -> bool:
        return self._internals_.isEnabled()

    @enabled.setter
    def enabled(self, value: bool):
        self._internals_.setEnabled_(value)

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
    def placeholder(self) -> str:
        return self._internals_.placeholder()

    @placeholder.setter
    def placeholder(self, value: str):
        self._internals_.setPlaceholder_(value)

    @property
    def secure(self) -> bool:
        return self._internals_.isSecure()

    @secure.setter
    def secure(self, value: bool):
        self._internals_.setSecure_(value)

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

    def _pytoui_key_input(self, key_input: str, modifiers: frozenset[str]) -> bool:
        return self._internals_._pytoui_key_input(key_input, modifiers)

    def _pytoui_text_commit(self, text: str) -> bool:
        return self._internals_._pytoui_text_commit(text)

    def _pytoui_text_preedit(self, text: str, cursor: tuple[int, int] | None) -> bool:
        return self._internals_._pytoui_text_preedit(text, cursor)


if not IS_PYTHONISTA:

    @_final_
    class TextField(_TextField):
        pass

else:
    import ui

    TextField = ui.TextField  # type: ignore[misc,assignment]
