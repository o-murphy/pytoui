"""Demo app for TextField/TextView: python -m examples.textfield_textview_demo

Manual verification checklist (see the TextField/TextView implementation plan):
- Tap "Name" field -> caret blinks, typing inserts at cursor, placeholder hides.
- Type a digit into "Name" -> rejected by textfield_should_change (delegate).
- Tap "Password" field, type -> masked with bullets.
- Press Return in "Name"/"Password" -> ends editing, action fires (see console).
- Tap the multi-paragraph TextView -> word-wraps, scrolls, up/down arrows move
  the caret across wrapped lines, tap places the cursor at the tapped position.
- Tap "Name" then "Password" -> the first field's caret stops blinking the
  instant the second becomes first responder (Phase 0 first-responder fix).
- ESC while editing ends editing without closing the window; ESC again
  (nothing focused) closes the window.
- Typing an accented character via a dead-key sequence, or composing CJK text
  via an IME if available, should insert/preview correctly (Phase 0b).

Press ESC (when nothing is focused) or close the window to exit.
"""

from pytoui import ui


class NameFieldDelegate:
    def textfield_should_change(self, textfield, range, replacement):
        if replacement.isdigit():
            print("Rejected digit input:", replacement)
            return False
        return True

    def textfield_did_begin_editing(self, textfield):
        print("Name field: began editing")

    def textfield_did_end_editing(self, textfield):
        print("Name field: ended editing ->", repr(textfield.text))


class MainView(ui.View):
    def __init__(self):
        self.background_color = "white"

        self.name_label = ui.Label()
        self.name_label.text = "Name (rejects digits):"
        self.add_subview(self.name_label)

        self.name_field = ui.TextField()
        self.name_field.placeholder = "Name"
        self.name_field.delegate = NameFieldDelegate()
        self.name_field.action = self.on_name_return
        self.add_subview(self.name_field)

        self.password_label = ui.Label()
        self.password_label.text = "Password:"
        self.add_subview(self.password_label)

        self.password_field = ui.TextField()
        self.password_field.placeholder = "Password"
        self.password_field.secure = True
        self.add_subview(self.password_field)

        self.textview_label = ui.Label()
        self.textview_label.text = "Notes (multi-line, scrollable):"
        self.add_subview(self.textview_label)

        self.text_view = ui.TextView()
        self.text_view.text = (
            "The quick brown fox jumps over the lazy dog. "
            "Pack my box with five dozen liquor jugs.\n\n"
            "Second paragraph: this text is long enough to word-wrap across "
            "several lines inside the fixed-height frame below, so you can "
            "verify scrolling, up/down arrow caret movement across wrapped "
            "lines, and tap-to-place-cursor at a nonzero scroll offset.\n\n"
            "Third paragraph for extra scroll room."
        )
        self.text_view.border_color = "gray"
        self.text_view.border_width = 1
        self.add_subview(self.text_view)

        self.hint_label = ui.Label()
        self.hint_label.font = ("<system>", 12.0)
        self.hint_label.text_color = (0.4, 0.4, 0.4, 1.0)
        self.hint_label.number_of_lines = 2
        self.hint_label.text = (
            "Tap Name, then Password, to confirm focus switches (caret stops "
            "blinking on the field you left)."
        )
        self.add_subview(self.hint_label)

    def layout(self):
        pad = 12
        w = self.width - 2 * pad

        self.name_label.frame = (pad, pad, w, 20)
        self.name_field.frame = (pad, pad + 24, w, 32)

        self.password_label.frame = (pad, pad + 68, w, 20)
        self.password_field.frame = (pad, pad + 92, w, 32)

        self.textview_label.frame = (pad, pad + 136, w, 20)
        self.text_view.frame = (pad, pad + 160, w, 220)

        self.hint_label.frame = (pad, pad + 392, w, 40)

    def on_name_return(self, sender):
        print("Name field action fired:", repr(sender.text))


def main():
    root = MainView()
    root.name = "TextField / TextView Demo"
    root.frame = (0, 0, 420, 480)
    root.present("fullscreen")


if __name__ == "__main__":
    main()
