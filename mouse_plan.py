"Треба певно class MouseEvent" — так, це правильно. MouseEvent(Touch) матиме buttons: frozenset[int] (які кнопки затиснуті зараз), і MouseWheel(MouseEvent) наслідується від нього. Це дає змогу в mouse_wheel знати що ще натиснуто, а у mouse_dragged — яка кнопка «ведуча» і що інше тримається.

Write bubbly-wandering-oasis.md
323 lines
# Plan: Dedicated mouse_* handlers + MouseEvent class

## Context

Mouse button clicks, drags, hover, and wheel currently route through `touch_began/moved/ended`
with negative `touch_id` values. This is a workaround: no way to know which buttons are held
during a drag, no hover, wheel requires a 3-step touch hack.

Fix: keep `touch_*` unchanged (Pythonista iOS compat), add parallel `mouse_*` methods on
View with automatic fallback, and introduce `MouseEvent(Touch)` / `MouseWheel(MouseEvent)`
types that carry the buttons-held state.

---

## New type hierarchy (`src/pytoui/ui/_types.py`)

```
Touch                   ← existing, unchanged (real fingers + Pythonista)
└── MouseEvent(Touch)   ← NEW — all desktop mouse events
    └── MouseWheel(MouseEvent)  ← was MouseWheel(Touch), now with buttons
```

### `class MouseEvent(Touch)`

```python
class MouseEvent(Touch):
    """Desktop mouse event — never appears on real Pythonista.

    Attributes (beyond Touch):
        buttons: frozenset of currently held button IDs
                 (MOUSE_LEFT_ID, MOUSE_RIGHT_ID, MOUSE_MIDDLE_ID)
    """
    __slots__ = (*Touch.__slots__, "buttons")

    def __init__(self, location, phase, prev_location, timestamp, touch_id, buttons):
        super().__init__(location, phase, prev_location, timestamp, touch_id)
        self.buttons = frozenset(buttons)
```

### `class MouseWheel(MouseEvent)` (replaces current `MouseWheel(Touch)`)

```python
class MouseWheel(MouseEvent):
    """Scroll / trackpad event.  touch_id == SCROLL_TOUCH_ID."""
    __slots__ = (*MouseEvent.__slots__, "scroll_dx", "scroll_dy")

    def __init__(self, location, phase, prev_location, timestamp, buttons,
                 scroll_dx, scroll_dy):
        super().__init__(location, phase, prev_location, timestamp,
                         SCROLL_TOUCH_ID, buttons)
        self.scroll_dx = scroll_dx
        self.scroll_dy = scroll_dy
```

Export `MouseEvent` from `ui/__init__.py` alongside `MouseWheel`.

---

## New View API (`src/pytoui/ui/_view.py`)

5 new `pytoui_mouse_*` properties in `_ViewInternals` (after `pytoui_touch_ended`):

| Property | Fallback if method absent |
|----------|--------------------------|
| `pytoui_mouse_down` | `touch_began` |
| `pytoui_mouse_up` | `touch_ended` |
| `pytoui_mouse_dragged` | `touch_moved` |
| `pytoui_mouse_moved` | **none** (hover has no touch equivalent) |
| `pytoui_mouse_wheel` | **none** (replaces old 3-step hack) |

```python
@property
def pytoui_mouse_down(self) -> Callable[[MouseEvent], None] | None:
    cb = getattr(self._ref, "mouse_down", None)
    if cb is None:
        return getattr(self._ref, "touch_began", None)
    return cb

# …same pattern for mouse_up → touch_ended, mouse_dragged → touch_moved

@property
def pytoui_mouse_moved(self) -> Callable[[MouseEvent], None] | None:
    return getattr(self._ref, "mouse_moved", None)

@property
def pytoui_mouse_wheel(self) -> Callable[[MouseWheel], None] | None:
    return getattr(self._ref, "mouse_wheel", None)
```

---

## BaseRuntime changes (`src/pytoui/_base_runtime.py`)

### New state

```python
self._held_mouse_buttons: set[int] = set()
# Tracks which buttons are currently pressed (MOUSE_LEFT/RIGHT/MIDDLE_ID).
# Used to populate MouseEvent.buttons on every mouse event.
```

### New helper

