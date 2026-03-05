"""Pythonista-compatible UI framework for framebuffer rendering.

Usage:
    import ui

    v = ui.View()
    v.background_color = "white"

    class MyView(ui.View):
        def draw(self):
            ui.set_color("red")
            ui.Path.rect(0, 0, self.width, self.height).fill()
"""

from __future__ import annotations

from pytoui.ui._activity_indicator import ActivityIndicator
from pytoui.ui._button import Button
from pytoui.ui._button_item import ButtonItem
from pytoui.ui._constants import (
    # --- Activity Indicator Styles ---
    ACTIVITY_INDICATOR_STYLE_GRAY,
    ACTIVITY_INDICATOR_STYLE_WHITE,
    ACTIVITY_INDICATOR_STYLE_WHITE_LARGE,
    # --- Alignments ---
    ALIGN_CENTER,
    ALIGN_JUSTIFIED,
    ALIGN_LEFT,
    ALIGN_NATURAL,
    ALIGN_RIGHT,
    ALIGNMENTS,
    # --- Autocapitalization ---
    AUTOCAPITALIZE_ALL,
    AUTOCAPITALIZE_NONE,
    AUTOCAPITALIZE_SENTENCES,
    AUTOCAPITALIZE_WORDS,
    # --- Blending Modes ---
    BLEND_CLEAR,
    BLEND_COLOR,
    BLEND_COLOR_BURN,
    BLEND_COLOR_DODGE,
    BLEND_COPY,
    BLEND_DARKEN,
    BLEND_DESTINATION_ATOP,
    BLEND_DESTINATION_IN,
    BLEND_DESTINATION_OUT,
    BLEND_DESTINATION_OVER,
    BLEND_DIFFERENCE,
    BLEND_EXCLUSION,
    BLEND_HARD_LIGHT,
    BLEND_HUE,
    BLEND_LIGHTEN,
    BLEND_LUMINOSITY,
    BLEND_MULTIPLY,
    BLEND_NORMAL,
    BLEND_OVERLAY,
    BLEND_PLUS_DARKER,
    BLEND_PLUS_LIGHTER,
    BLEND_SATURATION,
    BLEND_SCREEN,
    BLEND_SOFT_LIGHT,
    BLEND_SOURCE_ATOP,
    BLEND_SOURCE_IN,
    BLEND_SOURCE_OUT,
    BLEND_XOR,
    # --- Regular Expressions ---
    COLOR_REGEX,
    # --- Content Modes ---
    CONTENT_BOTTOM,
    CONTENT_BOTTOM_LEFT,
    CONTENT_BOTTOM_RIGHT,
    CONTENT_CENTER,
    CONTENT_LEFT,
    CONTENT_REDRAW,
    CONTENT_RIGHT,
    CONTENT_SCALE_ASPECT_FILL,
    CONTENT_SCALE_ASPECT_FIT,
    CONTENT_SCALE_TO_FILL,
    CONTENT_TOP,
    CONTENT_TOP_LEFT,
    CONTENT_TOP_RIGHT,
    # --- Correction Types ---
    CORRECTION_TYPES,
    # --- Date Picker Modes ---
    DATE_PICKER_MODE_COUNTDOWN,
    DATE_PICKER_MODE_DATE,
    DATE_PICKER_MODE_DATE_AND_TIME,
    DATE_PICKER_MODE_TIME,
    # --- Keyboard Types ---
    KEYBOARD_ASCII,
    KEYBOARD_DECIMAL_PAD,
    KEYBOARD_DEFAULT,
    KEYBOARD_EMAIL,
    KEYBOARD_NAME_PHONE_PAD,
    KEYBOARD_NUMBER_PAD,
    KEYBOARD_NUMBERS,
    KEYBOARD_PHONE_PAD,
    KEYBOARD_TWITTER,
    KEYBOARD_URL,
    KEYBOARD_WEB_SEARCH,
    # --- Line and Text Layout ---
    LB_CHAR_WRAP,
    LB_CLIP,
    LB_TRUNCATE_HEAD,
    LB_TRUNCATE_MIDDLE,
    LB_TRUNCATE_TAIL,
    LB_WORD_WRAP,
    LINE_CAP_BUTT,
    LINE_CAP_ROUND,
    LINE_CAP_SQUARE,
    LINE_JOIN_BEVEL,
    LINE_JOIN_MITER,
    LINE_JOIN_ROUND,
    PY3,
    RECT_REGEX,
    # --- Rendering Modes ---
    RENDERING_MODE_AUTOMATIC,
    RENDERING_MODE_ORIGINAL,
    RENDERING_MODE_TEMPLATE,
)
from pytoui.ui._draw import (
    GState,
    ImageContext,
    Path,
    Transform,
    animate,
    cancel_delays,
    concat_ctm,
    convert_point,
    convert_rect,
    delay,
    draw_string,
    fill_rect,
    get_screen_size,
    get_ui_style,
    get_window_size,
    in_background,
    measure_string,
    parse_color,
    set_blend_mode,
    set_color,
    set_shadow,
)
from pytoui.ui._image import Image
from pytoui.ui._image_view import ImageView
from pytoui.ui._label import Label
from pytoui.ui._navigation_view import NavigationView
from pytoui.ui._scroll_view import ScrollView
from pytoui.ui._segmented_control import SegmentedControl
from pytoui.ui._serialize import (
    _bind_action,
    _color2str,
    _rect2str,
    _str2color,
    _str2rect,
    _view_from_dict,
    _view_to_dict,
)
from pytoui.ui._slider import Slider
from pytoui.ui._switch import Switch
from pytoui.ui._types import (
    MouseEvent,
    MouseWheel,
    Point,
    Rect,
    Size,
    Touch,
    Vector2,
    autoreleasepool,
)
from pytoui.ui._view import View

