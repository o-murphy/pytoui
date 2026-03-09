from __future__ import annotations

import calendar
import locale
import math
import time
from datetime import datetime
from typing import TYPE_CHECKING, Callable, List, Literal, cast

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
from pytoui.ui._internals import _final_, get_ui_style
from pytoui.ui._types import Touch
from pytoui.ui._view import View

if TYPE_CHECKING:
    from pytoui.ui._types import MouseWheel

__all__ = ("DatePicker",)

# ---------------------------------------------------------------------------
# Mode constants
# ---------------------------------------------------------------------------

DATE_PICKER_MODE_TIME: Literal[0] = 0
DATE_PICKER_MODE_DATE: Literal[1] = 1
DATE_PICKER_MODE_DATE_AND_TIME: Literal[2] = 2

DatePickerMode = Literal[0, 1, 2]

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

if get_ui_style() == "light":
    _BG_COLOR = (1.0, 1.0, 1.0, 1.0)
    _BG_COLOR_REVERSED = (0.0, 0.0, 0.0, 1.0)
    _TEXT_PRIMARY_COLOR = (0.0, 0.0, 0.0, 1.0)
    _TEXT_TODAY_SELECTED_COLOR = (1.0, 1.0, 1.0, 1.0)
    _WEEKDAY_TEXT_COLOR = _BG_COLOR_REVERSED
    _WHEEL_TEXT_COLOR = (0.0, 0.0, 0.0, 1.0)
else:
    _BG_COLOR = (0.3, 0.3, 0.3, 1.0)
    _BG_COLOR_REVERSED = (0.7, 0.7, 0.7, 1.0)
    _TEXT_PRIMARY_COLOR = (1.0, 1.0, 1.0, 1.0)
    _TEXT_TODAY_SELECTED_COLOR = (1.0, 1.0, 1.0, 1.0)
    _WEEKDAY_TEXT_COLOR = _BG_COLOR_REVERSED
    _WHEEL_TEXT_COLOR = (0.7, 0.7, 0.7, 1.0)

# ---------------------------------------------------------------------------
# Layout / font constants
# ---------------------------------------------------------------------------

_DAY_ITEM_SIZE = 44
_CALENDAR_HEADER_HEIGHT = 48
_WEEKDAY_HEADER_HEIGHT = 24

_FONT_REGULAR = ("Helvetica Neue", 15)
_FONT_BOLD = ("Helvetica Neue Bold", 15)
_BUTTON_FONT = ("Helvetica Neue", 28)
_WEEKDAY_FONT = ("Helvetica Neue", 11)

_PICKER_WHEEL_ITEM_HEIGHT = 40
_PICKER_ITEM_FONT = ("Helvetica Neue", 18)
_PICKER_LENS_HEIGHT = 44
_PICKER_LENS_WIDTH_RATIO = 0.94
_PICKER_LENS_CORNER_RADIUS = 16
_PICKER_MAGNIFICATION = 1.35
_PICKER_WHEEL_SNAP_VEL_TH = 0.5
_PICKER_WHEEL_DECELERATION = 0.85
_PICKER_WHEEL_SNAP_SPEED = 0.35
_PICKER_WHEEL_SNAP_EPSILON = 0.005

# ---------------------------------------------------------------------------
# Locale helpers  (module-level, shared by all classes)
# ---------------------------------------------------------------------------


def _weekday_names() -> List[str]:
    try:
        locale.setlocale(locale.LC_TIME, "")
        return [datetime(2026, 1, i).strftime("%a").upper()[:3] for i in range(1, 8)]
    except Exception:
        return ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def _fmt_date(dt: datetime) -> str:
    """Date string in the current locale format (e.g. 09.03.2026 or 3/9/2026)."""
    try:
        locale.setlocale(locale.LC_TIME, "")
        return dt.strftime("%x")
    except Exception:
        return dt.strftime("%d.%m.%Y")


def _fmt_time(dt: datetime) -> str:
    """HH:MM honoring the locale's 12h/24h preference."""
    try:
        locale.setlocale(locale.LC_TIME, "")
        ref = datetime(2000, 1, 1, 13, 45)
        full = ref.strftime("%X")  # "13:45:00"  or  "1:45:00 PM"
        if "1:45" in full and "13" not in full:
            # 12-hour locale
            return f"{int(dt.strftime('%I'))}:{dt.minute:02d} {dt.strftime('%p')}"
        return f"{dt.hour:02d}:{dt.minute:02d}"
    except Exception:
        return f"{dt.hour:02d}:{dt.minute:02d}"


