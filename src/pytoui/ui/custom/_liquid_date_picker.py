from __future__ import annotations

import calendar
import locale
import math
import time
from datetime import datetime
from typing import TYPE_CHECKING, Callable, List

from pytoui.ui._button import Button
from pytoui.ui._constants import ALIGN_CENTER, LINE_CAP_ROUND
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
from pytoui.ui._internals import get_ui_style
from pytoui.ui._view import View

if TYPE_CHECKING:
    from pytoui.ui._types import MouseWheel, Touch

__all__ = ("LiquidDatePicker",)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


if get_ui_style() == "light":
    _BG_COLOR = (1.0, 1.0, 1.0, 1.0)
    _BG_COLOR_REVERSED = (0.0, 0.0, 0.0, 1.0)
    _TINT_COLOR = (0.0, 0.478, 1.0, 1.0)
    _TINT_LIGHT_COLOR = (0.0, 0.478, 1.0, 0.25)
    _TINT_HOVER_COLOR = (0.0, 0.478, 1.0, 0.08)
    _TEXT_PRIMARY_COLOR = (0.0, 0.0, 0.0, 1.0)
    _TEXT_TODAY_SELECTED_COLOR = (1.0, 1.0, 1.0, 1.0)
    _WEEKDAY_TEXT_COLOR = _BG_COLOR_REVERSED
    _WHEEL_TEXT_COLOR = (0.0, 0.0, 0.0, 1.0)
else:
    _BG_COLOR = (0.3, 0.3, 0.3, 1.0)
    _BG_COLOR_REVERSED = (0.7, 0.7, 0.7, 1.0)
    _TINT_COLOR = (0.04, 0.52, 1.0, 1.0)
    _TINT_LIGHT_COLOR = (0.04, 0.52, 1.0, 0.25)
    _TINT_HOVER_COLOR = (0.04, 0.52, 1.0, 0.08)
    _TEXT_PRIMARY_COLOR = (1.0, 1.0, 1.0, 1.0)
    _TEXT_TODAY_SELECTED_COLOR = (1.0, 1.0, 1.0, 1.0)
    _WEEKDAY_TEXT_COLOR = _BG_COLOR_REVERSED
    _WHEEL_TEXT_COLOR = (0.7, 0.7, 0.7, 1.0)

_DAY_ITEM_SIZE = 44
_CALENDAR_HEADER_HEIGHT = 48
_WEEKDAY_HEADER_HEIGHT = 24

_FONT_REGULAR = ("Helvetica Neue", 15)
_FONT_BOLD = ("Helvetica Neue Bold", 15)
_BUTTON_FONT = ("Helvetica Neue", 28)
_WEEKDAY_FONT = ("Helvetica Neue", 11)

# Wheel Picker
_PICKER_WHEEL_ITEM_HEIGHT = 40
_PICKER_ITEM_FONT = ("Helvetica Neue", 18)
_PICKER_LENS_HEIGHT = 44
_PICKER_LENS_WIDTH_RATIO = 0.94
_PICKER_LENS_CORNER_RADIUS = 16
_PICKER_MAGNIFICATION = 1.35
_PICKER_WHEEL_SNAP_VEL_TH = 0.5  # was 0.1
_PICKER_WHEEL_DECELERATION = 0.85  # was 0.95
_PICKER_WHEEL_SNAP_SPEED = 0.35  # was 0.2
_PICKER_WHEEL_SNAP_EPSILON = 0.005  # was 0.001
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _weekday_names() -> List[str]:
    try:
        locale.setlocale(locale.LC_TIME, "")
        return [datetime(2026, 1, i).strftime("%a").upper()[:3] for i in range(1, 8)]
    except Exception:
        return ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


# ---------------------------------------------------------------------------
# _DateState  —  delegate, notifies all receivers except the sender
# ---------------------------------------------------------------------------


