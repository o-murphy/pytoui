from __future__ import annotations

import calendar
import locale
from datetime import datetime
from typing import Callable, List

from pytoui.ui._button import Button
from pytoui.ui._constants import ALIGN_CENTER
from pytoui.ui._internals import _final_
from pytoui.ui._label import Label
from pytoui.ui._scroll_view import ScrollView
from pytoui.ui._view import View

__all__ = ("LiquidDatePicker",)


IOS_BLUE = (0.0, 122 / 255, 1.0, 1.0)
DAY_SIZE = 40
HEADER_HEIGHT = 40
WEEKDAY_HEIGHT = 20


class _DayView(View):
    def __init__(self, day: int, is_current_month: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.day = day
        self.is_current_month = is_current_month
        self.is_today = False
        self.is_selected = False

        today = datetime.now()
        if day > 0 and is_current_month:
            self.is_today = day == today.day

        self._button = Button()
        self._button.background_color = "transparent"
        self._button.title = str(day) if day > 0 else ""
        self._button.corner_radius = DAY_SIZE / 2
        if day <= 0:
            self._button.hidden = True
        self.add_subview(self._button)

        self.frame = (0, 0, DAY_SIZE, DAY_SIZE)

    def layout(self):
        self._button.frame = self.bounds.as_tuple()

    def draw(self):
        if self.day <= 0 or not self.is_current_month:
            return

        if self.is_today:
            self._button.font = ("<system-bold>", 14)
        else:
            self._button.font = ("<system>", 14)

        if self.is_selected:
            self._button.border_width = 2
            self._button.border_color = IOS_BLUE
            if self.is_today:
                self._button.background_color = IOS_BLUE
            else:
                self._button.background_color = "transparent"
        else:
            self._button.border_width = 0
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
            is_current_month = day > 0
            day_view = _DayView(day, is_current_month)

            if (
                is_current_month
                and day == today.day
                and month == today.month
                and year == today.year
            ):
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


class _MonthContentView(View):
    def __init__(self, month: int, year: int, **kwargs):
        super().__init__(**kwargs)
        self.month = month
        self.year = year

        self._weeks: List[_WeekRow] = []
        month_calendar = calendar.monthcalendar(self.year, self.month)

        for week_days in month_calendar:
            week = _WeekRow(week_days, month, year)
            self._weeks.append(week)
            self.add_subview(week)

    def layout(self):
        w = self.bounds.width

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


class _MonthPage(View):
    def __init__(self, month: int, year: int | None = None, **kwargs):
        super().__init__(**kwargs)

        self.month = month
        self.year = year or datetime.now().year
        self.background_color = (0.95, 0.95, 0.95, 1.0)

        self._month_label = Label()
        self._month_label.alignment = ALIGN_CENTER
        self._month_label.font = ("<system-bold>", 18)
        self._month_label.text = self._get_month_name()
        self.add_subview(self._month_label)

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

        self._scroll_view = ScrollView()
        self._scroll_view.shows_vertical_scroll_indicator = True
        self._scroll_view.bounces = True
        self._scroll_view.background_color = "clear"
        self.add_subview(self._scroll_view)

        self._content = _MonthContentView(self.month, self.year)
        self._scroll_view.add_subview(self._content)

    def _get_month_name(self) -> str:
        try:
            locale.setlocale(locale.LC_TIME, "")
            return datetime(self.year, self.month, 1).strftime("%B %Y").capitalize()
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
            return f"{months[self.month - 1]} {self.year}"

    def _get_weekday_names(self) -> List[str]:
        try:
            locale.setlocale(locale.LC_TIME, "")
            return [
                datetime(2024, 1, i).strftime("%a").capitalize() for i in range(1, 8)
            ]
        except Exception:
            return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    def layout(self):
        w = DAY_SIZE * 7

        self._month_label.frame = (0, 0, w, HEADER_HEIGHT)

        for i, lbl in enumerate(self._weekday_labels):
            lbl.frame = (i * DAY_SIZE, HEADER_HEIGHT, DAY_SIZE, WEEKDAY_HEIGHT)

        header_height = HEADER_HEIGHT + WEEKDAY_HEIGHT
        weeks_count = len(calendar.monthcalendar(self.year, self.month))
        content_height = weeks_count * DAY_SIZE

        self._scroll_view.frame = (0, header_height, w, content_height)
        self._content.frame = (0, 0, w, content_height)
        self._scroll_view.content_size = (w, content_height)

    def select_day(self, day: int) -> bool:
        return self._content.select_day(day)

    def clear_selection(self):
        self._content.clear_selection()


@_final_
class LiquidDatePicker(View):
    def __init__(
        self, start_year: int | None = None, end_year: int | None = None, **kwargs
    ):
        super().__init__(**kwargs)

        self.background_color = "white"
        self.corner_radius = 16

        current_year = datetime.now().year
        self.start_year = start_year or current_year - 1
        self.end_year = end_year or current_year + 2

        self._main_scroll = ScrollView()
        self._main_scroll.paging_enabled = True
        self._main_scroll.shows_horizontal_scroll_indicator = False
        self._main_scroll.bounces = True
        self.add_subview(self._main_scroll)

        self._months: List[_MonthPage] = []

        for year in range(self.start_year, self.end_year + 1):
            for month_i in range(1, 13):
                month_page = _MonthPage(month_i, year)
                self._months.append(month_page)
                self._main_scroll.add_subview(month_page)

        self._current_month_idx = 0
        today = datetime.now()
        for i, month in enumerate(self._months):
            if month.year == today.year and month.month == today.month:
                self._current_month_idx = i
                month.select_day(today.day)
                break

    def layout(self):
        current_month = self._months[self._current_month_idx]
        weeks_count = len(
            calendar.monthcalendar(current_month.year, current_month.month)
        )
        content_height = weeks_count * DAY_SIZE
        total_height = HEADER_HEIGHT + WEEKDAY_HEIGHT + content_height

        self.frame = (self.frame.x, self.frame.y, DAY_SIZE * 7, total_height)

        w, h = self.bounds.size

        self._main_scroll.frame = (0, 0, w, h)

        self._main_scroll.content_size = (w * len(self._months), h)

        for i, month in enumerate(self._months):
            month.frame = (i * w, 0, w, h)

        self._main_scroll.content_offset = (self._current_month_idx * w, 0)

    @property
    def current_month(self) -> tuple[int, int]:
        page = round(self._main_scroll.content_offset.x / self.bounds.width)
        page = max(0, min(page, len(self._months) - 1))
        month = self._months[page]
        return (month.year, month.month)

    @property
    def selected_date(self) -> tuple[int, int, int] | None:
        for month in self._months:
            for week in month._content._weeks:
                for day in week._day_views:
                    if day.is_selected and day.day > 0:
                        return (month.year, month.month, day.day)
        return None

    def scroll_to_month(self, year: int, month: int, animated: bool = True):
        for i, m in enumerate(self._months):
            if m.year == year and m.month == month:
                target_x = i * self.bounds.width
                if animated:
                    self._main_scroll._internals_._start_page_anim(target_x, 0)
                else:
                    self._main_scroll.content_offset = (target_x, 0)
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
                for week in month._content._weeks:
                    for day_view in week._day_views:
                        if day_view._button is sender:
                            for m in self._months:
                                m.clear_selection()
                            day_view.is_selected = True
                            action(day_view)
                            return

        for month in self._months:
            for week in month._content._weeks:
                for day_view in week._day_views:
                    day_view.action = wrapped_action


if __name__ == "__main__":
    from pytoui.ui._view import View

    def on_day_selected(day_view):
        print(f"Selected day: {day_view.day}")

    picker = LiquidDatePicker(start_year=2024, end_year=2026)
    picker.set_day_action(on_day_selected)

    root = View()
    root.add_subview(picker)
    root.present("fullscreen")

    # v = _DayView(1, is_current_month=False)
    # v.present()
    # print(v.frame)
