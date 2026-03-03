from pytoui._platform import IS_PYTHONISTA
from pytoui.ui._button import Button
from pytoui.ui._constants import ALIGN_CENTER
from pytoui.ui._draw import fill_rect, measure_string, set_color
from pytoui.ui._final import _final_
from pytoui.ui._label import Label
from pytoui.ui._view import View

__all__ = ("alert",)


@_final_
class _AlertView(View):
    MAX_WIDTH = 280
    BTN_H = 32
    TITLE_H = 36
    MESSAGE_H = 32

    def __init__(
        self,
        title: str,
        message: str | None = None,
        button1: str | None = None,
        button2: str | None = None,
        button3: str | None = None,
        hide_cancel_button: bool = False,
    ):
        super().__init__()

        self._result: str = "cancel"
        self._action_buttons: list[Button] = []

        self.background_color = (0.2, 0.2, 0.2, 0.96)
        self.name = title

        if message:
            w, _ = measure_string(message)
        else:
            w = 150.0

        self.frame = (0.0, 0.0, min(w, 400), 150.0)

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
            lbl.text_color = (0.85, 0.85, 0.85, 1.0)
            lbl.alignment = ALIGN_CENTER
            lbl.size_to_fit()
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
                btn.flex = "WT"
                btn.background_color = (0.2, 0.2, 0.2, 0.96)
                self._action_buttons.append(btn)
                self.add_subview(btn)

    def draw(self):
        factor = 0.25
        r, g, b, a = self.background_color
        r = r + (1.0 - r) * factor
        g = g + (1.0 - g) * factor
        b = b + (1.0 - b) * factor

        for btn in self._action_buttons:
            x, y, w, h = btn.frame
            set_color((r, g, b, a))
            fill_rect(x, y + h, w, 2)

    def layout(self):
        w, h = self.frame.size.as_tuple()

        btns_h = len(self._action_buttons) * self.BTN_H

        y_btn = h - btns_h
        for btn in self._action_buttons:
            btn.frame = (0, y_btn, w, self.BTN_H)
            y_btn += self.BTN_H

        y = 0
        self._title_lbl.frame = (0, y, w, self.TITLE_H)
        y += self.TITLE_H

        if self._msg_lbl:
            msg_h = max(0, h - btns_h - y)
            self._msg_lbl.frame = (0, y, w, msg_h)

    def _action(self, sender: Button):
        self._result = sender.title.lower() if sender.title else "cancel"
        self.close()


def alert(
    title: str,
    message: str | None = None,
    button1: str | None = None,
    button2: str | None = None,
    button3: str | None = None,
    hide_cancel_button: bool = False,
) -> str:
    """Show a modal alert dialog and return the tapped button title (lowercase).

    Returns "cancel" if the Cancel button was tapped or the dialog was dismissed.
    """
    v = _AlertView(title, message, button1, button2, button3, hide_cancel_button)
    v.present()
    v.wait_modal()
    return v._result


if IS_PYTHONISTA:
    from console import (  # type: ignore[import-not-found,no-redef]
        alert,
    )
