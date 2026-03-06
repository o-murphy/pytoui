from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pytoui._platform import IS_PYTHONISTA
from pytoui.ui._scroll_view import _ScrollView

if TYPE_CHECKING:
    from pytoui.ui._types import (
        _Alignment,
        _CapitalizationType,
        _ColorLike,
        _Font,
        _KeyboardType,
    )


__all__ = ("TextView",)


class _TextView(_ScrollView):
    alignment: _Alignment
    autocapitalization_type: _CapitalizationType
    autocorrection_type: bool
    delegate: Any
    editable: bool
    font: _Font
    keyboard_type: _KeyboardType
    selectable: bool
    selected_range: tuple[int, int]
    spellchecking_type: Any
    text: str
    text_color: _ColorLike

    def __init__(self, *args, **kwargs): ...

    def begin_editing(self) -> None: ...
    def end_editing(self) -> None: ...
    def replace_range(self, start: int, end: int, text: str) -> None: ...


if not IS_PYTHONISTA:
    TextView = _TextView
else:
    import ui

    TextView = ui.TextView  # type: ignore[misc,assignment]
