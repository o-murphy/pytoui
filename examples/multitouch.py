"""Input event visualizer.

Demonstrates all desktop input event types:

  Finger touch / drag    — coloured circles, numeric ID
  Mouse click (L/R/M)    — coloured circle, letter label, persists while held
  Mouse drag             — same circle follows the cursor
  Mouse hover            — thin ring + crosshair, no fill
  Mouse wheel / trackpad — arrow at cursor showing scroll delta

Run: python examples/multitouch.py
"""

from pytoui import ui

_FINGER_COLORS = [
    (1.0, 0.30, 0.30, 0.90),  # red
    (0.20, 0.85, 0.35, 0.90),  # green
    (1.00, 0.80, 0.10, 0.90),  # yellow
    (0.85, 0.25, 0.95, 0.90),  # magenta
    (0.15, 0.90, 0.90, 0.90),  # cyan
]

_MOUSE_COLORS = {
    ui._MOUSE_LEFT_ID: (0.30, 0.65, 1.00, 0.90),  # blue
    ui._MOUSE_RIGHT_ID: (1.00, 0.45, 0.20, 0.90),  # orange
    ui._MOUSE_MIDDLE_ID: (0.75, 0.30, 0.95, 0.90),  # purple
}
_MOUSE_LABELS = {
    ui._MOUSE_LEFT_ID: "L",
    ui._MOUSE_RIGHT_ID: "R",
    ui._MOUSE_MIDDLE_ID: "M",
}

R = 26  # circle radius for press events
RH = 16  # ring radius for hover


class _Info:
    __slots__ = ("x", "y", "color", "label")

    def __init__(self, x, y, color, label):
        self.x = x
        self.y = y
        self.color = color
        self.label = label


class Panel(ui.View):
    """Named sub-view — forwards every event to the root."""

    def __init__(self, name: str, color: tuple, root: "DemoView"):
        self.name = name
        self.background_color = color
        self._root = root

        lbl = ui.Label()
        lbl.text = name
        lbl.text_color = (1, 1, 1, 0.65)
        lbl.font = ("<system-bold>", 18.0)
        lbl.alignment = ui.ALIGN_CENTER
        lbl.touch_enabled = False
        self.add_subview(lbl)
        self._lbl = lbl

    def layout(self):
        self._lbl.frame = (0, self.height / 2 - 14, self.width, 28)

    # ── finger touch ─────────────────────────────────────────────────────────
    def touch_began(self, t):
        self._root.on_press(t, "began", self)

    def touch_moved(self, t):
        self._root.on_press(t, "moved", self)

    def touch_ended(self, t):
        self._root.on_press(t, "ended", self)

    # ── mouse button ─────────────────────────────────────────────────────────
    def mouse_down(self, t):
        self._root.on_press(t, "began", self)

    def mouse_dragged(self, t):
        self._root.on_press(t, "moved", self)

    def mouse_up(self, t):
        self._root.on_press(t, "ended", self)

    # ── hover & scroll ───────────────────────────────────────────────────────
    def mouse_moved(self, t):
        self._root.on_hover(t, self)

    def mouse_wheel(self, t):
        self._root.on_scroll(t, self)


