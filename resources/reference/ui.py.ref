#import 'pythonista'
from _ui import *
import _ui
import re
import json
import inspect
import sys
import os

PY3 = sys.version_info[0] >= 3

if PY3:
	basestring = str

def in_background(fn):
  import functools
  import _ui
  def new_fn(*args, **kwargs):
    return _ui._dispatch(functools.partial(fn, *args, **kwargs))
  return new_fn

class ImageContext (object):
  def __init__(self, width, height, scale=0.0):
    self.width = width
    self.height = height
    self.scale = scale
  
  def __enter__(self):
    begin_image_context(self.width, self.height, self.scale)
    return self
  
  def __exit__(self, type, value, traceback):
    end_image_context()
  
  def get_image(self):
    return Image.from_image_context()


class GState (object):
  def __enter__(self):
    import _ui
    _ui._save_gstate()

  def __exit__(self, type, value, traceback):
    import _ui
    _ui._restore_gstate()


class autoreleasepool (object):
	def __init__(self):
		self.pool = None
	
	def __enter__(self):
		import _ui
		self.pool = _ui._create_autoreleasepool()
	
	def __exit__(self, type, value, traceback):
		if self.pool:
			import _ui
			_ui._drain_autoreleasepool(self.pool)


class ListDataSourceList (list):
	def __init__(self, seq, datasource):
		list.__init__(self, seq)
		self.datasource = datasource
	
	def append(self, item):
		list.append(self, item)
		self.datasource.reload()
	
	def __setitem__(self, key, value):
		list.__setitem__(self, key, value)
		self.datasource.reload()
	
	def __delitem__(self, key):
		list.__delitem__(self, key)
		self.datasource.reload()
	
	def __setslice__(self, i, j, seq):
		list.__setslice__(self, i, j, seq)
		self.datasource.reload()
	
	def __delslice__(self, i, j):
		list.__delslice__(self, i, j)
		self.datasource.reload()


class ListDataSource (object):
	def __init__(self, items=None):
		self.tableview = None
		self.reload_disabled = False
		self.delete_enabled = True
		self.move_enabled = False
		
		self.action = None
		self.edit_action = None
		self.accessory_action = None
		
		self.tapped_accessory_row = -1
		self.selected_row = -1
		
		if items is not None:
			self.items = items
		else:
			self.items = ListDataSourceList([])
		self.text_color = None
		self.highlight_color = None
		self.font = None
		self.number_of_lines = 1
	
	def reload(self):
		if self.tableview and not self.reload_disabled:
			self.tableview.reload()
	
	@property
	def items(self):
		return self._items
	
	@items.setter
	def items(self, value):
		self._items = ListDataSourceList(value, self)
		self.reload()
	
	def tableview_number_of_sections(self, tv):
		self.tableview = tv
		return 1
	
	def tableview_number_of_rows(self, tv, section):
		return len(self.items)
	
	def tableview_can_delete(self, tv, section, row):
		return self.delete_enabled
	
	def tableview_can_move(self, tv, section, row):
		return self.move_enabled
	
	def tableview_accessory_button_tapped(self, tv, section, row):
		self.tapped_accessory_row = row
		if self.accessory_action:
			self.accessory_action(self)
	
	def tableview_did_select(self, tv, section, row):
		self.selected_row = row
		if self.action:
			self.action(self)
	
	def tableview_move_row(self, tv, from_section, from_row, to_section, to_row):
		if from_row == to_row:
			return
		moved_item = self.items[from_row]
		self.reload_disabled = True
		del self.items[from_row]
		self.items[to_row:to_row] = [moved_item]
		self.reload_disabled = False
		if self.edit_action:
			self.edit_action(self)
	
	def tableview_delete(self, tv, section, row):
		self.reload_disabled = True
		del self.items[row]
		self.reload_disabled = False
		tv.delete_rows([row])
		if self.edit_action:
			self.edit_action(self)
	
	def tableview_cell_for_row(self, tv, section, row):
		item = self.items[row]
		cell = TableViewCell()
		cell.text_label.number_of_lines = self.number_of_lines
		if isinstance(item, dict):
			cell.text_label.text = item.get('title', '')
			img = item.get('image', None)
			if img:
				if isinstance(img, basestring):
					cell.image_view.image = Image.named(img)
				elif isinstance(img, Image):
					cell.image_view.image = img
			accessory = item.get('accessory_type', 'none')
			cell.accessory_type = accessory
		else:
			cell.text_label.text = str(item)
		if self.text_color:
			cell.text_label.text_color = self.text_color
		if self.highlight_color:
			bg_view = View(background_color=self.highlight_color)
			cell.selected_background_view = bg_view
		if self.font:
			cell.text_label.font = self.font
		return cell


