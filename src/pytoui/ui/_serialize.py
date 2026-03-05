import re
import sys
from typing import TYPE_CHECKING, Any

from pytoui._platform import IS_PYTHONISTA
from pytoui.ui._constants import COLOR_REGEX, RECT_REGEX
from ui import View

if TYPE_CHECKING:
    from pytoui.ui._types import _RGBA, _ColorLike, _RectLike

__all__ = (
    "_str2rect",
    "_str2color",
    "_rect2str",
    "_color2str",
    "_view_to_dict",
    "_view_from_dict",
    "_bind_action",
)


def _str2rect(rect_str: str) -> tuple[float, ...] | None:
    m = re.match(RECT_REGEX, rect_str)
    if m:
        return tuple([float(s) for s in m.groups()])
    return None


def _str2color(color_str: str, default: _ColorLike = None):
    if not color_str:
        return default
    m = re.match(COLOR_REGEX, color_str)
    if m:
        return tuple([float(s) for s in m.groups()])
    return default


def _rect2str(rect: _RectLike) -> str:
    if not len(rect) == 4:
        raise TypeError("Expected a sequence of length 4")
    return "{{%s,%s},{%s,%s}}" % (rect[0], rect[1], rect[2], rect[3])


def _color2str(color: _RGBA | None) -> str | None:
    if not color:
        return None
    if not len(color) == 4:
        raise TypeError("Expected a sequence of length 4")
    return "RGBA(%f,%f,%f,%f)" % (color[0], color[1], color[2], color[3])


