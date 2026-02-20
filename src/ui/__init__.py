"""
Pythonista-compatible UI framework for framebuffer rendering.

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

from ui._types import (
    Vector2,
    Rect,
    Point,
    Size,
    Touch,
    autoreleasepool,
)
from ui._view import View
from ui._label import Label
from ui._button import Button
from ui._switch import Switch
from ui._segmented_control import SegmentedControl
from ui._activity_indicator import ActivityIndicator
from ui._slider import Slider
from ui._image import Image
from ui._imageview import ImageView
from ui._draw import (
    GState,
    ImageContext,
    parse_color,
    set_color,
    set_blend_mode,
    set_shadow,
    fill_rect,
    concat_ctm,
    begin_path,
    draw_string,
    measure_string,
    convert_point,
    convert_rect,
    animate,
    delay,
    cancel_delays,
    in_background,
    get_screen_size,
    get_window_size,
    get_ui_style,
    Path,
    Transform,
)

from ui._constants import (
    # --- Regular Expressions ---
    COLOR_REGEX,
    RECT_REGEX,
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
    KEYBOARD_NUMBERS,
    KEYBOARD_NUMBER_PAD,
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
    # --- Rendering Modes ---
    RENDERING_MODE_AUTOMATIC,
    RENDERING_MODE_ORIGINAL,
    RENDERING_MODE_TEMPLATE,
)

# backward compat


__all__ = (
    # Types
    "Vector2",
    "Rect",
    "Point",
    "Touch",
    "Size",
    "autoreleasepool",
    # View
    "View",
    "Transform",
    # Label
    "Label",
    # Button
    "Button",
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
    # Drawing
    "GState",
    "ImageContext",
    "parse_color",
    "set_color",
    "set_blend_mode",
    "set_shadow",
    "fill_rect",
    "concat_ctm",
    "begin_path",
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
)
