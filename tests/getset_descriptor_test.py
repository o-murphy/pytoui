import pytest


class getset_descriptor:
    def __init__(self, name: str, default_value=1.0):
        self.public_name = name
        self.default_value = default_value
        self.mangled_name = None  # Обчислимо пізніше
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
        return None  # self

    def setter(self, func):
        self._setter = func
        return None  # self


class _ViewMeta(type):
    def __new__(mcls, name, bases, namespace, **kwargs):
        for base in bases:
            if getattr(base, "__final__", False):
                raise TypeError(f"{base.__name__} cannot be subclassed")
        return super().__new__(mcls, name, bases, namespace, **kwargs)


class _view(object):
    __final__ = False
    __slots__ = ("__alpha", "__beta")

    alpha: getset_descriptor = getset_descriptor("alpha", 1.0)
    beta: getset_descriptor = getset_descriptor("beta", "hello")

    @alpha.setter
    def __set_alpha(self, value):
        # Тепер setattr спрацює, бо ми вказуємо точне спотворене ім'я
        setattr(self, _view.alpha.mangled_name, value)


class View(_view, metaclass=_ViewMeta):
    __final__ = False

    @_view.beta.setter
    def __beta(self, value: str):
        setattr(self, _view.beta.mangled_name, str(value) + "Bar")

    @_view.beta.getter
    def __beta(self) -> str:
        return getattr(self, _view.beta.mangled_name, "")


class Mixin:
    def help(self):
        return "HELP"


class View2(View, Mixin):
    __final__ = True

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


# --- Код класів (GetSetAttribute, View, тощо) залишається без змін ---
# Припустимо, вони імпортовані або знаходяться вище


def test_view_base_alpha():
    """Перевірка базового встановлення та отримання alpha"""
    v = _view()
    v.alpha = 5
    assert v.alpha == 5
    assert hasattr(v, "_view__alpha")  # Перевірка mangling у slots


def test_view2_inheritance_and_mangling():
    """Перевірка, що View2 правильно працює з атрибутами базового класу"""
    v2 = View2()
    v2.alpha = 10
    # Перевіряємо, що значення повернулося 10, а не дефолтне 1.0
    assert v2.alpha == 10
    # Перевіряємо кастомну логіку beta (Bar -> BarBar)
    assert v2.beta == "BarBar"


def test_encapsulation_privacy():
    """Перевірка, що прямий доступ до __beta заборонений"""
    v2 = View2()
    with pytest.raises(AttributeError):
        _ = v2.__beta


def test_final_class_violation():
    """Перевірка метакласу: заборона наслідування від фінального класу"""
    with pytest.raises(TypeError, match="View2 cannot be subclassed"):

        class View3(View2):
            pass


def test_no_setter_error():
    """Перевірка викидання AttributeError, якщо сеттер не визначено"""

    # Створимо тимчасовий клас без сеттера для тесту
    class ReadOnlyView(_view, metaclass=_ViewMeta):
        gamma = getset_descriptor("gamma", 1.0)

    ro = ReadOnlyView()
    with pytest.raises(AttributeError, match="property 'gamma' has no setter"):
        ro.gamma = 20


def test_delete_prohibited():
    """Перевірка заборони видалення атрибута"""
    v = _view()
    with pytest.raises(AttributeError, match="Can't delete alpha attribute"):
        del v.alpha


def test_mixin_integration():
    """Перевірка, що Mixin працює разом із нашою ієрархією"""
    v2 = View2()
    assert v2.help() == "HELP"


def test_slots_efficiency():
    """Перевірка, що __dict__ відсутній (економія пам'яті через slots)"""
    v = _view()
    assert not hasattr(v, "__dict__")