RECT_REGEX = re.compile(r'\{\{(\-?\d+\.?\d*),\s?(\-?\d+\.?\d*)\},\s?\{(\-?\d+\.?\d*),\s?(\-?\d+\.?\d*)\}\}')
COLOR_REGEX = r'RGBA\((\d+\.?\d*),(\d+\.?\d*),(\d+\.?\d*),(\d+\.?\d*)\)'
ALIGNMENTS = {'left': ALIGN_LEFT, 'right': ALIGN_RIGHT, 'center': ALIGN_CENTER}
CORRECTION_TYPES = {'yes': True, 'no': False, 'default': None}

def _str2rect(rect_str):
	m = re.match(RECT_REGEX, rect_str)
	if m:
		return tuple([float(s) for s in m.groups()])
	return None

def _str2color(color_str, default=None):
	if not color_str:
		return default
	m = re.match(COLOR_REGEX, color_str)
	if m:
		return tuple([float(s) for s in m.groups()])
	return default

def _rect2str(rect):
	if not len(rect) == 4:
		raise TypeError('Expected a sequence of length 4')
	return '{{%s,%s},{%s,%s}}' % (rect[0], rect[1], rect[2], rect[3])

def _color2str(color):
	if not color:
		return None
	if not len(color) == 4:
		raise TypeError('Expected a sequence of length 4')
	return 'RGBA(%f,%f,%f,%f)' % (color[0], color[1], color[2], color[3])

def _bind_action(v, action_str, f_globals, f_locals, attr_name='action', verbose=True):
	if action_str:
		try:
			action = eval(action_str, f_globals, f_locals)
			if callable(action):
				setattr(v, attr_name, action)
			elif verbose:
				sys.stderr.write('Warning: Could not bind action: Not callable\n')
		except Exception as e:
			if verbose:
				sys.stderr.write('Warning: Could not bind action: %s\n' % (e,))