def _view_to_dict(view: View) -> dict[str, Any]:
    """Serialize view hierarchy to dict.

    Recursively converts view and all subviews to dict.
    Saves:
    - "class": classname (a.g., "Button")
    - "frame": [x, y, w, h]
    - "flex": str flex
    - "background_color": color _color2str
    - "name": view name
    - "subviews": list of dicts for each child of a view
    - Class specific attrs:
      * Button: "title", "action" (method name), "font", "enabled"
      * Label: "text", "font", "text_color", "alignment", "number_of_lines"
      * ImageView: "image" (save path), "content_mode"
      * ScrollView: "content_size", "scroll_enabled", "paging_enabled"
      * Switch: "value", "enabled"
      * Slider: "value", "continuous"
      * SegmentedControl: "segments", "selected_index"
      * TextField: "text", "placeholder", "secure", "keyboard_type"

    Uses for saving UI state.
    """
    return {}
    # if not isinstance(view, View):
    #     raise TypeError("Expected a ui.View or subclass")
    # view_dict = {}
    # view_dict["frame"] = _rect2str(view.frame)
    # class_name = type(view).__name__
    # if class_name not in dir(_ui):
    #     class_name = "View"
    # view_dict["class"] = class_name
    # if view.subviews:
    #     view_dict["nodes"] = [_view_to_dict(v) for v in view.subviews]
    # attrs = {}
    # view_dict["attributes"] = attrs
    # attrs["flex"] = view.flex
    # attrs["alpha"] = view.alpha
    # attrs["name"] = view.name
    # attrs["background_color"] = _color2str(view.background_color)
    # attrs["tint_color"] = _color2str(view.tint_color)
    # attrs["border_width"] = view.border_width
    # attrs["border_color"] = _color2str(view.border_color)
    # attrs["corner_radius"] = view.corner_radius
    # alignments = {ALIGN_LEFT: "left", ALIGN_RIGHT: "right", ALIGN_CENTER: "center"}
    # correction_types = {True: "yes", False: "no", None: "default"}

    # def _set_action_name(view_attrs, action, key="action"):
    #     try:
    #         if inspect.ismethod(action):
    #             # Assuming the most common case here,
    #             # this won't work for everything...
    #             view_attrs[key] = "self." + action.__name__
    #         else:
    #             view_attrs[key] = action.__name__
    #     except Exception:
    #         pass

    # if class_name == "View" and not type(view) == View:
    #     attrs["custom_class"] = type(view).__name__
    # if isinstance(view, (Label, TextField, TextView)):
    #     attrs["text"] = view.text
    #     font_name, font_size = view.font
    #     attrs["font_name"] = font_name
    #     attrs["font_size"] = font_size
    #     attrs["alignment"] = alignments.get(view.alignment, "left")
    #     attrs["text_color"] = _color2str(view.text_color)
    # if isinstance(view, Label):
    #     attrs["number_of_lines"] = view.number_of_lines
    # if isinstance(view, TextField):
    #     attrs["placeholder"] = view.placeholder or ""
    #     attrs["secure"] = view.secure
    #     attrs["autocorrection_type"] = correction_types[view.autocorrection_type]
    #     attrs["spellchecking_type"] = correction_types[view.spellchecking_type]
    #     _set_action_name(attrs, view.action)
    # if isinstance(view, TextView):
    #     attrs["autocorrection_type"] = correction_types[view.autocorrection_type]
    #     attrs["spellchecking_type"] = correction_types[view.spellchecking_type]
    #     attrs["editable"] = view.editable
    # if isinstance(view, Button):
    #     attrs["title"] = view.title
    #     if view.image and view.image.name:
    #         attrs["image_name"] = view.image.name
    #     font_name, font_size = view.font
    #     attrs["font_name"] = font_name
    #     attrs["font_size"] = font_size
    #     _set_action_name(attrs, view.action)
    # if isinstance(view, Slider):
    #     attrs["value"] = view.value
    #     attrs["continuous"] = view.continuous
    #     _set_action_name(attrs, view.action)
    # if isinstance(view, Switch):
    #     attrs["value"] = view.value
    #     _set_action_name(attrs, view.action)
    # if isinstance(view, SegmentedControl):
    #     attrs["segments"] = "|".join(view.segments)
    #     _set_action_name(attrs, view.action)
    # if isinstance(view, WebView):
    #     attrs["scales_to_fit"] = view.scales_page_to_fit
    # if isinstance(view, TableView):
    #     attrs["row_height"] = view.row_height
    #     attrs["editing"] = view.editing
    #     if isinstance(view.data_source, ListDataSource) and isinstance(
    #         view.delegate, ListDataSource
    #     ):
    #         data_source = view.data_source
    #         _set_action_name(attrs, data_source.action, "data_source_action")
    #         _set_action_name(
    #             attrs, data_source.edit_action, "data_source_edit_action"
    #         )
    #         _set_action_name(
    #             attrs, data_source.accessory_action, "data_source_accessory_action"
    #         )
    #         attrs["data_source_number_of_lines"] = data_source.number_of_lines
    #         attrs["data_source_move_enabled"] = data_source.move_enabled
    #         attrs["data_source_delete_enabled"] = data_source.delete_enabled
    #         _, font_size = data_source.font
    #         attrs["data_source_font_size"] = font_size
    #         try:
    #             # NOTE: This only works if the data source's items are all strings
    #             #       (which is the common case)
    #             attrs["data_source_items"] = "\n".join(data_source.items)
    #         except:
    #             pass
    #     else:
    #         attrs["data_source_number_of_lines"] = 0
    #         attrs["data_source_move_enabled"] = False
    #         attrs["data_source_delete_enabled"] = False
    #         attrs["data_source_font_size"] = 18
    #         attrs["data_source_items"] = ""
    # if isinstance(view, DatePicker):
    #     attrs["mode"] = view.mode
    #     _set_action_name(attrs, view.action)
    # if isinstance(view, ScrollView):
    #     attrs["content_width"] = int(view.content_size[0])
    #     attrs["content_height"] = int(view.content_size[1])
    # if isinstance(view, ImageView):
    #     if view.image and view.image.name:
    #         attrs["image_name"] = view.image.name
    # # TODO: Support NavigationView properly...
    # return view_dict