# ---------------------------------------------------------------------------
# _DateState
# ---------------------------------------------------------------------------


@_final_
class _DateState:
    """
    Central state shared by all picker components.

    selected_date — confirmed datetime (year/month/day/hour/minute).
                    Updated on day tap, time-wheel settle, or .date setter.
    display       — year/month/hour/minute currently browsed in the UI.
                    Updated while swiping the calendar or spinning wheels.

    Receivers implement on_display_changed() and/or on_selection_changed().
    Each notification skips the sender to avoid feedback loops.
    """

    def __init__(self, date: datetime | None = None):
        d = date or datetime.now()
        self._selected: datetime = d
        self._display_year: int = d.year
        self._display_month: int = d.month
        self._display_hour: int = d.hour
        self._display_minute: int = d.minute
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

    # ── display ───────────────────────────────────────────────────────────────

    @property
    def display_year(self) -> int:
        return self._display_year

    @property
    def display_month(self) -> int:
        return self._display_month

    @property
    def display_hour(self) -> int:
        return self._display_hour

    @property
    def display_minute(self) -> int:
        return self._display_minute

    @property
    def display_month_index(self) -> int:
        return self._display_year * 12 + (self._display_month - 1)

    # backwards compatibility
    @property
    def month_index(self) -> int:
        return self.display_month_index

    def set_display_date(self, year: int, month: int, sender: object = None) -> None:
        if year == self._display_year and month == self._display_month:
            return
        self._display_year = year
        self._display_month = month
        self._notify_display(sender)

    def set_display_time(self, hour: int, minute: int, sender: object = None) -> None:
        if hour == self._display_hour and minute == self._display_minute:
            return
        self._display_hour = hour
        self._display_minute = minute
        self._notify_display(sender)

    def set_display_from_index(self, idx: int, sender: object = None) -> None:
        year, month = self.year_month_from_index(idx)
        self.set_display_date(year, month, sender)

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
# _WheelState  —  scroll state for a single wheel column
# ---------------------------------------------------------------------------


@_final_
class _WheelState:
    def __init__(self, values, initial):
        self.values = list(values)
        self.total = len(self.values)
        self.middle_offset = self.total * 100
        initial_idx = self.values.index(initial) if initial in self.values else 0
        self.current_idx = float(self.middle_offset + initial_idx)
        self.velocity = 0.0
        self.is_dragging = False


# ---------------------------------------------------------------------------
# _BaseWheelView  —  shared rendering + physics for all wheel pickers
# ---------------------------------------------------------------------------