class _DateState:
    """
    Holds two independent pieces of state:

    selected_date  — full date (year + month + day); changed only on a day tap
                     or via the public LiquidDatePicker.date setter.
    display        — year + month currently visible on screen; changed when the
                     user swipes the calendar or scrolls the wheel picker.

    Each component registers itself as a receiver via register().
    On every state change _DateState notifies all receivers EXCEPT the sender.

    Receivers are expected to implement:
      on_display_changed()   — called when the display year/month changes
      on_selection_changed() — called when selected_date changes
    """

    def __init__(self, date: datetime | None):
        d = date or datetime.now()
        self._selected: datetime = d
        self._display_year: int = d.year
        self._display_month: int = d.month
        self._receivers: list[object] = []

    # ── Registration ─────────────────────────────────────────────────────────

    def register(self, receiver: object) -> None:
        if receiver not in self._receivers:
            self._receivers.append(receiver)

    def _notify_display(self, sender: object) -> None:
        for r in self._receivers:
            if r is not sender and hasattr(r, "on_display_changed"):
                r.on_display_changed()

    def _notify_selection(self, sender: object) -> None:
        for r in self._receivers:
            if r is not sender and hasattr(r, "on_selection_changed"):
                r.on_selection_changed()

    # ── selected_date ────────────────────────────────────────────────────────

    @property
    def selected_date(self) -> datetime:
        return self._selected

    # backwards compatibility
    @property
    def date(self) -> datetime:
        return self._selected

    @date.setter
    def date(self, value: datetime | None) -> None:
        self.set_selected(value or datetime.now(), sender=None)

    def set_selected(self, value: datetime, sender: object = None) -> None:
        if value == self._selected:
            return
        self._selected = value
        self._notify_selection(sender)

    # ── display (year + month) ────────────────────────────────────────────────

    @property
    def display_year(self) -> int:
        return self._display_year

    @property
    def display_month(self) -> int:
        return self._display_month

    @property
    def display_month_index(self) -> int:
        return self._display_year * 12 + (self._display_month - 1)

    # backwards compatibility
    @property
    def month_index(self) -> int:
        return self.display_month_index

    def set_display(self, year: int, month: int, sender: object = None) -> None:
        if year == self._display_year and month == self._display_month:
            return
        self._display_year = year
        self._display_month = month
        self._notify_display(sender)

    def set_display_from_index(self, idx: int, sender: object = None) -> None:
        year, month = self.year_month_from_index(idx)
        self.set_display(year, month, sender)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def month_name(self) -> str:
        try:
            locale.setlocale(locale.LC_TIME, "")
            return (
                datetime(self._display_year, self._display_month, 1)
                .strftime("%B %Y")
                .capitalize()
            )
        except Exception:
            NAMES = [
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ]
            return f"{NAMES[self._display_month - 1]} {self._display_year}"

    @staticmethod
    def year_month_from_index(idx: int) -> tuple[int, int]:
        year, month = divmod(idx, 12)
        return year, month + 1

    # backwards compatibility
    @staticmethod
    def year_month_from_month_index(idx: int) -> tuple[int, int]:
        return _DateState.year_month_from_index(idx)


# ---------------------------------------------------------------------------
# _CalendarView
# ---------------------------------------------------------------------------


