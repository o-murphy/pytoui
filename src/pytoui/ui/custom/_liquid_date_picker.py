from __future__ import annotations

import calendar
import locale
from datetime import datetime
from typing import TYPE_CHECKING, Callable, List

from pytoui.ui._button import Button
from pytoui.ui._constants import ALIGN_CENTER
from pytoui.ui._internals import _final_
from pytoui.ui._label import Label
from pytoui.ui._scroll_view import ScrollView
from pytoui.ui._view import View

if TYPE_CHECKING:
    pass

__all__ = ("LiquidDatePicker",)


IOS_BLUE = (0.0, 122 / 255, 1.0, 1.0)
DAY_SIZE = 42
HEADER_HEIGHT = 42
WEEKDAY_HEIGHT = 24


class _DayView(View):
    def __init__(self, day: int, **kwargs):
        super().__init__(**kwargs)
        self.day = day
        self.is_today = False
        self.is_current_month = False
        self.is_selected = False
        self._button = Button()
        self._button.title = str(day) if day > 0 else ""
        self._button.corner_radius = DAY_SIZE / 2
        if day <= 0:
            self._button.hidden = True
        self.add_subview(self._button)

        self.frame = (0, 0, DAY_SIZE, DAY_SIZE)

    def layout(self):
        self._button.frame = self.bounds.as_tuple()

    def draw(self):
        if self.is_selected:
            self._button.font = ("<system-bold>", 14)
            if self.is_today:
                self._button.background_color = IOS_BLUE
                self._button.tint_color = "white"
            else:
                r, g, b, a = IOS_BLUE
                alpha = (r, g, b, a * 0.4)
                self._button.background_color = alpha
                self._button.tint_color = IOS_BLUE
        else:
            if self.is_today:
                self._button.tint_color = IOS_BLUE
            else:
                self._button.tint_color = "black"
            self._button.font = ("<system>", 14)
            self._button.background_color = "transparent"

    @property
    def action(self) -> Callable | None:
        return self._button.action

    @action.setter
    def action(self, value: Callable | None):
        self._button.action = value


class _WeekRow(View):
    def __init__(self, days: List[int], month: int, year: int, **kwargs):
        super().__init__(**kwargs)
        self.days = days
        self.month = month
        self.year = year
        self._day_views: List[_DayView] = []

        today = datetime.now()

        for day in days:
            day_view = _DayView(day)
            day_view.is_current_month = month == today.month
            if day == today.day and day_view.is_current_month and year == today.year:
                day_view.is_today = True

            self._day_views.append(day_view)
            self.add_subview(day_view)

    def layout(self):
        w, h = self.bounds.size
        day_width = DAY_SIZE

        for i, day_view in enumerate(self._day_views):
            day_view.frame = (i * day_width, 0, day_width, DAY_SIZE)

    def select_day(self, day: int) -> bool:
        selected = False
        for day_view in self._day_views:
            if day_view.day == day and day_view.is_current_month:
                day_view.is_selected = True
                selected = True
            else:
                day_view.is_selected = False
        return selected

    def clear_selection(self):
        for day_view in self._day_views:
            day_view.is_selected = False


class _MonthPage(View):
    def __init__(self, month: int, year: int, **kwargs):
        super().__init__(**kwargs)

        self.month: int = month
        self.year: int = datetime.now().year
        self.background_color = (0.95, 0.95, 0.95, 1.0)

        self._weeks: List[_WeekRow] = []
        month_calendar = calendar.monthcalendar(self.year, self.month)

        for week_days in month_calendar:
            week = _WeekRow(week_days, month, year)
            self._weeks.append(week)
            self.add_subview(week)

    def layout(self):
        w = DAY_SIZE * 7
        for i, week in enumerate(self._weeks):
            week.frame = (0, i * DAY_SIZE, w, DAY_SIZE)

    def select_day(self, day: int) -> bool:
        for week in self._weeks:
            if week.select_day(day):
                return True
        return False

    def clear_selection(self):
        for week in self._weeks:
            week.clear_selection()


