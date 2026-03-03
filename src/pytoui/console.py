from pytoui._platform import IS_PYTHONISTA
from pytoui.ui._button import Button
from pytoui.ui._constants import ALIGN_CENTER
from pytoui.ui._final import _final_
from pytoui.ui._label import Label
from pytoui.ui._view import View

__all__ = ("alert",)


@_final_
class _Alert(View):
    MAX_WIDTH = 280
    BTN_H = 32
    TITLE_H = 36
    MESSAGE_H = 32

    def __init__(
        self,
        title: str,
        message: str | None = None,
        button1: str = "OK",
        button2: str | None = None,
        button3: str | None = None,
        hide_cancel_button: bool = False,
    ):
        super().__init__()

        self._result: str = "cancel"
        self._action_buttons: list[Button] = []

        self.background_color = (0.2, 0.2, 0.2, 0.96)
        self.name = title

        # Title
        self._title_lbl = Label()
        self._title_lbl.text = title
        self._title_lbl.alignment = ALIGN_CENTER
        self._title_lbl.font = ("<system-bold>", 16)
        self._title_lbl.text_color = "white"
        self.add_subview(self._title_lbl)

        # Message (optional)
        self._msg_lbl: Label | None = None
        if message:
            lbl = Label()
            lbl.text = str(message)
            lbl.alignment = ALIGN_CENTER
            lbl.text_color = (0.85, 0.85, 0.85, 1.0)
            self._msg_lbl = lbl
            self.add_subview(lbl)

        buttons_texts = [button1, button2, button3]
        if not hide_cancel_button:
            buttons_texts.append("Cancel")

        for text in buttons_texts:
            if text:
                btn = Button()
                btn.title = str(text)
                btn.action = self._action
                btn.background_color = (0.2, 0.2, 0.2, 0.96)
                self._action_buttons.append(btn)
                self.add_subview(btn)

    def layout(self):
        w, _ = self.frame.size.as_tuple()
        y = 0

        self._title_lbl.frame = (0, y, w, self.TITLE_H)
        y += self._title_lbl.height

        if self._msg_lbl:
            self._msg_lbl.frame = (0, y, w, self.MESSAGE_H)
            y += self._msg_lbl.height

        for btn in self._action_buttons:
            btn.frame = (0, y, w, self.BTN_H)
            y += btn.height

    def _action(self, sender: Button):
        self._result = sender.title.lower() if sender.title else "cancel"
        self.close()


def alert(
    title: str,
    message: str | None = None,
    button1: str = "OK",
    button2: str | None = None,
    button3: str | None = None,
    hide_cancel_button: bool = False,
) -> str:
    """Show a modal alert dialog and return the tapped button title (lowercase).

    Returns "cancel" if the Cancel button was tapped or the dialog was dismissed.
    """
    v = _Alert(title, message, button1, button2, button3, hide_cancel_button)
    v.present()
    v.wait_modal()
    return v._result


if IS_PYTHONISTA:
    from console import (  # type: ignore[import-not-found,no-redef]
        alert,
    )
