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
        "_current_content_view",
        "_navigation_bar_hidden",
        "_bar_tint_color",
        "_title_color",
        "_back_button",
        "_title_label",
    )

    NAVIGATION_BAR_HEIGHT = 60
    DEFAULT_BACK_BTN_TITLE = "Back"

    def __init__(self, view: _NavigationView):
        super().__init__(view)
        self.content_mode = CONTENT_REDRAW

        self._navigation_bar_hidden: bool = False
        self._bar_tint_color: _RGBA | None = None
        self._title_color: _RGBA | None = None

        self._navigation_stack: list[_ViewInternals] = []
        self._current_content_view: _ViewInternals | None = None

        # Create UI elements
        self._back_button = Button()
        self._back_button.title = f"< {self.DEFAULT_BACK_BTN_TITLE}"
        self._back_button.hidden = True  # Спочатку схована
        self._back_button.action = lambda _: self.pop_view()

        self._title_label = Label()
        self._title_label.alignment = ALIGN_CENTER
        self.pytoui_add_internal_subview(self._back_button._internals_)
        self.pytoui_add_internal_subview(self._title_label._internals_)

    def pytoui_layout(self):
        nav_h = self.NAVIGATION_BAR_HEIGHT if not self._navigation_bar_hidden else 0

        if not self._navigation_bar_hidden:
            self._back_button.frame = (0, (nav_h - 30) / 2, 120, 30)  # Центруємо кнопку
            self._title_label.frame = (
                120,
                0,
                self._frame.width - 240,
                nav_h,
            )

        if self._current_content_view:
            x, y, w, h = self._bounds
            self._current_content_view.frame = (x, y + nav_h, w, h - nav_h)

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
        self.set_needs_layout()

    @property
    def bar_tint_color(self) -> _RGBA | None:
        return self._bar_tint_color

    @bar_tint_color.setter
    def bar_tint_color(self, value: _ColorLike):
        self._bar_tint_color = parse_color(value)
        if value is None:
            self._bar_tint_color = self._tint_color
        self._back_button._text_color = self._bar_tint_color
        self.set_needs_display()

    @property
    def title_color(self) -> _RGBA | None:
        return self._title_color

    @title_color.setter
    def title_color(self, value: _ColorLike):
        self._title_color = parse_color(value)
        self._title_label.text_color = self._title_color
        self.set_needs_display()

    def push_view(self, view: _ViewInternals, animated: bool = True):
        """Add view to nav stack"""
        if view in self._navigation_stack:
            return

        # remove current view
        if self._current_content_view:
            self.pytoui_remove_internal_subview(self._current_content_view)

        # add to stack
        self._navigation_stack.append(view)
        view._navigation_view = self

        self._current_content_view = view
        self._title_label.text = view.name or ""

        # update UI
        count = len(self._navigation_stack)
        self._back_button.hidden = count <= 1
        if count > 1:
            prev_view = self._navigation_stack[-2]
            self._back_button.title = (
                f"< {prev_view.name if prev_view.name else self.DEFAULT_BACK_BTN_TITLE}"
            )

        # add new view as internal
        self.pytoui_add_internal_subview(view)

        self.set_needs_layout()

    def pop_view(self, animated: bool = True):
        """Removes top view from nav stack"""
        if len(self._navigation_stack) <= 1:
            return  # prevent last view from deletion

        # remove current view
        removed = self._navigation_stack.pop()
        removed._navigation_view = None

        self.pytoui_remove_internal_subview(removed)

        # update current view
        self._current_content_view = (
            self._navigation_stack[-1] if self._navigation_stack else None
        )

        if self._current_content_view:
            self.pytoui_add_internal_subview(self._current_content_view)
            self._title_label.text = self._current_content_view.name or ""

        count = len(self._navigation_stack)
        self._back_button.hidden = count <= 1
        if count > 1:
            prev_view = self._navigation_stack[-2]
            self._back_button.title = (
                f"< {prev_view.name if prev_view.name else self.DEFAULT_BACK_BTN_TITLE}"
            )

        self.set_needs_layout()

    def current_view(self) -> _ViewInternals | None:
        return self._current_content_view


@_final_
class _NavigationView(_View):
    _internals_: _getset_descriptor["_NavigationView", "_NavigationViewInternals"] = (
        _getset_descriptor(
            "internals_",
            factory=lambda obj: _NavigationViewInternals(obj),
            readonly=True,
        )
    )

    def __init__(self, view: _View, /, **kwargs):
        self.push_view(view)

        super().__init__(view, **kwargs)

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
        self._internals_.pop_view(animated)

    def push_view(self, view: _View, animated: bool = True):
        self._internals_.push_view(view._internals_, animated)


if not IS_PYTHONISTA:
    NavigationView = _NavigationView

else:
    import ui  # type: ignore[import-not-found]

    NavigationView = ui.NavigationView  # type: ignore[assignment,misc,no-redef]
