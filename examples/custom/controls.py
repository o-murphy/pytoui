from pytoui import ui
import math
from typing import Callable
from abc import abstractmethod

# --- Store / Model ---


class MockScrollView(ui.View):
    pass


if not hasattr(ui, "ScrollView"):
    setattr(ui, "ScrollView", MockScrollView)


class ValueStore:
    """Простий observable store для значень"""

    def __init__(self, defaults: dict[str, float] = None):
        self._values: dict[str, float] = dict(defaults or {})
        self._listeners: dict[str, list[Callable[[float], None]]] = {}

    def get(self, key: str) -> float:
        return self._values.get(key, 0.0)

    def set(self, key: str, value: float):
        value = max(0, min(1, value))
        if self._values.get(key) != value:
            self._values[key] = value
            for listener in self._listeners.get(key, []):
                listener(value)

    def subscribe(self, key: str, listener: Callable[[float], None]):
        if key not in self._listeners:
            self._listeners[key] = []
        self._listeners[key].append(listener)
        listener(self.get(key))

    def unsubscribe(self, key: str, listener: Callable[[float], None]):
        if key in self._listeners and listener in self._listeners[key]:
            self._listeners[key].remove(listener)


# --- Mock Server ---


class MockServer:
    """Імітує сервер з затримкою"""

    def __init__(self, store: ValueStore):
        self.store = store

    def send_value(self, key: str, value: float):
        import time
        import threading

        def delayed_update():
            time.sleep(0.05)
            self.store.set(key, value)

        threading.Thread(target=delayed_update).start()


# --- Mixins ---


class ScrollAwareMixin:
    """Міксин для контролів що працюють всередині ScrollView"""

    def _find_scroll_view(self):
        # view = self.superview
        # while view:
        #     if isinstance(view, ui.ScrollView):
        #         return view
        #     view = view.superview
        return None

    def _disable_scroll(self):
        sv = self._find_scroll_view()
        if sv:
            sv.scroll_enabled = False

    def _enable_scroll(self):
        sv = self._find_scroll_view()
        if sv:
            sv.scroll_enabled = True


class DraggableMixin(ScrollAwareMixin):
    """Міксин для контролів з вертикальним drag-жестом"""

    DRAG_SENSITIVITY = 200

    def _init_draggable(self, steps: int | None = None):
        self._drag_start_value = 0.0
        self._drag_start_y = 0.0
        self.steps = steps

    def _snap_value(self, value: float) -> float:
        if self.steps is None:
            return value
        snapped = round(value * self.steps) / self.steps
        return max(0, min(1, snapped))

    def touch_began(self, touch: ui.Touch):
        self._drag_start_y = touch.location[1]
        self._drag_start_value = self._display_value
        self._disable_scroll()

    def touch_moved(self, touch: ui.Touch):
        delta_y = self._drag_start_y - touch.location[1]
        delta_value = delta_y / self.DRAG_SENSITIVITY
        new_value = max(0, min(1, self._drag_start_value + delta_value))
        new_value = self._snap_value(new_value)
        if self.on_input:
            self.on_input(new_value)

    def touch_ended(self, touch: ui.Touch):
        self._enable_scroll()


class OptionsMixin:
    """Міксин для контролів з дискретними опціями"""

    def _init_options(
        self,
        options: list[str] = None,
        values: list[float] = None,
        match_mode: str = "nearest",
    ):
        self.options = options or ["Off", "On"]
        self.match_mode = match_mode
        n = len(self.options)
        self.values = (
            values if values else [i / (n - 1) if n > 1 else 0.5 for i in range(n)]
        )

    def _value_to_index(self, value: float) -> int:
        if self.match_mode == "exact":
            for i, v in enumerate(self.values):
                if abs(value - v) < 0.001:
                    return i
            return 0
        elif self.match_mode == "range":
            for i in range(len(self.values) - 1):
                if value < (self.values[i] + self.values[i + 1]) / 2:
                    return i
            return len(self.values) - 1
        else:  # nearest
            return min(
                range(len(self.values)), key=lambda i: abs(value - self.values[i])
            )

    def _index_to_value(self, index: int) -> float | None:
        return self.values[index] if 0 <= index < len(self.values) else None