def _view_from_dict(
    view_dict: dict[str, Any], f_globals, f_locals, verbose: bool = True
) -> View:
    """Deserialize view hierarchy from dict.

    Creates view from dict, recursivelly creates subviews.
    Uses for load UI state.

    Expects same format as _view_to_dict.

    For action saves method name as a str,
    which can be bind then with _bind_action.
    """
    return View()
    # attrs = view_dict.get("attributes", {})
    # classname = view_dict.get("class", "View")
    # ViewClass = _ui.__dict__.get(classname)
    # if not ViewClass:
    #     return None

    # custom_class_str = attrs.get("custom_class")
    # if custom_class_str:
    #     try:
    #         CustomViewClass = eval(custom_class_str, f_globals, f_locals)
    #         if inspect.isclass(CustomViewClass) and issubclass(CustomViewClass, View):
    #             ViewClass = CustomViewClass
    #         elif verbose:
    #             sys.stderr.write(
    #                 'Warning: Invalid custom view class "%s"' % (custom_class_str,)
    #             )
    #     except Exception as e:
    #         if verbose:
    #             sys.stderr.write(
    #                 "Warning: Could not resolve custom view class: %s\n" % (e,)
    #             )

    # if classname == "NavigationView":
    #     # Special case for ui.NavigationView: Subviews are added to an
    #     # implicitly-created root view instead of the NavigationView itself.
    #     root_view = View()
    #     root_view.name = attrs.get("root_view_name")
    #     root_view.background_color = _str2color(
    #         attrs.get("background_color"), "white"
    #     )
    #     subview_dicts = view_dict.get("nodes", [])
    #     if subview_dicts:
    #         for d in subview_dicts:
    #             subview = _view_from_dict(d, f_globals, f_locals, verbose=verbose)
    #             if subview:
    #                 root_view.add_subview(subview)
    #         del view_dict["nodes"]
    #     v = NavigationView(root_view)
    #     v.title_color = _str2color(attrs.get("title_color"))
    #     v.bar_tint_color = _str2color(attrs.get("title_bar_color"))
    # else:
    #     v = ViewClass()

    # v.frame = _str2rect(view_dict.get("frame"))
    # v.flex = attrs.get("flex", "")
    # v.alpha = attrs.get("alpha", 1.0)
    # v.name = attrs.get("name")
    # v.background_color = _str2color(attrs.get("background_color"), "clear")
    # v.tint_color = _str2color(attrs.get("tint_color"))
    # v.border_width = attrs.get("border_width", 0)
    # v.border_color = _str2color(attrs.get("border_color"))
    # v.corner_radius = attrs.get("corner_radius", 0)
    # if classname == "Label":
    #     v.text = attrs.get("text", "")
    #     font_name = attrs.get("font_name", "<System>")
    #     font_size = attrs.get("font_size", 17)
    #     v.font = (font_name, font_size)
    #     v.alignment = ALIGNMENTS.get(attrs.get("alignment", "left"), ALIGN_LEFT)
    #     v.number_of_lines = attrs.get("number_of_lines", 0)
    #     v.text_color = _str2color(attrs.get("text_color"), "black")
    # elif classname == "TextField":
    #     v.text = attrs.get("text", "")
    #     font_name = attrs.get("font_name", "<System>")
    #     font_size = attrs.get("font_size", 17)
    #     v.font = (font_name, font_size)
    #     v.alignment = ALIGNMENTS.get(attrs.get("alignment", "left"), ALIGN_LEFT)
    #     v.text_color = _str2color(attrs.get("text_color"), "black")
    #     v.placeholder = attrs.get("placeholder", "")
    #     v.autocorrection_type = CORRECTION_TYPES[
    #         attrs.get("autocorrection_type", "default")
    #     ]
    #     v.spellchecking_type = CORRECTION_TYPES[
    #         attrs.get("spellchecking_type", "default")
    #     ]
    #     v.secure = attrs.get("secure", False)
    #     _bind_action(v, attrs.get("action"), f_globals, f_locals, verbose=verbose)
    # elif classname == "TextView":
    #     v.text = attrs.get("text", "")
    #     font_name = attrs.get("font_name", "<System>")
    #     font_size = attrs.get("font_size", 17)
    #     v.font = (font_name, font_size)
    #     v.alignment = ALIGNMENTS.get(attrs.get("alignment", "left"), ALIGN_LEFT)
    #     v.text_color = _str2color(attrs.get("text_color"), "black")
    #     v.autocorrection_type = CORRECTION_TYPES[
    #         attrs.get("autocorrection_type", "default")
    #     ]
    #     v.spellchecking_type = CORRECTION_TYPES[
    #         attrs.get("spellchecking_type", "default")
    #     ]
    #     v.editable = attrs.get("editable", True)
    # elif classname == "Button":
    #     v.title = attrs.get("title", "")
    #     image_name = attrs.get("image_name")
    #     if image_name:
    #         v.image = Image.named(image_name)
    #     font_size = attrs.get("font_size", 15)
    #     font_name = "<System%s>" % ("-Bold" if attrs.get("font_bold") else "",)
    #     v.font = (font_name, font_size)
    #     _bind_action(v, attrs.get("action"), f_globals, f_locals, verbose=verbose)
    # elif classname == "Slider":
    #     v.value = attrs.get("value", 0.5)
    #     v.continuous = attrs.get("continuous", False)
    #     _bind_action(v, attrs.get("action"), f_globals, f_locals, verbose=verbose)
    # elif classname == "Switch":
    #     v.value = attrs.get("value", True)
    #     _bind_action(v, attrs.get("action"), f_globals, f_locals, verbose=verbose)
    # elif classname == "SegmentedControl":
    #     v.segments = attrs.get("segments").split("|")
    #     v.selected_index = 0
    #     _bind_action(v, attrs.get("action"), f_globals, f_locals, verbose=verbose)
    # elif classname == "WebView":
    #     v.scales_page_to_fit = attrs.get("scales_to_fit")
    # elif classname == "TableView":
    #     v.row_height = attrs.get("row_height", 44)
    #     v.editing = attrs.get("editing", False)
    #     list_items = attrs.get("data_source_items", "").split("\n")
    #     # TODO: Parse items for accessory type ('>' or '(i)' suffix)
    #     data_source = ListDataSource(list_items)
    #     _bind_action(
    #         data_source,
    #         attrs.get("data_source_action"),
    #         f_globals,
    #         f_locals,
    #         verbose=verbose,
    #     )
    #     _bind_action(
    #         data_source,
    #         attrs.get("data_source_edit_action"),
    #         f_globals,
    #         f_locals,
    #         "edit_action",
    #         verbose=verbose,
    #     )
    #     _bind_action(
    #         data_source,
    #         attrs.get("data_source_accessory_action"),
    #         f_globals,
    #         f_locals,
    #         "accessory_action",
    #         verbose=verbose,
    #     )
    #     data_source.font = ("<System>", attrs.get("data_source_font_size", 18))
    #     data_source.delete_enabled = attrs.get("data_source_delete_enabled", False)
    #     data_source.move_enabled = attrs.get("data_source_move_enabled", False)
    #     data_source.number_of_lines = attrs.get("data_source_number_of_lines")
    #     v.data_source = data_source
    #     v.delegate = data_source
    # elif classname == "DatePicker":
    #     v.mode = attrs.get("mode", DATE_PICKER_MODE_DATE)
    #     _bind_action(v, attrs.get("action"), f_globals, f_locals, verbose=verbose)
    # elif classname == "ScrollView":
    #     v.content_size = (
    #         int(attrs.get("content_width", "0")),
    #         int(attrs.get("content_height", "0")),
    #     )
    # elif classname == "ImageView":
    #     image_name = attrs.get("image_name")
    #     if image_name:
    #         v.image = Image.named(image_name)

    # custom_attr_str = attrs.get("custom_attributes")
    # if custom_attr_str:
    #     try:
    #         f_locals["this"] = v
    #         custom_attributes = eval(custom_attr_str, f_globals, f_locals)
    #         if isinstance(custom_attributes, dict):
    #             items = (
    #                 custom_attributes.items()
    #                 if PY3 else custom_attributes.iteritems()
    #             )
    #             for key, value in items:
    #                 setattr(v, key, value)
    #         elif custom_attributes and verbose:
    #             sys.stderr.write(
    #                 'Warning: Custom attributes of view "%s" are not a dict\n'
    #                 % (v.name,)
    #             )
    #     except Exception as e:
    #         if verbose:
    #             sys.stderr.write(
    #                 'Warning: Could not load custom attributes of view "%s": %s\n'
    #                 % (v.name, e)
    #             )
    #     finally:
    #         del f_locals["this"]
    # v._pyui = view_dict
    # subview_dicts = view_dict.get("nodes", [])
    # for d in subview_dicts:
    #     subview = _view_from_dict(d, f_globals, f_locals, verbose=verbose)
    #     if subview:
    #         v.add_subview(subview)
    # if custom_class_str and hasattr(v, "did_load"):
    #     v.did_load()
    # return v


def _bind_action(
    v: View,
    action_str: str,
    f_globals,
    f_locals,
    attr_name: str = "action",
    verbose: bool = True,
) -> None:
    if action_str:
        try:
            action = eval(action_str, f_globals, f_locals)
            if callable(action):
                setattr(v, attr_name, action)
            elif verbose:
                sys.stderr.write("Warning: Could not bind action: Not callable\n")
        except Exception as e:
            if verbose:
                sys.stderr.write("Warning: Could not bind action: %s\n" % (e,))


if IS_PYTHONISTA:
    from ui import (  # type: ignore[assignment]
        _color2str,
        _rect2str,
        _str2color,
        _str2rect,
    )
