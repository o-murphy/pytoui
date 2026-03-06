from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pytoui._platform import IS_PYTHONISTA
from pytoui.ui._view import View

if TYPE_CHECKING:
    from pytoui.ui._types import (
        _Action,
        _CapitalizationType,
        _ColorLike,
        _Font,
        _KeyboardType,
    )


__all__ = ("TextField",)


class _TextField(View):
    action: _Action | None
    autocapitalization_type: _CapitalizationType
    autocorrection_type: Any
    bordered: bool
    clear_button_mode: int  # 0=never, 1=while editing, 2=unless editing, 3=always
    delegate: Any
    enabled: bool
    font: _Font
    keyboard_type: _KeyboardType
    placeholder: str
    secure: bool
    spellchecking_type: Any
    text: str
    text_color: _ColorLike

    def __init__(self, *args, **kwargs): ...

    def begin_editing(self) -> None: ...
    def end_editing(self) -> None: ...


if not IS_PYTHONISTA:
    TextField = _TextField
else:
    import ui

    TextField = ui.TextField  # type: ignore[misc,assignment]
