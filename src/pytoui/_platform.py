"""Platform detection for pytoui.

IS_PYTHONISTA    True when running inside Pythonista on iOS/iPadOS.
_pui             Reference to Pythonista's native `ui` module, or None on desktop.
"""

from __future__ import annotations

try:
    import ui as _pui  # type: ignore[import-not-found]

    IS_PYTHONISTA: bool = True
except ImportError:
    _pui = None  # type: ignore[assignment]
    IS_PYTHONISTA: bool = False  # type: ignore[no-redef]

__all__ = ("IS_PYTHONISTA", "_pui")