class _BaseWheelView(View):
    """
    Reusable base for drum-roll wheel pickers.

    Subclasses must implement:
      _all_states()      → list[_WheelState]
      _state_for_x(x)   → _WheelState
      _commit_to_state() → None
    """

    def __init__(self, **kwargs):
        self._active_state: _WheelState | None = None
        self._last_y = 0.0
        self._last_t = 0.0
        self._was_moving = False
        self.mouse_wheel_enabled = True
        self.update_interval = 1 / 60
        super().__init__(**kwargs)

    # ── Subclass interface ────────────────────────────────────────────────────

    def _all_states(self) -> list[_WheelState]:
        raise NotImplementedError

    def _state_for_x(self, x: float) -> _WheelState:
        raise NotImplementedError

    def _commit_to_state(self) -> None:
        raise NotImplementedError

    # ── Physics update ────────────────────────────────────────────────────────

    def update(self):
        moving = False
        for state in self._all_states():
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

        if self._was_moving and not moving:
            self._commit_to_state()
        self._was_moving = moving

    # ── Touch / scroll ────────────────────────────────────────────────────────

    def mouse_wheel(self, event: MouseWheel):
        if not self.mouse_wheel_enabled:
            return
        state = self._state_for_x(event.location.x)
        state.current_idx = float(
            round(state.current_idx) + (-1 if event.scroll_dy > 0 else 1)
        )
        state.velocity = 0.0
        self._commit_to_state()
        self.set_needs_display()

    def touch_began(self, touch: Touch):
        self._active_state = self._state_for_x(touch.location.x)
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

    # ── Shared helpers ────────────────────────────────────────────────────────

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

    # ── Shared rendering ──────────────────────────────────────────────────────

    def _draw_wheel_text(self, txt: str, x: float, y: float, sx: float, sy: float):
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

    def _draw_wheel(
        self, state: _WheelState, center_x: float, mid_y: float, lens_path: Path
    ):
        w, h = self.width, self.height
        if w == 0 or h == 0:
            return
        for i in range(int(state.current_idx) - 4, int(state.current_idx) + 5):
            val = state.values[i % state.total]
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
                self._draw_wheel_text(
                    f"{val:02d}", center_x, y_pos, 1.0, math.cos(angle)
                )

            with GState():
                lens_path.add_clip()
                focus = 1.0 - min(1.0, abs(dist) * 0.8)
                mag = 1.0 + (_PICKER_MAGNIFICATION - 1.0) * focus
                self._draw_wheel_text(f"{val:02d}", center_x, y_pos, mag * 1.05, mag)

    def _make_lens_path(self) -> Path:
        w, h = self.width, self.height
        lw = w * _PICKER_LENS_WIDTH_RATIO
        lx = (w - lw) / 2
        ly = h / 2 - _PICKER_LENS_HEIGHT / 2
        return Path.rounded_rect(
            lx, ly, lw, _PICKER_LENS_HEIGHT, _PICKER_LENS_CORNER_RADIUS
        )

    def _draw_wheel_chrome(self, lens_path: Path):
        """Fade bands above/below the lens + lens border."""
        w, h = self.width, self.height
        ly = h / 2 - _PICKER_LENS_HEIGHT / 2
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
# _CalendarView
# ---------------------------------------------------------------------------


@_final_
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

        self._date_state.register(self)
        super().__init__(**kwargs)

    # ── Delegate receivers ────────────────────────────────────────────────────

    def on_display_changed(self) -> None:
        new_idx = self._date_state.display_month_index
        if self._origin_idx + round(self._offset) == new_idx:
            return
        self._origin_idx = new_idx
        self._offset = 0.0
        self._snap_target = None
        self.set_needs_display()

    def on_selection_changed(self) -> None:
        self.set_needs_display()

    # ── draw ─────────────────────────────────────────────────────────────────

    def draw(self):
        pw = self.width
        for delta in range(
            math.floor(self._offset - 0.5), math.ceil(self._offset + 0.5) + 1
        ):
            x0 = (delta - self._offset) * pw
            if x0 > pw or x0 + pw < 0:
                continue
            self._draw_month(x0, self._origin_idx + delta)

    def _draw_month(self, x0: float, idx: int):
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
                cr = _DAY_ITEM_SIZE / 2 - 3

                is_today = (
                    day == today.day and month == today.month and year == today.year
                )
                is_selected = day == sel_d and month == sel_m and year == sel_y
                is_hovered = hov is not None and hov == (year, month, day)

                r, g, b, a = self.tint_color
                if is_selected:
                    set_color((r, g, b, a if is_today else 0.25))
                    Path.oval(cx - cr, cy - cr, cr * 2, cr * 2).fill()
                elif is_hovered:
                    set_color((r, g, b, 0.08))
                    Path.oval(cx - cr, cy - cr, cr * 2, cr * 2).fill()

                if is_selected and is_today:
                    color, font = _TEXT_TODAY_SELECTED_COLOR, _FONT_BOLD
                elif is_selected:
                    color, font = self.tint_color, _FONT_BOLD
                elif is_today:
                    color, font = self.tint_color, _FONT_REGULAR
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
        self._hover = self._day_at(touch.location[0], touch.location[1])
        self.set_needs_display()

    def touch_moved(self, touch: Touch):
        if not self._touch_active:
            return
        x = touch.location[0]
        now = time.monotonic()
        dt = now - self._last_t
        pw = self.width

        if (
            not self._is_dragging
            and abs(x - self._touch_start_x) >= self._DRAG_THRESHOLD
        ):
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
        self.set_needs_display()

        if touch.phase == "cancelled" or not self._is_dragging:
            self._snap_to(round(self._offset))
            if not self._is_dragging and touch.phase != "cancelled":
                self._handle_tap(touch.location[0], touch.location[1])
            return

        self._snap_to(float(round(self._offset + self._vel * 0.18)))

    def mouse_wheel(self, event: MouseWheel):
        if event.scroll_dy > 0:
            self._snap_to(round(self._offset) + 1)
        elif event.scroll_dy < 0:
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
        self._offset = self._snap_start + (self._snap_target - self._snap_start) * (
            1.0 - (1.0 - t) ** 3
        )

        if self.on_offset_changed:
            self.on_offset_changed(self._offset)
        self.set_needs_display()

        if t >= 1.0:
            self._offset = self._snap_target
            self._snap_target = None
            self.update_interval = 0.0
            if self.on_settled:
                year, month = self._date_state.year_month_from_month_index(
                    self._origin_idx + int(round(self._offset))
                )
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
        return None if day == 0 else (year, month, day)

    def _handle_tap(self, x: float, y: float):
        result = self._day_at(x, y)
        if result is None:
            return
        year, month, day = result
        self._date_state.set_selected(
            self._date_state.selected_date.replace(year=year, month=month, day=day),
            sender=self,
        )