```python
def _create_mouse_event(self, view, x, y, phase, button_id, prev, buttons) -> MouseEvent:
    from pytoui.ui._types import MouseEvent
    local = convert_point((x, y), to_view=view)
    prev_local = convert_point(prev, to_view=view)
    return MouseEvent(
        location=(local.x, local.y),
        phase=phase,
        prev_location=(prev_local.x, prev_local.y),
        timestamp=int(time.time() * 1000),
        touch_id=button_id,
        buttons=buttons,
    )
```

### New dispatch methods (replace old `_touch_*` for mouse ids)

```python
def _mouse_down(self, x, y, button_id):
    self._held_mouse_buttons.add(button_id)
    self._last_pos[button_id] = (x, y)
    target = self.root.pytoui_hit_test(x, y)
    if not target:
        return
    cb = target.pytoui_mouse_down
    if not cb:
        return
    self._tracked[button_id] = target
    cb(self._create_mouse_event(target, x, y, "began", button_id, (x, y),
                                frozenset(self._held_mouse_buttons)))

def _mouse_up(self, x, y, button_id):
    self._held_mouse_buttons.discard(button_id)
    prev = self._last_pos.pop(button_id, (x, y))
    target = self._tracked.pop(button_id, None)
    if not target:
        return
    cb = target.pytoui_mouse_up
    if not cb:
        return
    current = self.root.pytoui_hit_test(x, y)
    phase = "ended" if current is target else "cancelled"
    cb(self._create_mouse_event(target, x, y, phase, button_id, prev,
                                frozenset(self._held_mouse_buttons)))

def _mouse_dragged(self, x, y, button_id):
    prev = self._last_pos.get(button_id, (x, y))
    self._last_pos[button_id] = (x, y)
    target = self._tracked.get(button_id)
    if not target:
        return
    cb = target.pytoui_mouse_dragged
    if not cb:
        return
    phase = "moved" if (x, y) != prev else "stationary"
    cb(self._create_mouse_event(target, x, y, phase, button_id, prev,
                                frozenset(self._held_mouse_buttons)))

def _mouse_moved(self, x, y):
    target = self.root.pytoui_hit_test(x, y)
    if not target:
        return
    cb = target.pytoui_mouse_moved
    if not cb:
        return
    cb(self._create_mouse_event(target, x, y, "moved", MOUSE_LEFT_ID, (x, y),
                                frozenset()))  # no buttons held

def _mouse_cancel(self, button_id):
    self._held_mouse_buttons.discard(button_id)
    x, y = self._last_pos.pop(button_id, (0.0, 0.0))
    target = self._tracked.pop(button_id, None)
    if not target:
        return
    cb = target.pytoui_mouse_up
    if not cb:
        return
    cb(self._create_mouse_event(target, x, y, "cancelled", button_id, (x, y),
                                frozenset(self._held_mouse_buttons)))
```

### Updated `_scroll_event` — single call, no 3-step

```python
def _scroll_event(self, cursor_x, cursor_y, dx, dy):
    from pytoui.ui._types import MouseWheel
    target = self.root.pytoui_hit_test(cursor_x, cursor_y)
    if not target:
        return
    cb = target.pytoui_mouse_wheel
    if not cb:
        return
    local = convert_point((cursor_x, cursor_y), to_view=target)
    cb(MouseWheel(
        location=(local.x, local.y),
        phase="moved",
        prev_location=(local.x, local.y),
        timestamp=int(time.time() * 1000),
        buttons=frozenset(self._held_mouse_buttons),
        scroll_dx=dx,
        scroll_dy=dy,
    ))
```

Remove `_make_scroll_touch` (no longer needed).

Add to module-level imports:
```python
from pytoui.ui._types import MOUSE_LEFT_ID
```

---

## SDL runtime (`src/pytoui/_sdlrt.py`)

