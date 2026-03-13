from __future__ import annotations

import time
from typing import TYPE_CHECKING

from typing_extensions import override

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
        "_pytoui_navigationStack",
        "_pytoui_currentContentView",
        "_pytoui_isNavigationBarHidden",
        "_pytoui_barTintColor",
        "_pytoui_titleColor",
        "_pytoui_backButton",
        "_pytoui_titleLabel",
        # slide animation
        "_pytoui_animOutgoing",  # view being removed (slides out)
        "_pytoui_animT0",  # animation start time
        "_pytoui_animDir",  # +1 = push (right→left), -1 = pop (left→right)
    )

    NAVIGATION_BAR_HEIGHT = 60
    DEFAULT_BACK_BTN_TITLE = "Back"
    _ANIM_DUR: float = 0.35

    def __init__(self, view: _NavigationView):
        super().__init__(view)
        self.setContentMode_(CONTENT_REDRAW)

        tint_color = self.tintColor()
        self._pytoui_barTintColor: _RGBA | None = tint_color
        self._pytoui_titleColor: _RGBA = tint_color
        self._pytoui_isNavigationBarHidden: bool = False
        self._pytoui_navigationStack: list[_ViewInternals] = []

        self._pytoui_currentContentView: _ViewInternals | None = None

        # animation state
        self._pytoui_animOutgoing: _ViewInternals | None = None
        self._pytoui_animT0: float = 0.0
        self._pytoui_animDir: int = 0  # 0 = no animation

        # Create UI elements
        self._pytoui_backButton = Button()
        self._pytoui_backButton.title = f"< {self.DEFAULT_BACK_BTN_TITLE}"
        self._pytoui_backButton.hidden = True
        self._pytoui_backButton.action = lambda _: self.pop_view()

        self._pytoui_titleLabel = Label()
        self._pytoui_titleLabel.alignment = ALIGN_CENTER
        self.pytoui_AddInternalSubview_(self._pytoui_backButton._internals_)
        self.pytoui_AddInternalSubview_(self._pytoui_titleLabel._internals_)

    @override
    def pytoui_layout(self, force: bool = False):
        nav_h = (
            self.NAVIGATION_BAR_HEIGHT if not self._pytoui_isNavigationBarHidden else 0
        )

        if not self._pytoui_isNavigationBarHidden:
            self._pytoui_backButton.frame = (0, (nav_h - 30) / 2, 120, 30)
            self._pytoui_titleLabel.frame = (
                120,
                0,
                self._frame.width - 240,
                nav_h,
            )

        x, y, w, h = self._bounds
        content_h = h - nav_h
        content_y = y + nav_h

        if (
            self._pytoui_animDir != 0
            and self._pytoui_currentContentView
            and self._pytoui_animOutgoing
        ):
            # Compute eased progress (0 → 1)
            elapsed = time.monotonic() - self._pytoui_animT0
            t = min(1.0, elapsed / self._ANIM_DUR)
            progress = 1.0 - (1.0 - t) ** 3  # cubic easeOut

            incoming_x = w * self._pytoui_animDir * (1.0 - progress)
            outgoing_x = -w * self._pytoui_animDir * progress

            self._pytoui_currentContentView.setFrame_(
                (incoming_x, content_y, w, content_h)
            )
            self._pytoui_animOutgoing.setFrame_((outgoing_x, content_y, w, content_h))
        elif self._pytoui_currentContentView:
            self._pytoui_currentContentView.setFrame_((x, content_y, w, content_h))

        super().pytoui_layout(force)

    def pytoui_navigationStack(self) -> list[_ViewInternals]:
        return self._pytoui_navigationStack

    def pytoui_isNavigationBarHidden(self) -> bool:
        return self._pytoui_isNavigationBarHidden

    def pytoui_setNavigationBarHidden_(self, value: bool):
        self._pytoui_isNavigationBarHidden = bool(value)
        self.setNeedsDisplay()
        self.setNeedsLayout()

    def pytoui_barTintColor(self) -> _RGBA | None:
        return self._pytoui_barTintColor

    def pytoui_setBarTintColor_(self, value: _ColorLike):
        self._pytoui_barTintColor = parse_color(value)
        if value is None:
            self._pytoui_barTintColor = self.tintColor()
        self._pytoui_backButton.tint_color = self._pytoui_barTintColor
        self.setNeedsDisplay()

    def pytoui_titleColor(self) -> _RGBA:
        return self._pytoui_titleColor

    def pytoui_setTitleColor_(self, value: _ColorLike):
        self._pytoui_titleColor = parse_color(value)
        self._pytoui_titleLabel.text_color = self._pytoui_titleColor
        self.setNeedsDisplay()

    def _pytoui_finishAnim(self):
        """Clean up after a slide animation completes."""
        if self._pytoui_animOutgoing is not None:
            self.pytoui_removeInternalSubview(self._pytoui_animOutgoing)
            self._pytoui_animOutgoing = None
        self._pytoui_animDir = 0
        self.pytoui_setUpdateInterval_(0.0)

    def push_view(self, view: _ViewInternals, animated: bool = True):
        """Add view to nav stack"""
        if view in self._pytoui_navigationStack:
            return

        # Finish any in-progress animation immediately
        if self._pytoui_animDir != 0:
            self._pytoui_finishAnim()

        old_view = self._pytoui_currentContentView

        # add to stack
        self._pytoui_navigationStack.append(view)
        view._pytoui_navigationView = self
        self._pytoui_currentContentView = view
        self._pytoui_titleLabel.text = view.name() or ""

        # update UI
        count = len(self._pytoui_navigationStack)
        self._pytoui_backButton.hidden = count <= 1
        if count > 1:
            prev_view = self._pytoui_navigationStack[-2]
            prev_view_name = prev_view.name()
            self._pytoui_backButton.title = (
                f"< {prev_view_name if prev_view_name else self.DEFAULT_BACK_BTN_TITLE}"
            )

        # add new view (will be laid out off-screen right when animated)
        self.pytoui_AddInternalSubview_(view)

        if animated and not _UI_DISABLE_ANIMATIONS and old_view is not None:
            self._pytoui_animOutgoing = old_view
            self._pytoui_animDir = 1  # push: incoming from right
            self._pytoui_animT0 = time.monotonic()
            self.pytoui_setUpdateInterval_(1.0 / 60.0)
        else:
            # Instant: remove old view immediately
            if old_view is not None:
                self.pytoui_removeInternalSubview(old_view)

        self.setNeedsLayout()

    def pop_view(self, animated: bool = True):
        """Removes top view from nav stack"""
        if len(self._pytoui_navigationStack) <= 1:
            return  # prevent last view from deletion

        # Finish any in-progress animation immediately
        if self._pytoui_animDir != 0:
            self._pytoui_finishAnim()

        outgoing = self._pytoui_navigationStack.pop()
        outgoing._pytoui_navigationView = None

        # Restore previous view
        prev_view = (
            self._pytoui_navigationStack[-1] if self._pytoui_navigationStack else None
        )
        self._pytoui_currentContentView = prev_view

        if prev_view:
            self.pytoui_AddInternalSubview_(prev_view)
            self._pytoui_titleLabel.text = prev_view.name() or ""

        count = len(self._pytoui_navigationStack)
        self._pytoui_backButton.hidden = count <= 1
        if count > 1:
            prev2 = self._pytoui_navigationStack[-2]
            prev2_name = prev2.name()
            self._pytoui_backButton.title = (
                f"< {prev2_name if prev2_name else self.DEFAULT_BACK_BTN_TITLE}"
            )

        if animated and not _UI_DISABLE_ANIMATIONS and prev_view is not None:
            self._pytoui_animOutgoing = outgoing
            self._pytoui_animDir = -1  # pop: incoming from left
            self._pytoui_animT0 = time.monotonic()
            self.pytoui_setUpdateInterval_(1.0 / 60.0)
        else:
            self.pytoui_removeInternalSubview(outgoing)

        self.setNeedsLayout()

    @override
    def pytoui_update(self):
        super().pytoui_update()
        if self._pytoui_animDir == 0:
            return
        elapsed = time.monotonic() - self._pytoui_animT0
        if elapsed >= self._ANIM_DUR:
            self._pytoui_finishAnim()
        self.setNeedsLayout()


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

        super().__init__(**kwargs)

    @property
    def navigation_bar_hidden(self) -> bool:
        return self._internals_.pytoui_isNavigationBarHidden()

    @navigation_bar_hidden.setter
    def navigation_bar_hidden(self, value: bool):
        self._internals_.pytoui_setNavigationBarHidden_(value)

    @property
    def bar_tint_color(self) -> _RGBA | None:
        return self._internals_.pytoui_barTintColor()

    @bar_tint_color.setter
    def bar_tint_color(self, value: _ColorLike):
        self._internals_.pytoui_setBarTintColor_(value)

    @property
    def title_color(self) -> _RGBA:
        return self._internals_.pytoui_titleColor()

    @title_color.setter
    def title_color(self, value: _ColorLike):
        self._internals_.pytoui_setTitleColor_(value)

    def pop_view(self, animated: bool = True):
        self._internals_.pop_view(animated)

    def push_view(self, view: _View, animated: bool = True):
        self._internals_.push_view(view._internals_, animated)


if not IS_PYTHONISTA:
    NavigationView = _NavigationView

else:
    import ui  # type: ignore[import-not-found]

    NavigationView = ui.NavigationView  # type: ignore[assignment,misc,no-redef]