# ---------------------------------------------------------------------------
# _WheelPickerView  —  year / month wheels (used inside LiquidDatePicker)
# ---------------------------------------------------------------------------


@_final_
class _WheelPickerView(_BaseWheelView):
    def __init__(self, date_state: _DateState, /, **kwargs):
        self._date_state = date_state
        self._year_state = _WheelState(range(1970, 2101), date_state.display_year)
        self._month_state = _WheelState(range(1, 13), date_state.display_month)
        self.corner_radius = 16
        self.background_color = _BG_COLOR
        self._date_state.register(self)
        super().__init__(**kwargs)

    def _all_states(self) -> list[_WheelState]:
        return [self._year_state, self._month_state]

    def _state_for_x(self, x: float) -> _WheelState:
        return self._year_state if x < self.width / 2 else self._month_state

    def _commit_to_state(self) -> None:
        year = self._year_state.values[
            round(self._year_state.current_idx) % self._year_state.total
        ]
        month = self._month_state.values[
            round(self._month_state.current_idx) % self._month_state.total
        ]
        self._date_state.set_display_date(year, month, sender=self)

    def on_display_changed(self) -> None:
        self._set_wheel_value(self._year_state, self._date_state.display_year)
        self._set_wheel_value(self._month_state, self._date_state.display_month)
        self.set_needs_display()

    def refresh(self) -> None:
        self.on_display_changed()

    def draw(self):
        w, h = self.width, self.height
        if w == 0 or h == 0:
            return
        lens = self._make_lens_path()
        self._draw_wheel(self._year_state, w * 0.3, h / 2, lens)
        self._draw_wheel(self._month_state, w * 0.7, h / 2, lens)
        self._draw_wheel_chrome(lens)


# ---------------------------------------------------------------------------
# _LiquidTimePicker  —  hour / minute wheels
# ---------------------------------------------------------------------------


@_final_
class _LiquidTimePicker(_BaseWheelView):
    def __init__(self, date_state: _DateState, /, **kwargs):
        self._date_state = date_state
        self._hour_state = _WheelState(range(0, 24), date_state.display_hour)
        self._minute_state = _WheelState(range(0, 60), date_state.display_minute)
        self.corner_radius = 16
        self.background_color = _BG_COLOR
        self.frame = (0, 0, 200, 200)
        self._date_state.register(self)
        super().__init__(**kwargs)

    def _all_states(self) -> list[_WheelState]:
        return [self._hour_state, self._minute_state]

    def _state_for_x(self, x: float) -> _WheelState:
        return self._hour_state if x < self.width / 2 else self._minute_state

    def _commit_to_state(self) -> None:
        hour = self._hour_state.values[
            round(self._hour_state.current_idx) % self._hour_state.total
        ]
        minute = self._minute_state.values[
            round(self._minute_state.current_idx) % self._minute_state.total
        ]
        self._date_state.set_display_time(hour, minute, sender=self)
        self._date_state.set_selected(
            self._date_state.selected_date.replace(hour=hour, minute=minute),
            sender=self,
        )

    def on_display_changed(self) -> None:
        self._set_wheel_value(self._hour_state, self._date_state.display_hour)
        self._set_wheel_value(self._minute_state, self._date_state.display_minute)
        self.set_needs_display()

    def on_selection_changed(self) -> None:
        sel = self._date_state.selected_date
        self._set_wheel_value(self._hour_state, sel.hour)
        self._set_wheel_value(self._minute_state, sel.minute)
        self.set_needs_display()

    def refresh(self) -> None:
        self.on_display_changed()

    def draw(self):
        w, h = self.width, self.height
        if w == 0 or h == 0:
            return
        lens = self._make_lens_path()
        self._draw_wheel(self._hour_state, w * 0.3, h / 2, lens)
        self._draw_wheel(self._minute_state, w * 0.7, h / 2, lens)
        self._draw_wheel_chrome(lens)


