from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    TypeVar,
    Union,
    cast,
    overload,
)

from pytoui._platform import IS_PYTHONISTA

if TYPE_CHECKING:
    from pytoui.ui._types import _UiStyle


__all__ = (
    "_final_",
    "_getset_descriptor",
    "get_ui_style",
    "settrace",
)


__T = TypeVar("__T", bound=type)


def _final_(cls: __T) -> __T:
    """Decorator to mark class as a non-accessible base class."""

    def __init_subclass__(subcls: type, /, **kwargs: Any) -> None:
        raise TypeError(f"{cls.__name__} is not an acceptable base type")

    cast(Any, cls).__init_subclass__ = classmethod(__init_subclass__)
    return cls


__ClassT = TypeVar("__ClassT")
__PropT = TypeVar("__PropT")


class _getset_descriptor(Generic[__ClassT, __PropT]):
    def __init__(
        self,
        name: str,
        factory: Callable[[__ClassT], __PropT] | None = None,
        readonly: bool = True,
    ):
        self._public_name = name
        self._mangled_name: str = f"__{name}"
        self._factory = factory
        self._readonly: bool = readonly

    def __set_name__(self, owner: type[__ClassT], name: str):
        self._mangled_name = (
            f"_{owner.__name__.lstrip('_')}__{self._public_name.lstrip('_')}"
        )

    @overload
    def __get__(
        self, obj: None, objtype: type[__ClassT] | None = None
    ) -> _getset_descriptor[__ClassT, __PropT]: ...

    @overload
    def __get__(
        self, obj: __ClassT, objtype: type[__ClassT] | None = None
    ) -> __PropT: ...

    def __get__(
        self, obj: __ClassT | None, objtype: type[__ClassT] | None = None
    ) -> Union["_getset_descriptor"[__ClassT, __PropT], __PropT]:
        if obj is None:
            return self
        if not hasattr(obj, self._mangled_name):
            if self._factory is None:
                raise AttributeError(f"{self._public_name} not initialized")
            setattr(obj, self._mangled_name, self._factory(obj))
        return getattr(obj, self._mangled_name)

    def __set__(self, obj: __ClassT, value: __PropT):
        if self._readonly:
            raise AttributeError()
        setattr(obj, self._mangled_name, value)

    def __delete__(self, obj: __ClassT):
        raise AttributeError(f"Can't delete {self._public_name} attribute")


def settrace(func: Callable | None) -> None:
    # FIXME: implement
    if __debug__:
        import warnings

        warnings.warn(
            "settrace() is not yet implemented in pytoui",
            UserWarning,
            stacklevel=2,
        )


def get_ui_style() -> _UiStyle:
    """Return the current UI style: 'dark' or 'light'.

    Controlled by the UI_STYLE environment variable (default: 'dark').
    """
    import os

    style = os.environ.get("UI_STYLE", "light").lower()
    return cast(_UiStyle, style if style in ("dark", "light") else "dark")


if IS_PYTHONISTA:
    from ui import get_ui_style  # type: ignore[import-not-found,no-redef,assignment]