```python
case "mousedown":
    match msg[1]:
        case sdl2.SDL_BUTTON_LEFT:   self._mouse_down(msg[2], msg[3], -1)
        case sdl2.SDL_BUTTON_RIGHT:  self._mouse_down(msg[2], msg[3], -2)
        case sdl2.SDL_BUTTON_MIDDLE: self._mouse_down(msg[2], msg[3], -3)
case "mouseup":
    match msg[1]:
        case sdl2.SDL_BUTTON_LEFT:   self._mouse_up(msg[2], msg[3], -1)
        case sdl2.SDL_BUTTON_RIGHT:  self._mouse_up(msg[2], msg[3], -2)
        case sdl2.SDL_BUTTON_MIDDLE: self._mouse_up(msg[2], msg[3], -3)
case "mousemove":
    self._cursor_pos = (float(msg[2]), float(msg[3]))
    any_drag = False
    if msg[1] & sdl2.SDL_BUTTON_LMASK:
        self._mouse_dragged(msg[2], msg[3], -1); any_drag = True
    if msg[1] & sdl2.SDL_BUTTON_RMASK:
        self._mouse_dragged(msg[2], msg[3], -2); any_drag = True
    if msg[1] & sdl2.SDL_BUTTON_MMASK:
        self._mouse_dragged(msg[2], msg[3], -3); any_drag = True
    if not any_drag:
        self._mouse_moved(msg[2], msg[3])
case "windowevent":
    if msg[1] == sdl2.SDL_WINDOWEVENT_LEAVE:
        for bid in (-1, -2, -3):
            self._mouse_cancel(bid)
# mousewheel unchanged — still calls self._scroll_event(cx, cy, dx, dy)
```

---

## Winit runtime (`src/pytoui/_winitrt.py`)

```python
def _internal_event(self, etype, x, y, touch_id: int):
    match etype:
        case 0:
            if touch_id < 0: self._mouse_down(x, y, touch_id)
            else:            self._touch_down(x, y, touch_id)
        case 1:
            if touch_id < 0: self._mouse_up(x, y, touch_id)
            else:            self._touch_up(x, y, touch_id)
        case 2:
            self._cursor_pos = (x, y)
            if touch_id < 0:
                # CursorMoved always sends touch_id=-1; infer drag vs hover from _tracked
                any_drag = False
                for bid in (-1, -2, -3):
                    if bid in self._tracked:
                        self._mouse_dragged(x, y, bid); any_drag = True
                if not any_drag:
                    self._mouse_moved(x, y)
            else:
                self._touch_move(x, y, touch_id)
        case 3:
            if touch_id < 0: self._mouse_cancel(touch_id)
            else:            self._touch_cancel(touch_id)
        case 4:
            cx, cy = self._cursor_pos
            self._scroll_event(cx, cy, x, y)
```

---

## Files to modify

| File | Changes |
|------|---------|
| `src/pytoui/ui/_types.py` | Add `MouseEvent(Touch)`; change `MouseWheel` to extend `MouseEvent` (new `buttons` param) |
| `src/pytoui/ui/__init__.py` | Export `MouseEvent` |
| `src/pytoui/ui/_view.py` | Add 5 `pytoui_mouse_*` properties |
| `src/pytoui/_base_runtime.py` | Add `_held_mouse_buttons`, `_create_mouse_event`, 5 `_mouse_*` methods; update `_scroll_event` |
| `src/pytoui/_sdlrt.py` | Route all mouse events to `_mouse_*` |
| `src/pytoui/_winitrt.py` | Route touch_id<0 events to `_mouse_*`; drag vs hover detection |
| `examples/mouse_wheel.py` | Update to use `mouse_wheel(self, touch)` |

No changes to `lib.rs` (Rust side already correct).

---

## Backward compat

Views with only `touch_began/moved/ended` (no `mouse_*`): unchanged behavior —
`pytoui_mouse_down/up/dragged` fall back to `touch_*`.
The Touch object they receive is now a `MouseEvent` instance (subclass of Touch),
so existing `isinstance(t, Touch)` checks pass.

---

## Verification

```python
class TestView(ui.View):
    def mouse_down(self, e):
        print(f"down  btn={e.touch_id}  held={e.buttons}  {e.location}")
    def mouse_dragged(self, e):
        print(f"drag  btn={e.touch_id}  held={e.buttons}  {e.location}")
    def mouse_moved(self, e):
        print(f"hover {e.location}")
    def mouse_wheel(self, e):
        print(f"wheel dx={e.scroll_dx:.0f} dy={e.scroll_dy:.0f}  held={e.buttons}")

# Also verify backward compat: a View with only touch_began still works with mouse clicks
```
Так, саме так — через наслідування MouseEvent(Touch) будь-який MouseEvent вже є Touch:

isinstance(e, Touch) → True — старий код без mouse_* отримує MouseEvent у touch_began, і все працює
isinstance(e, MouseEvent) → для нового коду, щоб перевірити «це мишка»
isinstance(e, MouseWheel) → для колеса
Нічого явно конвертувати не потрібно — ієрархія вже забезпечує це.

Claude’s Plan
Plan: Dedicated mouse_* handlers + MouseEvent class
Context
Mouse button clicks, drags, hover, and wheel currently route through touch_began/moved/ended
with negative touch_id values. This is a workaround: no way to know which buttons are held
during a drag, no hover, wheel requires a 3-step touch hack.

Fix: keep touch_* unchanged (Pythonista iOS compat), add parallel mouse_* methods on
View with automatic fallback, and introduce MouseEvent(Touch) / MouseWheel(MouseEvent)
types that carry the buttons-held state.

New type hierarchy (src/pytoui/ui/_types.py)

Touch                   ← existing, unchanged (real fingers + Pythonista)
└── MouseEvent(Touch)   ← NEW — all desktop mouse events
    └── MouseWheel(MouseEvent)  ← was MouseWheel(Touch), now with buttons
class MouseEvent(Touch)

class MouseEvent(Touch):
    """Desktop mouse event — never appears on real Pythonista.

    Attributes (beyond Touch):
        buttons: frozenset of currently held button IDs
                 (MOUSE_LEFT_ID, MOUSE_RIGHT_ID, MOUSE_MIDDLE_ID)
    """
    __slots__ = (*Touch.__slots__, "buttons")

    def __init__(self, location, phase, prev_location, timestamp, touch_id, buttons):
        super().__init__(location, phase, prev_location, timestamp, touch_id)
        self.buttons = frozenset(buttons)
class MouseWheel(MouseEvent) (replaces current MouseWheel(Touch))

class MouseWheel(MouseEvent):
    """Scroll / trackpad event.  touch_id == SCROLL_TOUCH_ID."""
    __slots__ = (*MouseEvent.__slots__, "scroll_dx", "scroll_dy")

    def __init__(self, location, phase, prev_location, timestamp, buttons,
                 scroll_dx, scroll_dy):
        super().__init__(location, phase, prev_location, timestamp,
                         SCROLL_TOUCH_ID, buttons)
        self.scroll_dx = scroll_dx
        self.scroll_dy = scroll_dy
Export MouseEvent from ui/__init__.py alongside MouseWheel.

New View API (src/pytoui/ui/_view.py)
5 new pytoui_mouse_* properties in _ViewInternals (after pytoui_touch_ended):

Property	Fallback if method absent
pytoui_mouse_down	touch_began
pytoui_mouse_up	touch_ended
pytoui_mouse_dragged	touch_moved
pytoui_mouse_moved	none (hover has no touch equivalent)
pytoui_mouse_wheel	none (replaces old 3-step hack)

@property
def pytoui_mouse_down(self) -> Callable[[MouseEvent], None] | None:
    cb = getattr(self._ref, "mouse_down", None)
    if cb is None:
        return getattr(self._ref, "touch_began", None)
    return cb

# …same pattern for mouse_up → touch_ended, mouse_dragged → touch_moved

@property
def pytoui_mouse_moved(self) -> Callable[[MouseEvent], None] | None:
    return getattr(self._ref, "mouse_moved", None)

@property
def pytoui_mouse_wheel(self) -> Callable[[MouseWheel], None] | None:
    return getattr(self._ref, "mouse_wheel", None)
BaseRuntime changes (src/pytoui/_base_runtime.py)
New state

self._held_mouse_buttons: set[int] = set()
# Tracks which buttons are currently pressed (MOUSE_LEFT/RIGHT/MIDDLE_ID).
# Used to populate MouseEvent.buttons on every mouse event.
New helper

