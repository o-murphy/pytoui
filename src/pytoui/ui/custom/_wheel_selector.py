import math
import time

from pytoui.ui._constants import ALIGN_CENTER
from pytoui.ui._draw import (
    GState,
    Path,
    Transform,
    concat_ctm,
    draw_string,
    fill_rect,
    measure_string,
    set_color,
)
from pytoui.ui._types import Touch
from pytoui.ui._view import View

ITEM_HEIGHT = 50
LENS_HEIGHT = 58
LENS_WIDTH_RATIO = 0.94
LENS_CORNER_RADIUS = 16
MAGNIFICATION = 1.35
FONT_SIZE = 22


class WheelState:
    def __init__(self, values, initial):
        self.values = list(values)
        self.total = len(self.values)
        self.middle_offset = self.total * 100
        initial_idx = self.values.index(initial) if initial in self.values else 0
        self.current_idx = float(self.middle_offset + initial_idx)
        self.velocity = 0.0
        self.is_dragging = False


class LiquidTimePicker(View):
    def __init__(self, h_init=12, m_init=30):
        super().__init__()
        self.corner_radius = 16
        self.background_color = "white"
        self.h_state = WheelState(range(0, 24), h_init)
        self.m_state = WheelState(range(0, 60), m_init)

        self.active_state = None
        self.last_y = 0
        self.last_t = 0

        self.update_interval = 1 / 60  # 60 fps

    def update(self):
        """Automatically calls each frame"""
        changed = False
        for state in [self.h_state, self.m_state]:
            if not state.is_dragging:
                if abs(state.velocity) > 0.1:
                    state.current_idx += state.velocity * 0.016
                    state.velocity *= 0.95
                    changed = True
                else:
                    target = round(state.current_idx)
                    diff = target - state.current_idx
                    if abs(diff) > 0.001:
                        state.current_idx += diff * 0.2
                        changed = True
                    else:
                        state.current_idx = target
                        state.velocity = 0.0

        if changed:
            self.set_needs_display()

    def touch_began(self, touch: Touch):
        if touch.location.x < self.width / 2:
            self.active_state = self.h_state
        else:
            self.active_state = self.m_state

        if self.active_state:
            self.active_state.is_dragging = True
            self.active_state.velocity = 0
            self.last_y = touch.location.y
            self.last_t = time.time()

    def touch_moved(self, touch: Touch):
        if not self.active_state:
            return

        dy = touch.location.y - self.last_y
        dt = max(time.time() - self.last_t, 0.001)

        self.active_state.current_idx -= dy / ITEM_HEIGHT
        self.active_state.velocity = -dy / ITEM_HEIGHT / dt * 0.3  # Reduced sensitivity

        self.last_y = touch.location.y
        self.last_t = time.time()
        self.set_needs_display()

    def touch_ended(self, touch: Touch):
        if self.active_state:
            self.active_state.is_dragging = False
            self.active_state = None

    def _draw_text(self, txt, x, y, sx, sy, opacity, bold):
        font = ("<system-bold>" if bold else "<system>", FONT_SIZE)
        tw, th = measure_string(txt, font=font)
        with GState():
            set_color((0, 0, 0, opacity))
            concat_ctm(Transform.translation(x, y))
            concat_ctm(Transform.scale(sx, sy))
            draw_string(
                txt,
                rect=(-tw / 2, -th / 2.6, tw, th),
                font=font,
                alignment=ALIGN_CENTER,
            )

    def _draw_wheel(self, state, center_x, mid_y, lens_path):
        w, h = self.width, self.height
        if w == 0 or h == 0:
            return

        start_i = int(state.current_idx) - 4
        end_i = int(state.current_idx) + 5

        for i in range(start_i, end_i):
            val = state.values[i % state.total]
            txt = f"{val:02d}"
            dist = i - state.current_idx

            angle = dist * (ITEM_HEIGHT / (h * 0.45))
            if abs(angle) > math.pi / 2:
                continue

            y_pos = mid_y + math.sin(angle) * (h * 0.42)

            # LAYER 1: BACKGROUND (Beyond the rounded magnifying glass)
            with GState():
                # Use Even-Odd Clipping to "cut" the magnifier from the screen
                bg_mask = Path.rect(0, 0, w, h)
                bg_mask.append_path(lens_path)
                bg_mask.eo_fill_rule = True
                bg_mask.add_clip()

                self._draw_text(txt, center_x, y_pos, 1.0, math.cos(angle), 0.3, False)

            # LAYER 2: MAGNIFYING GLASS (Inside the rounded rectangle)
            with GState():
                lens_path.add_clip()

                focus = 1.0 - min(1.0, abs(dist) * 0.8)
                mag = 1.0 + (MAGNIFICATION - 1.0) * focus
                self._draw_text(txt, center_x, y_pos, mag * 1.05, mag, 1.0, True)

    def draw(self):
        w, h = self.width, self.height
        if w == 0 or h == 0:
            return

        mid_y = h / 2

        # We define the parameters of the rounded magnifier
        lw = w * LENS_WIDTH_RATIO
        lx = (w - lw) / 2
        ly = mid_y - LENS_HEIGHT / 2
        lens_path = Path.rounded_rect(lx, ly, lw, LENS_HEIGHT, LENS_CORNER_RADIUS)

        # 1. Separator
        with GState():
            set_color((0, 0, 0, 0.6))
            draw_string(
                ":",
                rect=(w / 2 - 5, mid_y - 15, 10, 30),
                font=("<system-bold>", 24),
                alignment=ALIGN_CENTER,
            )

        # 2. Wheel
        self._draw_wheel(self.h_state, w * 0.3, mid_y, lens_path)
        self._draw_wheel(self.m_state, w * 0.7, mid_y, lens_path)

        # 3. Glass layer (Overlay)
        with GState():
            # Glass corners
            for i in range(int(ly)):
                a = 0.85 * (1.0 - i / (h / 2.2))
                set_color((1, 1, 1, a))
                fill_rect(0, i, w, 1)
                fill_rect(0, h - i - 1, w, 1)

            # Glass lence
            set_color((0, 0, 0, 0.03))
            lens_path.fill()

            # Lence color
            set_color((0, 0, 0, 0.08))
            lens_path.line_width = 0.5
            lens_path.stroke()


if __name__ == "__main__":
    picker = LiquidTimePicker()
    picker.frame = (0, 0, 280, 220)
    picker.background_color = "white"

    root = View()
    root.add_subview(picker)
    root.present("fullscreen")
