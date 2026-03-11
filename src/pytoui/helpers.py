from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING

from pytoui._platform import IS_PYTHONISTA

if TYPE_CHECKING:
    from pytoui.ui._view import View


__all__ = (
    "modal_protect_on",
    "modal_protect_off",
    "sheet_gesture_on",
    "sheet_gesture_off",
)

if IS_PYTHONISTA:
    from objc_util import ObjCClass, ObjCInstance  # type: ignore[import-not-found]

    def _get_presented_vc(view: View):
        try:
            o = ObjCInstance(view._objc_ptr)
            window = o.window()
            root = window.rootViewController()
            vc = root.presentedViewController()
            return vc
        except Exception:
            return None

    def _get_view_controller(view: "View"):
        try:
            o = ObjCInstance(view._objc_ptr)
            r = o
            while r:
                r = r.nextResponder()
                if r and r.isKindOfClass_(ObjCClass("UIViewController")):
                    return r
        except Exception:
            return None

    # def _set_modal_presentation(view: "View", value: bool):
    #     vc = _get_view_controller(view)
    #     if vc:
    #         vc.setModalInPresentation_(bool(value))

    def _set_modal_presentation(view: View, value: bool):
        vc = _get_presented_vc(view)
        if vc:
            vc.setModalInPresentation_(bool(value))

    def _set_sheet_gesture(view: "View", enabled: bool):
        vc = _get_view_controller(view)
        if not vc:
            return
        try:
            gestures = vc.view().gestureRecognizers()
            if gestures:
                for g in gestures:
                    g.setEnabled_(enabled)
        except Exception:
            pass

else:

    def _set_modal_presentation(view: View, value: bool):
        pass

    def _set_sheet_gesture(view: "View", enabled: bool):
        pass


def modal_protect_on(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            _set_modal_presentation(self, True)
        except Exception:
            pass
        return fn(self, *args, **kwargs)

    return wrapper


def modal_protect_off(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            _set_modal_presentation(self, False)
        except Exception:
            pass
        return fn(self, *args, **kwargs)

    return wrapper


def sheet_gesture_off(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            _set_sheet_gesture(self, False)
        except Exception:
            pass
        return fn(self, *args, **kwargs)

    return wrapper


def sheet_gesture_on(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            _set_sheet_gesture(self, True)
        except Exception:
            pass
        return fn(self, *args, **kwargs)

    return wrapper
