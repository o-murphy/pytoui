from pytoui.ui import View
from pytoui.objc_util import ObjCInstance


def test_objc_proxy():
    v = View()
    assert isinstance(v.objc_instance, ObjCInstance)
    assert callable(v.objc_instance)
    assert isinstance(v.objc_instance.dumb_prop, ObjCInstance)
    assert callable(v.objc_instance.dumb_prop)
    v.objc_instance.dumb_prop = "dumb value"
    v.objc_instance.dumb_prop()