def _view_from_dict(view_dict, f_globals, f_locals, verbose=True):
	attrs = view_dict.get('attributes', {})
	classname = view_dict.get('class', 'View')
	ViewClass = _ui.__dict__.get(classname)
	if not ViewClass:
		return None
	
	custom_class_str = attrs.get('custom_class')
	if custom_class_str:
		try:
			CustomViewClass = eval(custom_class_str, f_globals, f_locals)
			if inspect.isclass(CustomViewClass) and issubclass(CustomViewClass, View):
				ViewClass = CustomViewClass
			elif verbose:
				sys.stderr.write('Warning: Invalid custom view class "%s"' % (custom_class_str,))
		except Exception as e:
			if verbose:
				sys.stderr.write('Warning: Could not resolve custom view class: %s\n' % (e,))
	
	if classname == 'NavigationView':
		# Special case for ui.NavigationView: Subviews are added to an
		# implicitly-created root view instead of the NavigationView itself.
		root_view = View()
		root_view.name = attrs.get('root_view_name')
		root_view.background_color = _str2color(attrs.get('background_color'), 'white')
		subview_dicts = view_dict.get('nodes', [])
		if subview_dicts:
			for d in subview_dicts:
				subview = _view_from_dict(d, f_globals, f_locals, verbose=verbose)
				if subview:
					root_view.add_subview(subview)
			del view_dict['nodes']
		v = NavigationView(root_view)
		v.title_color = _str2color(attrs.get('title_color'))
		v.bar_tint_color = _str2color(attrs.get('title_bar_color'))
	else:
		v = ViewClass()
	
	v.frame = _str2rect(view_dict.get('frame'))
	v.flex = attrs.get('flex', '')
	v.alpha = attrs.get('alpha', 1.0)
	v.name = attrs.get('name')
	v.background_color = _str2color(attrs.get('background_color'), 'clear')
	v.tint_color = _str2color(attrs.get('tint_color'))
	v.border_width = attrs.get('border_width', 0)
	v.border_color = _str2color(attrs.get('border_color'))
	v.corner_radius = attrs.get('corner_radius', 0)
	if classname == 'Label':
		v.text = attrs.get('text', '')
		font_name = attrs.get('font_name', '<System>')
		font_size = attrs.get('font_size', 17)
		v.font = (font_name, font_size)
		v.alignment = ALIGNMENTS.get(attrs.get('alignment', 'left'), ALIGN_LEFT)
		v.number_of_lines = attrs.get('number_of_lines', 0)
		v.text_color = _str2color(attrs.get('text_color'), 'black')
	elif classname == 'TextField':
		v.text = attrs.get('text', '')
		font_name = attrs.get('font_name', '<System>')
		font_size = attrs.get('font_size', 17)
		v.font = (font_name, font_size)
		v.alignment = ALIGNMENTS.get(attrs.get('alignment', 'left'), ALIGN_LEFT)
		v.text_color = _str2color(attrs.get('text_color'), 'black')
		v.placeholder = attrs.get('placeholder', '')
		v.autocorrection_type = CORRECTION_TYPES[attrs.get('autocorrection_type', 'default')]
		v.spellchecking_type = CORRECTION_TYPES[attrs.get('spellchecking_type', 'default')]
		v.secure = attrs.get('secure', False)
		_bind_action(v, attrs.get('action'), f_globals, f_locals, verbose=verbose)
	elif classname == 'TextView':
		v.text = attrs.get('text', '')
		font_name = attrs.get('font_name', '<System>')
		font_size = attrs.get('font_size', 17)
		v.font = (font_name, font_size)
		v.alignment = ALIGNMENTS.get(attrs.get('alignment', 'left'), ALIGN_LEFT)
		v.text_color = _str2color(attrs.get('text_color'), 'black')
		v.autocorrection_type = CORRECTION_TYPES[attrs.get('autocorrection_type', 'default')]
		v.spellchecking_type = CORRECTION_TYPES[attrs.get('spellchecking_type', 'default')]
		v.editable = attrs.get('editable', True)
	elif classname == 'Button':
		v.title = attrs.get('title', '')
		image_name = attrs.get('image_name')
		if image_name:
			v.image = Image.named(image_name)
		font_size = attrs.get('font_size', 15)
		font_name = '<System%s>' % ('-Bold' if attrs.get('font_bold') else '',)
		v.font = (font_name, font_size)
		_bind_action(v, attrs.get('action'), f_globals, f_locals, verbose=verbose)
	elif classname == 'Slider':
		v.value = attrs.get('value', 0.5)
		v.continuous = attrs.get('continuous', False)
		_bind_action(v, attrs.get('action'), f_globals, f_locals, verbose=verbose)
	elif classname == 'Switch':
		v.value = attrs.get('value', True)
		_bind_action(v, attrs.get('action'), f_globals, f_locals, verbose=verbose)
	elif classname == 'SegmentedControl':
		v.segments = attrs.get('segments').split('|')
		v.selected_index = 0
		_bind_action(v, attrs.get('action'), f_globals, f_locals, verbose=verbose)
	elif classname == 'WebView':
		v.scales_page_to_fit = attrs.get('scales_to_fit')
	elif classname == 'TableView':
		v.row_height = attrs.get('row_height', 44)
		v.editing = attrs.get('editing', False)
		list_items = attrs.get('data_source_items', '').split('\n')
		# TODO: Parse items for accessory type ('>' or '(i)' suffix)
		data_source = ListDataSource(list_items)
		_bind_action(data_source, attrs.get('data_source_action'), f_globals, f_locals, verbose=verbose)
		_bind_action(data_source, attrs.get('data_source_edit_action'), f_globals, f_locals, 'edit_action', verbose=verbose)
		_bind_action(data_source, attrs.get('data_source_accessory_action'), f_globals, f_locals, 'accessory_action', verbose=verbose)
		data_source.font = ('<System>', attrs.get('data_source_font_size', 18))
		data_source.delete_enabled = attrs.get('data_source_delete_enabled', False)
		data_source.move_enabled = attrs.get('data_source_move_enabled', False)
		data_source.number_of_lines = attrs.get('data_source_number_of_lines')
		v.data_source = data_source
		v.delegate = data_source
	elif classname == 'DatePicker':
		v.mode = attrs.get('mode', DATE_PICKER_MODE_DATE)
		_bind_action(v, attrs.get('action'), f_globals, f_locals, verbose=verbose)
	elif classname == 'ScrollView':
		v.content_size = int(attrs.get('content_width', '0')), int(attrs.get('content_height', '0'))
	elif classname == 'ImageView':
		image_name = attrs.get('image_name')
		if image_name:
			v.image = Image.named(image_name)
	
	custom_attr_str = attrs.get('custom_attributes')
	if custom_attr_str:
		try:
			f_locals['this'] = v
			custom_attributes = eval(custom_attr_str, f_globals, f_locals)
			if isinstance(custom_attributes, dict):
				items = custom_attributes.items() if PY3 else custom_attributes.iteritems()
				for key, value in items:
					setattr(v, key, value)
			elif custom_attributes and verbose:
				sys.stderr.write('Warning: Custom attributes of view "%s" are not a dict\n' % (v.name,))
		except Exception as e:
			if verbose:
				sys.stderr.write('Warning: Could not load custom attributes of view "%s": %s\n' % (v.name, e))
		finally:
			del f_locals['this']
	v._pyui = view_dict		
	subview_dicts = view_dict.get('nodes', [])
	for d in subview_dicts:
		subview = _view_from_dict(d, f_globals, f_locals, verbose=verbose)
		if subview:
			v.add_subview(subview)
	if custom_class_str and hasattr(v, 'did_load'):
		v.did_load()
	return v

