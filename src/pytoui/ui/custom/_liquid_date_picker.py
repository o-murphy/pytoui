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
IOS_BLUE_ALPHA = (0.0, 122 / 255, 1.0, 0.4)
DAY_SIZE = 42
HEADER_HEIGHT = 42
WEEKDAY_HEIGHT = 24

# Index of the "current" page in the 3-page window
_CENTER_PAGE = 1


# LIGHT_THEME = {
#     "selected": {
#         "today": {"background_color": IOS_BLUE, "tint_color": "white"},
#         "default": {"background_color": IOS_BLUE_ALPHA, "tint_color": IOS_BLUE},
#     },
#     "not_selected": {
#         "today": {"background_color": "transparent", "tint_color": IOS_BLUE},
#         "default": {"background_color": "transparent", "tint_color": "black"},
#     },
# }

# DARK_THEME = {}

# THEME = DARK_THEME if get_ui_style() == "dark" else LIGHT_THEME


def _month_offset(year: int, month: int, delta: int) -> tuple[int, int]:
    """Return (year, month) shifted by `delta` months."""
    total = (year - 1) * 12 + (month - 1) + delta
    return divmod(total, 12)[0] + 1, divmod(total, 12)[1] + 1


def _get_month_name(year: int, month: int) -> str:
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


class _DayView(View):
    def __init__(self, day: int, **kwargs):
        super().__init__(**kwargs)
        self.day = day
        self.is_today = False
        self.is_current_month = False
        self.is_selected = False
        self._button = Button()
        self._button.title = str(day) if day > 0 else ""
        self.corner_radius = DAY_SIZE / 2
        if day <= 0:
            self.hidden = True
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
                self._button.background_color = IOS_BLUE_ALPHA
                self._button.tint_color = IOS_BLUE
        else:
            self._button.font = ("<system>", 14)
            self._button.tint_color = IOS_BLUE if self.is_today else "black"
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
            dv = _DayView(day)
            dv.is_current_month = day > 0  # all non-padding days belong to this month
            if day == today.day and month == today.month and year == today.year:
                dv.is_today = True
            self._day_views.append(dv)
            self.add_subview(dv)

    def layout(self):
        for i, dv in enumerate(self._day_views):
            dv.frame = (i * DAY_SIZE, 0, DAY_SIZE, DAY_SIZE)

    def select_day(self, day: int) -> bool:
        selected = False
        for dv in self._day_views:
            hit = dv.day == day and dv.is_current_month
            dv.is_selected = hit
            dv.draw()
            if hit:
                selected = True
        return selected

    def clear_selection(self):
        for dv in self._day_views:
            dv.is_selected = False
            dv.draw()


