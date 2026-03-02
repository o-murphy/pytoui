import math
from collections.abc import Callable

from examples.custom.controls import (
    BaseControl,
    KnobView,
    MockServer,
    ThresholdMixin,
    ValueStore,
)

from pytoui import ui


class LedIndicator(BaseControl):
    preferred_height = 16

    def __init__(
        self,
        on_input: Callable[[float], None] = None,
        on_color: str = "#FF0000",
        off_color: str = "#440000",
        threshold: float = 0.5,
        inverted: bool = False,
        **kwargs,
    ):
        super().__init__(on_input=on_input, **kwargs)
        self.on_color = on_color
        self.off_color = off_color
        self.threshold = threshold
        self.inverted = inverted

    def _is_on(self) -> bool:
        is_on = self._display_value > self.threshold
        return not is_on if self.inverted else is_on

    def draw(self):
        cx, cy = self.width / 2, self.height / 2
        radius = min(cx, cy) - 2

        housing = ui.Path.oval(
            cx - radius - 1,
            cy - radius - 1,
            (radius + 1) * 2,
            (radius + 1) * 2,
        )
        ui.set_color("#222222")
        housing.fill()

        led = ui.Path.oval(cx - radius, cy - radius, radius * 2, radius * 2)
        ui.set_color(self.on_color if self._is_on() else self.off_color)
        led.fill()

        if self._is_on():
            bright_radius = radius * 0.5
            bright = ui.Path.oval(
                cx - bright_radius,
                cy - bright_radius,
                bright_radius * 2,
                bright_radius * 2,
            )
            ui.set_color("#FF6666")
            bright.fill()

        highlight_radius = radius * 0.25
        highlight = ui.Path.oval(
            cx - radius * 0.3,
            cy - radius * 0.5,
            highlight_radius,
            highlight_radius,
        )
        ui.set_color("#FFFFFF66" if self._is_on() else "#FFFFFF22")
        highlight.fill()


class FootswitchButton(BaseControl, ThresholdMixin):
    def __init__(
        self,
        on_input: Callable[[float], None] = None,
        threshold: float = 0.5,
        inverted: bool = False,
        on_value: float = 1.0,
        off_value: float = 0.0,
        **kwargs,
    ):
        super().__init__(on_input=on_input, **kwargs)
        self._init_threshold(threshold, inverted, on_value, off_value)
        self._is_pressed = False

    def draw(self):
        w, h = self.width, self.height
        padding = 4

        frame_rect = ui.Path.rounded_rect(0, 0, w, h, 4)
        ui.set_color("#444444")
        frame_rect.fill()

        press_offset = 3 if self._is_pressed else 0
        rubber_rect = ui.Path.rounded_rect(
            padding,
            padding,
            w - padding * 2,
            h - padding * 2 - press_offset,
            3,
        )
        ui.set_color("#1a1a1a" if not self._is_pressed else "#111111")
        rubber_rect.fill()

        line_area_x = padding + 20
        line_area_w = w - padding * 2 - 40
        line_area_y = padding + 20
        line_area_h = h - padding * 2 - 40 - press_offset

        for i in range(5):
            y = line_area_y + (i / 4) * line_area_h
            line = ui.Path()
            line.line_cap_style = ui.LINE_CAP_ROUND
            line.move_to(line_area_x, y)
            line.line_to(line_area_x + line_area_w, y)
            line.line_width = 26
            ui.set_color("#2a2a2a")
            line.stroke()

    def touch_began(self, touch):
        self._is_pressed = True
        self.set_needs_display()

    def touch_ended(self, touch):
        self._is_pressed = False
        current_bool = self._value_to_bool(self._display_value)
        new_value = self._bool_to_value(not current_bool)
        self._emit(new_value)
        self.set_needs_display()


