from __future__ import annotations

import re
from typing import Literal

# --- Regular Expressions ---
COLOR_REGEX: str = (
    "RGBA\\((\\d+\\.?\\d*),(\\d+\\.?\\d*),(\\d+\\.?\\d*),(\\d+\\.?\\d*)\\)"
)
RECT_REGEX: re.Pattern = re.compile(
    "\\{\\{(\\-?\\d+\\.?\\d*),\\s?(\\-?\\d+\\.?\\d*)\\},\\s?\\{(\\-?\\d+\\.?\\d*),\\s?(\\-?\\d+\\.?\\d*)\\}\\}",
)

# --- Activity Indicator Styles ---
ACTIVITY_INDICATOR_STYLE_GRAY: Literal[2] = 2
ACTIVITY_INDICATOR_STYLE_WHITE: Literal[1] = 1
ACTIVITY_INDICATOR_STYLE_WHITE_LARGE: Literal[0] = 0

# --- Alignments ---
ALIGN_CENTER: Literal[1] = 1
ALIGN_JUSTIFIED: Literal[3] = 3
ALIGN_LEFT: Literal[0] = 0
ALIGN_NATURAL: Literal[4] = 4
ALIGN_RIGHT: Literal[2] = 2
ALIGNMENTS: dict = {"left": 0, "right": 2, "center": 1}

# --- Autocapitalization ---
AUTOCAPITALIZE_ALL: Literal[3] = 3
AUTOCAPITALIZE_NONE: Literal[0] = 0
AUTOCAPITALIZE_SENTENCES: Literal[2] = 2
AUTOCAPITALIZE_WORDS: Literal[1] = 1

# --- Blending Modes ---
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

# --- Content Modes ---
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

# --- Correction Types ---
CORRECTION_TYPES: dict = {"yes": True, "no": False, "default": None}

# --- Date Picker Modes ---
DATE_PICKER_MODE_COUNTDOWN: Literal[3] = 3
DATE_PICKER_MODE_DATE: Literal[1] = 1
DATE_PICKER_MODE_DATE_AND_TIME: Literal[2] = 2
DATE_PICKER_MODE_TIME: Literal[0] = 0

# --- Keyboard Types ---
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

# --- Line and Text Layout ---
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

# --- Rendering Modes ---
RENDERING_MODE_AUTOMATIC: Literal[0] = 0
RENDERING_MODE_ORIGINAL: Literal[1] = 1
RENDERING_MODE_TEMPLATE: Literal[2] = 2


__all__ = (
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

# ── Pythonista shim ────────────────────────────────────────────────────────────

from pytoui._platform import IS_PYTHONISTA

if IS_PYTHONISTA:
    from ui import (  # type: ignore[import-not-found,no-redef]
        ACTIVITY_INDICATOR_STYLE_GRAY,
        ACTIVITY_INDICATOR_STYLE_WHITE,
        ACTIVITY_INDICATOR_STYLE_WHITE_LARGE,
        ALIGN_CENTER,
        ALIGN_JUSTIFIED,
        ALIGN_LEFT,
        ALIGN_NATURAL,
        ALIGN_RIGHT,
        AUTOCAPITALIZE_ALL,
        AUTOCAPITALIZE_NONE,
        AUTOCAPITALIZE_SENTENCES,
        AUTOCAPITALIZE_WORDS,
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
        DATE_PICKER_MODE_COUNTDOWN,
        DATE_PICKER_MODE_DATE,
        DATE_PICKER_MODE_DATE_AND_TIME,
        DATE_PICKER_MODE_TIME,
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
        RENDERING_MODE_AUTOMATIC,
        RENDERING_MODE_ORIGINAL,
        RENDERING_MODE_TEMPLATE,
    )