class ThresholdMixin:
    """Міксин для контролів з порогом on/off"""

    def _init_threshold(
        self,
        threshold: float = 0.5,
        inverted: bool = False,
        on_value: float = 1.0,
        off_value: float = 0.0,
    ):
        self.threshold = threshold
        self.inverted = inverted
        self.on_value = on_value
        self.off_value = off_value

    def _value_to_bool(self, value: float) -> bool:
        is_on = value > self.threshold
        return not is_on if self.inverted else is_on

    def _bool_to_value(self, is_on: bool) -> float:
        if self.inverted:
            is_on = not is_on
        return self.on_value if is_on else self.off_value


# --- Base Control ---


class BaseControl(ui.View):
    """Базовий клас для всіх контролів"""

    preferred_height: float | None = None

    def __init__(self, on_input: Callable[[float], None] = None, **kwargs):
        super().__init__(**kwargs)
        self.on_input = on_input
        self._display_value = 0.0
        self.background_color = "transparent"

    def set_display_value(self, value: float):
        """Встановлює відображуване значення (викликається ззовні)"""
        self._display_value = max(0, min(1, value))
        self.set_needs_display()

    def _emit(self, value: float):
        """Відправляє значення через on_input"""
        if self.on_input:
            self.on_input(value)


# --- UI Controls ---


class KnobView(BaseControl, DraggableMixin):
    """Універсальний кноб з опціональними тіками та прогрес-дугою"""

    DRAG_SENSITIVITY = 200

    def __init__(
        self,
        on_input: Callable[[float], None] = None,
        style: str = "arc",
        num_ticks: int = 11,
        major_every: int | None = 5,
        steps: int | None = None,
        **kwargs,
    ):
        super().__init__(on_input=on_input, **kwargs)
        self._init_draggable(steps)
        self.style = style
        self.num_ticks = num_ticks
        self.major_every = major_every

    def _value_to_angle(self, value: float) -> float:
        start_angle = math.pi * 0.75
        sweep = math.pi * 1.5
        return start_angle + value * sweep

    def draw(self):
        cx, cy = self.width / 2, self.height / 2

        if self.style == "ticks":
            self._draw_ticks_style(cx, cy)
        elif self.style == "arc":
            self._draw_arc_style(cx, cy)
        else:
            self._draw_minimal_style(cx, cy)

    def _draw_arc_style(self, cx, cy):
        radius = min(cx, cy) - 10

        bg = ui.Path.oval(cx - radius, cy - radius, radius * 2, radius * 2)
        ui.set_color("#d1d1d1")
        bg.fill()

        arc_radius = radius - 8
        start_angle = self._value_to_angle(0)
        end_angle = self._value_to_angle(1)

        self._draw_arc(cx, cy, arc_radius, start_angle, end_angle, "#888888", 3)

        if self._display_value > 0.01:
            progress_end = self._value_to_angle(self._display_value)
            self._draw_arc(cx, cy, arc_radius, start_angle, progress_end, "#007AFF", 4)

        self._draw_indicator(cx, cy, radius - 2, from_center=True)
        self._draw_center_dot(cx, cy, 5)

    def _draw_ticks_style(self, cx, cy):
        outer_radius = min(cx, cy) - 4
        knob_radius = outer_radius - 16

        tick_outer = outer_radius
        tick_inner_major = outer_radius - 10
        tick_inner_minor = outer_radius - 6

        for i in range(self.num_ticks):
            t = i / (self.num_ticks - 1)
            angle = self._value_to_angle(t)

            is_major = self.major_every is not None and i % self.major_every == 0
            tick_inner = tick_inner_major if is_major else tick_inner_minor
            line_width = 2 if is_major else 1

            x1 = cx + math.cos(angle) * tick_inner
            y1 = cy + math.sin(angle) * tick_inner
            x2 = cx + math.cos(angle) * tick_outer
            y2 = cy + math.sin(angle) * tick_outer

            tick = ui.Path()
            tick.line_width = line_width
            tick.move_to(x1, y1)
            tick.line_to(x2, y2)
            ui.set_color("#666666")
            tick.stroke()

        bg = ui.Path.oval(
            cx - knob_radius, cy - knob_radius, knob_radius * 2, knob_radius * 2
        )
        ui.set_color("#d1d1d1")
        bg.fill()
        ui.set_color("#aaaaaa")
        bg.line_width = 2
        bg.stroke()

        self._draw_indicator(
            cx, cy, knob_radius - 4, from_center=False, inner_radius=knob_radius * 0.3
        )
        self._draw_center_dot(cx, cy, 4)

    def _draw_minimal_style(self, cx, cy):
        radius = min(cx, cy) - 10

        bg = ui.Path.oval(cx - radius, cy - radius, radius * 2, radius * 2)
        ui.set_color("#d1d1d1")
        bg.fill()
        ui.set_color("#aaaaaa")
        bg.line_width = 2
        bg.stroke()

        self._draw_indicator(
            cx, cy, radius - 4, from_center=False, inner_radius=radius * 0.3
        )
        self._draw_center_dot(cx, cy, 5)

    def _draw_arc(self, cx, cy, radius, start, end, color, width):
        arc = ui.Path()
        arc.line_width = width
        arc.line_cap_style = ui.LINE_CAP_ROUND
        steps = 30
        for i in range(steps + 1):
            t = i / steps
            a = start + t * (end - start)
            x = cx + math.cos(a) * radius
            y = cy + math.sin(a) * radius
            if i == 0:
                arc.move_to(x, y)
            else:
                arc.line_to(x, y)
        ui.set_color(color)
        arc.stroke()

    def _draw_indicator(self, cx, cy, outer_radius, from_center=True, inner_radius=0):
        angle = self._value_to_angle(self._display_value)
        end_x = cx + math.cos(angle) * outer_radius
        end_y = cy + math.sin(angle) * outer_radius

        if from_center:
            start_x, start_y = cx, cy
        else:
            start_x = cx + math.cos(angle) * inner_radius
            start_y = cy + math.sin(angle) * inner_radius

        indicator = ui.Path()
        indicator.line_width = 4
        indicator.line_cap_style = ui.LINE_CAP_ROUND
        indicator.move_to(start_x, start_y)
        indicator.line_to(end_x, end_y)
        ui.set_color("#007AFF" if not from_center else "#333333")
        indicator.stroke()

    def _draw_center_dot(self, cx, cy, radius):
        dot = ui.Path.oval(cx - radius, cy - radius, radius * 2, radius * 2)
        ui.set_color("#555555")
        dot.fill()


