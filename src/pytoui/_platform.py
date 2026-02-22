"""Platform detection for pytoui.

IS_PYTHONISTA    True when running inside Pythonista on iOS/iPadOS.
_pui             Reference to Pythonista's native `ui` module, or None on desktop.
"""

from __future__ import annotations
import os

try:
    import ui as _pui  # type: ignore[import-not-found]

    IS_PYTHONISTA: bool = True
except ImportError:
    _pui = None  # type: ignore[assignment]
    IS_PYTHONISTA: bool = False  # type: ignore[no-redef]


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

__all__ = (
    "IS_PYTHONISTA",
    "_pui",
    # Globals
    "_UI_DISABLE_ANIMATIONS",
    "_UI_RT",
    "_UI_ANTIALIAS",
    "_UI_RT_FPS",
    "_UI_RT_SDL_DELAY",
    "_UI_RT_SDL_MAX_DELAY",
)
