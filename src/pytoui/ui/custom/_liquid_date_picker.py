from __future__ import annotations

import calendar
import locale
import math
from datetime import datetime
from typing import TYPE_CHECKING, Callable, List

from pytoui.ui._button import Button
from pytoui.ui._constants import ALIGN_CENTER
from pytoui.ui._draw import measure_string
from pytoui.ui._internals import _final_
from pytoui.ui._label import Label
from pytoui.ui._scroll_view import ScrollView
from pytoui.ui._view import View

if TYPE_CHECKING:
    from pytoui.ui._types import _Action

__all__ = ("LiquidDatePicker",)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IOS_BLUE = (0.0, 122 / 255, 1.0, 1.0)
IOS_BLUE_ALPHA = (0.0, 122 / 255, 1.0, 0.4)
TRANSPARENT_WHITE = (1.0, 1.0, 1.0, 0.9)

DAY_SIZE = 42
HEADER_HEIGHT = 42
WEEKDAY_HEIGHT = 24

_CENTER_PAGE = 1

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _month_offset(year: int, month: int, delta: int) -> tuple[int, int]:
    q, r = divmod((year - 1) * 12 + (month - 1) + delta, 12)
    return q + 1, r + 1


def _month_name(year: int, month: int) -> str:
    try:
        locale.setlocale(locale.LC_TIME, "")
        return datetime(year, month, 1).strftime("%B %Y").capitalize()
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
        return f"{NAMES[month - 1]} {year}"


def _weekday_names() -> List[str]:
    try:
        locale.setlocale(locale.LC_TIME, "")
        return [datetime(2026, 1, i).strftime("%a").upper() for i in range(1, 8)]
    except Exception:
        return ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


# ---------------------------------------------------------------------------
# _DayView
# ---------------------------------------------------------------------------


class _DayView(View):
    def __init__(self, day: int, **kwargs):
        super().__init__(**kwargs)
        self.day = day
        self.is_today = False
        self.is_current_month = False
        self._selected = False

        self._button = Button()
        self._button.title = str(day) if day > 0 else ""
        self._button.corner_radius = DAY_SIZE / 2
        self._button.frame = (0, 0, DAY_SIZE, DAY_SIZE)
        self.add_subview(self._button)

        self.hidden = day <= 0
        self._apply_style()

    @property
    def action(self) -> Callable | None:
        return self._button.action

    @action.setter
    def action(self, value: Callable | None):
        self._button.action = value

    @property
    def is_selected(self) -> bool:
        return self._selected

    @is_selected.setter
    def is_selected(self, value: bool):
        if self._selected == bool(value):
            return
        self._selected = bool(value)
        self._apply_style()
        self.set_needs_display()

    def _apply_style(self):
        if self._selected:
            self._button.font = ("<system-bold>", 14)
            if self.is_today:
                self._button.background_color = IOS_BLUE
                self._button.tint_color = "white"
            else:
                self._button.background_color = IOS_BLUE_ALPHA
                self._button.tint_color = IOS_BLUE
        else:
            self._button.font = ("<s>", 14)
            self._button.tint_color = IOS_BLUE if self.is_today else "black"
            self._button.background_color = "transparent"


# ---------------------------------------------------------------------------
# _WeekRow
# ---------------------------------------------------------------------------


class _WeekRow(View):
    def __init__(self, days: List[int], month: int, year: int, **kwargs):
        super().__init__(**kwargs)
        self.month = month
        self.year = year
        self._day_views: List[_DayView] = []

        today = datetime.now()
        for i, day in enumerate(days):
            dv = _DayView(day)
            dv.is_current_month = day > 0
            dv.is_today = (
                day == today.day and month == today.month and year == today.year
            )
            self.add_subview(dv)
            dv.frame = (i * DAY_SIZE, 0, DAY_SIZE, DAY_SIZE)
            self._day_views.append(dv)

    def layout(self):
        for i, dv in enumerate(self._day_views):
            dv.frame = (i * DAY_SIZE, 0, DAY_SIZE, DAY_SIZE)

    def select_day(self, day: int) -> bool:
        found = False
        for dv in self._day_views:
            hit = dv.day == day and dv.is_current_month
            dv.is_selected = hit
            found = found or hit
        return found

    def clear_selection(self):
        for dv in self._day_views:
            dv.is_selected = False


# ---------------------------------------------------------------------------
# _MonthPage
# ---------------------------------------------------------------------------


