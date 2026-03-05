from __future__ import annotations
from collections.abc import Callable, Sequence
import re
from typing import (
    Any,
    Literal,
    TypeAlias,
    TypedDict,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from typing_extensions import Unpack, NotRequired

PY3: bool = True

RECT_REGEX: re.Pattern = re.compile(
    r"\{\{(\-?\d+\.?\d*),\s?(\-?\d+\.?\d*)\},\s?\{(\-?\d+\.?\d*),\s?(\-?\d+\.?\d*)\}\}"
)
COLOR_REGEX: str = r"RGBA\((\d+\.?\d*),(\d+\.?\d*),(\d+\.?\d*),(\d+\.?\d*)\)"
ALIGNMENTS: dict[str, Literal[0, 1, 2]] = {"left": 0, "right": 2, "center": 1}
CORRECTION_TYPES: dict[str, bool | None] = {"yes": True, "no": False, "default": None}

BLEND_CLEAR: Literal[16] = 16
BLEND_COLOR: Literal[14] = 14
BLEND_COLOR_BURN: Literal[7] = 7
BLEND_COLOR_DODGE: Literal[6] = 6
BLEND_COPY: Literal[17] = 17
BLEND_DARKEN: Literal[4] = 4
BLEND_DESTINATION_ATOP: Literal[24] = 24
BLEND_DESTINATION_IN: Literal[22] = 22
BLEND_DESTINATION_OUT: Literal[23] = 23
BLEND_DESTINATION_OVER: Literal[21] = 21
BLEND_DIFFERENCE: Literal[10] = 10
BLEND_EXCLUSION: Literal[11] = 11
BLEND_HARD_LIGHT: Literal[9] = 9
BLEND_HUE: Literal[12] = 12
BLEND_LIGHTEN: Literal[5] = 5
BLEND_LUMINOSITY: Literal[15] = 15
BLEND_MULTIPLY: Literal[1] = 1
BLEND_NORMAL: Literal[0] = 0
BLEND_OVERLAY: Literal[3] = 3
BLEND_PLUS_DARKER: Literal[26] = 26
BLEND_PLUS_LIGHTER: Literal[27] = 27
BLEND_SATURATION: Literal[13] = 13
BLEND_SCREEN: Literal[2] = 2
BLEND_SOFT_LIGHT: Literal[8] = 8
BLEND_SOURCE_ATOP: Literal[20] = 20
BLEND_SOURCE_IN: Literal[18] = 18
BLEND_SOURCE_OUT: Literal[19] = 19
BLEND_XOR: Literal[25] = 25

CONTENT_BOTTOM: Literal[6] = 6
CONTENT_BOTTOM_LEFT: Literal[11] = 11
CONTENT_BOTTOM_RIGHT: Literal[12] = 12
CONTENT_CENTER: Literal[4] = 4
CONTENT_LEFT: Literal[7] = 7
CONTENT_REDRAW: Literal[3] = 3
CONTENT_RIGHT: Literal[8] = 8
CONTENT_SCALE_ASPECT_FILL: Literal[2] = 2
CONTENT_SCALE_ASPECT_FIT: Literal[1] = 1
CONTENT_SCALE_TO_FILL: Literal[0] = 0
CONTENT_TOP: Literal[5] = 5
CONTENT_TOP_LEFT: Literal[9] = 9
CONTENT_TOP_RIGHT: Literal[10] = 10

DATE_PICKER_MODE_COUNTDOWN: Literal[3] = 3
DATE_PICKER_MODE_DATE: Literal[1] = 1
DATE_PICKER_MODE_DATE_AND_TIME: Literal[2] = 2
DATE_PICKER_MODE_TIME: Literal[0] = 0

ACTIVITY_INDICATOR_STYLE_GRAY: Literal[2] = 2
ACTIVITY_INDICATOR_STYLE_WHITE: Literal[1] = 1
ACTIVITY_INDICATOR_STYLE_WHITE_LARGE: Literal[0] = 0

ALIGN_CENTER: Literal[1] = 1
ALIGN_JUSTIFIED: Literal[3] = 3
ALIGN_LEFT: Literal[0] = 0
ALIGN_NATURAL: Literal[4] = 4
ALIGN_RIGHT: Literal[2] = 2

AUTOCAPITALIZE_ALL: Literal[3] = 3
AUTOCAPITALIZE_NONE: Literal[0] = 0
AUTOCAPITALIZE_SENTENCES: Literal[2] = 2
AUTOCAPITALIZE_WORDS: Literal[1] = 1

KEYBOARD_ASCII: Literal[1] = 1
KEYBOARD_DECIMAL_PAD: Literal[8] = 8
KEYBOARD_DEFAULT: Literal[0] = 0
KEYBOARD_EMAIL: Literal[7] = 7
KEYBOARD_NAME_PHONE_PAD: Literal[6] = 6
KEYBOARD_NUMBERS: Literal[2] = 2
KEYBOARD_NUMBER_PAD: Literal[4] = 4
KEYBOARD_PHONE_PAD: Literal[5] = 5
KEYBOARD_TWITTER: Literal[9] = 9
KEYBOARD_URL: Literal[3] = 3
KEYBOARD_WEB_SEARCH: Literal[10] = 10

LB_CHAR_WRAP: Literal[1] = 1
LB_CLIP: Literal[2] = 2
LB_TRUNCATE_HEAD: Literal[3] = 3
LB_TRUNCATE_MIDDLE: Literal[5] = 5
LB_TRUNCATE_TAIL: Literal[4] = 4
LB_WORD_WRAP: Literal[0] = 0

LINE_CAP_BUTT: Literal[0] = 0
LINE_CAP_ROUND: Literal[1] = 1
LINE_CAP_SQUARE: Literal[2] = 2
LINE_JOIN_BEVEL: Literal[2] = 2
LINE_JOIN_MITER: Literal[0] = 0
LINE_JOIN_ROUND: Literal[1] = 1

RENDERING_MODE_AUTOMATIC: Literal[0] = 0
RENDERING_MODE_ORIGINAL: Literal[1] = 1
RENDERING_MODE_TEMPLATE: Literal[2] = 2

__Alignment: TypeAlias = Literal[0, 1, 2, 3, 4]
__BlendMode: TypeAlias = Literal[
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    26,
    27,
]
__ContentMode: TypeAlias = Literal[
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
]
__ActivityIndicatorStyle: TypeAlias = Literal[0, 1, 2]
__DatePickerMode: TypeAlias = Literal[0, 1, 2, 3]
__KeyboardType: TypeAlias = Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
__LineBrakeMode: TypeAlias = Literal[0, 1, 2, 3, 4, 5]
__LineJoinMode: TypeAlias = Literal[0, 1, 2]
__LineCapStyle: TypeAlias = Literal[0, 1, 2]
__CapitalizationType: TypeAlias = Literal[0, 1, 2, 3]
__RenderingMode: TypeAlias = Literal[0, 1, 2]
__UiStyle: TypeAlias = Literal["dark", "light"]

class Vector2:
    x: float
    y: float

    def __init__(self, *args) -> None: ...
    def __add__(self, other: Vector2) -> Vector2: ...
    def __len__(self) -> int: ...
    def __getitem__(self, index: int) -> float: ...
    def as_tuple(self) -> tuple[float, float]: ...

class Size(Vector2):
    h: float
    height: float
    w: float
    width: float

class Point(Vector2): ...

__RGB: TypeAlias = tuple[float, float, float]
__RGBA: TypeAlias = tuple[float, float, float, float]
__HEX: TypeAlias = str | int
__RectLike: TypeAlias = Rect | tuple[float, float, float, float] | list[float]
__PointLike: TypeAlias = Point | tuple[float, float]
__SizeLike: TypeAlias = Size | tuple[float, float]
__TouchPhase: TypeAlias = Literal["began", "ended", "moved", "stationary", "cancelled"]
__ColorLike: TypeAlias = __RGB | __RGBA | __HEX | None
__ViewFlex: TypeAlias = Literal[
    "",
    "W",
    "H",
    "L",
    "R",
    "T",
    "B",
    "w",
    "h",
    "l",
    "r",
    "t",
    "b",
    "WH",
    "WL",
    "WR",
    "WT",
    "WB",
    "HL",
    "HR",
    "HT",
    "HB",
    "LR",
    "LT",
    "LB",
    "RT",
    "RB",
    "TB",
    "wh",
    "wl",
    "wr",
    "wt",
    "wb",
    "hl",
    "hr",
    "ht",
    "hb",
    "lr",
    "lt",
    "lb",
    "rt",
    "rb",
    "tb",
    "WHL",
    "WHR",
    "WHT",
    "WHB",
    "WLR",
    "WLT",
    "WLB",
    "WRT",
    "WRB",
    "WTB",
    "whl",
    "whr",
    "wht",
    "whb",
    "wlr",
    "wlt",
    "wlb",
    "wrt",
    "wrb",
    "wtb",
    "HLR",
    "HLT",
    "HLB",
    "HRT",
    "HRB",
    "HTB",
    "hlr",
    "hlt",
    "hlb",
    "hrt",
    "hrb",
    "htb",
    "LRT",
    "LRB",
    "LTB",
    "RTB",
    "lrt",
    "lrb",
    "ltb",
    "rtb",
    "WHLR",
    "WHLT",
    "WHLB",
    "WHRT",
    "WHRB",
    "WHTB",
    "WLRT",
    "WLRB",
    "WLTB",
    "WRTB",
    "whlr",
    "whlt",
    "whlb",
    "whrt",
    "whrb",
    "whtb",
    "wlrt",
    "wlrb",
    "wltb",
    "wrtb",
    "HLRT",
    "HLRB",
    "HLTB",
    "HRTB",
    "hlrt",
    "hlrb",
    "hltb",
    "hrtb",
    "LRTB",
    "lrtb",
    "WHLRT",
    "WHLRB",
    "WHLTB",
    "WHRTB",
    "WLRTB",
    "whlrt",
    "whlrb",
    "whltb",
    "whrtb",
    "wlrtb",
    "HLRTB",
    "hlrtb",
    "WHLRTB",
    "whlrtb",
]
__PresentStyle: TypeAlias = Literal[
    "default", "full_screen", "sheet", "popover", "panel"
]
__PresentOrientation: TypeAlias = Literal[
    "portrait",
    "portrait-upside-down",
    "landscape",
    "landscape-left",
    "landscape-right",
]
__Action: TypeAlias = Callable[[View], None] | Callable[[], None]
__Font: TypeAlias = tuple[str, float]
__ScrollIndicatorStyle: TypeAlias = Literal["default", "white", "black"]

class Rect:
    x: float
    y: float
    w: float
    width: float
    h: float
    height: float
    max_x: float
    max_y: float
    min_x: float
    min_y: float
    origin: Point
    size: Size
    def __init__(self, *args) -> None: ...
    def __getitem__(self, index: int) -> float: ...
    def __len__(self) -> int: ...
    def as_tuple(self) -> tuple[float, float, float, float]: ...
    def center(self) -> Point: ...
    def contains_point(self, point: tuple[float, float]) -> bool: ...
    def contains_rect(self, rect: __RectLike) -> bool: ...
    def inset(self, dx: float, dy: float) -> Rect: ...
    def intersection(self, rect: __RectLike) -> Rect: ...
    def intersects(self, rect: __RectLike) -> bool: ...
    def max(self) -> Point: ...
    def min(self) -> Point: ...
    def translate(self, dx: float, dy: float) -> Rect: ...
    def union(self, rect: __RectLike) -> Rect: ...

class Touch:
    location: Point
    phase: __TouchPhase
    prev_location: Point
    timestamp: int
    touch_id: int
    objc_instance: Any

    _objc_ptr: Any

    def __init__(self, *args, **kwargs) -> None: ...

class GState:
    def __enter__(self) -> None: ...
    def __exit__(self, type, value, traceback) -> None: ...
    def __init__(self) -> None: ...

class ImageContext:
    def __enter__(self) -> None: ...
    def __exit__(self, type, value, traceback) -> None: ...
    def __init__(self, *args, **kwargs) -> None: ...
    def get_image(self) -> Image: ...

class Path:
    bounds: Rect
    eo_fill_rule: bool
    line_cap_style: __LineCapStyle
    line_join_style: __LineJoinMode
    line_width: float
    objc_instance: Any

    _objc_ptr: Any = ...

    def __init__(self) -> None: ...
    def _debug_quicklook_(self) -> str: ...
    def add_arc(
        self,
        cx: float,
        cy: float,
        r: float,
        start: float,
        end: float,
        clockwise: bool = True,
    ) -> None: ...
    def add_clip(self) -> None: ...
    def add_curve(
        self,
        end_x: float,
        end_y: float,
        cp1_x: float,
        cp1_y: float,
        cp2_x: float,
        cp2_y: float,
    ) -> None: ...
    def add_quad_curve(
        self,
        end_x: float,
        end_y: float,
        cp_x: float,
        cp_y: float,
    ) -> None: ...
    def append_path(self, other: Path) -> None: ...
    def close(self) -> None: ...
    def fill(self) -> None: ...
    def hit_test(self, x: float, y: float) -> bool: ...
    def line_to(self, x: float, y: float) -> None: ...
    def move_to(self, x: float, y: float) -> None: ...
    def oval(cls, x: float, y: float, w: float, h: float) -> Path: ...
    def rect(cls, x: float, y: float, w: float, h: float) -> Path: ...
    def rounded_rect(cls, x: float, y: float, w: float, h: float, r: float) -> Path: ...
    def set_line_dash(self, sequence: Sequence[float], phase: float = 0.0) -> None: ...
    def stroke(self) -> None: ...

class Image:
    name: Any
    rendering_mode: __RenderingMode
    scale: Any
    size: Any

    objc_instance: Any
    _objc_ptr: Any = ...

    def __init__(self, *args, **kwargs) -> None: ...
    def _debug_quicklook_(self) -> str: ...
    def clip_to_mask(self, *args, **kwargs) -> Any: ...
    def draw(self, *args, **kwargs) -> Any: ...
    def draw_as_pattern(self, *args, **kwargs) -> Any: ...
    def from_data(self, *args, **kwargs) -> Any: ...
    def from_image_context(self, *args, **kwargs) -> Any: ...
    def named(self, *args, **kwargs) -> Any: ...
    def resizable_image(self, *args, **kwargs) -> Any: ...
    def show(self, *args, **kwargs) -> Any: ...
    def to_jpeg(self, *args, **kwargs) -> Any: ...
    def to_png(self, *args, **kwargs) -> Any: ...
    def with_rendering_mode(self, *args, **kwargs) -> Any: ...

class autoreleasepool:
    def __enter__(self) -> None: ...
    def __exit__(self) -> None: ...
    def __init__(self, type, value, traceback) -> None: ...

class __ViewKwargs(TypedDict, total=False):
    frame: NotRequired[__RectLike]
    flex: NotRequired[__ViewFlex]
    background_color: NotRequired[__ColorLike]
    name: NotRequired[str | None]

    alpha: NotRequired[float]
    autoresizing: NotRequired[str]
    bg_color: NotRequired[__ColorLike]
    border_color: NotRequired[__ColorLike]
    border_width: NotRequired[float]
    bounds: NotRequired[__RectLike]
    center: NotRequired[__PointLike]
    content_mode: NotRequired[__ContentMode]
    corner_radius: NotRequired[float]
    height: NotRequired[float]
    hidden: NotRequired[bool]
    left_button_items: NotRequired[Sequence[ButtonItem] | None]
    multitouch_enabled: NotRequired[bool]
    # navigation_view: NavigationView | None  # readonly
    right_button_items: NotRequired[Sequence[ButtonItem] | None]
    tint_color: NotRequired[__ColorLike]
    touch_enabled: NotRequired[bool]
    transform: NotRequired[Transform | None]
    update_interval: NotRequired[float]
    width: NotRequired[float]
    x: NotRequired[float]
    y: NotRequired[float]

    # # ObjC-compat
    # objc_instance: NotRequired[Any]
    # _objc_ptr: NotRequired[Any]

class View:
    alpha: float
    autoresizing: str
    background_color: __ColorLike
    bg_color: __ColorLike
    border_color: __ColorLike
    border_width: float
    bounds: __RectLike
    center: __PointLike
    content_mode: __ContentMode
    corner_radius: float
    flex: __ViewFlex
    frame: __RectLike
    height: float
    hidden: bool
    @property
    def left_button_items(self) -> tuple[ButtonItem] | None: ...
    @left_button_items.setter
    def left_button_items(self, value: Sequence[ButtonItem] | None): ...
    multitouch_enabled: bool
    name: str
    navigation_view: NavigationView | None  # readonly
    on_screen: bool
    @property
    def right_button_items(self) -> tuple[ButtonItem] | None: ...
    @right_button_items.setter
    def right_button_items(self, value: Sequence[ButtonItem] | None): ...
    subviews: tuple[
        View,
        ...,
    ]
    superview: View | None
    tint_color: __ColorLike
    touch_enabled: bool
    transform: Transform | None
    update_interval: float
    width: float
    x: float
    y: float

    objc_instance: Any
    _objc_ptr: Any
    def __init__(self, *args, **kwargs: Unpack[__ViewKwargs]) -> None: ...
    def __getitem__(self, name: str) -> View: ...
    def __len__(self) -> int: ...
    def _debug_quicklook_(self) -> str: ...
    def add_subview(self, view: View) -> None: ...
    def become_first_responder(self) -> None: ...
    def bring_to_front(self) -> None: ...
    def close(self) -> None: ...
    def draw_snapshot(self) -> None: ...
    def get_key_commands(self) -> list[dict]: ...
    def key_command(self, sender: dict) -> None: ...
    def present(
        self,
        style: __PresentStyle = "default",
        animated: bool = True,
        popover_location: __PointLike | None = None,
        hide_title_bar: bool = False,
        title_bar_color: __ColorLike = None,
        title_color: __ColorLike = None,
        orientations: Sequence[__PresentOrientation] | None = None,
        hide_close_button: bool = False,
    ) -> None: ...
    def remove_subview(self, view: View) -> None: ...
    def send_to_back(self) -> None: ...
    def set_needs_display(self) -> None: ...
    def size_to_fit(self) -> None: ...
    def wait_modal(self) -> None: ...

class __ActivityIndicatorKwargs(__ViewKwargs, total=False):
    hides_when_stopped: NotRequired[bool]
    style: NotRequired[__ActivityIndicatorStyle]

class ActivityIndicator(View):
    hides_when_stopped: bool
    style: __ActivityIndicatorStyle
    def __init__(self, *args, **kwargs: Unpack[__ActivityIndicatorKwargs]) -> None: ...
    def start(self) -> None: ...
    def start_animating(self) -> None: ...
    def stop(self) -> None: ...
    def stop_animating(self) -> None: ...

class __ButtonKwargs(__ViewKwargs, total=False):
    action: NotRequired[__Action | None]
    background_image: NotRequired[Image | None]
    enabled: NotRequired[bool]
    font: NotRequired[__Font]
    image: NotRequired[Image | None]
    title: NotRequired[str]

class Button(View):
    action: __Action | None
    background_image: Image | None
    enabled: bool
    font: __Font
    image: Image | None
    title: str
    def __init__(self, *args, **kwargs: Unpack[__ButtonKwargs]) -> None: ...

class ButtonItem:
    action: __Action
    enabled: bool
    image: Image
    tint_color: __ColorLike
    title: str
    _objc_ptr: Any
    def __init__(self, *args, **kwargs) -> None: ...

class DatePicker(View):
    action: __Action | None
    countdown_duration: Any
    date: Any
    mode: __DatePickerMode
    def __init__(self, *args, **kwargs) -> None: ...

class __ImageViewKwargs(__ViewKwargs, total=False):
    image: NotRequired[Image]

class ImageView(View):
    image: Image
    def __init__(self, *args, **kwargs: Unpack[__ImageViewKwargs]) -> None: ...
    def load_from_url(self, url: str) -> None: ...

class __LabelKwargs(__ViewKwargs, total=False):
    alignment: NotRequired[__Alignment]
    font: NotRequired[__Font]
    min_font_scale: NotRequired[float]
    number_of_lines: NotRequired[int]
    scales_font: NotRequired[float]
    text: NotRequired[str]
    text_color: NotRequired[__ColorLike]

class Label(View):
    alignment: __Alignment
    font: __Font
    min_font_scale: float
    number_of_lines: int
    scales_font: float
    text: str
    text_color: __ColorLike
    def __init__(self, *args, **kwargs: Unpack[__LabelKwargs]) -> None: ...

class ListDataSource:
    def __init__(self, *args, **kwargs) -> None: ...
    items: Any  # default: <property object at 0x1165fc720>
    def reload(self, *args, **kwargs) -> Any: ...
    def tableview_accessory_button_tapped(self, *args, **kwargs) -> Any: ...
    def tableview_can_delete(self, *args, **kwargs) -> Any: ...
    def tableview_can_move(self, *args, **kwargs) -> Any: ...
    def tableview_cell_for_row(self, *args, **kwargs) -> Any: ...
    def tableview_delete(self, *args, **kwargs) -> Any: ...
    def tableview_did_select(self, *args, **kwargs) -> Any: ...
    def tableview_move_row(self, *args, **kwargs) -> Any: ...
    def tableview_number_of_rows(self, *args, **kwargs) -> Any: ...
    def tableview_number_of_sections(self, *args, **kwargs) -> Any: ...

class ListDataSourceList(list):
    def __add__(self, *args, **kwargs) -> Any: ...
    def __getitem__(self, *args, **kwargs) -> Any: ...
    def __init__(self, *args, **kwargs) -> None: ...
    def __iter__(self, *args, **kwargs) -> Any: ...
    def __len__(self, *args, **kwargs) -> Any: ...
    def __setitem__(self, *args, **kwargs) -> Any: ...
    def append(self, *args, **kwargs) -> Any: ...
    def clear(self, *args, **kwargs) -> Any: ...
    def copy(self, *args, **kwargs) -> Any: ...
    def count(self, *args, **kwargs) -> Any: ...
    def extend(self, *args, **kwargs) -> Any: ...
    def index(self, *args, **kwargs) -> Any: ...
    def insert(self, *args, **kwargs) -> Any: ...
    def pop(self, *args, **kwargs) -> Any: ...
    def remove(self, *args, **kwargs) -> Any: ...
    def reverse(self, *args, **kwargs) -> Any: ...
    def sort(self, *args, **kwargs) -> Any: ...

class __NavigationViewKwargs(__ViewKwargs, total=False):
    navigation_bar_hidden: NotRequired[bool]
    bar_tint_color: NotRequired[__ColorLike]
    title_color: NotRequired[__ColorLike]

class NavigationView(View):
    bar_tint_color: __ColorLike  # default: <attributbool 'bar_tint_color' of '_ui.NavigationView' objects>
    navigation_bar_hidden: bool
    title_color: __ColorLike
    def __init__(
        self, view: View, /, **kwargs: Unpack[__NavigationViewKwargs]
    ) -> None: ...
    def pop_view(self, animated: bool = True) -> None: ...
    def push_view(self, view: View, animated: bool = True) -> None: ...

class __ScrollViewKwargs(__ViewKwargs, total=False):
    always_bounce_horizontal: NotRequired[bool]
    always_bounce_vertical: NotRequired[bool]
    bounces: NotRequired[bool]
    content_inset: NotRequired[tuple[float, float, float, float]]
    content_offset: NotRequired[__PointLike]
    content_size: NotRequired[__SizeLike]
    decelerating: NotRequired[bool]
    delegate: NotRequired[Any | None]
    directional_lock_enabled: NotRequired[bool]
    dragging: NotRequired[bool]
    indicator_style: NotRequired[__ScrollIndicatorStyle]
    paging_enabled: NotRequired[bool]
    scroll_enabled: NotRequired[bool]
    scroll_indicator_insets: NotRequired[tuple[float, float, float, float]]
    shows_horizontal_scroll_indicator: NotRequired[bool]
    shows_vertical_scroll_indicator: NotRequired[bool]
    tracking: NotRequired[bool]

class ScrollView(View):
    always_bounce_horizontal: bool
    always_bounce_vertical: bool
    bounces: bool
    content_inset: tuple[float, float, float, float]
    content_offset: __PointLike
    content_size: __SizeLike
    decelerating: bool
    delegate: Any | None
    directional_lock_enabled: bool
    dragging: bool
    indicator_style: __ScrollIndicatorStyle
    paging_enabled: bool
    scroll_enabled: bool
    scroll_indicator_insets: tuple[float, float, float, float]
    shows_horizontal_scroll_indicator: bool
    shows_vertical_scroll_indicator: bool
    tracking: bool
    def __init__(self, *args, **kwargs: Unpack[__ScrollViewKwargs]) -> None: ...

class __SegmentedControlKwargs(__ViewKwargs, total=False):
    action: NotRequired[__Action | None]
    enabled: NotRequired[bool]
    segments: NotRequired[Sequence[str]]
    selected_index: NotRequired[int]

class SegmentedControl(View):
    action: __Action | None
    enabled: bool
    segments: Sequence[str]
    selected_index: int
    def __init__(self, *args, **kwargs: Unpack[__SegmentedControlKwargs]) -> None: ...

class __SliderKwargs(__ViewKwargs, total=False):
    action: NotRequired[__Action | None]
    continuous: NotRequired[bool]
    value: NotRequired[float]

class Slider(View):
    action: __Action | None
    continuous: bool
    value: float
    def __init__(self, *args, **kwargs: Unpack[__SliderKwargs]) -> None: ...

class __SwitchKwargs(__ViewKwargs, total=False):
    action: NotRequired[__Action | None]
    enabled: NotRequired[bool]
    value: NotRequired[bool]

class Switch(View):
    action: __Action | None
    enabled: bool
    value: bool
    def __init__(self, *args, **kwargs: Unpack[__SwitchKwargs]) -> None: ...

class TableView(ScrollView, View):
    allows_multiple_selection: Any
    allows_multiple_selection_during_editing: Any
    allows_selection: Any
    allows_selection_during_editing: Any
    always_bounce_horizontal: Any
    always_bounce_vertical: Any
    bounces: Any
    content_inset: Any
    content_offset: Any
    content_size: Any
    data_source: Any
    decelerating: Any
    delegate: Any
    def delete_rows(self, *args, **kwargs) -> Any: ...
    directional_lock_enabled: Any
    dragging: Any
    editing: Any
    indicator_style: Any
    def __init__(self, *args, **kwargs) -> None: ...
    def insert_rows(self, *args, **kwargs) -> Any: ...
    paging_enabled: Any
    def reload(self, *args, **kwargs) -> Any: ...
    def reload_data(self, *args, **kwargs) -> Any: ...
    row_height: Any
    scroll_enabled: Any
    scroll_indicator_insets: Any
    selected_row: Any
    selected_rows: Any
    separator_color: Any
    def set_editing(self, *args, **kwargs) -> Any: ...
    shows_horizontal_scroll_indicator: Any
    shows_vertical_scroll_indicator: Any
    tracking: Any

class TableViewCell(View):
    accessory_type: Any
    content_view: Any
    corner_radius: Any
    detail_text_label: Any
    image_view: Any
    selectable: Any
    selected_background_view: Any
    text_label: Any

class TextField(View):
    action: __Action | None
    autocapitalization_type: __CapitalizationType
    autocorrection_type: Any
    def begin_editing(self, *args, **kwargs) -> Any: ...
    bordered: Any
    clear_button_mode: Any
    delegate: Any
    enabled: bool
    def end_editing(self, *args, **kwargs) -> Any: ...
    font: __Font
    keyboard_type: __KeyboardType
    placeholder: Any
    secure: Any
    spellchecking_type: Any
    text: str
    text_color: __ColorLike

class TextView(ScrollView, View):
    alignment: __Alignment
    always_bounce_horizontal: Any
    always_bounce_vertical: Any
    auto_content_inset: Any
    autocapitalization_type: Any
    autocorrection_type: Any
    def begin_editing(self, *args, **kwargs) -> Any: ...
    bounces: Any
    content_inset: Any
    content_offset: Any
    content_size: Any
    decelerating: Any
    delegate: Any
    directional_lock_enabled: Any
    dragging: Any
    editable: Any
    def end_editing(self, *args, **kwargs) -> Any: ...
    font: __Font
    indicator_style: Any
    keyboard_type: Any
    paging_enabled: Any
    def replace_range(self, *args, **kwargs) -> Any: ...
    scroll_enabled: Any
    scroll_indicator_insets: Any
    selectable: Any
    selected_range: Any
    shows_horizontal_scroll_indicator: Any
    shows_vertical_scroll_indicator: Any
    spellchecking_type: Any
    text: Any
    text_color: Any
    tracking: Any

class Transform:
    def __init__(self, a=1.0, b=0.0, c=0.0, d=1.0, tx=0.0, ty=0.0) -> None: ...
    def concat(self, other: Transform) -> Transform: ...
    def invert(self) -> Transform: ...
    def rotation(cls, rad: float) -> Transform: ...
    def scale(cls, sx: float, sy: float) -> Transform: ...
    def translation(cls, tx: float, ty: float) -> Transform: ...

class WebView(View):
    delegate: Any
    def eval_js(self, *args, **kwargs) -> Any: ...
    def evaluate_javascript(self, *args, **kwargs) -> Any: ...
    def go_back(self, *args, **kwargs) -> Any: ...
    def go_forward(self, *args, **kwargs) -> Any: ...
    def load_html(self, *args, **kwargs) -> Any: ...
    def load_url(self, *args, **kwargs) -> Any: ...
    def reload(self, *args, **kwargs) -> Any: ...
    scales_page_to_fit: Any
    def stop(self, *args, **kwargs) -> Any: ...

def _bind_action(
    v: View,
    action_str: str,
    f_globals,
    f_locals,
    attr_name: str = "action",
    verbose: bool = True,
) -> None: ...
def _color2str(color: __RGBA | None) -> str | None: ...
def _rect2str(rect: __RectLike) -> str: ...
def _str2color(color_str: str, default: __ColorLike = None): ...
def _str2rect(rect_str: str) -> tuple[float, ...] | None: ...
def _view_from_dict(
    view_dict: dict[str, Any], f_globals, f_locals, verbose: bool = True
) -> View: ...
def _view_to_dict(view: View) -> dict[str, Any]: ...
def animate(
    animation: Callable,
    duration: float = 0.25,
    delay: float = 0.0,
    completion: Callable | None = None,
) -> None: ...

basestring: TypeAlias = str

def begin_image_context(*args, **kwargs) -> Any: ...
def cancel_delays() -> None: ...
def close_all(*args, **kwargs) -> Any: ...
def concat_ctm(transform: Transform) -> None: ...
def convert_point(
    point: __PointLike = (0, 0),
    from_view: View | None = None,
    to_view: View | None = None,
) -> Point: ...
def convert_rect(
    rect: __RectLike = (0, 0, 0, 0),
    from_view: View | None = None,
    to_view: View | None = None,
) -> Rect: ...
def delay(func: Callable, seconds: float) -> None: ...
def draw_string(
    s: str,
    rect: __RectLike = (0, 0, 0, 0),
    font: tuple[str, float] = ("<system>", 17.0),
    color: __ColorLike | None = None,
    alignment: __Alignment = ...,
    line_break_mode: __LineBrakeMode = ...,
) -> None: ...
def dump_view(*args, **kwargs) -> Any: ...
def end_editing(*args, **kwargs) -> Any: ...
def end_image_context(*args, **kwargs) -> Any: ...
def fill_rect(x: float, y: float, w: float, h: float) -> None: ...
def get_keyboard_frame(*args, **kwargs) -> Any: ...
def get_screen_size() -> tuple[int, int]: ...
def get_ui_style() -> __UiStyle: ...
def get_window_size() -> tuple[int, int]: ...
def in_background(fn: Callable) -> Callable: ...
def load_view(*args, **kwargs) -> Any: ...
def load_view_str(*args, **kwargs) -> Any: ...
def measure_string(
    s: str,
    max_width: float = 0,
    font: tuple[str, float] = ("<system>", 12.0),
    alignment: __Alignment = ...,
    line_break_mode: __LineBrakeMode = ...,
) -> tuple[float, float]: ...
def parse_color(c: __ColorLike) -> __RGBA: ...
def set_alpha(alpha: float) -> None: ...
def set_blend_mode(mode: __BlendMode) -> None: ...
def set_color(c: __ColorLike) -> None: ...
def set_shadow(
    color: __ColorLike,
    offset_x: float,
    offset_y: float,
    blur_radius: float,
) -> None: ...
def settrace(*args, **kwargs) -> Any: ...
