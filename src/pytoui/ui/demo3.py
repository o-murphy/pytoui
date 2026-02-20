"""
Demo3: multitouch visualizer.

Shows touch points as colored circles; each finger gets a unique color.
Panels are named sub-views — the header shows which view each finger is on.

Run: python -m pytoui.ui.demo3
"""

from pytoui import ui

_FINGER_COLORS = [
    (1.0, 0.30, 0.30, 0.90),  # red
    (0.25, 0.60, 1.00, 0.90),  # blue
    (0.20, 0.85, 0.35, 0.90),  # green
    (1.00, 0.80, 0.10, 0.90),  # yellow
    (0.85, 0.25, 0.95, 0.90),  # magenta
    (0.15, 0.90, 0.90, 0.90),  # cyan
]

RADIUS = 26


class _TouchInfo:
    __slots__ = ("x", "y", "color", "view_name", "touch_id")

    def __init__(self, x, y, color, view_name, touch_id):
        self.x = x
        self.y = y
        self.color = color
        self.view_name = view_name
        self.touch_id = touch_id


class Panel(ui.View):
    """Named colored rectangle that forwards all touches to the root."""

    def __init__(self, name: str, color: tuple, root: "TouchDemoView"):
        self.name = name
        self.background_color = color
        self._root = root

        lbl = ui.Label()
        lbl.text = name
        lbl.text_color = (1, 1, 1, 0.75)
        lbl.font = ("<system-bold>", 18.0)
        lbl.alignment = ui.ALIGN_CENTER
        lbl.touch_enabled = False
        self.add_subview(lbl)
        self._lbl = lbl

    def layout(self):
        self._lbl.frame = (0, self.height / 2 - 14, self.width, 28)

    def touch_began(self, touch):
        self._root.record_touch(touch, "began", self)

    def touch_moved(self, touch):
        self._root.record_touch(touch, "moved", self)

    def touch_ended(self, touch):
        self._root.record_touch(touch, "ended", self)


class TouchDemoView(ui.View):
    def __init__(self):
        self.name = "Demo3 — Multitouch"
        self.background_color = (0.07, 0.07, 0.10, 1.0)

        self._touches: dict[int, _TouchInfo] = {}
        self._color_pool: dict[int, tuple] = {}
        self._color_idx = 0

        # Header bar
        self._header = ui.Label()
        self._header.background_color = (0.0, 0.0, 0.0, 0.55)
        self._header.text_color = (0.9, 0.9, 0.9, 1.0)
        self._header.font = ("<system>", 15.0)
        self._header.alignment = ui.ALIGN_CENTER
        self._header.text = "Touch the screen"
        self._header.touch_enabled = False
        self.add_subview(self._header)

        # 4 colored panels in a 2×2 grid
        specs = [
            ("Red", (0.55, 0.10, 0.10, 0.85)),
            ("Green", (0.10, 0.42, 0.15, 0.85)),
            ("Blue", (0.10, 0.18, 0.58, 0.85)),
            ("Yellow", (0.48, 0.42, 0.05, 0.85)),
        ]
        self._panels = [Panel(n, c, self) for n, c in specs]
        for p in self._panels:
            self.add_subview(p)

    def layout(self):
        w, h = self.width, self.height
        header_h = 44
        self._header.frame = (0, 0, w, header_h)

        # 2×2 grid occupies the full remaining area
        pw, ph = w / 2, (h - header_h) / 2
        for i, p in enumerate(self._panels):
            col, row = i % 2, i // 2
            p.frame = (col * pw, header_h + row * ph, pw, ph)

    # ── Touch tracking ────────────────────────────────────────────────────────

    def record_touch(self, touch, phase: str, source: ui.View):
        tid = touch.touch_id
        # Convert touch location from source-view space to root (self) space
        root_pt = ui.convert_point(touch.location, from_view=source, to_view=self)

        if phase == "began":
            if tid not in self._color_pool:
                self._color_pool[tid] = _FINGER_COLORS[
                    self._color_idx % len(_FINGER_COLORS)
                ]
                self._color_idx += 1
            self._touches[tid] = _TouchInfo(
                root_pt.x,
                root_pt.y,
                self._color_pool[tid],
                source.name,
                tid,
            )
        elif phase in ("moved", "stationary"):
            if tid in self._touches:
                self._touches[tid].x = root_pt.x
                self._touches[tid].y = root_pt.y
                self._touches[tid].view_name = source.name
        else:  # ended / cancelled
            self._touches.pop(tid, None)
            self._color_pool.pop(tid, None)

        self._update_header()
        self.set_needs_display()

    def _update_header(self):
        n = len(self._touches)
        if n == 0:
            self._header.text = "Touch the screen — 0 fingers"
        else:
            views = ", ".join(sorted({t.view_name for t in self._touches.values()}))
            label = "finger" if n == 1 else "fingers"
            self._header.text = f"{n} {label}  |  {views}"

    # ── Self-touch (background area not covered by panels) ───────────────────

    def touch_began(self, touch):
        self.record_touch(touch, "began", self)

    def touch_moved(self, touch):
        self.record_touch(touch, "moved", self)

    def touch_ended(self, touch):
        self.record_touch(touch, "ended", self)

    # ── Drawing ───────────────────────────────────────────────────────────────

    def draw(self):
        for info in self._touches.values():
            cx, cy = info.x, info.y
            r = RADIUS

            # Filled circle
            ui.set_color(info.color)
            ui.Path.oval(cx - r, cy - r, r * 2, r * 2).fill()

            # White ring
            ring = ui.Path.oval(cx - r, cy - r, r * 2, r * 2)
            ring.line_width = 2.5
            ui.set_color((1, 1, 1, 0.85))
            ring.stroke()

            # Label: "M" for mouse, numeric id for real touch
            tag = "M" if info.touch_id < 0 else str(info.touch_id % 100)
            ui.draw_string(
                tag,
                rect=(cx - r, cy - 10, r * 2, 20),
                font=("<system-bold>", 15.0),
                color=(1, 1, 1, 1),
                alignment=ui.ALIGN_CENTER,
            )


def main():
    root = TouchDemoView()
    root.frame = (0, 0, 700, 520)
    root.present()


if __name__ == "__main__":
    main()