class DS1KnobView(KnobView):
    def __init__(
        self,
        on_input: Callable[[float], None] = None,
        num_ticks: int = 2,
        major_every: int | None = 1,
        steps: int | None = None,
        dot_color: str = "#1a1a1a",
        knob_color: str = "#1a1a1a",
        indicator_color: str = "#f1f1f1",
        **kwargs,
    ):
        super().__init__(
            on_input=on_input,
            style="ticks",
            num_ticks=num_ticks,
            major_every=major_every,
            steps=steps,
            **kwargs,
        )
        self.dot_color = dot_color
        self.knob_color = knob_color
        self.indicator_color = indicator_color

    def draw(self):
        cx, cy = self.width / 2, self.height / 2
        self._draw_boss_style(cx, cy)

    def _draw_boss_style(self, cx, cy):
        outer_radius = min(cx, cy) - 4
        knob_radius = outer_radius - 8

        dot_radius_major = 3
        dot_radius_minor = 2
        dot_distance = outer_radius - 2

        for i in range(self.num_ticks):
            t = i / (self.num_ticks - 1)
            angle = self._value_to_angle(t)

            is_major = self.major_every is not None and i % self.major_every == 0
            dot_r = dot_radius_major if is_major else dot_radius_minor

            x = cx + math.cos(angle) * dot_distance
            y = cy + math.sin(angle) * dot_distance

            dot = ui.Path.oval(x - dot_r, y - dot_r, dot_r * 2, dot_r * 2)
            ui.set_color(self.dot_color)
            dot.fill()

        knob_bg = ui.Path.oval(
            cx - knob_radius,
            cy - knob_radius,
            knob_radius * 2,
            knob_radius * 2,
        )
        ui.set_color(self.knob_color)
        knob_bg.fill()

        center_radius = knob_radius * 0.55
        center = ui.Path.oval(
            cx - center_radius,
            cy - center_radius,
            center_radius * 2,
            center_radius * 2,
        )
        ui.set_color("#D8D8D8")
        center.fill()

        ring = ui.Path.oval(
            cx - knob_radius,
            cy - knob_radius,
            knob_radius * 2,
            knob_radius * 2,
        )
        ring.line_width = 1.5
        ui.set_color("#999999")
        ring.stroke()

        self._draw_boss_indicator(cx, cy, knob_radius)

    def _draw_boss_indicator(self, cx, cy, knob_radius):
        angle = self._value_to_angle(self._display_value)

        inner_r = knob_radius * 0.6
        outer_r = knob_radius * 0.9

        x1 = cx + math.cos(angle) * inner_r
        y1 = cy + math.sin(angle) * inner_r
        x2 = cx + math.cos(angle) * outer_r
        y2 = cy + math.sin(angle) * outer_r

        indicator = ui.Path()
        indicator.move_to(x1, y1)
        indicator.line_to(x2, y2)
        indicator.line_width = knob_radius * 0.15
        # indicator.line_cap_style = ui.LINE_CAP_ROUND
        ui.set_color(self.indicator_color)
        indicator.stroke()