@_final_
class _DatePickerHeader(View):
    def __init__(self, *args, **kwargs):
        self._month_year_btn = Button()
        self._month_year_btn.tint_color = "black"
        self._month_year_btn.font = ("<system>", 16)
        self._month_year_btn.title = "<MONTH YEAR >"  # self._get_month_name()
        self.add_subview(self._month_year_btn)

        self._prev_btn = Button(title="<")
        self._prev_btn.font = ("<system-bold>", 24)
        self._prev_btn.flex = "L"
        self.add_subview(self._prev_btn)

        self._next_btn = Button(title=">")
        self._next_btn.flex = "L"
        self._next_btn.font = ("<system-bold>", 24)
        self.add_subview(self._next_btn)

        self._weekday_labels: List[Label] = []
        weekdays = self._get_weekday_names()
        for i, day_name in enumerate(weekdays):
            lbl = Label()
            lbl.alignment = ALIGN_CENTER
            lbl.font = ("<system>", 12)
            lbl.text = day_name
            lbl.alpha = 0.7
            self._weekday_labels.append(lbl)
            self.add_subview(lbl)

    def layout(self):
        self._month_year_btn.frame = (0, 0, 200, HEADER_HEIGHT)
        w = self.width
        self._prev_btn.frame = (w - 2 * DAY_SIZE, 0, DAY_SIZE, HEADER_HEIGHT)
        self._next_btn.frame = (w - DAY_SIZE, 0, DAY_SIZE, HEADER_HEIGHT)

        for i, lbl in enumerate(self._weekday_labels):
            lbl.frame = (i * DAY_SIZE, HEADER_HEIGHT, DAY_SIZE, WEEKDAY_HEIGHT)
            lbl.alignment = ALIGN_CENTER

    def _get_weekday_names(self) -> List[str]:
        try:
            locale.setlocale(locale.LC_TIME, "")
            return [
                datetime(2024, 1, i).strftime("%a").capitalize() for i in range(1, 8)
            ]
        except Exception:
            return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _get_month_name(year, month) -> str:
    try:
        locale.setlocale(locale.LC_TIME, "")
        return datetime(year, month, 1).strftime("%B %Y").capitalize()
    except Exception:
        months = [
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
        return f"{months[month - 1]} {year}"


class _ScrollViewDelegate:
    def __init__(self, picker: LiquidDatePicker):
        self.picker = picker
        self.current_month = picker.current_month

    def scrollview_did_scroll(self, sv: ScrollView | None = None):
        current_month = self.picker.current_month
        if self.current_month != current_month:
            self.current_month = current_month
            self.picker._header._month_year_btn.title = _get_month_name(
                *self.current_month
            )


@_final_
class LiquidDatePicker(View):
    def __init__(self, date: datetime | None = None, **kwargs):
        super().__init__(**kwargs)

        self.background_color = "white"
        self.corner_radius = 16

        self._date = date if date else datetime.now()

        current_year = self._date.year
        self.start_year = current_year - 1
        self.end_year = current_year + 1

        self._header = _DatePickerHeader()
        self.add_subview(self._header)

        self._months: List[_MonthPage] = []

        self._scroll_container = ScrollView()
        self._scroll_container.bounces = True
        self._scroll_container.paging_enabled = True
        self._scroll_container.shows_horizontal_scroll_indicator = False
        self._scroll_container.delegate = _ScrollViewDelegate(self)
        self.add_subview(self._scroll_container)

        for year in range(self.start_year, self.end_year + 1):
            for month_i in range(1, 13):
                month_page = _MonthPage(month_i, year)
                self._months.append(month_page)
                self._scroll_container.add_subview(month_page)

        self._current_month_idx = 0
        today = datetime.now()
        for i, month in enumerate(self._months):
            if month.year == today.year and month.month == today.month:
                self._current_month_idx = i
                month.select_day(today.day)
                break

    def layout(self):
        w = DAY_SIZE * 7
        header_h = HEADER_HEIGHT + WEEKDAY_HEIGHT

        current_month = self._months[self._current_month_idx]
        weeks_count = len(
            calendar.monthcalendar(current_month.year, current_month.month)
        )

        content_h = weeks_count * DAY_SIZE
        total_h = header_h + content_h

        self._header.frame = (0, 0, w, header_h)
        self._scroll_container.frame = (0, header_h, w, content_h)
        self._scroll_container.content_size = (w * len(self._months), content_h)
        self._scroll_container.content_offset = (self._current_month_idx * w, 0)

        for i, month in enumerate(self._months):
            month.frame = (i * w, 0, w, content_h)

        self.frame = (self.frame.x, self.frame.y, w, total_h)

    @property
    def current_month(self) -> tuple[int, int]:
        try:
            page = round(self._scroll_container.content_offset.x / self.bounds.width)
            page = max(0, min(page, len(self._months) - 1))
            month = self._months[page]
            return (month.year, month.month)
        except IndexError:
            return (0, 0)

    @property
    def selected_date(self) -> tuple[int, int, int] | None:
        for month in self._months:
            for week in month._weeks:
                for day in week._day_views:
                    if day.is_selected and day.day > 0:
                        return (month.year, month.month, day.day)
        return None

    def scroll_to_month(self, year: int, month: int, animated: bool = True):
        for i, m in enumerate(self._months):
            if m.year == year and m.month == month:
                target_x = i * self.bounds.width
                if animated:
                    self._scroll_container._internals_._start_page_anim(target_x, 0)
                else:
                    self._scroll_container.content_offset = (target_x, 0)
                break

    def select_date(self, year: int, month: int, day: int) -> bool:
        for m in self._months:
            m.clear_selection()

        for m in self._months:
            if m.year == year and m.month == month:
                result = m.select_day(day)
                if result:
                    self.scroll_to_month(year, month)
                return result
        return False

    def set_day_action(self, action: Callable):
        def wrapped_action(sender):
            for month in self._months:
                for week in month._weeks:
                    for day_view in week._day_views:
                        if day_view._button is sender:
                            for m in self._months:
                                m.clear_selection()
                            day_view.is_selected = True
                            action(day_view)
                            return

        for month in self._months:
            for week in month._weeks:
                for day_view in week._day_views:
                    day_view.action = wrapped_action


if __name__ == "__main__":
    from pytoui.ui._view import View

    def on_day_selected(day_view):
        print(f"Selected day: {day_view.day}")

    picker = LiquidDatePicker()
    picker.set_day_action(on_day_selected)

    root = View()
    root.add_subview(picker)
    root.present("fullscreen")