class _CalendarView(View):
    _SNAP_DUR = 0.30
    _DRAG_THRESHOLD = 8

    def __init__(self, date_state: _DateState, /, **kwargs):
        self._date_state = date_state
        self._origin_idx: int = self._date_state.month_index
        self._offset: float = 0.0
        self._today = datetime.now()

        self._touch_active = False
        self._touch_start_x = 0.0
        self._touch_start_y = 0.0
        self._touch_start_offset = 0.0
        self._last_x = 0.0
        self._last_t = 0.0
        self._vel = 0.0
        self._is_dragging = False

        self._hover: tuple[int, int, int] | None = None

        self._snap_target: float | None = None
        self._snap_start: float = 0.0
        self._snap_t0: float = 0.0

        self.on_offset_changed: Callable[[float], None] | None = None
        self.on_settled: Callable[[int, int], None] | None = None
        self.mouse_wheel_enabled = True

        super().__init__(**kwargs)

        self._date_state.register(self)

    # ── Delegate receiver ─────────────────────────────────────────────────────

    def on_display_changed(self) -> None:
        """_WheelPickerView changed the display — jump to the new page."""
        new_idx = self._date_state.display_month_index
        current_idx = self._origin_idx + round(self._offset)
        if current_idx == new_idx:
            return
        self._origin_idx = new_idx
        self._offset = 0.0
        self._snap_target = None
        self.set_needs_display()

    def on_selection_changed(self) -> None:
        """The selected day changed — redraw."""
        self.set_needs_display()

    # ── draw ─────────────────────────────────────────────────────────────────

    def draw(self):
        pw = self.width
        left_idx = math.floor(self._offset - 0.5)
        right_idx = math.ceil(self._offset + 0.5)
        for delta in range(left_idx, right_idx + 1):
            x0 = (delta - self._offset) * pw
            if x0 > pw or x0 + pw < 0:
                continue
            self._draw_month(x0, self._origin_idx + delta)

    def _draw_month(self, x0: float, idx):
        year, month = self._date_state.year_month_from_month_index(idx)

        sel = self._date_state.selected_date
        sel_y, sel_m, sel_d = sel.year, sel.month, sel.day
        today = self._today
        hov = self._hover

        for row_i, week in enumerate(calendar.monthcalendar(year, month)):
            for col_i, day in enumerate(week):
                if day == 0:
                    continue

                cx = x0 + col_i * _DAY_ITEM_SIZE + _DAY_ITEM_SIZE / 2
                cy = row_i * _DAY_ITEM_SIZE + _DAY_ITEM_SIZE / 2
                r = _DAY_ITEM_SIZE / 2 - 3

                is_today = (
                    day == today.day and month == today.month and year == today.year
                )
                is_selected = day == sel_d and month == sel_m and year == sel_y
                is_hovered = hov is not None and hov == (year, month, day)

                if is_selected:
                    set_color(_TINT_COLOR if is_today else _TINT_LIGHT_COLOR)
                    Path.oval(cx - r, cy - r, r * 2, r * 2).fill()
                elif is_hovered:
                    set_color(_TINT_HOVER_COLOR)
                    Path.oval(cx - r, cy - r, r * 2, r * 2).fill()

                if is_selected and is_today:
                    color, font = _TEXT_TODAY_SELECTED_COLOR, _FONT_BOLD
                elif is_selected:
                    color, font = _TINT_COLOR, _FONT_BOLD
                elif is_today:
                    color, font = _TINT_COLOR, _FONT_REGULAR
                else:
                    color, font = _TEXT_PRIMARY_COLOR, _FONT_REGULAR

                text = str(day)
                tw, th = measure_string(text, font=font)
                draw_string(
                    text,
                    rect=(cx - tw / 2, cy - th / 2, tw, th),
                    font=font,
                    color=color,
                    alignment=ALIGN_CENTER,
                )

    # ── touch ────────────────────────────────────────────────────────────────

    def touch_began(self, touch: Touch):
        self._touch_active = True
        self._is_dragging = False
        self._touch_start_x = touch.location[0]
        self._touch_start_y = touch.location[1]
        self._touch_start_offset = self._offset
        self._last_x = touch.location[0]
        self._last_t = time.monotonic()
        self._vel = 0.0
        self._snap_target = None
        self.update_interval = 1.0 / 60.0

        hit = self._day_at(touch.location[0], touch.location[1])
        self._hover = hit
        self.set_needs_display()

    def touch_moved(self, touch: Touch):
        if not self._touch_active:
            return
        x = touch.location[0]
        now = time.monotonic()
        dt = now - self._last_t
        pw = self.width

        dx = abs(x - self._touch_start_x)

        if not self._is_dragging and dx >= self._DRAG_THRESHOLD:
            self._is_dragging = True
            if self._hover is not None:
                self._hover = None
                self.set_needs_display()

        if self._is_dragging:
            self._offset = self._touch_start_offset + (self._touch_start_x - x) / pw
            if dt > 0.001:
                self._vel = (self._last_x - x) / pw / dt
            if self.on_offset_changed:
                self.on_offset_changed(self._offset)
            self.set_needs_display()

        self._last_x = x
        self._last_t = now

    def touch_ended(self, touch: Touch):
        if not self._touch_active:
            return
        self._touch_active = False
        self._hover = None

        if touch.phase == "cancelled":
            self.set_needs_display()
            self._snap_to(round(self._offset))
            return

        if not self._is_dragging:
            self.set_needs_display()
            self._snap_to(round(self._offset))
            self._handle_tap(touch.location[0], touch.location[1])
            return

        self.set_needs_display()
        target = round(self._offset + self._vel * 0.18)
        self._snap_to(float(target))

    def mouse_wheel(self, event: MouseWheel):
        dy = event.scroll_dy
        if dy > 0:
            self._snap_to(round(self._offset) + 1)
        if dy < 0:
            self._snap_to(round(self._offset) - 1)

    # ── snap ─────────────────────────────────────────────────────────────────

    def _snap_to(self, target: float):
        self._snap_target = target
        self._snap_start = self._offset
        self._snap_t0 = time.monotonic()
        self._vel = 0.0
        self.update_interval = 1.0 / 60.0

    def update(self):
        if self._snap_target is None:
            self.update_interval = 0.0
            return

        elapsed = time.monotonic() - self._snap_t0
        t = min(1.0, elapsed / self._SNAP_DUR)
        e = 1.0 - (1.0 - t) ** 3

        self._offset = self._snap_start + (self._snap_target - self._snap_start) * e

        if self.on_offset_changed:
            self.on_offset_changed(self._offset)
        self.set_needs_display()

        if t >= 1.0:
            self._offset = self._snap_target
            self._snap_target = None
            self.update_interval = 0.0
            year, month = self._date_state.year_month_from_month_index(
                self._origin_idx + int(round(self._offset))
            )
            if self.on_settled:
                self.on_settled(year, month)

    # ── hit test ─────────────────────────────────────────────────────────────

    def _day_at(self, x: float, y: float) -> tuple[int, int, int] | None:
        pw = self.width
        delta = round(self._offset + (x - pw / 2) / pw)
        year, month = self._date_state.year_month_from_month_index(
            self._origin_idx + delta
        )
        page_x0 = (delta - self._offset) * pw
        col_i = int((x - page_x0) / _DAY_ITEM_SIZE)
        row_i = int(y / _DAY_ITEM_SIZE)
        if not (0 <= col_i <= 6):
            return None
        weeks = calendar.monthcalendar(year, month)
        if row_i >= len(weeks):
            return None
        day = weeks[row_i][col_i]
        if day == 0:
            return None
        return year, month, day

    def _handle_tap(self, x: float, y: float):
        result = self._day_at(x, y)
        if result is None:
            return
        year, month, day = result
        self._date_state.set_selected(datetime(year, month, day), sender=self)


