from pytoui.objc_util import ObjCInstance
from pytoui.ui import View, Rect


def test_objc_proxy():
    v = View()
    assert isinstance(v.objc_instance, ObjCInstance)
    assert callable(v.objc_instance)
    assert isinstance(v.objc_instance.dumb_prop, ObjCInstance)
    assert callable(v.objc_instance.dumb_prop)
    v.objc_instance.dumb_prop = "dumb value"
    assert callable(v.objc_instance.frame)
    assert isinstance(v.objc_instance.frame(), Rect)
    v.objc_instance.frame = (1, 1), (2, 2)
    assert v.frame == Rect(1, 1, 2, 2)
