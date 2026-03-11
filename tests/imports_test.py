"""Smoke tests: no missing imports or circular imports on PC and Pythonista.

Each test runs in a subprocess so the import chain is truly fresh — there is
no sys.modules cache inherited from the test runner.  A circular import or a
missing name in any shim will make the subprocess exit with a non-zero code and
a Python traceback, which is surfaced in the assertion message.
"""

import subprocess
import sys
import textwrap

# ---------------------------------------------------------------------------
# PC (IS_PYTHONISTA=False)
# ---------------------------------------------------------------------------

_PC_SCRIPT = """
from pytoui.ui import *
import pytoui.console
"""

# ---------------------------------------------------------------------------
# Pythonista simulation (IS_PYTHONISTA=True)
# ---------------------------------------------------------------------------
# We inject stub modules for 'ui' and 'console' into sys.modules, then patch
# pytoui._platform.IS_PYTHONISTA = True before any pytoui.ui.* module is
# imported.  Each module reads IS_PYTHONISTA at its own import time via
#   from pytoui._platform import IS_PYTHONISTA
# which binds the current (patched) value — so the shims at the bottom of
# each file run correctly.

_MOCK_SETUP = """
import sys, types

_ui = types.ModuleType('ui')

# Classes: some shims do `class View(ui.View): pass`, so they must be proper types
for _n in [
    'View', 'Button', 'Label', 'Switch', 'Slider', 'SegmentedControl',
    'ActivityIndicator', 'ImageView', 'ScrollView', 'TableView', 'TableViewCell',
    'ListDataSource', 'ListDataSourceList', 'TextField', 'TextView', 'WebView',
    'NavigationView', 'DatePicker', 'ButtonItem',
    'Path', 'GState', 'Image', 'ImageContext', 'Transform',
]:
    setattr(_ui, _n, type(_n, (), {}))

# Functions imported by the shims
for _n in [
    'animate', 'begin_image_context', 'cancel_delays', 'concat_ctm',
    'convert_point', 'convert_rect', 'delay', 'draw_string', 'end_image_context',
    'fill_rect', 'in_background', 'measure_string', 'parse_color', 'set_blend_mode',
    'set_color', 'set_shadow', 'set_alpha',
    'close_all', 'get_keyboard_frame', 'get_screen_size', 'get_window_size',
    '_color2str', '_rect2str', '_str2color', '_str2rect',
]:
    setattr(_ui, _n, lambda *a, **kw: None)
# get_ui_style is called at module level in _date_picker.py and must return a string
_ui.get_ui_style = lambda: 'light'

# Any remaining attribute (constants: ALIGN_CENTER, BLEND_NORMAL, …) returns 0
_ui.__getattr__ = lambda name: 0

sys.modules['ui'] = _ui

_console = types.ModuleType('console')
_console.alert = lambda *a, **kw: None
sys.modules['console'] = _console

_objc_util = types.ModuleType('objc_util')
for _n in [
    'ObjCClass', 'ObjCInstance',
]:
    setattr(_objc_util, _n, type(_n, (), {}))
sys.modules['objc_util'] = _objc_util
    
# Patch IS_PYTHONISTA=True BEFORE importing any pytoui.ui.* module so that
# every `from pytoui._platform import IS_PYTHONISTA` reads the patched value.
import pytoui._platform as _plat
_plat.IS_PYTHONISTA = True
"""

_PYTHONISTA_SCRIPT = (
    _MOCK_SETUP
    + """
from pytoui.ui import *
import pytoui.console
"""
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _run(script: str) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stderr


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_pc_imports():
    """from pytoui.ui import * must succeed on PC (IS_PYTHONISTA=False)."""
    rc, err = _run(_PC_SCRIPT)
    assert rc == 0, f"PC import failed:\n{err}"


def test_pythonista_imports():
    """from pytoui.ui import * must succeed in simulated Pythonista mode."""
    rc, err = _run(_PYTHONISTA_SCRIPT)
    assert rc == 0, f"Pythonista simulation import failed:\n{err}"