# ---------------------------------------------------------------------------
# _WheelPickerView
# ---------------------------------------------------------------------------


class _WheelState:
    def __init__(self, values, initial):
        self.values = list(values)
        self.total = len(self.values)
        self.middle_offset = self.total * 100
        initial_idx = self.values.index(initial) if initial in self.values else 0
        self.current_idx = float(self.middle_offset + initial_idx)
        self.velocity = 0.0
        self.is_dragging = False


class _WheelPickerView(View):
    def __init__(self, date_state: _DateState, /, **kwargs):
        self._date_state = date_state

        self.corner_radius = 16
        self.background_color = _BG_COLOR

        self._month_state = _WheelState(range(1, 13), date_state.display_month)
        self._year_state = _WheelState(range(1970, 2101), date_state.display_year)

        self._active_state: _WheelState | None = None
        self._last_y = 0.0
        self._last_t = 0.0
        self._was_moving = False  # used to detect the moment wheels settle

        self.mouse_wheel_enabled = True
        self.update_interval = 1 / 60
        super().__init__(**kwargs)

        self._date_state.register(self)

    # ── Delegate receiver ─────────────────────────────────────────────────────

    def on_display_changed(self) -> None:
        """_CalendarView changed the display — sync the wheels."""
        self._set_wheel_value(self._year_state, self._date_state.display_year)
        self._set_wheel_value(self._month_state, self._date_state.display_month)
        self.set_needs_display()

    def _set_wheel_value(self, state: _WheelState, value) -> None:
        if value not in state.values:
            return
        target_idx = state.values.index(value)
        current_base = round(state.current_idx) % state.total
        delta = (
            target_idx - current_base + state.total // 2
        ) % state.total - state.total // 2
        state.current_idx = round(state.current_idx) + delta
        state.velocity = 0.0

    def _commit_to_state(self) -> None:
        """Push current wheel values into the display state.
        sender=self ensures we don't receive our own notification back."""
        year_idx = round(self._year_state.current_idx) % self._year_state.total
        month_idx = round(self._month_state.current_idx) % self._month_state.total
        year = self._year_state.values[year_idx]
        month = self._month_state.values[month_idx]
        self._date_state.set_display(year, month, sender=self)

    def refresh(self) -> None:
        """Force-sync the wheels with the current display state."""
        self.on_display_changed()

    # ── update loop ───────────────────────────────────────────────────────────

    def update(self):
        moving = False
        for state in [self._year_state, self._month_state]:
            if state.is_dragging:
                moving = True
                continue
            if abs(state.velocity) > _PICKER_WHEEL_SNAP_VEL_TH:
                state.current_idx += state.velocity * 0.016
                state.velocity *= _PICKER_WHEEL_DECELERATION
                moving = True
            else:
                target = round(state.current_idx)
                diff = target - state.current_idx
                if abs(diff) > _PICKER_WHEEL_SNAP_EPSILON:
                    state.current_idx += diff * _PICKER_WHEEL_SNAP_SPEED
                    moving = True
                else:
                    state.current_idx = float(target)
                    state.velocity = 0.0

        self.set_needs_display()

        # Commit exactly once, at the transition from moving → settled
        if self._was_moving and not moving:
            self._commit_to_state()
        self._was_moving = moving

    # ── touch ────────────────────────────────────────────────────────────────

    def mouse_wheel(self, event: MouseWheel):
        if not self.mouse_wheel_enabled:
            return
        state = (
            self._year_state if event.location.x < self.width / 2 else self._month_state
        )
        state.current_idx = float(
            round(state.current_idx) + (-1 if event.scroll_dy > 0 else 1)
        )
        state.velocity = 0.0
        self._commit_to_state()
        self.set_needs_display()

    def touch_began(self, touch: Touch):
        if touch.location.x < self.width / 2:
            self._active_state = self._year_state
        else:
            self._active_state = self._month_state
        if self._active_state:
            self._active_state.is_dragging = True
            self._active_state.velocity = 0
            self._last_y = touch.location.y
            self._last_t = time.time()

    def touch_moved(self, touch: Touch):
        if not self._active_state:
            return
        dy = touch.location.y - self._last_y
        dt = max(time.time() - self._last_t, 0.001)
        self._active_state.current_idx -= dy / _PICKER_WHEEL_ITEM_HEIGHT
        self._active_state.velocity = -dy / _PICKER_WHEEL_ITEM_HEIGHT / dt * 0.3
        self._last_y = touch.location.y
        self._last_t = time.time()
        self.set_needs_display()

    def touch_ended(self, touch: Touch):
        if self._active_state:
            self._active_state.is_dragging = False
            self._active_state = None

    # ── draw ─────────────────────────────────────────────────────────────────

    def _draw_text(self, txt, x, y, sx, sy, opacity, bold):
        tw, th = measure_string(txt, font=_PICKER_ITEM_FONT)
        with GState():
            concat_ctm(Transform.translation(x, y))
            concat_ctm(Transform.scale(sx, sy))
            draw_string(
                txt,
                rect=(-tw / 2, -th / 2, tw, th),
                font=_PICKER_ITEM_FONT,
                alignment=ALIGN_CENTER,
                color=_WHEEL_TEXT_COLOR,
            )

    def _draw_wheel(self, state: _WheelState, center_x, mid_y, lens_path: Path):
        w, h = self.width, self.height
        if w == 0 or h == 0:
            return

        start_i = int(state.current_idx) - 4
        end_i = int(state.current_idx) + 5

        for i in range(start_i, end_i):
            val = state.values[i % state.total]
            txt = f"{val:02d}"
            dist = i - state.current_idx

            angle = dist * (_PICKER_WHEEL_ITEM_HEIGHT / (h * 0.45))
            if abs(angle) > math.pi / 2:
                continue

            y_pos = mid_y + math.sin(angle) * (h * 0.42)

            with GState():
                bg_mask = Path.rect(0, 0, w, h)
                bg_mask.append_path(lens_path)
                bg_mask.eo_fill_rule = True
                bg_mask.add_clip()
                self._draw_text(txt, center_x, y_pos, 1.0, math.cos(angle), 0.3, False)

            with GState():
                lens_path.add_clip()
                focus = 1.0 - min(1.0, abs(dist) * 0.8)
                mag = 1.0 + (_PICKER_MAGNIFICATION - 1.0) * focus
                self._draw_text(txt, center_x, y_pos, mag * 1.05, mag, 1.0, True)

    def draw(self):
        w, h = self.width, self.height
        if w == 0 or h == 0:
            return

        mid_y = h / 2
        lw = w * _PICKER_LENS_WIDTH_RATIO
        lx = (w - lw) / 2
        ly = mid_y - _PICKER_LENS_HEIGHT / 2
        lens_path = Path.rounded_rect(
            lx, ly, lw, _PICKER_LENS_HEIGHT, _PICKER_LENS_CORNER_RADIUS
        )

        self._draw_wheel(self._year_state, w * 0.3, mid_y, lens_path)
        self._draw_wheel(self._month_state, w * 0.7, mid_y, lens_path)

        with GState():
            for i in range(int(ly)):
                a = 0.85 * (1.0 - i / (h / 2.2))
                r, g, b, _ = _BG_COLOR
                set_color((r, g, b, a))
                fill_rect(0, i, w, 1)
                fill_rect(0, h - i - 1, w, 1)

            r, g, b, _ = _BG_COLOR_REVERSED
            set_color((r, g, b, 0.03))
            lens_path.fill()

            set_color((r, g, b, 0.08))
            lens_path.line_width = 0.5
            lens_path.stroke()