def load_view_str(json_str, bindings=None, stackframe=None, verbose=True):
	root_list = json.loads(json_str)
	if stackframe is None and not bindings:
		stackframe = inspect.currentframe().f_back
	if root_list:
		root_view_dict = root_list[0]
		if bindings:
			g = bindings
			l = bindings
		else:
			g = stackframe.f_globals
			l = stackframe.f_locals
		return _view_from_dict(root_view_dict, g, l, verbose=verbose)

def load_view(pyui_path=None, bindings=None, stackframe=None, verbose=True):
	if stackframe is None and not bindings:
		stackframe = inspect.currentframe().f_back
	if pyui_path is None:
		f = inspect.currentframe().f_back
		script_path = f.f_globals.get('__file__')
		pyui_path = os.path.splitext(script_path)[0] + '.pyui'
	if len(os.path.splitext(pyui_path)[1]) == 0:
		# The '.pyui' extension can be omitted, but if there is an extension (e.g. '.json'), it should be kept.
		pyui_path += '.pyui'
	with (open(pyui_path, encoding='utf-8') if PY3 else open(pyui_path)) as f:
		json_str = f.read()
	return load_view_str(json_str, bindings, stackframe, verbose=verbose)

def _view_to_dict(view):
	if not isinstance(view, View):
		raise TypeError('Expected a ui.View or subclass')
	view_dict = {}
	view_dict['frame'] = _rect2str(view.frame)
	class_name = type(view).__name__
	if class_name not in dir(_ui):
		class_name = 'View'
	view_dict['class'] = class_name
	if view.subviews:
		view_dict['nodes'] = [_view_to_dict(v) for v in view.subviews]
	attrs = {}
	view_dict['attributes'] = attrs
	attrs['flex'] = view.flex
	attrs['alpha'] = view.alpha
	attrs['name'] = view.name
	attrs['background_color'] = _color2str(view.background_color)
	attrs['tint_color'] = _color2str(view.tint_color)
	attrs['border_width'] = view.border_width
	attrs['border_color'] = _color2str(view.border_color)
	attrs['corner_radius'] = view.corner_radius
	alignments = {ALIGN_LEFT: 'left', ALIGN_RIGHT: 'right', ALIGN_CENTER: 'center'}
	correction_types = {True: 'yes', False: 'no', None: 'default'}
	def _set_action_name(view_attrs, action, key='action'):
		try:
			if inspect.ismethod(action):
				# Assuming the most common case here, this won't work for everything...
				view_attrs[key] = 'self.' + action.__name__
			else:
				view_attrs[key] = action.__name__
		except:
			pass
	if class_name == 'View' and not type(view) == View:
		attrs['custom_class'] = type(view).__name__
	if isinstance(view, (Label, TextField, TextView)):
		attrs['text'] = view.text
		font_name, font_size = view.font
		attrs['font_name'] = font_name
		attrs['font_size'] = font_size
		attrs['alignment'] = alignments.get(view.alignment, 'left')
		attrs['text_color'] = _color2str(view.text_color)
	if isinstance(view, Label):
		attrs['number_of_lines'] = view.number_of_lines
	if isinstance(view, TextField):
		attrs['placeholder'] = view.placeholder or ''
		attrs['secure'] = view.secure
		attrs['autocorrection_type'] = correction_types[view.autocorrection_type]
		attrs['spellchecking_type'] = correction_types[view.spellchecking_type]
		_set_action_name(attrs, view.action)
	if isinstance(view, TextView):
		attrs['autocorrection_type'] = correction_types[view.autocorrection_type]
		attrs['spellchecking_type'] = correction_types[view.spellchecking_type]
		attrs['editable'] = view.editable
	if isinstance(view, Button):
		attrs['title'] = view.title
		if view.image and view.image.name:
			attrs['image_name'] = view.image.name
		font_name, font_size = view.font
		attrs['font_name'] = font_name
		attrs['font_size'] = font_size
		_set_action_name(attrs, view.action)
	if isinstance(view, Slider):
		attrs['value'] = view.value
		attrs['continuous'] = view.continuous
		_set_action_name(attrs, view.action)
	if isinstance(view, Switch):
		attrs['value'] = view.value
		_set_action_name(attrs, view.action)
	if isinstance(view, SegmentedControl):
		attrs['segments'] = '|'.join(view.segments)
		_set_action_name(attrs, view.action)
	if isinstance(view, WebView):
		attrs['scales_to_fit'] = view.scales_page_to_fit
	if isinstance(view, TableView):
		attrs['row_height'] = view.row_height
		attrs['editing'] = view.editing
		if isinstance(view.data_source, ListDataSource) and isinstance(view.delegate, ListDataSource):
			data_source = view.data_source
			_set_action_name(attrs, data_source.action, 'data_source_action')
			_set_action_name(attrs, data_source.edit_action, 'data_source_edit_action')
			_set_action_name(attrs, data_source.accessory_action, 'data_source_accessory_action')
			attrs['data_source_number_of_lines'] = data_source.number_of_lines
			attrs['data_source_move_enabled'] = data_source.move_enabled
			attrs['data_source_delete_enabled'] = data_source.delete_enabled
			_, font_size = data_source.font
			attrs['data_source_font_size'] = font_size
			try:
				# NOTE: This only works if the data source's items are all strings (which is the common case)
				attrs['data_source_items'] = '\n'.join(data_source.items)
			except:
				pass
		else:
			attrs['data_source_number_of_lines'] = 0
			attrs['data_source_move_enabled'] = False
			attrs['data_source_delete_enabled'] = False
			attrs['data_source_font_size'] = 18
			attrs['data_source_items'] = ''
	if isinstance(view, DatePicker):
		attrs['mode'] = view.mode
		_set_action_name(attrs, view.action)
	if isinstance(view, ScrollView):
		attrs['content_width'] = int(view.content_size[0])
		attrs['content_height'] = int(view.content_size[1])
	if isinstance(view, ImageView):
		if view.image and view.image.name:
			attrs['image_name'] = view.image.name
	# TODO: Support NavigationView properly...
	return view_dict

def dump_view(view):
	view_dict = _view_to_dict(view)
	return json.dumps([view_dict], indent=2)
	