# backward compat


__all__ = (
    # Types
    "Vector2",
    "Rect",
    "Point",
    "Touch",
    "MouseEvent",
    "MouseWheel",
    "Size",
    "autoreleasepool",
    # View
    "View",
    "Transform",
    # Label
    "Label",
    # Button
    "Button",
    # ButtonItem
    "ButtonItem",
    # Switch
    "Switch",
    # SegmentedControl
    "SegmentedControl",
    # Image
    "Image",
    "ImageView",
    # ActivityIndicator
    "ActivityIndicator",
    # Slider
    "Slider",
    # ScrollView
    "ScrollView",
    # NavigationView
    "NavigationView",
    # Drawing
    "GState",
    "ImageContext",
    "parse_color",
    "set_color",
    "set_blend_mode",
    "set_shadow",
    "fill_rect",
    "concat_ctm",
    "draw_string",
    "measure_string",
    "Path",
    # animate / delay / threading
    "animate",
    "delay",
    "cancel_delays",
    "in_background",
    # system info
    "get_screen_size",
    "get_window_size",
    "get_ui_style",
    # convert
    "convert_point",
    "convert_rect",
    # Constants
    "PY3",
    # --- Regular Expressions ---
    "COLOR_REGEX",
    "RECT_REGEX",
    # --- Activity Indicator Styles ---
    "ACTIVITY_INDICATOR_STYLE_GRAY",
    "ACTIVITY_INDICATOR_STYLE_WHITE",
    "ACTIVITY_INDICATOR_STYLE_WHITE_LARGE",
    # --- Alignments ---
    "ALIGN_CENTER",
    "ALIGN_JUSTIFIED",
    "ALIGN_LEFT",
    "ALIGN_NATURAL",
    "ALIGN_RIGHT",
    "ALIGNMENTS",
    # --- Autocapitalization ---
    "AUTOCAPITALIZE_ALL",
    "AUTOCAPITALIZE_NONE",
    "AUTOCAPITALIZE_SENTENCES",
    "AUTOCAPITALIZE_WORDS",
    # --- Blending Modes ---
    "BLEND_CLEAR",
    "BLEND_COLOR",
    "BLEND_COLOR_BURN",
    "BLEND_COLOR_DODGE",
    "BLEND_COPY",
    "BLEND_DARKEN",
    "BLEND_DESTINATION_ATOP",
    "BLEND_DESTINATION_IN",
    "BLEND_DESTINATION_OUT",
    "BLEND_DESTINATION_OVER",
    "BLEND_DIFFERENCE",
    "BLEND_EXCLUSION",
    "BLEND_HARD_LIGHT",
    "BLEND_HUE",
    "BLEND_LIGHTEN",
    "BLEND_LUMINOSITY",
    "BLEND_MULTIPLY",
    "BLEND_NORMAL",
    "BLEND_OVERLAY",
    "BLEND_PLUS_DARKER",
    "BLEND_PLUS_LIGHTER",
    "BLEND_SATURATION",
    "BLEND_SCREEN",
    "BLEND_SOFT_LIGHT",
    "BLEND_SOURCE_ATOP",
    "BLEND_SOURCE_IN",
    "BLEND_SOURCE_OUT",
    "BLEND_XOR",
    # --- Content Modes ---
    "CONTENT_BOTTOM",
    "CONTENT_BOTTOM_LEFT",
    "CONTENT_BOTTOM_RIGHT",
    "CONTENT_CENTER",
    "CONTENT_LEFT",
    "CONTENT_REDRAW",
    "CONTENT_RIGHT",
    "CONTENT_SCALE_ASPECT_FILL",
    "CONTENT_SCALE_ASPECT_FIT",
    "CONTENT_SCALE_TO_FILL",
    "CONTENT_TOP",
    "CONTENT_TOP_LEFT",
    "CONTENT_TOP_RIGHT",
    # --- Correction Types ---
    "CORRECTION_TYPES",
    # --- Date Picker Modes ---
    "DATE_PICKER_MODE_COUNTDOWN",
    "DATE_PICKER_MODE_DATE",
    "DATE_PICKER_MODE_DATE_AND_TIME",
    "DATE_PICKER_MODE_TIME",
    # --- Keyboard Types ---
    "KEYBOARD_ASCII",
    "KEYBOARD_DECIMAL_PAD",
    "KEYBOARD_DEFAULT",
    "KEYBOARD_EMAIL",
    "KEYBOARD_NAME_PHONE_PAD",
    "KEYBOARD_NUMBERS",
    "KEYBOARD_NUMBER_PAD",
    "KEYBOARD_PHONE_PAD",
    "KEYBOARD_TWITTER",
    "KEYBOARD_URL",
    "KEYBOARD_WEB_SEARCH",
    # --- Line and Text Layout ---
    "LB_CHAR_WRAP",
    "LB_CLIP",
    "LB_TRUNCATE_HEAD",
    "LB_TRUNCATE_MIDDLE",
    "LB_TRUNCATE_TAIL",
    "LB_WORD_WRAP",
    "LINE_CAP_BUTT",
    "LINE_CAP_ROUND",
    "LINE_CAP_SQUARE",
    "LINE_JOIN_BEVEL",
    "LINE_JOIN_MITER",
    "LINE_JOIN_ROUND",
    # --- Rendering Modes ---
    "RENDERING_MODE_AUTOMATIC",
    "RENDERING_MODE_ORIGINAL",
    "RENDERING_MODE_TEMPLATE",
    # --- Serialization ---
    "_str2rect",
    "_str2color",
    "_rect2str",
    "_color2str",
    "_view_to_dict",
    "_view_from_dict",
    "_bind_action",
)