# ---------------------------------------------------------------------------
# _DatePickerHeader
# ---------------------------------------------------------------------------


@_final_
class _DatePickerHeader(View):
    def __init__(self, on_prev: Callable, on_next: Callable, on_expand, **kwargs):
        pw = _DAY_ITEM_SIZE * 7

        self._expanded = False
        self._on_expand = on_expand
        self._title = ""

        self._title_btn = Button()
        self._title_btn.frame = (0, 0, pw - 2 * _DAY_ITEM_SIZE, _CALENDAR_HEADER_HEIGHT)
        self._title_btn.action = self._expand
        self.add_subview(self._title_btn)

        self._prev = Button(title="‹", font=_BUTTON_FONT)
        self._prev.frame = (
            pw - 2 * _DAY_ITEM_SIZE,
            0,
            _DAY_ITEM_SIZE,
            _CALENDAR_HEADER_HEIGHT,
        )
        self._prev.action = lambda _: on_prev()
        self.add_subview(self._prev)

        self._next = Button(title="›", font=_BUTTON_FONT)
        self._next.frame = (
            pw - _DAY_ITEM_SIZE,
            0,
            _DAY_ITEM_SIZE,
            _CALENDAR_HEADER_HEIGHT,
        )
        self._next.action = lambda _: on_next()
        self.add_subview(self._next)
        super().__init__(**kwargs)

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
        tw, th = measure_string(self._title, font=_FONT_BOLD)
        draw_string(
            self._title,
            rect=(16, (_CALENDAR_HEADER_HEIGHT - th) / 2, tw, th),
            font=_FONT_BOLD,
            color=self.tint_color if self._expanded else _TEXT_PRIMARY_COLOR,
        )

        set_color(self.tint_color)
        p = Path()
        p.line_width = 2
        p.line_cap_style = LINE_CAP_ROUND
        x, y = 16 + tw + 4, _CALENDAR_HEADER_HEIGHT / 2
        if self._expanded:
            p.move_to(x, y)
            p.line_to(x + 4, y + 4)
            p.line_to(x + 8, y)
        else:
            p.move_to(x, y - 4)
            p.line_to(x + 4, y)
            p.line_to(x, y + 4)
        p.stroke()

        if not self._expanded:
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


@_final_
class _LiquidDatePicker(View):
    """
    Infinite horizontal month-paging date picker.

    Public API
    ----------
    date : datetime — read / write; all components sync automatically
    """

    def __init__(self, date_state: _DateState, **kwargs):
        self.background_color = _BG_COLOR
        self.corner_radius = 16

        self._date_state = date_state

        pw = _DAY_ITEM_SIZE * 7
        header_h = _CALENDAR_HEADER_HEIGHT + _WEEKDAY_HEADER_HEIGHT

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
        super().__init__(**kwargs)

    # ── Delegate receivers ────────────────────────────────────────────────────

    def on_display_changed(self) -> None:
        self._header.title = self._date_state.month_name

    def _on_expand(self, sender: _DatePickerHeader):
        self._cal.hidden = sender._expanded
        self._year_picker.hidden = not sender._expanded

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def date(self) -> datetime:
        return self._date_state.selected_date

    @date.setter
    def date(self, value: datetime) -> None:
        self._date_state.set_selected(value, sender=None)
        self._date_state.set_display_date(value.year, value.month, sender=None)

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
        idx = self._cal._origin_idx + round(offset)
        self._date_state.set_display_from_index(idx, sender=self._cal)

    def _on_settled(self, year: int, month: int):
        settled_idx = self._date_state.display_month_index
        delta = settled_idx - self._cal._origin_idx
        self._cal._origin_idx = settled_idx
        self._cal._offset -= delta


