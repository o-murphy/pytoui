from typing import TYPE_CHECKING

from pytoui._platform import IS_PYTHONISTA
from pytoui.ui._draw import parse_color
from pytoui.ui._final import _final_
from pytoui.ui._view import View

if TYPE_CHECKING:
    from pytoui.ui._types import _RGBA, _ColorLike

__all__ = ("NavigationView",)


@_final_
class _NavigationView(View):
    __slots__ = (
        "_navigation_bar_hidden",
        "_bar_tint_color",
        "_title_color",
    )

    def __init__(self):
        self._navigation_bar_hidden: bool = False
        self._bar_tint_color: _RGBA | None = None
        self._title_color: _RGBA | None = None

        self._views_stack: list[View] = []

    @property
    def navigation_bar_hidden(self) -> bool:
        return self._navigation_bar_hidden

    @navigation_bar_hidden.setter
    def navigation_bar_hidden(self, value: bool):
        self._navigation_bar_hidden = bool(value)

    @property
    def bar_tint_color(self) -> _RGBA | None:
        return self._bar_tint_color

    @bar_tint_color.setter
    def bar_tint_color(self, value: _ColorLike):
        self._bar_tint_color = parse_color(value)

    @property
    def title_color(self) -> _RGBA | None:
        return self._title_color

    @title_color.setter
    def title_color(self, value: _ColorLike):
        self._title_color = parse_color(value)

    def pop_view(self, animated: bool = True):
        self._views_stack.pop()

    def push_view(self, view: View, animated: bool = True):
        self._views_stack.append(view)


if not IS_PYTHONISTA:
    NavigationView = _NavigationView

else:
    import ui  # type: ignore[import-not-found]

    NavigationView = ui.NavigationView  # type: ignore[assignment,misc,no-redef]
