from __future__ import annotations

from pytoui.ui._constants import ALIGN_CENTER
from pytoui.ui._internals import _final_
from pytoui.ui._label import Label
from pytoui.ui._scroll_view import ScrollView
from pytoui.ui._view import View

__all__ = ("LiquidDatePicker",)


class _MonthPage(View):
    def __init__(self, month: int = 1, /, **kwargs):

        self.corner_radius = 32
        self.background_color = "blue"

        self._lbl = Label(text=str(month))
        self._lbl.alignment = ALIGN_CENTER
        self.add_subview(self._lbl)

        super().__init__(**kwargs)

    def layout(self):
        self._lbl.center = self.bounds.center().as_tuple()


@_final_
class LiquidDatePicker(View):
    def __init__(self, *args, **kwargs):
        self.background_color = "white"
        self.corner_radius = 16
        self._scroll_view = ScrollView()
        self._scroll_view.paging_enabled = True
        self._months = [_MonthPage(i) for i in range(1, 13)]
        for m in self._months:
            self._scroll_view.add_subview(m)

        self.add_subview(self._scroll_view)

        super().__init__(*args, **kwargs)

    def layout(self):
        self._scroll_view.frame = self.frame.as_tuple()
        w, h = self._scroll_view.frame.size
        self._scroll_view.content_size = (w * 12, h)
        for i, m in enumerate(self._months):
            m.frame = (i * w, 0, w, h)


if __name__ == "__main__":
    picker = LiquidDatePicker()
    picker.frame = (0, 0, 280, 220)
    picker.background_color = "white"

    root = View()
    root.add_subview(picker)
    root.present("fullscreen")