class _MonthPage(View):
    def __init__(self, month: int, year: int, **kwargs):
        super().__init__(**kwargs)
        self.month = month
        self.year = year
        self.background_color = (0.95, 0.95, 0.95, 1.0)
        self._weeks: List[_WeekRow] = []
        self._rebuild()

    def _rebuild(self):
        """Reconstruct week rows for self.year / self.month."""
        for w in list(self._weeks):
            self.remove_subview(w)
        self._weeks.clear()

        for week_days in calendar.monthcalendar(self.year, self.month):
            week = _WeekRow(week_days, self.month, self.year)
            self._weeks.append(week)
            self.add_subview(week)

    def reassign(self, year: int, month: int):
        """Reuse the page view for a different month."""
        self.year = year
        self.month = month
        self._rebuild()

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
        super().__init__(*args, **kwargs)
        self._month_year_btn = Button()
        self._month_year_btn.tint_color = "black"
        self._month_year_btn.font = ("<system>", 16)
        self._month_year_btn.title = ""
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
        for i, day_name in enumerate(self._get_weekday_names()):
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

    @staticmethod
    def _get_weekday_names() -> List[str]:
        try:
            locale.setlocale(locale.LC_TIME, "")
            return [
                datetime(2024, 1, i).strftime("%a").capitalize() for i in range(1, 8)
            ]
        except Exception:
            return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class _ScrollViewDelegate:
    """
    3-page window:  [prev | current | next]
    After the user snaps to prev or next page we:
      1. Update _current_year/_current_month on the picker.
      2. Reassign the three _MonthPage views to new months.
      3. Silently reset content_offset to the center page (no animation).
    """

    def __init__(self, picker: LiquidDatePicker):
        self._picker = picker
        self._snapping = False
        self._prev_offset_x: float = -1.0
        self._settled_page: int = _CENTER_PAGE
        self.was_dragging: bool = False

    def scrollview_did_scroll(self, sv: ScrollView | None = None):
        picker = self._picker
        if self._snapping:
            return

        page_w = DAY_SIZE * 7
        try:
            offset_x = picker._scroll_container.content_offset.x
        except Exception:
            return

        self.was_dragging = True

        page = round(offset_x / page_w)
        distance_to_snap = abs(offset_x - page * page_w)

        y, m = _month_offset(
            picker._current_year, picker._current_month, page - _CENTER_PAGE
        )
        picker._header._month_year_btn.title = _get_month_name(y, m)

        prev = self._prev_offset_x
        self._prev_offset_x = offset_x

        if distance_to_snap > 3:
            return

        if abs(offset_x - prev) > 0.5:
            return

        # Fully settled
        self.was_dragging = False

        if page == self._settled_page:
            return

        self._settled_page = page

        # Refresh selection whenever we settle (including returning to center)
        picker._refresh_selection()

        if page == _CENTER_PAGE:
            return

        delta = page - _CENTER_PAGE
        picker._current_year, picker._current_month = _month_offset(
            picker._current_year, picker._current_month, delta
        )

        picker._rebuild_pages()
        picker._refresh_selection()
        self._settled_page = _CENTER_PAGE


