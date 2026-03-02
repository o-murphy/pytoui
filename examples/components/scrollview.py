"""Demo: ScrollView with colored tiles and a delegate.

Scroll with mouse wheel (desktop) or touch drag.
Press ESC or close the window to exit.
"""

from pytoui import ui

TILE_W = 180
TILE_H = 80
COLS = 2
ROWS = 12
GAP = 10
PADDING = 10

COLORS = [
    "tomato",
    "steelblue",
    "mediumseagreen",
    "darkorange",
    "mediumpurple",
    "goldenrod",
    "cornflowerblue",
    "indianred",
]


class ScrollDelegate:
    def __init__(self, label: ui.Label):
        self._label = label

    def scrollview_did_scroll(self, sv: ui.ScrollView):
        ox, oy = sv.content_offset
        self._label.text = f"offset: ({ox:.0f}, {oy:.0f})"


def make_tile(row: int, col: int) -> ui.View:
    color = COLORS[(row * COLS + col) % len(COLORS)]
    x = PADDING + col * (TILE_W + GAP)
    y = PADDING + row * (TILE_H + GAP)

    tile = ui.View()
    tile.frame = (x, y, TILE_W, TILE_H)
    tile.background_color = color
    tile.corner_radius = 10

    lbl = ui.Label()
    lbl.frame = (0, 0, TILE_W, TILE_H)
    lbl.text = f"Item {row * COLS + col + 1}"
    lbl.text_color = "white"
    lbl.alignment = ui.ALIGN_CENTER
    tile.add_subview(lbl)
    tile.touch_enabled = False

    return tile


def main():
    WIN_W, WIN_H = 400, 600

    # ── Status label ──────────────────────────────────────────────────────────
    status = ui.Label()
    status.frame = (0, 0, WIN_W, 30)
    status.text = "offset: (0, 0)"
    status.alignment = ui.ALIGN_CENTER
    status.background_color = (0.1, 0.1, 0.1, 1.0)
    status.text_color = "white"

    # ── ScrollView ────────────────────────────────────────────────────────────
    sv = ui.ScrollView()
    sv.frame = (20, 50, WIN_W - 40, WIN_H - 70)
    sv.background_color = (0.95, 0.95, 0.95, 1.0)
    sv.border_color = "steelblue"
    sv.border_width = 3
    sv.corner_radius = 8
    sv.delegate = ScrollDelegate(status)
    sv.bounces = True

    content_w = COLS * TILE_W + (COLS - 1) * GAP + 2 * PADDING
    content_h = ROWS * TILE_H + (ROWS - 1) * GAP + 2 * PADDING
    sv.content_size = (content_w, content_h)
    sv.content_inset = (8, 8, 8, 8)

    for row in range(ROWS):
        for col in range(COLS):
            sv.add_subview(make_tile(row, col))

    # ── Root view ─────────────────────────────────────────────────────────────
    root = ui.View()
    root.frame = (0, 0, WIN_W, WIN_H)
    root.name = "Demo: ScrollView"
    root.background_color = "black"
    root.add_subview(status)
    root.add_subview(sv)
    root.present("fullscreen")


if __name__ == "__main__":
    main()
