import pytest

from pytoui.ui._final import _final_


class getset_descriptor:
    def __init__(self, name: str, default_value=1.0):
        self.public_name = name
        self.default_value = default_value
        self.mangled_name = None
        self._getter = None
        self._setter = None

    def __set_name__(self, owner, name):
        class_name = owner.__name__.lstrip("_")
        self.mangled_name = f"_{class_name}__{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if self._getter is not None:
            return self._getter(obj)

        return getattr(obj, self.mangled_name, self.default_value)

    def __set__(self, obj, value):
        if self._setter is not None:
            self._setter(obj, value)
        else:
            raise AttributeError(f"property '{self.public_name}' has no setter")

    def __delete__(self, obj):
        raise AttributeError(f"Can't delete {self.public_name} attribute")

    def getter(self, func):
        self._getter = func

    def setter(self, func):
        self._setter = func


class _view:
    __slots__ = ("__alpha", "__beta")

    alpha: getset_descriptor = getset_descriptor("alpha", 1.0)
    beta: getset_descriptor = getset_descriptor("beta", "hello")

    @alpha.setter
    def __set_alpha(self, value):
        setattr(self, _view.alpha.mangled_name, value)


class View(_view):
    @_view.beta.setter
    def __beta(self, value: str):
        setattr(self, _view.beta.mangled_name, str(value) + "Bar")

    @_view.beta.getter
    def __beta(self) -> str:
        return getattr(self, _view.beta.mangled_name, "")


class Mixin:
    def help(self):
        return "HELP"


@_final_
class View2(View, Mixin):
    def __init__(self):
        self.beta = "Bar"


# --- Testing ---


try:

    class View3(View2):
        def __init__(self):
            self.beta = "Bar"
except TypeError as e:
    print("TypeError", e)


print("--- View ---")
v = _view()
v.alpha = 5
print(f"Alpha: {v.alpha}")  # 5.0

print("\n--- View2 ---")
v2 = View2()
v2.alpha = 10
print(f"Alpha: {v2.alpha}")  # 10.0

print(f"Beta: {v2.beta}")  # FooBar

try:
    print(v2.__beta)
except AttributeError as e:
    print("AttributeError", e)


def test_view_base_alpha():
    v = _view()
    v.alpha = 5
    assert v.alpha == 5
    assert hasattr(v, "_view__alpha")


def test_view2_inheritance_and_mangling():
    v2 = View2()
    v2.alpha = 10
    assert v2.alpha == 10
    assert v2.beta == "BarBar"


def test_encapsulation_privacy():
    v2 = View2()
    with pytest.raises(AttributeError):
        _ = v2.__beta


def test_final_class_violation():
    with pytest.raises(TypeError, match="View3 is not an acceptable base type"):

        class View3(View2):
            pass


def test_no_setter_error():
    class ReadOnlyView(_view):
        gamma = getset_descriptor("gamma", 1.0)

    ro = ReadOnlyView()
    with pytest.raises(AttributeError, match="property 'gamma' has no setter"):
        ro.gamma = 20


def test_delete_prohibited():
    v = _view()
    with pytest.raises(AttributeError, match="Can't delete alpha attribute"):
        del v.alpha


def test_mixin_integration():
    v2 = View2()
    assert v2.help() == "HELP"


def test_slots_efficiency():
    v = _view()
    assert not hasattr(v, "__dict__")
