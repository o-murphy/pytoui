"""Demo: ScrollView with paging enabled.

Swipe (touch) or scroll with mouse wheel to flip pages.
Page dots at the bottom reflect the current page.
"""

from pytoui import ui

PAGES = [
    ("#E74C3C", "Page 1", "Swipe or scroll →"),
    ("#3498DB", "Page 2", "← Swipe or scroll →"),
    ("#2ECC71", "Page 3", "← Swipe or scroll →"),
    ("#9B59B6", "Page 4", "← Swipe or scroll →"),
    ("#F39C12", "Page 5", "← Swipe or scroll"),
]


class PageDots(ui.View):
    def __init__(self, count: int):
        self._count = count
        self._page = 0

    def set_page(self, page: int):
        p = max(0, min(self._count - 1, page))
        if p != self._page:
            self._page = p
            self.set_needs_display()

    def draw(self):
        r = 5
        gap = 14
        total_w = self._count * (r * 2) + (self._count - 1) * gap
        sx = (self.width - total_w) / 2
        cy = self.height / 2
        for i in range(self._count):
            x = sx + i * (r * 2 + gap)
            ui.set_color("white" if i == self._page else (1.0, 1.0, 1.0, 0.35))
            ui.Path.oval(x, cy - r, r * 2, r * 2).fill()


class PagingDelegate:
    def __init__(self, dots: PageDots, page_w: float):
        self._dots = dots
        self._page_w = page_w

    def scrollview_did_scroll(self, sv: ui.ScrollView):
        ox, _ = sv.content_offset
        if self._page_w > 0:
            self._dots.set_page(round(ox / self._page_w))


def main():
    WIN_W, WIN_H = 420, 600
    HEADER_H = 44
    DOTS_H = 36
    PAGE_H = WIN_H - HEADER_H - DOTS_H

    root = ui.View()
    root.frame = (0, 0, WIN_W, WIN_H)
    root.background_color = "#1a1a2e"
    root.name = "Demo: Paging ScrollView"

    # Header
    header = ui.Label()
    header.frame = (0, 0, WIN_W, HEADER_H)
    header.text = "Paging ScrollView"
    header.text_color = "white"
    header.font = ("<system-bold>", 17)
    header.alignment = ui.ALIGN_CENTER
    header.background_color = (0.0, 0.0, 0.0, 0.45)
    root.add_subview(header)

    # Page dots
    dots = PageDots(len(PAGES))
    dots.frame = (0, WIN_H - DOTS_H, WIN_W, DOTS_H)
    dots.background_color = "transparent"
    root.add_subview(dots)

    # ScrollView
    sv = ui.ScrollView()
    sv.frame = (0, HEADER_H, WIN_W, PAGE_H)
    sv.paging_enabled = True
    sv.bounces = False
    sv.shows_horizontal_scroll_indicator = False
    sv.shows_vertical_scroll_indicator = False
    sv.content_size = (WIN_W * len(PAGES), PAGE_H)
    sv.delegate = PagingDelegate(dots, WIN_W)
    root.add_subview(sv)

    # Pages
    PAD = 12
    for i, (color, title, subtitle) in enumerate(PAGES):
        page = ui.View()
        page.frame = (i * WIN_W + PAD, PAD, WIN_W - PAD * 2, PAGE_H - PAD * 2)
        page.background_color = color
        page.corner_radius = 20

        lbl_title = ui.Label()
        lbl_title.frame = (0, PAGE_H // 2 - 60, WIN_W - PAD * 2, 44)
        lbl_title.text = title
        lbl_title.text_color = "white"
        lbl_title.font = ("<system-bold>", 32)
        lbl_title.alignment = ui.ALIGN_CENTER
        page.add_subview(lbl_title)

        lbl_sub = ui.Label()
        lbl_sub.frame = (0, PAGE_H // 2 - 10, WIN_W - PAD * 2, 30)
        lbl_sub.text = subtitle
        lbl_sub.text_color = (1.0, 1.0, 1.0, 0.75)
        lbl_sub.font = ("<system>", 16)
        lbl_sub.alignment = ui.ALIGN_CENTER
        page.add_subview(lbl_sub)

        sv.add_subview(page)

    root.present("fullscreen")


if __name__ == "__main__":
    main()
