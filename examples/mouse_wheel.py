"""Mouse wheel / trackpad scroll demo.

Demonstrates MouseWheel touch events: scroll the mouse wheel or swipe on
a trackpad while hovering over the view.

- The log panel (bottom) shows the last scroll events.
- The colored indicator strip (top) shifts horizontally/vertically to
  visualise accumulated scroll.
- Regular mouse clicks do NOT produce MouseWheel events.

Run:
    python examples/mouse_wheel.py
"""

from pytoui import ui

_MAX_LOG = 12
_INDICATOR_SIZE = 40


class ScrollView(ui.View):
    def __init__(self):
        self.name = "Mouse Wheel Demo"
        self.background_color = (0.07, 0.07, 0.10, 1.0)

        self._offset_x = 0.0
        self._offset_y = 0.0
        self._log: list[str] = []

        # Header
        self._header = ui.Label()
        self._header.background_color = (0.0, 0.0, 0.0, 0.55)
        self._header.text_color = (0.9, 0.9, 0.9, 1.0)
        self._header.font = ("<system>", 15.0)
        self._header.alignment = ui.ALIGN_CENTER
        self._header.text = "Scroll the mouse wheel / swipe on trackpad"
        self._header.touch_enabled = False
        self.add_subview(self._header)

        # Log label
        self._log_label = ui.Label()
        self._log_label.background_color = (0.0, 0.0, 0.0, 0.45)
        self._log_label.text_color = (0.55, 1.0, 0.55, 1.0)
        self._log_label.font = ("<monospace>", 13.0)
        self._log_label.alignment = ui.ALIGN_LEFT
        self._log_label.number_of_lines = _MAX_LOG
        self._log_label.touch_enabled = False
        self.add_subview(self._log_label)

    def layout(self):
        w, h = self.width, self.height
        self._header.frame = (0, 0, w, 44)
        log_h = _MAX_LOG * 18 + 12
        self._log_label.frame = (8, h - log_h - 8, w - 16, log_h)

    # ── Touch handlers ─────────────────────────────────────────────────────────

    def touch_began(self, touch):
        if isinstance(touch, ui.MouseWheel):
            self._handle_scroll(touch, "began")

    def touch_moved(self, touch):
        if isinstance(touch, ui.MouseWheel):
            self._handle_scroll(touch, "moved")

    def touch_ended(self, touch):
        if isinstance(touch, ui.MouseWheel):
            self._handle_scroll(touch, "ended")

    def _handle_scroll(self, touch: ui.MouseWheel, phase: str):
        if phase == "moved":
            self._offset_x += touch.scroll_dx
            self._offset_y += touch.scroll_dy

        entry = (
            f"{phase:6s}  dx={touch.scroll_dx:+7.1f}  dy={touch.scroll_dy:+7.1f}"
            f"  @({touch.location.x:.0f},{touch.location.y:.0f})"
        )
        self._log.append(entry)
        if len(self._log) > _MAX_LOG:
            self._log.pop(0)

        self._log_label.text = "\n".join(self._log)
        self._header.text = (
            f"offset  x={self._offset_x:+.0f}  y={self._offset_y:+.0f}  "
            f"(id={touch.touch_id})"
        )
        self.set_needs_display()

    # ── Drawing ────────────────────────────────────────────────────────────────

    def draw(self):
        w, h = self.width, self.height
        log_h = _MAX_LOG * 18 + 28
        area_y = 44
        area_h = h - area_y - log_h

        # Background for scroll area
        ui.set_color((0.12, 0.12, 0.18, 1.0))
        ui.fill_rect(0, area_y, w, area_h)

        # Grid lines
        ui.set_color((1, 1, 1, 0.06))
        step = 40
        x = step
        while x < w:
            p = ui.Path()
            p.move_to(x, area_y)
            p.line_to(x, area_y + area_h)
            p.line_width = 1
            p.stroke()
            x += step
        y = area_y + step
        while y < area_y + area_h:
            p = ui.Path()
            p.move_to(0, y)
            p.line_to(w, y)
            p.line_width = 1
            p.stroke()
            y += step

        # Scrollable indicator: a colored square that moves with accumulated offset
        cx = w / 2 + (self._offset_x % w)
        cy = area_y + area_h / 2 + (self._offset_y % area_h)
        s = _INDICATOR_SIZE

        ui.set_color((0.20, 0.65, 1.00, 0.90))
        ui.Path.oval(cx - s, cy - s, s * 2, s * 2).fill()

        ui.set_color((1, 1, 1, 0.80))
        ring = ui.Path.oval(cx - s, cy - s, s * 2, s * 2)
        ring.line_width = 2.5
        ring.stroke()

        ui.draw_string(
            "W",
            rect=(cx - s, cy - 11, s * 2, 22),
            font=("<system-bold>", 16.0),
            color=(1, 1, 1, 1),
            alignment=ui.ALIGN_CENTER,
        )


def main():
    v = ScrollView()
    v.frame = (0, 0, 640, 520)
    v.present()


if __name__ == "__main__":
    main()