class _SliderView(BaseControl, ScrollAwareMixin):
    """Абстрактний базовий клас для слайдерів"""

    DRAG_SENSITIVITY = 200

    def __init__(
        self,
        on_input: Callable[[float], None] = None,
        steps: int | None = None,
        style: str = "default",  # 'default' | 'ticks'
        num_ticks: int = 11,
        major_every: int | None = 5,
        track_color: str = "#888888",
        fill_color: str = "#007AFF",
        **kwargs,
    ):
        super().__init__(on_input=on_input, **kwargs)
        self.steps = steps
        self.style = style
        self.num_ticks = num_ticks
        self.major_every = major_every
        self.track_color = track_color
        self.fill_color = fill_color
        self._drag_start_pos = 0.0
        self._drag_start_value = 0.0

    def _snap_value(self, value: float) -> float:
        if self.steps is None:
            return value
        snapped = round(value * self.steps) / self.steps
        return max(0, min(1, snapped))

    @abstractmethod
    def _get_drag_pos(self, touch) -> float:
        """Повертає позицію для drag"""
        pass

    @abstractmethod
    def _get_drag_direction(self) -> int:
        """Повертає напрямок: 1 або -1"""
        pass

    @abstractmethod
    def _draw_default_style(self):
        pass

    @abstractmethod
    def _draw_ticks_style(self):
        pass

    def touch_began(self, touch):
        self._drag_start_pos = self._get_drag_pos(touch)
        self._drag_start_value = self._display_value
        self._disable_scroll()

    def touch_moved(self, touch):
        current_pos = self._get_drag_pos(touch)
        delta = (current_pos - self._drag_start_pos) * self._get_drag_direction()
        delta_value = delta / self.DRAG_SENSITIVITY
        new_value = max(0, min(1, self._drag_start_value + delta_value))
        new_value = self._snap_value(new_value)
        if self.on_input:
            self.on_input(new_value)

    def touch_ended(self, touch):
        self._enable_scroll()

    def draw(self):
        if self.style == "ticks":
            self._draw_ticks_style()
        else:
            self._draw_default_style()


