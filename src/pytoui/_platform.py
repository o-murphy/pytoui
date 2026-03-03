"""Platform detection for pytoui.

IS_PYTHONISTA    True when running inside Pythonista on iOS/iPadOS.
_pui             Reference to Pythonista's native `ui` module, or None on desktop.
"""

from __future__ import annotations

import os
import re
import sys

PYTHONISTA_EXECUTABLE_REGEX = re.escape("Pythonista3.app")


def is_pythonista():
    if sys.platform == "ios" and re.search(PYTHONISTA_EXECUTABLE_REGEX, sys.executable):
        return True
    return False


if is_pythonista():
    try:
        import ui as _pui

        IS_PYTHONISTA: bool = True
    except (AssertionError, ImportError):
        _pui = None  # type: ignore[no-redef,assignment]
        IS_PYTHONISTA: bool = False  # type: ignore[no-redef,assignment]
else:
    _pui = None  # type: ignore[no-redef,assignment]
    IS_PYTHONISTA: bool = False  # type: ignore[no-redef,assignment]


__all__ = (
    "IS_PYTHONISTA",
    "_pui",
    "pytoui_desktop_only",
    # Globals
    "_UI_DISABLE_ANIMATIONS",
    "_UI_RT",
    "_UI_ANTIALIAS",
    "_UI_RT_FPS",
    "_UI_RT_SDL_DELAY",
    "_UI_RT_SDL_MAX_DELAY",
    "_UI_FORCE_PYTOUI_VIEWS",
    "_UI_DISABLE_WINIT_CSD",
)


def pytoui_desktop_only(func):
    def wrapper(*args, **kwargs):
        if IS_PYTHONISTA:
            raise RuntimeError(
                f"{func.__name__} can be used only on non-Pythonista runtime",
            )
        return func(*args, **kwargs)

    return wrapper


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


_UI_DISABLE_ANIMATIONS = _get_env_bool("UI_DISABLE_ANIMATIONS", "0")
_UI_ANTIALIAS = _get_env_bool("UI_ANTIALIAS", "1")
# Runtime environment options
_env_ui_runtime = _get_env_var("UI_RT", "winit")
_UI_RT = _env_ui_runtime if _env_ui_runtime in {"sdl", "fb", "winit"} else "winit"
_UI_RT_FPS = _get_env_bool("UI_RT_FPS", "0")
_env_ui_runtime_delay = _get_env_var("UI_RT_SDL_DELAY", "4")
if _env_ui_runtime_delay in {"1", "2", "4", "8", "16"}:
    _UI_RT_SDL_DELAY = int(_env_ui_runtime_delay)
else:
    _UI_RT_SDL_DELAY = 4

_UI_RT_SDL_MAX_DELAY = 16

_UI_FORCE_PYTOUI_VIEWS = _get_env_bool("UI_FORCE_PYTHOUI_VIEWS", "0")

# winit: use Client-Side Decorations (drawn by sctk).
# Default 0 = no winit CSD; compositor draws SSD if supported (e.g. KDE Plasma).
# Set UI_WINIT_CSD=1 on compositors without SSD support (e.g. GNOME).
_UI_DISABLE_WINIT_CSD = _get_env_bool("UI_DISABLE_WINIT_CSD", "0")