class DS1PedalKnob(ui.View):
    def __init__(
        self,
        store: ValueStore,
        key: str,
        server: MockServer,
        label: str,
        label_position: str = "bottom",  # "top" | "bottom"
        label_color: str = "#1a1a1a",
        value_format: Callable[[float], str] = None,
        num_ticks: int = 2,
        major_every: int | None = 1,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.store = store
        self.key = key
        self.server = server
        self.label_position = label_position
        self.value_format = value_format or (lambda v: f"{int(v * 100)}")
        self.background_color = "transparent"

        self.knob = DS1KnobView(
            num_ticks=num_ticks,
            major_every=major_every,
        )
        self.knob.on_input = self._on_input
        self.add_subview(self.knob)

        # Label
        self.label = ui.Label()
        self.label.text = label
        self.label.font = ("<system-bold>", 14)
        self.label.text_color = label_color
        self.label.alignment = ui.ALIGN_CENTER
        self.add_subview(self.label)

        # Value display
        self.value_label = ui.Label()
        self.value_label.font = ("<system>", 12)
        self.value_label.text_color = "#000000"
        self.value_label.background_color = "transparent"
        self.value_label.alignment = ui.ALIGN_CENTER
        self.add_subview(self.value_label)

        store.subscribe(key, self._on_value_changed)

    def _on_input(self, value: float):
        self.server.send_value(self.key, value)

    def _on_value_changed(self, value: float):
        self.knob.set_display_value(value)
        self.value_label.text = self.value_format(value)

    def layout(self):
        w, h = self.width, self.height
        label_height = 14
        value_height = 10
        spacing = 2

        if self.label_position == "top":
            self.label.frame = (0, 0, w, label_height)
            knob_y = label_height + spacing
            knob_size = min(w, h - label_height - value_height - spacing * 3)
            self.knob.frame = ((w - knob_size) / 2, knob_y, knob_size, knob_size)
            self.value_label.frame = (
                (w - 30) / 2,
                knob_y + knob_size * 0.5 - value_height / 2,
                30,
                value_height,
            )
        else:
            knob_size = min(w, h - label_height - value_height - spacing * 3)
            self.knob.frame = ((w - knob_size) / 2, 0, knob_size, knob_size)
            self.label.frame = (0, knob_size + spacing, w, label_height)
            self.value_label.frame = (
                (w - 30) / 2,
                knob_size * 0.5 - value_height / 2,
                30,
                value_height,
            )


class DS1Pedal(ui.View):
    """BOSS DS-1 Distortion Pedal"""

    ORANGE = "#FF6A00"
    DARK_ORANGE = "#E55A00"
    BLACK = "#1a1a1a"

    def __init__(self, store: ValueStore, server: MockServer, **kwargs):
        super().__init__(**kwargs)
        self.store = store
        self.server = server
        self.background_color = "transparent"
        self._setup_ui()

    def _setup_ui(self):
        # === LED ===
        self.led = LedIndicator(
            on_color="#FF0000",
            off_color="#440000",
            inverted=True,
        )
        self.add_subview(self.led)
        self.store.subscribe("bypass", self.led.set_display_value)

        self.check_label = ui.Label()
        self.check_label.text = "CHECK"
        self.check_label.font = ("<system-bold>", 12)
        self.check_label.text_color = self.BLACK
        self.check_label.alignment = ui.ALIGN_CENTER
        self.add_subview(self.check_label)

        self.tone_knob = DS1PedalKnob(
            self.store,
            "tone",
            self.server,
            label="TONE",
            label_position="bottom",
            label_color=self.BLACK,
        )
        self.add_subview(self.tone_knob)

        self.level_knob = DS1PedalKnob(
            self.store,
            "level",
            self.server,
            label="LEVEL",
            label_position="top",
            label_color=self.BLACK,
        )
        self.add_subview(self.level_knob)

        self.dist_knob = DS1PedalKnob(
            self.store,
            "dist",
            self.server,
            label="DIST",
            label_position="bottom",
            label_color=self.BLACK,
        )
        self.add_subview(self.dist_knob)

        # === Jack labels ===
        self.output_label = self._create_jack_label("← OUTPUT")
        self.input_label = self._create_jack_label("INPUT ←")
        self.add_subview(self.output_label)
        self.add_subview(self.input_label)

        # === Title ===
        self.title_label = ui.Label()
        self.title_label.text = " ".join("Distortion")
        self.title_label.font = ("SourceCodePro-Bold", 22)
        self.title_label.text_color = self.BLACK
        self.title_label.alignment = ui.ALIGN_CENTER
        self.add_subview(self.title_label)

        self.subtitle_label = ui.Label()
        self.subtitle_label.text = "DS-1"
        self.subtitle_label.font = ("SourceCodePro-Bold", 20)
        self.subtitle_label.text_color = self.BLACK
        self.subtitle_label.alignment = ui.ALIGN_RIGHT
        self.add_subview(self.subtitle_label)

        # === Footswitch ===
        self.footswitch = FootswitchButton(inverted=True)
        self.add_subview(self.footswitch)
        self.store.subscribe("bypass", self.footswitch.set_display_value)
        self.footswitch.on_input = lambda v: self.server.send_value("bypass", v)

    def _create_jack_label(self, text: str) -> ui.Label:
        label = ui.Label()
        label.text = text
        label.font = ("<system-bold>", 15)
        label.text_color = self.BLACK
        label.alignment = ui.ALIGN_CENTER
        return label

    def layout(self):
        w, h = self.width, self.height

        # LED
        led_size = 16
        self.led.frame = ((w - led_size) / 2, 30, led_size, led_size)
        self.check_label.frame = ((w - 100) / 2, 15, 100, 12)

        knob_w = w * 0.4
        knob_h = knob_w + 32  # knob + label + value
        top_knob_y = 10
        bottom_knob_y = top_knob_y + knob_w * 0.6

        self.tone_knob.frame = (w * 0.05, top_knob_y, knob_w, knob_h)

        self.dist_knob.frame = (w * 0.95 - knob_w, top_knob_y, knob_w, knob_h)

        small_knob_w = knob_w - w * 0.1
        small_knob_h = knob_h - w * 0.1
        self.level_knob.frame = (
            (w - small_knob_w) / 2,
            bottom_knob_y,
            small_knob_w,
            small_knob_h,
        )

        # Jacks
        jacks_y = h * 0.38
        self.output_label.frame = (10, jacks_y, 100, 15)
        self.input_label.frame = (w - 100, jacks_y, 100, 15)

        # Title
        title_y = h * 0.5
        self.title_label.frame = (0, title_y, w, 40)
        self.subtitle_label.frame = (0, title_y + 35, w * 0.9, 20)

        # Footswitch
        footswitch_w = w * 0.9
        footswitch_h = h * 0.35
        footswitch_y = h - footswitch_h - 15
        self.footswitch.frame = (
            (w - footswitch_w) / 2,
            footswitch_y,
            footswitch_w,
            footswitch_h,
        )

    def draw(self):
        w, h = self.width, self.height

        body = ui.Path.rounded_rect(0, 0, w, h, 16)
        ui.set_color(self.ORANGE)
        body.fill()

        top_highlight = ui.Path.rounded_rect(2, 2, w - 4, h * 0.35, 14)
        ui.set_color("#FF7A20")
        top_highlight.fill()

        border = ui.Path.rounded_rect(2, 2, w - 4, h - 4, 14)
        border.line_width = 3
        ui.set_color(self.DARK_ORANGE)
        border.stroke()

        inner = ui.Path.rounded_rect(6, 6, w - 12, h - 12, 10)
        inner.line_width = 1
        ui.set_color("#CC5500")
        inner.stroke()


def main():
    store = ValueStore(
        {
            "tone": 0.5,
            "level": 0.7,
            "dist": 0.6,
            "bypass": 1.0,
        },
    )
    server = MockServer(store)

    v = ui.View()
    v.background_color = "#2a2a2a"
    v.frame = (0, 0, 400, 700)

    pedal_w = 290
    pedal_h = 550
    pedal = DS1Pedal(store, server)
    pedal.frame = ((400 - pedal_w) / 2, 50, pedal_w, pedal_h)
    v.add_subview(pedal)

    info = ui.Label()
    info.text = "Drag knobs • Tap footswitch"
    info.font = ("<system>", 12)
    info.text_color = "#666666"
    info.alignment = ui.ALIGN_CENTER
    info.frame = (0, 600, 400, 20)
    v.add_subview(info)

    v.present("fullscreen")


if __name__ == "__main__":
    main()
