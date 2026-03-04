from __future__ import annotations

from typing import TYPE_CHECKING

from pytoui._platform import IS_PYTHONISTA
from pytoui.ui._internals import _final_

if TYPE_CHECKING:
    from pytoui.ui._image import Image
    from pytoui.ui._types import _RGBA, _Action

__all__ = ("ButtonItem",)


@_final_
class _ButtonItem:
    """A button for use in the title bar when presenting views
    or inside a NavigationView.

    Set View.left_button_items or View.right_button_items to a list of ButtonItems.
    Unlike Button, this class does not inherit from View.
    """

    __slots__ = ("_action", "_enabled", "_image", "_tint_color", "_title")

    def __init__(
        self,
        title: str | None = None,
        image: Image | None = None,
        action: _Action | None = None,
        enabled: bool = True,
        tint_color: _RGBA | None = None,
    ):
        self._title: str | None = title
        self._image: Image | None = image
        self._action: _Action | None = action
        self._enabled: bool = enabled
        self._tint_color: _RGBA | None = tint_color

    # -- Properties -----------------------------------------------------------

    @property
    def title(self) -> str | None:
        """
        The button's title. A ButtonItem should have a title or an image, not both.
        """
        return self._title

    @title.setter
    def title(self, value: str | None):
        self._title = value

    @property
    def image(self) -> Image | None:
        """
        The button's image. A ButtonItem should have a title or an image, not both.
        """
        return self._image

    @image.setter
    def image(self, value: Image | None):
        self._image = value

    @property
    def action(self) -> _Action | None:
        """The action called when the button is tapped."""
        return self._action

    @action.setter
    def action(self, value: _Action | None):
        self._action = value

    @property
    def enabled(self) -> bool:
        """Whether the button is enabled. Disabled buttons are grayed out."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = bool(value)

    @property
    def tint_color(self) -> _RGBA | None:
        """The tint color for the button's title or image."""
        return self._tint_color

    @tint_color.setter
    def tint_color(self, value: _RGBA | None):
        self._tint_color = value

    def __str__(self) -> str:
        label = repr(self._title) if self._title else repr(self._image)
        return f"<ButtonItem {label}>"


if not IS_PYTHONISTA:
    ButtonItem = _ButtonItem
else:
    import ui

    ButtonItem = ui.ButtonItem  # type: ignore[misc,assignment]
