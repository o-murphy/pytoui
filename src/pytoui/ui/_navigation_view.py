from __future__ import annotations

import time
from typing import TYPE_CHECKING

from pytoui._platform import _UI_DISABLE_ANIMATIONS, IS_PYTHONISTA
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
        # slide animation
        "_anim_outgoing",  # view being removed (slides out)
        "_anim_t0",  # animation start time
        "_anim_dir",  # +1 = push (right→left), -1 = pop (left→right)
    )

    NAVIGATION_BAR_HEIGHT = 60
    DEFAULT_BACK_BTN_TITLE = "Back"
    _ANIM_DUR: float = 0.35

    def __init__(self, view: _NavigationView):
        super().__init__(view)
        self.content_mode = CONTENT_REDRAW

        self._navigation_bar_hidden: bool = False
        self._bar_tint_color: _RGBA | None = self.tint_color
        self._title_color: _RGBA = self.tint_color

        self._navigation_stack: list[_ViewInternals] = []
        self._current_content_view: _ViewInternals | None = None

        # animation state
        self._anim_outgoing: _ViewInternals | None = None
        self._anim_t0: float = 0.0
        self._anim_dir: int = 0  # 0 = no animation

        # Create UI elements
        self._back_button = Button()
        self._back_button.title = f"< {self.DEFAULT_BACK_BTN_TITLE}"
        self._back_button.hidden = True
        self._back_button.action = lambda _: self.pop_view()

        self._title_label = Label()
        self._title_label.alignment = ALIGN_CENTER
        self.pytoui_add_internal_subview(self._back_button._internals_)
        self.pytoui_add_internal_subview(self._title_label._internals_)

    def pytoui_layout(self, force: bool = False):
        nav_h = self.NAVIGATION_BAR_HEIGHT if not self._navigation_bar_hidden else 0

        if not self._navigation_bar_hidden:
            self._back_button.frame = (0, (nav_h - 30) / 2, 120, 30)
            self._title_label.frame = (
                120,
                0,
                self._frame.width - 240,
                nav_h,
            )

        x, y, w, h = self._bounds
        content_h = h - nav_h
        content_y = y + nav_h

        if self._anim_dir != 0 and self._current_content_view and self._anim_outgoing:
            # Compute eased progress (0 → 1)
            elapsed = time.monotonic() - self._anim_t0
            t = min(1.0, elapsed / self._ANIM_DUR)
            progress = 1.0 - (1.0 - t) ** 3  # cubic easeOut

            incoming_x = w * self._anim_dir * (1.0 - progress)
            outgoing_x = -w * self._anim_dir * progress

            self._current_content_view.frame = (incoming_x, content_y, w, content_h)
            self._anim_outgoing.frame = (outgoing_x, content_y, w, content_h)
        elif self._current_content_view:
            self._current_content_view.frame = (x, content_y, w, content_h)

        super().pytoui_layout(force)

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
            self._bar_tint_color = self.tint_color
        self._back_button.tint_color = self._bar_tint_color
        self.set_needs_display()

    @property
    def title_color(self) -> _RGBA:
        return self._title_color

    @title_color.setter
    def title_color(self, value: _ColorLike):
        self._title_color = parse_color(value)
        self._title_label.text_color = self._title_color
        self.set_needs_display()

    def _finish_anim(self):
        """Clean up after a slide animation completes."""
        if self._anim_outgoing is not None:
            self.pytoui_remove_internal_subview(self._anim_outgoing)
            self._anim_outgoing = None
        self._anim_dir = 0
        self.update_interval = 0.0

    def push_view(self, view: _ViewInternals, animated: bool = True):
        """Add view to nav stack"""
        if view in self._navigation_stack:
            return

        # Finish any in-progress animation immediately
        if self._anim_dir != 0:
            self._finish_anim()

        old_view = self._current_content_view

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

        # add new view (will be laid out off-screen right when animated)
        self.pytoui_add_internal_subview(view)

        if animated and not _UI_DISABLE_ANIMATIONS and old_view is not None:
            self._anim_outgoing = old_view
            self._anim_dir = 1  # push: incoming from right
            self._anim_t0 = time.monotonic()
            self.update_interval = 1.0 / 60.0
        else:
            # Instant: remove old view immediately
            if old_view is not None:
                self.pytoui_remove_internal_subview(old_view)

        self.set_needs_layout()

    def pop_view(self, animated: bool = True):
        """Removes top view from nav stack"""
        if len(self._navigation_stack) <= 1:
            return  # prevent last view from deletion

        # Finish any in-progress animation immediately
        if self._anim_dir != 0:
            self._finish_anim()

        outgoing = self._navigation_stack.pop()
        outgoing._navigation_view = None

        # Restore previous view
        prev_view = self._navigation_stack[-1] if self._navigation_stack else None
        self._current_content_view = prev_view

        if prev_view:
            self.pytoui_add_internal_subview(prev_view)
            self._title_label.text = prev_view.name or ""

        count = len(self._navigation_stack)
        self._back_button.hidden = count <= 1
        if count > 1:
            prev2 = self._navigation_stack[-2]
            self._back_button.title = (
                f"< {prev2.name if prev2.name else self.DEFAULT_BACK_BTN_TITLE}"
            )

        if animated and not _UI_DISABLE_ANIMATIONS and prev_view is not None:
            self._anim_outgoing = outgoing
            self._anim_dir = -1  # pop: incoming from left
            self._anim_t0 = time.monotonic()
            self.update_interval = 1.0 / 60.0
        else:
            self.pytoui_remove_internal_subview(outgoing)

        self.set_needs_layout()

    def pytoui_update(self):
        super().pytoui_update()
        if self._anim_dir == 0:
            return
        elapsed = time.monotonic() - self._anim_t0
        if elapsed >= self._ANIM_DUR:
            self._finish_anim()
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
    def title_color(self) -> _RGBA:
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
