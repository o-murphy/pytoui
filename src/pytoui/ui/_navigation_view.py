from __future__ import annotations

from typing import TYPE_CHECKING

from pytoui._platform import IS_PYTHONISTA
from pytoui.ui._button import Button
from pytoui.ui._constants import CONTENT_REDRAW
from pytoui.ui._draw import fill_rect, parse_color, set_color
from pytoui.ui._final import _final_
from pytoui.ui._view import _getset_descriptor, _View, _ViewInternals

if TYPE_CHECKING:
    from pytoui.ui._types import _RGBA, _ColorLike

__all__ = ("NavigationView", "_NavigationViewInternals")


class _NavigationViewInternals(_ViewInternals):
    __slots__ = (
        "_navigation_stack",
        "_navigation_bar_hidden",
        "_bar_tint_color",
        "_title_color",
        "_back_btn",
    )

    NAVIGATION_BAR_SIZE = 60

    def __init__(self, view: _View):
        super().__init__(view)
        self.content_mode = CONTENT_REDRAW

        self._navigation_bar_hidden: bool = False
        self._bar_tint_color: _RGBA | None = None
        self._title_color: _RGBA | None = None

        self._navigation_stack: list[_ViewInternals] = []

        self._back_btn = Button()
        self._back_btn.title = "<- Back"
        self._back_btn.frame = (0, 0, 100, self.NAVIGATION_BAR_SIZE)
        self._back_btn.action = lambda sender: self.pop_view()

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
        self.set_needs_display()

    def push_view(self, view: _ViewInternals):
        if view not in self._navigation_stack:
            self._navigation_stack.append(view)
            self.set_needs_display()

    def pop_view(self):
        # prevent from deleting last view
        if len(self._navigation_stack) > 1:
            self._navigation_stack.pop()
            self.set_needs_display()

    def pytoui_hit_test(self, x, y):
        # FIXME: fix if needed, idk which priority should be
        v = self.current_view()
        if v is not None:
            child_target = v.pytoui_hit_test(x, y)
            if child_target is not None:
                return child_target
        back_btn = self._back_btn._internals_.pytoui_hit_test(x, y)
        if back_btn is not None:
            return back_btn
        return super().pytoui_hit_test(x, y)

    def pytoui_scroll_hit_test(self, x, y):
        # FIXME: fix if needed, idk which priority should be
        v = self.current_view()
        if v is not None:
            child_target = v.pytoui_scroll_hit_test(x, y)
            if child_target is not None:
                return child_target
        back_btn = self._back_btn._internals_.pytoui_scroll_hit_test(x, y)
        if back_btn is not None:
            return back_btn
        return super().pytoui_scroll_hit_test(x, y)

    def current_view(self) -> _ViewInternals | None:
        if len(self._navigation_stack):
            return self._navigation_stack[-1]
        return None

    def draw(self):
        # FIXME: temp behaviour
        set_color(self.title_color)
        x, y, w, _ = self._frame
        bar_frame = (x, y, w, self.NAVIGATION_BAR_SIZE)
        fill_rect(bar_frame)

    def pytoui_render(self):
        # FIXME: fix: animations of current and back_btn is not working
        current = self.current_view()
        if current:
            margin = self.NAVIGATION_BAR_SIZE
            if current._pytoui_needs_display:
                self.set_needs_display()
                current.frame = (
                    self.frame.x,
                    self.frame.y + margin,
                    self.frame.width,
                    self.frame.height - margin,
                )

        super().pytoui_render()

        self._back_btn.background_color = self.title_color
        self._back_btn.set_needs_display()
        self._back_btn._internals_.pytoui_render()

        if current:
            current.pytoui_render()


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
