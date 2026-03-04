from __future__ import annotations

from typing import TYPE_CHECKING

from pytoui._platform import IS_PYTHONISTA
from pytoui.ui._button import Button
from pytoui.ui._constants import ALIGN_CENTER, CONTENT_REDRAW
from pytoui.ui._draw import parse_color
from pytoui.ui._internals import _final_, _getset_descriptor
from pytoui.ui._label import Label
from pytoui.ui._view import _View, _ViewInternals

if TYPE_CHECKING:
    from pytoui.ui._types import _RGBA, _ColorLike

__all__ = ("NavigationView", "_NavigationViewInternals")


class _NavigationViewInternals(_ViewInternals):
    __slots__ = (
        "_navigation_stack",
        "_navigation_bar_hidden",
        "_bar_tint_color",
        "_title_color",
        "_back_button",
        "_title_label",
    )

    NAVIGATION_BAR_SIZE = 60

    def __init__(self, view: _View):
        super().__init__(view)
        self.content_mode = CONTENT_REDRAW

        self._navigation_bar_hidden: bool = False
        self._bar_tint_color: _RGBA | None = None
        self._title_color: _RGBA | None = None

        self._navigation_stack: list[_ViewInternals] = []

        self._back_button = Button()
        self._back_button.title = "<- Back"
        self._back_button.flex = "R"
        self._back_button.action = self.pop_view

        self._title_label = Label()
        self._title_label.alignment = ALIGN_CENTER
        self._title_label.flex = "H"
        self.pytoui_add_internal_subview(self._back_button._internals_)
        self.pytoui_add_internal_subview(self._title_label._internals_)

    def pytoui_layout(self):
        nav_size = self.NAVIGATION_BAR_SIZE
        # self._back_button.frame = (0, 0, 100, nav_size)
        # self._title_label.frame = (100, 0, self.frame.width - 100, nav_size)
        # NOTE: or maybe centered?
        self._back_button.frame = (0, 0, 100, nav_size)
        self._title_label.frame = (
            self._back_button.x,
            0,
            self.frame.width - self._back_button.x,
            nav_size,
        )
        super().pytoui_layout()

    @property
    def navigation_stack(self) -> list[_ViewInternals]:
        return self._navigation_stack

    @property
    def navigation_bar_hidden(self) -> bool:
        return self._navigation_bar_hidden

    @navigation_bar_hidden.setter
    def navigation_bar_hidden(self, value: bool):
        self._navigation_bar_hidden = bool(value)
        self.set_needs_display()

    @property
    def bar_tint_color(self) -> _RGBA | None:
        return self._bar_tint_color

    @bar_tint_color.setter
    def bar_tint_color(self, value: _ColorLike):
        self._bar_tint_color = parse_color(value)
        self.set_needs_display()

    @property
    def title_color(self) -> _RGBA | None:
        return self._title_color

    @title_color.setter
    def title_color(self, value: _ColorLike):
        self._title_color = parse_color(value)
        self._title_label.text_color = self._title_color
        self.set_needs_display()

    def push_view(self, view: _ViewInternals):
        if view not in self._navigation_stack:
            self._navigation_stack.append(view)
            self._back_button.hidden = len(self._navigation_stack) <= 1
            if current := self.current_view():
                self._title_label.text = current.name
            self.set_needs_display()

    def pop_view(self):
        # prevent from deleting last view
        if len(self._navigation_stack) > 1:
            self._navigation_stack.pop()
            self._back_button.hidden = len(self._navigation_stack) <= 1
            if current := self.current_view():
                self._title_label.text = current.name
            self.set_needs_display()

    def current_view(self) -> _ViewInternals | None:
        if len(self._navigation_stack):
            return self._navigation_stack[-1]
        return None


@_final_
class _NavigationView(_View):
    __slots__ = ("__internals_",)

    _internals_: _getset_descriptor["_NavigationView", "_NavigationViewInternals"] = (
        _getset_descriptor(
            "internals_",
            factory=lambda obj: _NavigationViewInternals(obj),
            readonly=True,
        )
    )

    def __init__(self, view: _View):
        self.push_view(view)

    @property
    def navigation_bar_hidden(self) -> bool:
        return self._internals_.navigation_bar_hidden

    @navigation_bar_hidden.setter
    def navigation_bar_hidden(self, value: bool):
        self._internals_.navigation_bar_hidden = value

    @property
    def bar_tint_color(self) -> _RGBA | None:
        return self._internals_.bar_tint_color

    @bar_tint_color.setter
    def bar_tint_color(self, value: _ColorLike):
        self._internals_.bar_tint_color = value

    @property
    def title_color(self) -> _RGBA | None:
        return self._internals_.title_color

    @title_color.setter
    def title_color(self, value: _ColorLike):
        self._internals_.title_color = value

    def pop_view(self, animated: bool = True):
        self._internals_.pop_view()

    def push_view(self, view: _View, animated: bool = True):
        self._internals_.push_view(view._internals_)


if not IS_PYTHONISTA:
    NavigationView = _NavigationView

else:
    import ui  # type: ignore[import-not-found]

    NavigationView = ui.NavigationView  # type: ignore[assignment,misc,no-redef]