class VSliderView(_SliderView):
    """Вертикальний слайдер"""

    def _get_drag_pos(self, touch) -> float:
        return touch.location[1]

    def _get_drag_direction(self) -> int:
        return -1  # Вгору = більше

    def _draw_default_style(self):
        padding = 8
        track_width = min(self.width * 0.4, 30)
        track_height = self.height - padding * 2
        track_x = (self.width - track_width) / 2
        track_y = padding
        corner_radius = track_width / 2

        track = ui.Path.rounded_rect(
            track_x, track_y, track_width, track_height, corner_radius
        )
        ui.set_color(self.track_color)
        track.fill()

        fill_height = track_height * self._display_value
        fill_y = track_y + track_height - fill_height

        if fill_height > 0:
            ui.Path.rounded_rect(
                track_x, track_y, track_width, track_height, corner_radius
            ).add_clip()
            fill = ui.Path.rect(track_x, fill_y, track_width, fill_height)
            ui.set_color(self.fill_color)
            fill.fill()

    def _draw_ticks_style(self):
        padding = 8
        track_width = min(self.width * 0.3, 24)
        track_height = self.height - padding * 2
        track_x = (self.width - track_width) / 2
        track_y = padding
        corner_radius = track_width / 2

        # Тіки зліва
        tick_right = track_x - 4
        tick_left_major = tick_right - 12
        tick_left_minor = tick_right - 8

        for i in range(self.num_ticks):
            t = i / (self.num_ticks - 1)
            y = track_y + track_height - t * track_height

            is_major = self.major_every is not None and i % self.major_every == 0
            tick_left = tick_left_major if is_major else tick_left_minor
            line_width = 2 if is_major else 1

            tick = ui.Path()
            tick.line_width = line_width
            tick.move_to(tick_left, y)
            tick.line_to(tick_right, y)
            ui.set_color("#666666")
            tick.stroke()

        track = ui.Path.rounded_rect(
            track_x, track_y, track_width, track_height, corner_radius
        )
        ui.set_color(self.track_color)
        track.fill()

        fill_height = track_height * self._display_value
        fill_y = track_y + track_height - fill_height

        if fill_height > 0:
            ui.Path.rounded_rect(
                track_x, track_y, track_width, track_height, corner_radius
            ).add_clip()
            fill = ui.Path.rect(track_x, fill_y, track_width, fill_height)
            ui.set_color(self.fill_color)
            fill.fill()


class HSliderView(_SliderView):
    """Горизонтальний слайдер"""

    preferred_height = 50

    def _get_drag_pos(self, touch) -> float:
        return touch.location[0]

    def _get_drag_direction(self) -> int:
        return 1  # Вправо = більше

    def _draw_default_style(self):
        padding = 8
        track_height = min(self.height * 0.4, 20)
        track_width = self.width - padding * 2
        track_x = padding
        track_y = (self.height - track_height) / 2
        corner_radius = track_height / 2

        track = ui.Path.rounded_rect(
            track_x, track_y, track_width, track_height, corner_radius
        )
        ui.set_color(self.track_color)
        track.fill()

        fill_width = track_width * self._display_value

        if fill_width > 0:
            ui.Path.rounded_rect(
                track_x, track_y, track_width, track_height, corner_radius
            ).add_clip()
            fill = ui.Path.rect(track_x, track_y, fill_width, track_height)
            ui.set_color(self.fill_color)
            fill.fill()

    def _draw_ticks_style(self):
        padding = 8
        track_height = min(self.height * 0.3, 16)
        track_width = self.width - padding * 2
        track_x = padding
        track_y = (self.height - track_height) / 2 - 8
        corner_radius = track_height / 2

        # Тіки знизу
        tick_top = track_y + track_height + 4
        tick_bottom_major = tick_top + 12
        tick_bottom_minor = tick_top + 8

        for i in range(self.num_ticks):
            t = i / (self.num_ticks - 1)
            x = track_x + t * track_width

            is_major = self.major_every is not None and i % self.major_every == 0
            tick_bottom = tick_bottom_major if is_major else tick_bottom_minor
            line_width = 2 if is_major else 1

            tick = ui.Path()
            tick.line_width = line_width
            tick.move_to(x, tick_top)
            tick.line_to(x, tick_bottom)
            ui.set_color("#666666")
            tick.stroke()

        track = ui.Path.rounded_rect(
            track_x, track_y, track_width, track_height, corner_radius
        )
        ui.set_color(self.track_color)
        track.fill()

        fill_width = track_width * self._display_value

        if fill_width > 0:
            ui.Path.rounded_rect(
                track_x, track_y, track_width, track_height, corner_radius
            ).add_clip()
            fill = ui.Path.rect(track_x, track_y, fill_width, track_height)
            ui.set_color(self.fill_color)
            fill.fill()