# ---------------------------------------------------------------------------
# _DatePickerHeader
# ---------------------------------------------------------------------------


class _DatePickerHeader(View):
    def __init__(self, on_prev: Callable, on_next: Callable, on_expand, **kwargs):
        super().__init__(**kwargs)
        pw = _DAY_ITEM_SIZE * 7

        self._expanded = False
        self._on_expand = on_expand

        self._title = ""
        self._title_btn = Button()
        self._title_btn.frame = (0, 0, pw - 2 * _DAY_ITEM_SIZE, _CALENDAR_HEADER_HEIGHT)
        self.add_subview(self._title_btn)
        self._title_btn.action = self._expand

        self._prev = Button()
        self._prev.title = "‹"
        self._prev.font = _BUTTON_FONT
        self._prev.frame = (
            pw - 2 * _DAY_ITEM_SIZE,
            0,
            _DAY_ITEM_SIZE,
            _CALENDAR_HEADER_HEIGHT,
        )
        self._prev.action = lambda _: on_prev()
        self.add_subview(self._prev)

        self._next = Button()
        self._next.title = "›"
        self._next.font = _BUTTON_FONT
        self._next.frame = (
            pw - _DAY_ITEM_SIZE,
            0,
            _DAY_ITEM_SIZE,
            _CALENDAR_HEADER_HEIGHT,
        )
        self._next.action = lambda _: on_next()
        self.add_subview(self._next)

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str):
        self._title = value
        self.set_needs_display()

    def _expand(self, sender: Button):
        self._expanded = not self._expanded
        if callable(self._on_expand):
            self._on_expand(self)
        self._prev.hidden = self._expanded
        self._next.hidden = self._expanded
        self.set_needs_display()

    def draw(self):
        expanded = self._expanded

        text = self._title
        color = _TINT_COLOR if expanded else _TEXT_PRIMARY_COLOR

        tw, th = measure_string(text, font=_FONT_BOLD)
        margin_y = (_CALENDAR_HEADER_HEIGHT - th) / 2
        draw_string(text, rect=(16, margin_y, tw, th), font=_FONT_BOLD, color=color)

        set_color(_TINT_COLOR)
        p = Path()
        p.line_width = 2
        p.line_cap_style = LINE_CAP_ROUND
        x, y = 16 + tw + 4, _CALENDAR_HEADER_HEIGHT / 2
        if expanded:
            p.move_to(x, y)
            p.line_to(x + 4, y + 4)
            p.line_to(x + 8, y)
        else:
            p.move_to(x, y - 4)
            p.line_to(x + 4, y)
            p.line_to(x, y + 4)
        p.stroke()

        if not expanded:
            _, h = measure_string("ANY", 0, _WEEKDAY_FONT, ALIGN_CENTER)
            for i, name in enumerate(_weekday_names()):
                draw_string(
                    name,
                    (
                        i * _DAY_ITEM_SIZE,
                        _CALENDAR_HEADER_HEIGHT + h / 2,
                        _DAY_ITEM_SIZE,
                        _WEEKDAY_HEADER_HEIGHT,
                    ),
                    _WEEKDAY_FONT,
                    _WEEKDAY_TEXT_COLOR,
                    ALIGN_CENTER,
                )