@_final_
class LiquidDatePicker(View):
    """
    Infinite horizontal date picker.

    Single entry point: the `date` property (datetime).

    Internally, the scroll view holds exactly 3 _MonthPage objects
    (prev / current / next). After each swipe-snap the pages are
    reassigned to new months and the offset is silently reset to the
    center, giving the illusion of an infinite scroll.
    """

    def __init__(self, date: datetime | None = None, **kwargs):
        super().__init__(**kwargs)

        self.background_color = "white"
        self.corner_radius = 16

        _d = date if date else datetime.now()
        self._current_year: int = _d.year
        self._current_month: int = _d.month
        self._selected_year: int = _d.year
        self._selected_month: int = _d.month
        self._selected_day: int = _d.day

        self._day_action: Callable | None = None

        self._header = _DatePickerHeader()
        self._header._prev_btn.action = lambda _: self._go_prev()
        self._header._next_btn.action = lambda _: self._go_next()
        self.add_subview(self._header)

        self._pages: List[_MonthPage] = []
        for offset in (-1, 0, 1):
            y, m = _month_offset(self._current_year, self._current_month, offset)
            page = _MonthPage(m, y)
            self._pages.append(page)

        self._scroll_container = ScrollView()
        self._scroll_container.bounces = True
        self._scroll_container.paging_enabled = True
        self._scroll_container.shows_horizontal_scroll_indicator = False
        self._scroll_container.delegate = _ScrollViewDelegate(self)
        self.add_subview(self._scroll_container)

        for page in self._pages:
            self._scroll_container.add_subview(page)

        self._header._month_year_btn.title = _get_month_name(
            self._current_year, self._current_month
        )

        self._refresh_selection()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def date(self) -> datetime:
        return datetime(self._selected_year, self._selected_month, self._selected_day)

    @date.setter
    def date(self, value: datetime):
        self._selected_year = value.year
        self._selected_month = value.month
        self._selected_day = value.day
        self._current_year = value.year
        self._current_month = value.month
        self._rebuild_pages()
        self._header._month_year_btn.title = _get_month_name(value.year, value.month)
        self._refresh_selection()
        self.frame = self.frame

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def layout(self):
        page_w = DAY_SIZE * 7
        header_h = HEADER_HEIGHT + WEEKDAY_HEIGHT

        weeks_count = len(
            calendar.monthcalendar(self._current_year, self._current_month)
        )
        content_h = weeks_count * DAY_SIZE
        total_h = header_h + content_h

        self._header.frame = (0, 0, page_w, header_h)

        self._scroll_container.frame = (0, header_h, page_w, content_h)
        self._scroll_container.content_size = (page_w * 3, content_h)
        self._scroll_container.content_offset = (_CENTER_PAGE * page_w, 0)

        for i, page in enumerate(self._pages):
            page.frame = (i * page_w, 0, page_w, content_h)

        self.frame = (self.frame.x, self.frame.y, page_w, total_h)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rebuild_pages(self):
        """Reassign 3 pages to prev/current/next of _current_year/_current_month."""
        page_w = DAY_SIZE * 7

        delegate = self._scroll_container.delegate
        if isinstance(delegate, _ScrollViewDelegate):
            delegate._snapping = True

        for i, offset in enumerate((-1, 0, 1)):
            y, m = _month_offset(self._current_year, self._current_month, offset)
            self._pages[i].reassign(y, m)

        self._scroll_container._internals_._page_anim_target = None
        self._scroll_container._internals_._vel_x = 0.0
        self._scroll_container._internals_._vel_y = 0.0
        self._scroll_container._internals_._decelerating = False
        self._scroll_container._internals_._set_offset(
            _CENTER_PAGE * page_w, 0.0, clamp=False, notify=False
        )

        for page in self._pages:
            page.frame = page.frame

        if self._day_action is not None:
            self._attach_day_actions()

        if isinstance(delegate, _ScrollViewDelegate):
            delegate._snapping = False
            delegate._settled_page = _CENTER_PAGE
            delegate._prev_offset_x = _CENTER_PAGE * page_w
            delegate.was_dragging = False

    def _refresh_selection(self):
        """Clear all selections, then mark the selected day if visible."""
        for page in self._pages:
            page.clear_selection()
            if page.year == self._selected_year and page.month == self._selected_month:
                page.select_day(self._selected_day)

    def _go_prev(self):
        self._current_year, self._current_month = _month_offset(
            self._current_year, self._current_month, -1
        )
        self._rebuild_pages()
        self._header._month_year_btn.title = _get_month_name(
            self._current_year, self._current_month
        )
        self._refresh_selection()
        self.frame = self.frame

    def _go_next(self):
        self._current_year, self._current_month = _month_offset(
            self._current_year, self._current_month, 1
        )
        self._rebuild_pages()
        self._header._month_year_btn.title = _get_month_name(
            self._current_year, self._current_month
        )
        self._refresh_selection()
        self.frame = self.frame

    def _attach_day_actions(self):
        """Wire tap callbacks for all currently loaded day views."""
        action = self._day_action
        if action is None:
            return

        def make_handler(dv: _DayView, page: _MonthPage):
            def handler(sender):
                if dv.day <= 0:
                    return
                sv = self._scroll_container
                delegate = sv.delegate
                if isinstance(delegate, _ScrollViewDelegate):
                    if delegate.was_dragging or delegate._snapping:
                        return
                for p in self._pages:
                    p.clear_selection()
                dv.is_selected = True
                dv.draw()
                self._selected_year = page.year
                self._selected_month = page.month
                self._selected_day = dv.day
                action(dv)

            return handler

        for page in self._pages:
            for week in page._weeks:
                for dv in week._day_views:
                    dv.action = make_handler(dv, page)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def set_day_action(self, action: Callable):
        """Register a callback invoked with the tapped _DayView."""
        self._day_action = action
        self._attach_day_actions()


if __name__ == "__main__":

    def on_day_selected(day_view):
        print(f"Selected day: {day_view.day}")

    picker = LiquidDatePicker()
    picker.set_day_action(on_day_selected)

    root = View()
    root.add_subview(picker)
    root.present("fullscreen")
