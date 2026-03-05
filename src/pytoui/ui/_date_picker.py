from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pytoui._platform import IS_PYTHONISTA
from pytoui.ui._view import View

if TYPE_CHECKING:
    from pytoui.ui._constants import DATE_PICKER_MODE_DATE_AND_TIME
    from pytoui.ui._types import _Action, _DatePickerMode

__all__ = ("DatePicker",)


class _DatePicker(View):
    def __init__(self, *args, **kwargs):
        self._action: _Action | None = None
        self._countdown_duration: float = 0
        self._date: Any = None
        self._mode: _DatePickerMode = DATE_PICKER_MODE_DATE_AND_TIME

        super().__init__(*args, **kwargs)

    @property
    def action(self) -> _Action | None:
        return self._action

    @action.setter
    def action(self, value: _Action | None):
        self._action = value

    @property
    def countdown_duration(self) -> float:
        return self._countdown_duration

    @countdown_duration.setter
    def countdown_duration(self, value: float):
        self._countdown_duration = value

    @property
    def date(self) -> Any:
        return self._date

    @date.setter
    def date(self, value: Any):
        self._date = value

    @property
    def mode(self) -> _DatePickerMode:
        return self._mode

    @mode.setter
    def mode(self, value: _DatePickerMode):
        self._mode = value


if not IS_PYTHONISTA:
    DatePicker = _DatePicker
else:
    import ui

    DatePicker = ui.DatePicker  # type: ignore[misc,assignment]
