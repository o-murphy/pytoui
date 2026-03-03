from pytoui._platform import IS_PYTHONISTA
from pytoui.ui._button import Button
from pytoui.ui._constants import ALIGN_CENTER
from pytoui.ui._draw import measure_string
from pytoui.ui._final import _final_
from pytoui.ui._label import Label
from pytoui.ui._view import View


@_final_
class _Alert(View):
    MAX_WIDTH = 280
    BTN_H = 32
    TITLE_H = 36

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

        # Action buttons (button1 / button2 / button3) — tracked for index
        for text in [button1, button2, button3]:
            if text:
                btn = Button()
                btn.title = str(text)
                btn.action = self._action
                btn.background_color = (0.3, 0.5, 0.9, 1.0)
                self._action_buttons.append(btn)
                self.add_subview(btn)

        # Cancel button (shown by default unless hidden)
        self._cancel_btn: Button | None = None
        if not hide_cancel_button:
            cb = Button()
            cb.title = "Cancel"
            cb.action = self._action
            cb.background_color = (0.4, 0.4, 0.4, 1.0)
            self._cancel_btn = cb
            self.add_subview(cb)

    def layout(self):
        self.width = self.MAX_WIDTH
        all_texts = (
            [self._title_lbl.text]
            + ([self._msg_lbl.text] if self._msg_lbl else [])
            + [btn.title for btn in self._action_buttons]
        )
        needed_w = max((_text_width(t)) for t in all_texts)
        w = max(needed_w, 160)

        y = 0
        self._title_lbl.frame = (0, y, w, self.TITLE_H)
        y += self.TITLE_H

        if self._msg_lbl:
            self._msg_lbl.frame = (0, y, w, self.BTN_H)
            y += self.BTN_H

        y += 4  # separator
        for btn in self._action_buttons:
            btn.frame = (0, y, w, self.BTN_H)
            y += self.BTN_H

        if self._cancel_btn:
            self._cancel_btn.frame = (0, y, w, self.BTN_H)
            y += self.BTN_H

        self.width = w
        self.height = y

    def _action(self, sender: Button):
        self._result = sender.title.lower() if sender.title else "cancel"
        self.close()


def _text_width(text: str) -> float:
    w, _ = measure_string(text)
    # measure_string returns 0 when no backend is active (before present()).
    # Fall back to a rough character-width estimate so layout() produces a
    # usable frame size even when called before the window exists.
    return w if w > 0 else len(text) * 8.0


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
    pass  # type: ignore[import-not-found,no-redef]