class SwitchView(BaseControl, ThresholdMixin):
    """Свіч на базі ui.Switch"""

    preferred_height = 31

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

        self._switch = ui.Switch()
        self._switch.action = self._on_switch_changed
        self.add_subview(self._switch)

    def set_display_value(self, value: float):
        self._display_value = value
        self._switch.value = self._value_to_bool(value)

    def layout(self):
        sw_width = self._switch.width
        sw_height = self._switch.height
        self._switch.frame = (
            (self.width - sw_width) / 2,
            (self.height - sw_height) / 2,
            sw_width,
            sw_height,
        )

    def _on_switch_changed(self, sender):
        self._emit(self._bool_to_value(sender.value))


class SegmentView(BaseControl, OptionsMixin):
    """Сегментований контрол"""

    preferred_height = 32

    def __init__(
        self,
        on_input: Callable[[float], None] = None,
        options: list[str] = None,
        values: list[float] = None,
        match_mode: str = "nearest",
        **kwargs,
    ):
        super().__init__(on_input=on_input, **kwargs)
        self._init_options(options, values, match_mode)

        self._segment = ui.SegmentedControl()
        self._segment.segments = self.options
        self._segment.action = self._on_segment_changed
        self.add_subview(self._segment)

    def set_display_value(self, value: float):
        self._display_value = value
        index = self._value_to_index(value)
        if index != self._segment.selected_index:
            self._segment.selected_index = index

    def layout(self):
        self._segment.frame = (
            0,
            (self.height - self.preferred_height) / 2,
            self.width,
            self.preferred_height,
        )

    def _on_segment_changed(self, sender):
        value = self._index_to_value(sender.selected_index)
        if value is not None:
            self._emit(value)


class PickerView(BaseControl, OptionsMixin):
    """Пікер з діалогом вибору"""

    preferred_height = 44

    def __init__(
        self,
        on_input: Callable[[float], None] = None,
        options: list[str] = None,
        values: list[float] = None,
        match_mode: str = "nearest",
        title: str = "Select",
        **kwargs,
    ):
        super().__init__(on_input=on_input, **kwargs)
        self._init_options(options, values, match_mode)
        self._current_index = 0
        self._picker_title = title

        self._button = ui.Button()
        self._button.background_color = "#555555"
        self._button.tint_color = "white"
        self._button.corner_radius = 8
        self._button.action = self._show_picker
        self._update_button_title()
        self.add_subview(self._button)

        self._arrow = ui.Label()
        self._arrow.text = "▼"
        self._arrow.text_color = "#888888"
        self._arrow.font = ("<system>", 12)
        self._arrow.alignment = ui.ALIGN_CENTER
        self.add_subview(self._arrow)

    def set_display_value(self, value: float):
        self._display_value = value
        self._current_index = self._value_to_index(value)
        self._update_button_title()

    def _update_button_title(self):
        if 0 <= self._current_index < len(self.options):
            self._button.title = self.options[self._current_index]

    def layout(self):
        padding = 4
        self._button.frame = (0, padding, self.width, self.height - padding * 2)
        self._arrow.frame = (self.width - 32, 0, 24, self.height)

    def _show_picker(self, sender):
        import dialogs

        result = dialogs.list_dialog(title=self._picker_title, items=self.options)

        if result:
            try:
                index = self.options.index(result)
                self._current_index = index
                self._update_button_title()
                value = self._index_to_value(index)
                if value is not None:
                    self._emit(value)
            except ValueError:
                pass


# --- Labeled Control Container ---