# ---------------------------------------------------------------------------
# _PopupOverlay  —  full-screen transparent tap-to-dismiss wrapper
# ---------------------------------------------------------------------------


@_final_
class _PopupOverlay(View):
    """
    Full-screen transparent overlay — sits as the topmost subview on root.
    Intercepts all touches and routes them:

      began inside  popup       → track → redirect moved/ended to popup
      began inside  date_picker → track → redirect moved/ended to date_picker
      began outside both        → track → dismiss on ended

    Coordinates in touch.location are in root (overlay) space.
    Redirected touches are re-created with coords translated into the
    target view's local space.
    """

    def __init__(
        self, on_dismiss: Callable[[], None], popup: View, date_picker: View, **kwargs
    ):
        self._on_dismiss = on_dismiss
        self._popup = popup
        self._date_picker = date_picker
        self._target: View | None = None
        r, g, b, _ = _BG_COLOR
        self.background_color = (r, g, b, 0.5)
        super().__init__(**kwargs)

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _screen_xy(v: View) -> tuple[float, float]:
        """Absolute (root/screen) origin of v by walking up the superview chain."""
        x, y = v.x, v.y
        p = v.superview
        while p is not None and p.superview is not None:
            x += p.x
            y += p.y
            p = p.superview
        return x, y

    @classmethod
    def _hit(cls, v: View, x: float, y: float) -> bool:
        vx, vy = cls._screen_xy(v)
        return vx <= x < vx + v.width and vy <= y < vy + v.height

    @classmethod
    def _translate(cls, touch: Touch, v: View) -> Touch:
        ox, oy = cls._screen_xy(v)
        return Touch(
            location=(touch.location[0] - ox, touch.location[1] - oy),
            phase=touch.phase,
            prev_location=(touch.prev_location[0] - ox, touch.prev_location[1] - oy),
            timestamp=touch.timestamp,
            touch_id=touch.touch_id,
        )

    def _find_target(self, v: View, x: float, y: float) -> View | None:
        return self._hit_test_recursive(v, x, y)

    @classmethod
    def _hit_test_recursive(cls, v: View, x: float, y: float) -> View | None:
        if getattr(v, "hidden", False) or not getattr(v, "touch_enabled", True):
            return None
        vx, vy = cls._screen_xy(v)
        if not (vx <= x < vx + v.width and vy <= y < vy + v.height):
            return None

        for child in reversed(list(v.subviews)):
            target = cls._hit_test_recursive(cast(View, child), x, y)
            if target is not None:
                return target
        return v

    def _dispatch(self, method: str, touch: Touch) -> None:
        if self._target is None:
            return
        fn = getattr(self._target, method, None)
        if callable(fn):
            fn(self._translate(touch, self._target))

    # ── touch routing ─────────────────────────────────────────────────────────

    def touch_began(self, touch: Touch):
        x, y = touch.location[0], touch.location[1]
        if self._hit(self._date_picker, x, y):
            self._target = (
                self._find_target(self._date_picker, x, y) or self._date_picker
            )
        elif self._hit(self._popup, x, y):
            self._target = self._find_target(self._popup, x, y) or self._popup
        else:
            self._target = None
        self._dispatch("touch_began", touch)

    def touch_moved(self, touch: Touch):
        self._dispatch("touch_moved", touch)

    def touch_ended(self, touch: Touch):
        if self._target is None:
            self._on_dismiss()
        else:
            self._dispatch("touch_ended", touch)
        self._target = None


# ---------------------------------------------------------------------------
# DatePicker  —  compact button bar that spawns popups
# ---------------------------------------------------------------------------