# ---------------------------------------------------------------------------
# LiquidDatePicker
# ---------------------------------------------------------------------------


class LiquidDatePicker(View):
    """
    Infinite horizontal month-paging date picker.

    Public API
    ----------
    date   : datetime — read / write; all components sync automatically
    action : Callable[[LiquidDatePicker]]
    """

    def __init__(self, date: datetime | None = None, **kwargs):
        super().__init__(**kwargs)
        self.background_color = _BG_COLOR
        self.corner_radius = 16

        self._date_state = _DateState(date)

        pw = _DAY_ITEM_SIZE * 7
        header_h = _CALENDAR_HEADER_HEIGHT + _WEEKDAY_HEADER_HEIGHT

        self._action: Callable | None = None

        self._header = _DatePickerHeader(
            on_prev=lambda: self._cal._snap_to(round(self._cal._offset) - 1),
            on_next=lambda: self._cal._snap_to(round(self._cal._offset) + 1),
            on_expand=self._on_expand,
        )
        self._header.frame = (0, 0, pw, header_h)
        self.add_subview(self._header)

        self._cal = _CalendarView(self._date_state)
        self._cal.frame = (0, header_h, pw, self._cal_height())
        self._cal.on_offset_changed = self._on_offset_changed
        self._cal.on_settled = self._on_settled
        self.add_subview(self._cal)

        self._year_picker = _WheelPickerView(self._date_state)
        self._year_picker.hidden = True
        self._year_picker.frame = (
            0,
            _CALENDAR_HEADER_HEIGHT,
            pw,
            self._cal_height() + _WEEKDAY_HEADER_HEIGHT,
        )
        self.add_subview(self._year_picker)

        self._date_state.register(self)

        self._header.title = self._date_state.month_name
        self._relayout()

    # ── Delegate receiver ─────────────────────────────────────────────────────

    def on_display_changed(self) -> None:
        """Display changed — update the header title."""
        self._header.title = self._date_state.month_name

    def on_selection_changed(self) -> None:
        """selected_date changed — invoke the external action callback."""
        if self._action is not None:
            self._action(self)

    def _on_expand(self, sender: _DatePickerHeader):
        calendar_view = sender._expanded
        self._cal.hidden = calendar_view
        self._year_picker.hidden = not calendar_view

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def date(self) -> datetime:
        return self._date_state.selected_date

    @date.setter
    def date(self, value: datetime) -> None:
        self._date_state.set_selected(value, sender=None)
        self._date_state.set_display(value.year, value.month, sender=None)

    @property
    def action(self) -> Callable | None:
        return self._action

    @action.setter
    def action(self, value: Callable | None):
        self._action = value

    # ── Internal ──────────────────────────────────────────────────────────────

    def _cal_height(self) -> float:
        return 6 * _DAY_ITEM_SIZE

    def _relayout(self):
        pw = _DAY_ITEM_SIZE * 7
        header_h = _CALENDAR_HEADER_HEIGHT + _WEEKDAY_HEADER_HEIGHT
        cal_h = self._cal_height()
        self._cal.height = cal_h
        self.frame = (self.frame[0], self.frame[1], pw, header_h + cal_h)

    def _on_offset_changed(self, offset: float):
        """_CalendarView swiped — update display. sender=self._cal so that
        _CalendarView does not receive its own notification back."""
        idx = self._cal._origin_idx + round(offset)
        self._date_state.set_display_from_index(idx, sender=self._cal)

    def _on_settled(self, year: int, month: int):
        """Snap finished — normalise _origin_idx and _offset."""
        settled_idx = self._date_state.display_month_index
        delta = settled_idx - self._cal._origin_idx
        self._cal._origin_idx = settled_idx
        self._cal._offset -= delta


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    picker = LiquidDatePicker()
    picker.action = lambda s: print(s.date)

    root = View()
    root.background_color = "grey"
    root.add_subview(picker)
    picker.frame = (0, 0, picker.width, picker.height)
    root.present("fullscreen")
