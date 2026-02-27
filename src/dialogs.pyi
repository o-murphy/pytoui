from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from console import alert, hud_alert, input_alert, login_alert, password_alert
from pytoui.ui._constants import AUTOCAPITALIZE_SENTENCES

if TYPE_CHECKING:
    from pytoui.ui._types import _Font

__all__ = (
    "list_dialog",
    "edit_list_dialog",
    "form_dialog",
    "text_dialog",
    "date_dialog",
    "time_dialog",
    "datetime_dialog",
    "duration_dialog",
    "share_image",
    "share_text",
    "share_url",
    "pick_document",
    # console
    "alert",
    "input_alert",
    "login_alert",
    "password_alert",
    "hud_alert",
)

class _SupportsStr(Protocol):
    def __str__(self) -> str: ...

def list_dialog(
    title: str = "", items: list[_SupportsStr] | None = None, multiple: bool = False
): ...
def edit_list_dialog(
    title: str = "",
    items: list[_SupportsStr] | None = None,
    move: bool = True,
    delete: bool = True,
): ...
def form_dialog(title: str = "", fields=None, sections=None): ...
def text_dialog(
    title: str = "",
    text: str = "",
    font: _Font = ("<system>", 16),
    autocorrection=None,
    autocapitalization=AUTOCAPITALIZE_SENTENCES,
    spellchecking=None,
): ...
def date_dialog(title: str = ""): ...
def time_dialog(title: str = ""): ...
def datetime_dialog(title: str = ""): ...
def duration_dialog(title: str = ""): ...
def share_image(img): ...
def share_text(text: str): ...
def share_url(url: str): ...
def pick_document(types=["public.data"]): ...