class _MonthPage(View):
    def __init__(self, year: int, month: int, **kwargs):
        super().__init__(**kwargs)
        self.year = year
        self.month = month
        self._weeks: List[_WeekRow] = []
        self._build_weeks()

    def _build_weeks(self):
        for week in self._weeks:
            self.remove_subview(week)
        self._weeks.clear()
        w = DAY_SIZE * 7
        for i, week_days in enumerate(calendar.monthcalendar(self.year, self.month)):
            row = _WeekRow(week_days, self.month, self.year)
            self.add_subview(row)
            row.frame = (0, i * DAY_SIZE, w, DAY_SIZE)
            self._weeks.append(row)

    def reassign(self, year: int, month: int):
        self.year = year
        self.month = month
        self._build_weeks()

    def layout(self):
        w = DAY_SIZE * 7
        for i, week in enumerate(self._weeks):
            week.frame = (0, i * DAY_SIZE, w, DAY_SIZE)

    def select_day(self, day: int) -> bool:
        return any(week.select_day(day) for week in self._weeks)

    def clear_selection(self):
        for week in self._weeks:
            week.clear_selection()

    def iter_buttons(self):
        for week in self._weeks:
            yield from week._day_views


# ---------------------------------------------------------------------------
# _DatePickerHeader
# ---------------------------------------------------------------------------