class DemoView(ui.View):
    def __init__(self):
        self.name = "Input Event Visualizer"
        self.background_color = (0.07, 0.07, 0.10, 1.0)

        self._active: dict[int, _Info] = {}  # touch_id → press info
        self._finger_colors: dict[int, tuple] = {}
        self._color_idx = 0

        self._hover: tuple[float, float] | None = None  # cursor pos (hover)
        self._scroll: tuple[float, float, float, float] | None = None  # x,y,dx,dy

        self.mouse_scroll_enabled = True

        # Header
        self._header = ui.Label()
        self._header.background_color = (0.0, 0.0, 0.0, 0.55)
        self._header.text_color = (0.9, 0.9, 0.9, 1.0)
        self._header.font = ("<system>", 15.0)
        self._header.alignment = ui.ALIGN_CENTER
        self._header.text = "Touch / click / hover / scroll"
        self._header.touch_enabled = False
        self.add_subview(self._header)

        # 4 panels
        specs = [
            ("Red", (0.55, 0.10, 0.10, 0.80)),
            ("Green", (0.10, 0.42, 0.15, 0.80)),
            ("Blue", (0.10, 0.18, 0.58, 0.80)),
            ("Yellow", (0.48, 0.42, 0.05, 0.80)),
        ]
        self._panels = [Panel(n, c, self) for n, c in specs]
        for p in self._panels:
            self.add_subview(p)

    def layout(self):
        w, h = self.width, self.height
        self._header.frame = (0, 0, w, 44)
        pw, ph = w / 2, (h - 44) / 2
        for i, p in enumerate(self._panels):
            p.frame = (i % 2 * pw, 44 + i // 2 * ph, pw, ph)

    # ── press tracking (finger + mouse button) ────────────────────────────────

    def on_press(self, touch, phase: str, source: ui.View):
        tid = touch.touch_id
        pt = ui.convert_point(touch.location, from_view=source, to_view=self)

        if phase == "began":
            if tid >= 0:
                # finger
                if tid not in self._finger_colors:
                    self._finger_colors[tid] = _FINGER_COLORS[
                        self._color_idx % len(_FINGER_COLORS)
                    ]
                    self._color_idx += 1
                color = self._finger_colors[tid]
                label = str(tid % 100)
            else:
                # mouse button
                color = _MOUSE_COLORS.get(tid, (0.7, 0.7, 0.7, 0.9))
                label = _MOUSE_LABELS.get(tid, "?")
            self._active[tid] = _Info(pt.x, pt.y, color, label)

        elif phase in ("moved", "stationary"):
            if tid in self._active:
                self._active[tid].x = pt.x
                self._active[tid].y = pt.y

        else:  # ended / cancelled
            self._active.pop(tid, None)
            self._finger_colors.pop(tid, None)

        self._refresh_header()
        self.set_needs_display()

    # ── hover ─────────────────────────────────────────────────────────────────

    def on_hover(self, touch, source: ui.View):
        pt = ui.convert_point(touch.location, from_view=source, to_view=self)
        self._hover = (pt.x, pt.y)
        self.set_needs_display()

    # ── scroll ────────────────────────────────────────────────────────────────

    def on_scroll(self, touch: ui.MouseWheel, source: ui.View):
        pt = ui.convert_point(touch.location, from_view=source, to_view=self)
        self._scroll = (pt.x, pt.y, touch.scroll_dx, touch.scroll_dy)
        self._refresh_header()
        self.set_needs_display()

    # ── self-events (background area between panels) ──────────────────────────

    def touch_began(self, t):
        self.on_press(t, "began", self)

    def touch_moved(self, t):
        self.on_press(t, "moved", self)

    def touch_ended(self, t):
        self.on_press(t, "ended", self)

    def mouse_down(self, t):
        self.on_press(t, "began", self)

    def mouse_dragged(self, t):
        self.on_press(t, "moved", self)

    def mouse_up(self, t):
        self.on_press(t, "ended", self)

    def mouse_moved(self, t):
        self.on_hover(t, self)

    def mouse_wheel(self, t):
        self.on_scroll(t, self)

    # ── header ────────────────────────────────────────────────────────────────

    def _refresh_header(self):
        fingers = sum(1 for tid in self._active if tid >= 0)
        btns = [_MOUSE_LABELS.get(tid, "?") for tid in self._active if tid < 0]
        parts = []
        if fingers:
            parts.append(f"{fingers} finger{'s' if fingers != 1 else ''}")
        if btns:
            parts.append("btn " + "+".join(btns))
        if self._scroll:
            dx, dy = self._scroll[2], self._scroll[3]
            parts.append(f"scroll dx={dx:+.0f} dy={dy:+.0f}")
        self._header.text = (
            "  |  ".join(parts) if parts else "Touch / click / hover / scroll"
        )

    # ── drawing ───────────────────────────────────────────────────────────────

    def draw(self):
        # Active presses (finger + mouse button)
        for info in self._active.values():
            cx, cy = info.x, info.y

            ui.set_color(info.color)
            ui.Path.oval(cx - R, cy - R, R * 2, R * 2).fill()

            ring = ui.Path.oval(cx - R, cy - R, R * 2, R * 2)
            ring.line_width = 2.5
            ui.set_color((1, 1, 1, 0.85))
            ring.stroke()

            ui.draw_string(
                info.label,
                rect=(cx - R, cy - 10, R * 2, 20),
                font=("<system-bold>", 15.0),
                color=(1, 1, 1, 1),
                alignment=ui.ALIGN_CENTER,
            )

        # Hover cursor
        if self._hover:
            cx, cy = self._hover

            ring = ui.Path.oval(cx - RH, cy - RH, RH * 2, RH * 2)
            ring.line_width = 1.5
            ui.set_color((1, 1, 1, 0.55))
            ring.stroke()

            # crosshair
            arm = RH + 4
            for x0, y0, x1, y1 in [
                (cx - arm, cy, cx + arm, cy),
                (cx, cy - arm, cx, cy + arm),
            ]:
                p = ui.Path()
                p.move_to(x0, y0)
                p.line_to(x1, y1)
                p.line_width = 1.0
                p.stroke()

        # Last scroll indicator
        if self._scroll:
            sx, sy, dx, dy = self._scroll
            ui.set_color((1.0, 0.85, 0.20, 0.75))
            sr = 10
            ui.Path.oval(sx - sr, sy - sr, sr * 2, sr * 2).fill()

            # Arrow showing direction
            scale = 0.4
            ex, ey = sx + dx * scale, sy - dy * scale  # dy flipped: up = positive
            p = ui.Path()
            p.move_to(sx, sy)
            p.line_to(ex, ey)
            p.line_width = 2.0
            ui.set_color((1, 1, 1, 0.80))
            p.stroke()


def main():
    root = DemoView()
    root.frame = (0, 0, 700, 520)
    root.present()


if __name__ == "__main__":
    main()