def _create_mouse_event(self, view, x, y, phase, button_id, prev, buttons) -> MouseEvent:
    from pytoui.ui._types import MouseEvent
    local = convert_point((x, y), to_view=view)
    prev_local = convert_point(prev, to_view=view)
    return MouseEvent(
        location=(local.x, local.y),
        phase=phase,
        prev_location=(prev_local.x, prev_local.y),
        timestamp=int(time.time() * 1000),
        touch_id=button_id,
        buttons=buttons,
    )
New dispatch methods (replace old _touch_* for mouse ids)

def _mouse_down(self, x, y, button_id):
    self._held_mouse_buttons.add(button_id)
    self._last_pos[button_id] = (x, y)
    target = self.root.pytoui_hit_test(x, y)
    if not target:
        return
    cb = target.pytoui_mouse_down
    if not cb:
        return
    self._tracked[button_id] = target
    cb(self._create_mouse_event(target, x, y, "began", button_id, (x, y),
                                frozenset(self._held_mouse_buttons)))

def _mouse_up(self, x, y, button_id):
    self._held_mouse_buttons.discard(button_id)
    prev = self._last_pos.pop(button_id, (x, y))
    target = self._tracked.pop(button_id, None)
    if not target:
        return
    cb = target.pytoui_mouse_up
    if not cb:
        return
    current = self.root.pytoui_hit_test(x, y)
    phase = "ended" if current is target else "cancelled"
    cb(self._create_mouse_event(target, x, y, phase, button_id, prev,
                                frozenset(self._held_mouse_buttons)))

def _mouse_dragged(self, x, y, button_id):
    prev = self._last_pos.get(button_id, (x, y))
    self._last_pos[button_id] = (x, y)
    target = self._tracked.get(button_id)
    if not target:
        return
    cb = target.pytoui_mouse_dragged
    if not cb:
        return
    phase = "moved" if (x, y) != prev else "stationary"
    cb(self._create_mouse_event(target, x, y, phase, button_id, prev,
                                frozenset(self._held_mouse_buttons)))

def _mouse_moved(self, x, y):
    target = self.root.pytoui_hit_test(x, y)
    if not target:
        return
    cb = target.pytoui_mouse_moved
    if not cb:
        return
    cb(self._create_mouse_event(target, x, y, "moved", MOUSE_LEFT_ID, (x, y),
                                frozenset()))  # no buttons held

def _mouse_cancel(self, button_id):
    self._held_mouse_buttons.discard(button_id)
    x, y = self._last_pos.pop(button_id, (0.0, 0.0))
    target = self._tracked.pop(button_id, None)
    if not target:
        return
    cb = target.pytoui_mouse_up
    if not cb:
        return
    cb(self._create_mouse_event(target, x, y, "cancelled", button_id, (x, y),
                                frozenset(self._held_mouse_buttons)))
Updated _scroll_event — single call, no 3-step

def _scroll_event(self, cursor_x, cursor_y, dx, dy):
    from pytoui.ui._types import MouseWheel
    target = self.root.pytoui_hit_test(cursor_x, cursor_y)
    if not target:
        return
    cb = target.pytoui_mouse_wheel
    if not cb:
        return
    local = convert_point((cursor_x, cursor_y), to_view=target)
    cb(MouseWheel(
        location=(local.x, local.y),
        phase="moved",
        prev_location=(local.x, local.y),
        timestamp=int(time.time() * 1000),
        buttons=frozenset(self._held_mouse_buttons),
        scroll_dx=dx,
        scroll_dy=dy,
    ))
Remove _make_scroll_touch (no longer needed).

Add to module-level imports:


from pytoui.ui._types import MOUSE_LEFT_ID
SDL runtime (src/pytoui/_sdlrt.py)

case "mousedown":
    match msg[1]:
        case sdl2.SDL_BUTTON_LEFT:   self._mouse_down(msg[2], msg[3], -1)
        case sdl2.SDL_BUTTON_RIGHT:  self._mouse_down(msg[2], msg[3], -2)
        case sdl2.SDL_BUTTON_MIDDLE: self._mouse_down(msg[2], msg[3], -3)
case "mouseup":
    match msg[1]:
        case sdl2.SDL_BUTTON_LEFT:   self._mouse_up(msg[2], msg[3], -1)
        case sdl2.SDL_BUTTON_RIGHT:  self._mouse_up(msg[2], msg[3], -2)
        case sdl2.SDL_BUTTON_MIDDLE: self._mouse_up(msg[2], msg[3], -3)
