from typing import Any
from warnings import warn

from pytoui._platform import IS_PYTHONISTA

__all__ = ("ObjCInstance",)


class _ObjCInstanceProxy(object):
    def __init__(self, instance: object = None, *args, **kwargs):
        self._instance = instance

    def __call__(self, *args, **kwargs):
        warn(
            "Attempt to call native ObjCInstance method is ignored",
            UserWarning,
        )

    def __getattr__(self, name: str):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            warn(
                f"Attempt to call native ObjCInstance.{name} getter is ignored, "
                "returning dumb ObjCInstance",
                UserWarning,
            )
            return _ObjCInstanceProxy()

    def __setattr__(self, name: str, value: Any):
        try:
            if super().__getattribute__(name):
                super().__setattr__(name, value)
            else:
                raise AttributeError
        except AttributeError:
            warn(
                f"Attempt to call native ObjCInstance.{name} setter is ignored",
                UserWarning,
            )


class _NamedObjCInstance(_ObjCInstanceProxy):
    @property
    def name(self) -> str:
        print("Get name")
        return "test"

    @name.setter
    def name(self, value: str):
        print(f"Set name: {value}")


if not IS_PYTHONISTA:
    ObjCInstance = _ObjCInstanceProxy
else:
    from objc_util import (  # type: ignore[assignment,import-not-found,no-redef]
        ObjCInstance,
    )


if __name__ == "__main__":
    o = _NamedObjCInstance()

    # getter native prop
    print(o.nativeProperty)

    # getter defined prop
    print(o.name)

    # setter native prop
    o.nativeProperty = "nativeValue"

    # setter defined prop
    o.name = "some_name"

    # method
    o.callNativeMethod_("arg", kw="kwarg")