@_final_
class DatePicker(View):
    """
    Compact date/time picker showing one or two buttons depending on mode.

    mode
    ----
    DATE_PICKER_MODE_TIME          — time button only
    DATE_PICKER_MODE_DATE          — date button only
    DATE_PICKER_MODE_DATE_AND_TIME — both buttons (default)
    """

    __slots__ = (
        "_mode",
        "_enabled",
        "_date_state",
        "_popup",
        "_overlay",
        "_date_btn",
        "_time_btn",
    )

    _GAP = 8
    _DATE_W = 150
    _TIME_W = 65
    _H = 44

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self._mode: DatePickerMode = (DATE_PICKER_MODE_DATE_AND_TIME,)
        self._enabled: bool = True

        self._date_state = _DateState()
        self._popup: View | None = None
        self._overlay: _PopupOverlay | None = None

        btn_kw = {
            "tint_color": _TEXT_PRIMARY_COLOR,
            "background_color": _BG_COLOR,
            "corner_radius": 16,
        }

        self._date_btn = Button(
            title=_fmt_date(self._date_state.date),
            action=self._date_action,
            **btn_kw,
        )

        self._time_btn = Button(
            title=_fmt_time(self._date_state.date),
            action=self._time_action,
            **btn_kw,
        )

        self.add_subview(self._date_btn)
        self.add_subview(self._time_btn)

        self._date_state.register(self)
        self._apply_mode()

        super().__init__(*args, **kwargs)

    # ── mode ─────────────────────────────────────────────────────────────────

    @property
    def mode(self) -> DatePickerMode:
        return self._mode

    @mode.setter
    def mode(self, value: DatePickerMode) -> None:
        if value == self._mode:
            return
        self._mode = value
        self._close_popup()
        self._apply_mode()

    def _apply_mode(self) -> None:
        show_date = self._mode in (
            DATE_PICKER_MODE_DATE,
            DATE_PICKER_MODE_DATE_AND_TIME,
        )
        show_time = self._mode in (
            DATE_PICKER_MODE_TIME,
            DATE_PICKER_MODE_DATE_AND_TIME,
        )

        self._date_btn.hidden = not show_date
        self._time_btn.hidden = not show_time

        if show_date and show_time:
            total_w = self._DATE_W + self._GAP + self._TIME_W
            self._date_btn.frame = (0, 0, self._DATE_W, self._H)
            self._time_btn.frame = (self._DATE_W + self._GAP, 0, self._TIME_W, self._H)
        elif show_date:
            total_w = self._DATE_W
            self._date_btn.frame = (0, 0, self._DATE_W, self._H)
        else:
            total_w = self._TIME_W
            self._time_btn.frame = (0, 0, self._TIME_W, self._H)

        self.width = total_w
        self.height = self._H

    # ── Delegate receivers ────────────────────────────────────────────────────

    def on_selection_changed(self) -> None:
        sel = self._date_state.selected_date
        self._date_btn.title = _fmt_date(sel)
        self._time_btn.title = _fmt_time(sel)

    # ── popup helpers ─────────────────────────────────────────────────────────

    def _close_popup(self):
        self._date_btn.tint_color = _TEXT_PRIMARY_COLOR
        self._time_btn.tint_color = _TEXT_PRIMARY_COLOR
        if self._overlay and self._overlay.superview:
            self._overlay.superview.remove_subview(self._overlay)
        self._overlay = None
        self._popup = None

    def _push_popup(self):
        root = self
        while root.superview:
            root = root.superview
        self._popup.center = (root.width / 2, root.height / 2)
        self._overlay = _PopupOverlay(
            on_dismiss=self._close_popup,
            popup=self._popup,
            date_picker=self,
            tint_color=self.tint_color,
        )
        self._overlay.frame = (0, 0, root.width, root.height)
        self._overlay.flex = "WH"

        self._overlay.add_subview(self._popup)
        root.add_subview(self._overlay)

    def _date_action(self, sender: Button):
        should_open = not isinstance(self._popup, _LiquidDatePicker)
        self._close_popup()
        if should_open:
            self._popup = _LiquidDatePicker(self._date_state)
            self._push_popup()
            self._date_btn.tint_color = self.tint_color

    def _time_action(self, sender: Button):
        should_open = not isinstance(self._popup, _LiquidTimePicker)
        self._close_popup()
        if should_open:
            self._popup = _LiquidTimePicker(self._date_state)
            self._push_popup()
            self._time_btn.tint_color = self.tint_color

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def date(self) -> datetime:
        return self._date_state.date

    @date.setter
    def date(self, value: datetime | None):
        v = value or datetime.now()
        self._date_state.date = v
        self._date_state.set_display_date(v.year, v.month, sender=None)
        self._date_state.set_display_time(v.hour, v.minute, sender=None)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    dp = DatePicker(mode=DATE_PICKER_MODE_DATE_AND_TIME)
    dp.tint_color = "red"

    root = View()
    root.frame = (0, 0, 400, 600)
    root.add_subview(dp)
    root.present("fullscreen")