@_final_
class _DatePickerHeader(View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._title_btn = Button()
        self._title_btn.tint_color = "black"
        self._title_btn.font = ("<s>", 16)
        self.add_subview(self._title_btn)

        self._prev_btn = Button(title="<")
        self._prev_btn.font = ("<system-bold>", 24)
        self._prev_btn.flex = "L"
        self.add_subview(self._prev_btn)

        self._next_btn = Button(title=">")
        self._next_btn.font = ("<system-bold>", 24)
        self._next_btn.flex = "L"
        self.add_subview(self._next_btn)

        self._weekday_labels: List[Label] = []
        for name in _weekday_names():
            lbl = Label()
            lbl.alignment = ALIGN_CENTER
            lbl.font = ("<s>", 12)
            lbl.text = name
            lbl.alpha = 0.7
            self._weekday_labels.append(lbl)
            self.add_subview(lbl)

    @property
    def title(self) -> str:
        return self._title_btn.title

    @title.setter
    def title(self, value: str):
        self._title_btn.title = value
        text_w, _ = measure_string(self._title_btn.title, 0, self._title_btn.font)
        self._title_btn.frame = (0, 0, math.ceil(text_w) + 16, HEADER_HEIGHT)

    def layout(self):
        w = self.width
        self._prev_btn.frame = (w - 2 * DAY_SIZE, 0, DAY_SIZE, HEADER_HEIGHT)
        self._next_btn.frame = (w - DAY_SIZE, 0, DAY_SIZE, HEADER_HEIGHT)

        for i, lbl in enumerate(self._weekday_labels):
            lbl.frame = (i * DAY_SIZE, HEADER_HEIGHT, DAY_SIZE, WEEKDAY_HEIGHT)


# ---------------------------------------------------------------------------
# _PagingDelegate
# ---------------------------------------------------------------------------


class _PagingDelegate:
    def __init__(self, picker: "LiquidDatePicker"):
        self._picker = picker
        self._snapping = False
        self._prev_offset_x = float(_CENTER_PAGE * DAY_SIZE * 7)
        self._settled_page = _CENTER_PAGE
        self.was_dragging = False

    def scrollview_did_scroll(self, sv=None):
        if self._snapping:
            return

        picker = self._picker
        page_w = DAY_SIZE * 7
        offset_x = picker._scroll.content_offset.x

        self.was_dragging = True

        page = round(offset_x / page_w)
        y, m = _month_offset(
            picker._current_year, picker._current_month, page - _CENTER_PAGE
        )
        picker._header.title = _month_name(y, m)

        prev_x, self._prev_offset_x = self._prev_offset_x, offset_x

        if abs(offset_x - page * page_w) > 3:
            return
        if abs(offset_x - prev_x) > 0.5:
            return

        self.was_dragging = False

        if page == self._settled_page:
            return
        self._settled_page = page

        picker._refresh_selection()

        if page == _CENTER_PAGE:
            return

        delta = page - _CENTER_PAGE
        picker._current_year, picker._current_month = _month_offset(
            picker._current_year, picker._current_month, delta
        )
        picker._cycle_pages()
        picker._refresh_selection()
        self._settled_page = _CENTER_PAGE


# ---------------------------------------------------------------------------
# LiquidDatePicker
# ---------------------------------------------------------------------------


@_final_
class LiquidDatePicker(View):
    """
    Infinite horizontal month-paging date picker.

    Public API
    ----------
    date               : datetime   -- get / set the selected date
    set_day_action(fn)              -- fn(day_view: _DayView) on tap
    """

    def __init__(self, date: datetime | None = None, **kwargs):
        super().__init__(**kwargs)
        self.background_color = TRANSPARENT_WHITE
        self.corner_radius = 16

        d = date or datetime.now()
        self._current_year = d.year
        self._current_month = d.month
        self._sel_year = d.year
        self._sel_month = d.month
        self._sel_day = d.day
        self._action: _Action | None = None

        self._header = _DatePickerHeader()
        self._header._prev_btn.action = lambda _: self._navigate(-1)
        self._header._next_btn.action = lambda _: self._navigate(+1)
        self.add_subview(self._header)

        self._pages: List[_MonthPage] = [
            _MonthPage(*_month_offset(self._current_year, self._current_month, off))
            for off in (-1, 0, 1)
        ]

        self._scroll = ScrollView()
        self._scroll.bounces = True
        self._scroll.paging_enabled = True
        self._scroll.shows_horizontal_scroll_indicator = False
        self._scroll.delegate = _PagingDelegate(self)
        self.add_subview(self._scroll)

        for page in self._pages:
            self._scroll.add_subview(page)

        self._header.title = _month_name(self._current_year, self._current_month)
        self._refresh_selection()
        self.layout()

    @property
    def date(self) -> datetime:
        return datetime(self._sel_year, self._sel_month, self._sel_day)

    @date.setter
    def date(self, value: datetime):
        self._sel_year = value.year
        self._sel_month = value.month
        self._sel_day = value.day
        self._current_year = value.year
        self._current_month = value.month
        self._header.title = _month_name(value.year, value.month)
        self._cycle_pages()
        self._refresh_selection()

    @property
    def action(self) -> _Action | None:
        return self._action

    @action.setter
    def action(self, action: _Action | None):
        self._action = action
        self._attach_actions()

    def layout(self):
        page_w = DAY_SIZE * 7
        header_h = HEADER_HEIGHT + WEEKDAY_HEIGHT
        grid_h = (
            len(calendar.monthcalendar(self._current_year, self._current_month))
            * DAY_SIZE
        )

        self._header.frame = (0, 0, page_w, header_h)
        self._scroll.frame = (0, header_h, page_w, grid_h)
        self._scroll.content_size = (page_w * 3, grid_h)
        self._scroll.content_offset = (_CENTER_PAGE * page_w, 0)

        for i, page in enumerate(self._pages):
            page.frame = (i * page_w, 0, page_w, grid_h)

        self.frame = (self.frame.x, self.frame.y, page_w, header_h + grid_h)

    def _navigate(self, delta: int):
        self._current_year, self._current_month = _month_offset(
            self._current_year, self._current_month, delta
        )
        self._header.title = _month_name(self._current_year, self._current_month)
        self._cycle_pages()
        self._refresh_selection()
        self.frame = self.frame

    def _cycle_pages(self):
        page_w = DAY_SIZE * 7
        delegate = self._scroll.delegate

        if isinstance(delegate, _PagingDelegate):
            delegate._snapping = True

        grid_h = (
            len(calendar.monthcalendar(self._current_year, self._current_month))
            * DAY_SIZE
        )
        for i, offset in enumerate((-1, 0, 1)):
            y, m = _month_offset(self._current_year, self._current_month, offset)
            page = self._pages[i]
            page.reassign(y, m)
            page.frame = (i * page_w, 0, page_w, grid_h)

        if hasattr(self._scroll, "_internals_"):
            self._scroll._internals_._stop()
        self._scroll.content_offset = (_CENTER_PAGE * page_w, 0.0)

        if self._action is not None:
            self._attach_actions()

        if isinstance(delegate, _PagingDelegate):
            delegate._snapping = False
            delegate._settled_page = _CENTER_PAGE
            delegate._prev_offset_x = float(_CENTER_PAGE * page_w)
            delegate.was_dragging = False

    def _refresh_selection(self):
        for page in self._pages:
            page.clear_selection()
            if page.year == self._sel_year and page.month == self._sel_month:
                page.select_day(self._sel_day)

    def _attach_actions(self):
        for page in self._pages:
            for dv in page.iter_buttons():
                dv.action = self._make_tap_handler(dv, page)

    def _make_tap_handler(self, dv: _DayView, page: _MonthPage) -> Callable:
        def handler(_sender):
            if dv.day <= 0:
                return
            delegate = self._scroll.delegate
            if isinstance(delegate, _PagingDelegate):
                if delegate.was_dragging or delegate._snapping:
                    return
            for p in self._pages:
                p.clear_selection()
            dv.is_selected = True
            self._sel_year = page.year
            self._sel_month = page.month
            self._sel_day = dv.day
            self._action(self)

        return handler


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    picker = LiquidDatePicker()
    picker.action = lambda sender: print(sender.date)

    root = View()
    root.add_subview(picker)
    root.present("fullscreen")