case "mousemove":
    self._cursor_pos = (float(msg[2]), float(msg[3]))
    any_drag = False
    if msg[1] & sdl2.SDL_BUTTON_LMASK:
        self._mouse_dragged(msg[2], msg[3], -1); any_drag = True
    if msg[1] & sdl2.SDL_BUTTON_RMASK:
        self._mouse_dragged(msg[2], msg[3], -2); any_drag = True
    if msg[1] & sdl2.SDL_BUTTON_MMASK:
        self._mouse_dragged(msg[2], msg[3], -3); any_drag = True
    if not any_drag:
        self._mouse_moved(msg[2], msg[3])
case "windowevent":
    if msg[1] == sdl2.SDL_WINDOWEVENT_LEAVE:
        for bid in (-1, -2, -3):
            self._mouse_cancel(bid)
# mousewheel unchanged — still calls self._scroll_event(cx, cy, dx, dy)
Winit runtime (src/pytoui/_winitrt.py)

def _internal_event(self, etype, x, y, touch_id: int):
    match etype:
        case 0:
            if touch_id < 0: self._mouse_down(x, y, touch_id)
            else:            self._touch_down(x, y, touch_id)
        case 1:
            if touch_id < 0: self._mouse_up(x, y, touch_id)
            else:            self._touch_up(x, y, touch_id)
        case 2:
            self._cursor_pos = (x, y)
            if touch_id < 0:
                # CursorMoved always sends touch_id=-1; infer drag vs hover from _tracked
                any_drag = False
                for bid in (-1, -2, -3):
                    if bid in self._tracked:
                        self._mouse_dragged(x, y, bid); any_drag = True
                if not any_drag:
                    self._mouse_moved(x, y)
            else:
                self._touch_move(x, y, touch_id)
        case 3:
            if touch_id < 0: self._mouse_cancel(touch_id)
            else:            self._touch_cancel(touch_id)
        case 4:
            cx, cy = self._cursor_pos
            self._scroll_event(cx, cy, x, y)
Files to modify
File	Changes
src/pytoui/ui/_types.py	Add MouseEvent(Touch); change MouseWheel to extend MouseEvent (new buttons param)
src/pytoui/ui/__init__.py	Export MouseEvent
src/pytoui/ui/_view.py	Add 5 pytoui_mouse_* properties
src/pytoui/_base_runtime.py	Add _held_mouse_buttons, _create_mouse_event, 5 _mouse_* methods; update _scroll_event
src/pytoui/_sdlrt.py	Route all mouse events to _mouse_*
src/pytoui/_winitrt.py	Route touch_id<0 events to _mouse_*; drag vs hover detection
examples/mouse_wheel.py	Update to use mouse_wheel(self, touch)
No changes to lib.rs (Rust side already correct).

Backward compat
Views with only touch_began/moved/ended (no mouse_*): unchanged behavior —
pytoui_mouse_down/up/dragged fall back to touch_*.
The Touch object they receive is now a MouseEvent instance (subclass of Touch),
so existing isinstance(t, Touch) checks pass.

Verification

class TestView(ui.View):
    def mouse_down(self, e):
        print(f"down  btn={e.touch_id}  held={e.buttons}  {e.location}")
    def mouse_dragged(self, e):
        print(f"drag  btn={e.touch_id}  held={e.buttons}  {e.location}")
    def mouse_moved(self, e):
        print(f"hover {e.location}")
    def mouse_wheel(self, e):
        print(f"wheel dx={e.scroll_dx:.0f} dy={e.scroll_dy:.0f}  held={e.buttons}")

# Also verify backward compat: a View with only touch_began still works with mouse clicks
### TODO:
* Add MouseEvent(Touch) class to _types.py, update MouseWheel to extend MouseEvent
* Export MouseEvent from ui/__init__.py
* Add 5 pytoui_mouse_* properties to _view.py
* Add _mouse_* methods to _base_runtime.py
* Update _sdlrt.py to route to _mouse_*
* Update _winitrt.py to route touch_id<0 to _mouse_*

Update examples/mouse_wheel.py and examples/multi_touch.py to use mouse_wheel method