class LabeledControl(ui.View):
    """Універсальний композитний віджет з flex-лейаутом"""

    def __init__(
        self,
        store: ValueStore,
        key: str,
        server: MockServer,
        label: str = None,
        format_func: Callable[[float], str] = None,
        control: BaseControl = None,
        hide_value: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.store = store
        self.key = key
        self.server = server
        self.format_func = format_func or (lambda v: f"{v:.0%}")
        self.hide_value = hide_value

        self.background_color = "#3c3c3c"
        self.corner_radius = 8

        # Title label
        self.title_label = ui.Label()
        self.title_label.text = label or key
        self.title_label.text_color = "white"
        self.title_label.font = ("<system-bold>", 14)
        self.title_label.alignment = ui.ALIGN_CENTER
        self.title_label.flex = "W"
        self.add_subview(self.title_label)

        # Control container
        self._control_container = ui.View()
        self._control_container.background_color = "transparent"
        self._control_container.flex = "WH"
        self.add_subview(self._control_container)

        self.control = control or KnobView()
        self.control.on_input = self._on_control_input
        self._control_container.add_subview(self.control)

        # Value label
        if not self.hide_value:
            self.value_label = ui.Label()
            self.value_label.text_color = "#007AFF"
            self.value_label.font = ("<system>", 16)
            self.value_label.alignment = ui.ALIGN_CENTER
            self.value_label.flex = "W"
            self.add_subview(self.value_label)

        store.subscribe(key, self._on_value_changed)

    def will_close(self):
        self.store.unsubscribe(self.key, self._on_value_changed)

    def layout(self):
        padding = 8
        label_height = 20
        value_height = 24 if not self.hide_value else 0

        w, h = self.width, self.height

        self.title_label.frame = (0, padding, w, label_height)

        if not self.hide_value:
            self.value_label.frame = (0, h - value_height - padding, w, value_height)

        container_y = label_height + padding * 2
        container_h = h - label_height - value_height - padding * 4
        self._control_container.frame = (
            padding,
            container_y,
            w - padding * 2,
            container_h,
        )

        self._center_control()

    def _center_control(self):
        cw = self._control_container.width
        ch = self._control_container.height

        preferred_h = getattr(self.control, "preferred_height", None)

        if preferred_h is not None:
            ctrl_h = min(preferred_h, ch)
            ctrl_w = cw
        else:
            ctrl_size = min(cw, ch)
            ctrl_w = ctrl_size
            ctrl_h = ctrl_size

        ctrl_x = (cw - ctrl_w) / 2
        ctrl_y = (ch - ctrl_h) / 2
        self.control.frame = (ctrl_x, ctrl_y, ctrl_w, ctrl_h)

    def _on_control_input(self, value: float):
        self.server.send_value(self.key, value)

    def _on_value_changed(self, value: float):
        self.control.set_display_value(value)
        if not self.hide_value:
            self.value_label.text = self.format_func(value)


# --- Layout Helpers ---


def make_row(*controls, height=160):
    row = ui.View()
    row.background_color = "transparent"
    row.height = height
    row.flex = "W"
    for ctrl in controls:
        ctrl.flex = "H"
        row.add_subview(ctrl)
    return row


def layout_row(row):
    n = len(row.subviews)
    if n == 0:
        return
    w = row.width / n
    for i, sv in enumerate(row.subviews):
        sv.frame = (i * w + 5, 0, w - 10, row.height)


# --- App ---
def main():
    store = ValueStore(
        {
            "volume": 0.75,
            "tone": 0.5,
            "gain": 0.2,
            "bypass": 0.0,
            "mute": 1.0,
            "mode": 0.0,
            "quality": 0.5,
            "channel": 0.25,
            "preset": 0.0,
        }
    )
    server = MockServer(store)

    # Головний контейнер
    v = ui.View()
    v.background_color = "#1c1c1c"
    v.frame = (0, 0, 400, 600)

    # ScrollView
    # scroll = ui.ScrollView()
    scroll = ui.View()
    scroll.background_color = "transparent"
    # scroll.shows_vertical_scroll_indicator = True
    scroll.flex = "WH"
    v.add_subview(scroll)

    # Контент
    content = ui.View()
    content.background_color = "transparent"
    scroll.add_subview(content)

    # Ряди контролів
    rows = [
        # Кноби
        make_row(
            LabeledControl(store, "volume", server, label="Volume"),
            LabeledControl(
                store,
                "tone",
                server,
                label="Tone",
                control=KnobView(style="ticks", num_ticks=11, steps=10),
                format_func=lambda v: f"{int(v * 10)}",
            ),
            LabeledControl(
                store,
                "gain",
                server,
                label="Gain",
                control=KnobView(style="minimal", steps=5),
                format_func=lambda v: f"{int(v * 5)}",
            ),
        ),
        # Слайдери
        make_row(
            LabeledControl(
                store, "volume", server, label="Volume", control=VSliderView()
            ),
            LabeledControl(
                store,
                "tone",
                server,
                label="Tone",
                control=VSliderView(style="ticks", steps=10, num_ticks=11),
                format_func=lambda v: f"{int(v * 10)}",
            ),
            LabeledControl(
                store,
                "gain",
                server,
                label="Gain",
                control=VSliderView(steps=5),
                format_func=lambda v: f"{int(v * 5)}",
            ),
        ),
        make_row(
            LabeledControl(
                store,
                "tone",
                server,
                label="Tone",
                control=HSliderView(style="ticks", steps=10, num_ticks=11),
                format_func=lambda v: f"{int(v * 10)}",
            ),
            height=110,
        ),
        # Свічі
        make_row(
            LabeledControl(
                store,
                "bypass",
                server,
                label="Bypass",
                control=SwitchView(inverted=True),
                format_func=lambda v: "Off" if v > 0.5 else "On",
            ),
            LabeledControl(
                store,
                "mute",
                server,
                label="Mute",
                control=SwitchView(),
                format_func=lambda v: "Muted" if v > 0.5 else "Active",
            ),
            LabeledControl(
                store,
                "gain",
                server,
                label="Boost",
                control=SwitchView(threshold=0.3, on_value=0.8, off_value=0.1),
                format_func=lambda v: "High" if v > 0.3 else "Low",
            ),
            height=110,
        ),
        # Сегменти
        make_row(
            LabeledControl(
                store,
                "bypass",
                server,
                label="Bypass",
                control=SegmentView(options=["Off", "On"]),
                hide_value=True,
            ),
            height=90,
        ),
        make_row(
            LabeledControl(
                store,
                "mode",
                server,
                label="Mode",
                control=SegmentView(
                    options=["Low", "Mid", "High"], values=[0.0, 0.5, 1.0]
                ),
                hide_value=True,
            ),
            height=90,
        ),
        make_row(
            LabeledControl(
                store,
                "quality",
                server,
                label="Quality",
                control=SegmentView(
                    options=["Draft", "Normal", "HQ", "Ultra"],
                    values=[0.1, 0.4, 0.7, 1.0],
                ),
                format_func=lambda v: f"{int(v * 100)}%",
            ),
            height=110,
        ),
        make_row(
            LabeledControl(
                store,
                "channel",
                server,
                label="Channel",
                control=SegmentView(
                    options=["Ch 1", "Ch 2", "Ch 3", "Ch 4"],
                    values=[0.0, 0.25, 0.5, 0.75],
                    match_mode="range",
                ),
                hide_value=True,
            ),
            height=90,
        ),
        # Пікери
        make_row(
            LabeledControl(
                store,
                "preset",
                server,
                label="Preset",
                control=PickerView(
                    options=["Clean", "Crunch", "Overdrive", "Distortion", "Fuzz"],
                    values=[0.0, 0.25, 0.5, 0.75, 1.0],
                    title="Select Preset",
                ),
                hide_value=True,
            ),
            LabeledControl(
                store,
                "channel",
                server,
                label="Channel",
                control=PickerView(
                    options=["Ch 1", "Ch 2", "Ch 3", "Ch 4"],
                    values=[0.0, 0.25, 0.5, 0.75],
                    match_mode="range",
                    title="Select Channel",
                ),
                hide_value=True,
            ),
            height=90,
        ),
    ]

    def layout_content():
        padding_top = 20
        spacing = 10
        y = padding_top
        w = scroll.width

        for row in rows:
            row.frame = (0, y, w, row.height)
            layout_row(row)
            y += row.height + spacing

        content.frame = (0, 0, w, y + 20)
        # scroll.content_size = (w, y + 20)

    for row in rows:
        content.add_subview(row)

    def main_layout(sender):
        scroll.frame = (0, 0, sender.width, sender.height)
        layout_content()

    # v.layout = main_layout
    main_layout(v)

    v.present("fullscreen")


if __name__ == "__main__":
    main()
