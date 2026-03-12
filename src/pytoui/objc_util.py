from typing import Any
from warnings import warn
import ctypes

from pytoui._platform import IS_PYTHONISTA

__all__ = ("ObjCInstance",)


class _ObjCInstanceProxy:
    __slots__ = ("_instance",)

    def __new__(cls, instance: object | int | None = None, *args, **kwargs):
        # якщо передали адресу python-об'єкта
        if isinstance(instance, int):
            try:
                obj = ctypes.cast(instance, ctypes.py_object).value
                if isinstance(obj, cls):
                    return obj
            except Exception:
                pass

        return super().__new__(cls)

    def __init__(self, instance: object | None = None, *args, **kwargs):
        object.__setattr__(self, "_instance", instance)

    def __call__(self, *args, **kwargs):
        warn(
            f"Attempt to call native {self.__class__.__name__} method is ignored",
            UserWarning,
        )

    def __getattr__(self, name: str):
        instance = object.__getattribute__(self, "_instance")

        if instance is not None:
            try:
                return getattr(instance, name)
            except AttributeError:
                pass

        warn(
            f"Attempt to call native {self.__class__.__name__}.{name} "
            "getter is ignored, returning dumb ObjCInstance",
            UserWarning,
        )
        return _ObjCInstanceProxy()

    def __setattr__(self, name: str, value: Any):
        if name == "_instance":
            object.__setattr__(self, name, value)
            return

        instance = object.__getattribute__(self, "_instance")

        if instance is not None and hasattr(instance, name):
            setattr(instance, name, value)
            return

        warn(
            f"Attempt to call native {self.__class__.__name__}.{name} "
            "setter is ignored",
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
    from objc_util import ObjCInstance  # type: ignore


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
