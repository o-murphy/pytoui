from __future__ import annotations
import re
import os

# --- Regular Expressions ---
COLOR_REGEX: str = (
    "RGBA\\((\\d+\\.?\\d*),(\\d+\\.?\\d*),(\\d+\\.?\\d*),(\\d+\\.?\\d*)\\)"
)
RECT_REGEX: re.Pattern = re.compile(
    "\\{\\{(\\-?\\d+\\.?\\d*),\\s?(\\-?\\d+\\.?\\d*)\\},\\s?\\{(\\-?\\d+\\.?\\d*),\\s?(\\-?\\d+\\.?\\d*)\\}\\}"
)

# --- Activity Indicator Styles ---
ACTIVITY_INDICATOR_STYLE_GRAY: int = 2
ACTIVITY_INDICATOR_STYLE_WHITE: int = 1
ACTIVITY_INDICATOR_STYLE_WHITE_LARGE: int = 0

# --- Alignments ---
ALIGN_CENTER: int = 1
ALIGN_JUSTIFIED: int = 3
ALIGN_LEFT: int = 0
ALIGN_NATURAL: int = 4
ALIGN_RIGHT: int = 2
ALIGNMENTS: dict = {"left": 0, "right": 2, "center": 1}

# --- Autocapitalization ---
AUTOCAPITALIZE_ALL: int = 3
AUTOCAPITALIZE_NONE: int = 0
AUTOCAPITALIZE_SENTENCES: int = 2
AUTOCAPITALIZE_WORDS: int = 1

# --- Blending Modes ---
BLEND_CLEAR: int = 16
BLEND_COLOR: int = 14
BLEND_COLOR_BURN: int = 7
BLEND_COLOR_DODGE: int = 6
BLEND_COPY: int = 17
BLEND_DARKEN: int = 4
BLEND_DESTINATION_ATOP: int = 24
BLEND_DESTINATION_IN: int = 22
BLEND_DESTINATION_OUT: int = 23
BLEND_DESTINATION_OVER: int = 21
BLEND_DIFFERENCE: int = 10
BLEND_EXCLUSION: int = 11
BLEND_HARD_LIGHT: int = 9
BLEND_HUE: int = 12
BLEND_LIGHTEN: int = 5
BLEND_LUMINOSITY: int = 15
BLEND_MULTIPLY: int = 1
BLEND_NORMAL: int = 0
BLEND_OVERLAY: int = 3
BLEND_PLUS_DARKER: int = 26
BLEND_PLUS_LIGHTER: int = 27
BLEND_SATURATION: int = 13
BLEND_SCREEN: int = 2
BLEND_SOFT_LIGHT: int = 8
BLEND_SOURCE_ATOP: int = 20
BLEND_SOURCE_IN: int = 18
BLEND_SOURCE_OUT: int = 19
BLEND_XOR: int = 25

# --- Content Modes ---
CONTENT_BOTTOM: int = 6
CONTENT_BOTTOM_LEFT: int = 11
CONTENT_BOTTOM_RIGHT: int = 12
CONTENT_CENTER: int = 4
CONTENT_LEFT: int = 7
CONTENT_REDRAW: int = 3
CONTENT_RIGHT: int = 8
CONTENT_SCALE_ASPECT_FILL: int = 2
CONTENT_SCALE_ASPECT_FIT: int = 1
CONTENT_SCALE_TO_FILL: int = 0
CONTENT_TOP: int = 5
CONTENT_TOP_LEFT: int = 9
CONTENT_TOP_RIGHT: int = 10

# --- Correction Types ---
CORRECTION_TYPES: dict = {"yes": True, "no": False, "default": None}

# --- Date Picker Modes ---
DATE_PICKER_MODE_COUNTDOWN: int = 3
DATE_PICKER_MODE_DATE: int = 1
DATE_PICKER_MODE_DATE_AND_TIME: int = 2
DATE_PICKER_MODE_TIME: int = 0

# --- Keyboard Types ---
KEYBOARD_ASCII: int = 1
KEYBOARD_DECIMAL_PAD: int = 8
KEYBOARD_DEFAULT: int = 0
KEYBOARD_EMAIL: int = 7
KEYBOARD_NAME_PHONE_PAD: int = 6
KEYBOARD_NUMBERS: int = 2
KEYBOARD_NUMBER_PAD: int = 4
KEYBOARD_PHONE_PAD: int = 5
KEYBOARD_TWITTER: int = 9
KEYBOARD_URL: int = 3
KEYBOARD_WEB_SEARCH: int = 10

# --- Line and Text Layout ---
LB_CHAR_WRAP: int = 1
LB_CLIP: int = 2
LB_TRUNCATE_HEAD: int = 3
LB_TRUNCATE_MIDDLE: int = 5
LB_TRUNCATE_TAIL: int = 4
LB_WORD_WRAP: int = 0
LINE_CAP_BUTT: int = 0
LINE_CAP_ROUND: int = 1
LINE_CAP_SQUARE: int = 2
LINE_JOIN_BEVEL: int = 2
LINE_JOIN_MITER: int = 0
LINE_JOIN_ROUND: int = 1

# --- Rendering Modes ---
RENDERING_MODE_AUTOMATIC: int = 0
RENDERING_MODE_ORIGINAL: int = 1
RENDERING_MODE_TEMPLATE: int = 2


def _get_env_var(name: str, default: str):
    return os.environ.get(name, default).strip().strip().lower()


def _get_env_bool(name: str, default: str) -> bool:
    value: str = _get_env_var(name, default)
    return value in (
        "true",
        "1",
        "yes",
        "y",
    )


GLOBAL_UI_DISABLE_ANIMATIONS = _get_env_bool("UI_DISABLE_ANIMATIONS", "0")
GLOBAL_UI_ANTIALIAS = _get_env_bool("UI_ANTIALIAS", "1")
# Runtime environment options
_env_ui_runtime = _get_env_var("UI_RT", "sdl")
GLOBAL_UI_RT = _env_ui_runtime if _env_ui_runtime in ["sdl", "fb", "winit"] else "sdl"
GLOBAL_UI_RT_FPS = _get_env_bool("UI_RT_FPS", "0")
_env_ui_runtime_delay = _get_env_var("UI_RT_SDL_DELAY", "4")
if _env_ui_runtime_delay in {"1", "2", "4", "8", "16"}:
    GLOBAL_UI_RT_SDL_DELAY = int(_env_ui_runtime_delay)
else:
    GLOBAL_UI_RT_SDL_DELAY = 4

GLOBAL_UI_RT_SDL_MAX_DELAY = 16


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
    # Globals
    "GLOBAL_UI_DISABLE_ANIMATIONS",
    "GLOBAL_UI_RT",
    "GLOBAL_UI_ANTIALIAS",
    "GLOBAL_UI_RT_FPS",
    "GLOBAL_UI_RT_SDL_DELAY",
    "GLOBAL_UI_RT_SDL_MAX_DELAY",
)
