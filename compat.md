# ОНОВЛЕНЕ ТЕХНІЧНЕ ЗАВДАННЯ: Доробка pytoui до повної сумісності з Pythonista

## ✅ ЩО ВЖЕ РЕАЛІЗОВАНО

1. **`left_button_items` та `right_button_items`** - додані в `_ViewInternals` та `_View` - не реалізована внутрішня логіка
2. **`become_first_responder`** - змінено на `-> None` (було `-> bool`) - не реалізована внутрішня логіка

## 1. ВІДСУТНІ КЛАСИ (Високий пріоритет)

### 1.1 DatePicker
**Модуль:** `pytoui/ui/_date_picker.py`
**Базовий клас:** `View`

**Публічний API:**
```python
class DatePicker(View):
    action: __Action | None
    countdown_duration: Any
    date: Any
    mode: __DatePickerMode  # DATE_PICKER_MODE_* константи
```

**Конструктор:**
```python
# Варіант 1: Пустий
picker = DatePicker()  # mode = DATE_PICKER_MODE_DATE_AND_TIME

# Варіант 2: З режимом
picker = DatePicker(DATE_PICKER_MODE_TIME)

# Варіант 3: З frame та режимом
picker = DatePicker(10, 20, 300, 200, DATE_PICKER_MODE_COUNTDOWN)

# Варіант 4: Keyword аргументи
picker = DatePicker(mode=DATE_PICKER_MODE_DATE, date=some_date)
```

### 1.2 ListDataSource та ListDataSourceList
**Модуль:** `pytoui/ui/_list_data_source.py`

**Публічний API:**
```python
class ListDataSource:
    items: Any  # ListDataSourceList або звичайний список
    
    def __init__(self, items=None):  # items може бути списком
        """Створює data source зі списку items."""
    
    def reload(self) -> None
    def tableview_accessory_button_tapped(self, tableview, section, row) -> None
    def tableview_can_delete(self, tableview, section, row) -> bool
    def tableview_can_move(self, tableview, section, row) -> bool
    def tableview_cell_for_row(self, tableview, section, row) -> TableViewCell
    def tableview_delete(self, tableview, section, row) -> None
    def tableview_did_select(self, tableview, section, row) -> None
    def tableview_move_row(self, tableview, from_section, from_row, to_section, to_row) -> None
    def tableview_number_of_rows(self, tableview, section) -> int
    def tableview_number_of_sections(self, tableview) -> int

class ListDataSourceList(list):
    """Список, який автоматично повідомляє TableView про зміни."""
    # Всі методи list + автоматичний виклик reload() при змінах
```

### 1.3 TableView та TableViewCell
**Модуль:** `pytoui/ui/_table_view.py`

**Публічний API TableView:**
```python
class TableView(ScrollView):
    allows_multiple_selection: bool
    allows_selection: bool
    data_source: ListDataSource | None
    delegate: Any
    editing: bool
    row_height: float
    separator_color: __ColorLike
    selected_row: int
    selected_rows: list[int]
    
    def __init__(self, *args, **kwargs):
        # Варіант 1: Пустий
        # Варіант 2: З data source
        # Варіант 3: З frame та data source
    
    def reload(self) -> None
    def reload_data(self) -> None
    def delete_rows(self, rows: list[tuple[int, int]]) -> None  # (section, row)
    def insert_rows(self, rows: list[tuple[int, int]]) -> None
    def set_editing(self, editing: bool, animated: bool = True) -> None
```

**Публічний API TableViewCell:**
```python
class TableViewCell(View):
    accessory_type: int  # 0=none, 1=checkmark, 2=detail, 3=detail_disclosure
    content_view: View
    detail_text_label: Label
    image_view: ImageView
    selectable: bool
    selected_background_view: View
    text_label: Label
    
    def __init__(self, style='default', reuse_identifier=None):
        # style: 'default', 'subtitle', 'value1', 'value2'
        pass
```

### 1.4 TextView
**Модуль:** `pytoui/ui/_text_view.py`
**Базовий клас:** `ScrollView`

**Публічний API:**
```python
class TextView(ScrollView):
    alignment: __Alignment
    autocapitalization_type: __CapitalizationType
    autocorrection_type: bool
    delegate: Any
    editable: bool
    font: __Font
    keyboard_type: __KeyboardType
    selectable: bool
    selected_range: tuple[int, int]
    spellchecking_type: bool
    text: str
    text_color: __ColorLike
    
    def begin_editing(self) -> None
    def end_editing(self) -> None
    def replace_range(self, start: int, end: int, text: str) -> None
```

### 1.5 TextField
**Модуль:** `pytoui/ui/_text_field.py`
**Базовий клас:** `View`

**Публічний API:**
```python
class TextField(View):
    action: __Action | None
    autocapitalization_type: __CapitalizationType
    autocorrection_type: bool
    bordered: bool
    clear_button_mode: int  # 0=never, 1=while editing, 2=unless editing, 3=always
    delegate: Any
    enabled: bool
    font: __Font
    keyboard_type: __KeyboardType
    placeholder: str
    secure: bool
    spellchecking_type: bool
    text: str
    text_color: __ColorLike
    
    def begin_editing(self) -> None
    def end_editing(self) -> None
```

### 1.6 WebView
**Модуль:** `pytoui/ui/_web_view.py`
**Базовий клас:** `View`

**Публічний API:**
```python
class WebView(View):
    delegate: Any
    scales_page_to_fit: bool
    
    def load_url(self, url: str) -> None
    def load_html(self, html: str, base_url: str | None = None) -> None
    def eval_js(self, script: str) -> Any
    def evaluate_javascript(self, script: str) -> Any
    def go_back(self) -> None
    def go_forward(self) -> None
    def reload(self) -> None
    def stop(self) -> None
```

## 2. ДОПОВНЕННЯ ІСНУЮЧИХ КЛАСІВ

### 2.1 Image - додати методи
**Файл:** `pytoui/ui/_image.py`

```python
class _Image:
    # ВЖЕ Є: __init__, _make, from_data, from_image_context, named, 
    #        draw, show, to_jpeg, to_png, rendering_mode, with_rendering_mode
    
    # Додати:
    def clip_to_mask(self, x: float, y: float, w: float, h: float) -> None:
        """Use image as clipping mask.
        
        Встановлює поточне зображення як маску для наступних малювань.
        Після виклику цього методу, всі наступні малювання будуть обмежені
        непрозорими областями зображення.
        
        Аргументи:
            x, y: позиція маски
            w, h: розміри маски
        """
        # Реалізація через маскування в Rust
        # Зберігає поточний clip stack і додає новий рівень маскування
        
    def draw_as_pattern(self, x: float, y: float, w: float, h: float) -> None:
        """Fill rectangle with image as repeating pattern.
        
        Малює зображення як патерн, повторюючи його в заданому прямокутнику.
        Зображення повторюється як tile, починаючи з (x, y).
        
        Аргументи:
            x, y: позиція прямокутника для заповнення
            w, h: розміри прямокутника
        """
        # Реалізація через tile blitting
        # Малює зображення повторюючи його по горизонталі та вертикалі
        
    def resizable_image(self, top: float, left: float, bottom: float, right: float) -> Image:
        """Create a 9-patch image with the given edges.
        
        Створює копію зображення з метаданими для розтягування (9-patch).
        Кути залишаються незмінними, краї розтягуються в одному напрямку,
        центр розтягується в обох напрямках.
        
        Аргументи:
            top: відступ зверху, який не розтягується
            left: відступ зліва, який не розтягується
            bottom: відступ знизу, який не розтягується
            right: відступ справа, який не розтягується
            
        Повертає:
            Нове зображення з капами для розтягування
        """
        # Зберігає insets в _cap_insets атрибуті
        # При малюванні з розтягуванням використовує ці insets
```

## 3. ГЛОБАЛЬНІ ФУНКЦІЇ

### 3.1 Функції серіалізації/десеріалізації
**Файл:** `pytoui/ui/_serialize.py`

```python
def _color2str(color: __ColorLike) -> str:
    """Convert color to string format.
    
    Формати:
    - Назва кольору: "red", "blue" (якщо є в CSS)
    - RGBA: "RGBA(1.0,0.5,0.0,1.0)"
    - HEX: "#FF0000" або "0xFF0000"
    
    Якщо колір None, повертає "None".
    """
    # Використовується для серіалізації кольорів в JSON

def _str2color(s: str) -> __RGBA:
    """Parse color from string.
    
    Підтримує всі формати з _color2str.
    Якщо рядок "None", повертає None.
    Якщо не вдається розпарсити, повертає чорний колір (0,0,0,1).
    """

def _rect2str(rect: __RectLike) -> str:
    """Convert rect to string format.
    
    Формат: "{{x,y},{w,h}}" як в Pythonista
    Приклад: Rect(10, 20, 100, 50) -> "{{10,20},{100,50}}"
    """

def _str2rect(s: str) -> Rect:
    """Parse rect from string.
    
    Використовує RECT_REGEX для парсингу.
    Формат: "{{x,y},{w,h}}"
    Якщо не вдається розпарсити, повертає Rect(0,0,0,0).
    """

def _view_to_dict(view: View) -> dict:
    """Serialize view hierarchy to dict.
    
    Рекурсивно конвертує view та всі subviews в dict.
    Зберігає:
    - "class": назва класу (наприклад, "Button")
    - "frame": [x, y, w, h]
    - "flex": рядок flex
    - "background_color": колір через _color2str
    - "name": ім'я view
    - "subviews": список словників для кожної дочірньої view
    - Специфічні для класу атрибути:
      * Button: "title", "action" (ім'я методу), "font", "enabled"
      * Label: "text", "font", "text_color", "alignment", "number_of_lines"
      * ImageView: "image" (шлях до зображення), "content_mode"
      * ScrollView: "content_size", "scroll_enabled", "paging_enabled"
      * Switch: "value", "enabled"
      * Slider: "value", "continuous"
      * SegmentedControl: "segments", "selected_index"
      * TextField: "text", "placeholder", "secure", "keyboard_type"
    
    Використовується для збереження UI стану.
    """

def _view_from_dict(data: dict) -> View:
    """Deserialize view hierarchy from dict.
    
    Створює view з dict, рекурсивно створюючи subviews.
    Використовується для завантаження UI.
    
    Очікує той самий формат, що й _view_to_dict.
    
    Для action зберігає ім'я методу як рядок, який потім можна
    прив'язати через _bind_action.
    """

def _bind_action(view: View, action_name: str) -> None:
    """Bind action to view by name.
    
    Динамічно прив'язує метод об'єкта до action view.
    Шукає метод з іменем action_name в батьківському об'єкті
    (наприклад, в контролері, який містить цю view).
    
    Алгоритм:
    1. Піднімається по superview ланцюжку, поки не знайде об'єкт
       з методом action_name
    2. Якщо знайдено, встановлює view.action = bound method
    
    Приклад:
        class MyController:
            def __init__(self):
                self.button = Button(title="OK")
                _bind_action(self.button, "button_tapped")
            
            def button_tapped(self, sender):
                print("Button tapped!")
    """
```

### 3.2 Утиліти
**Файл:** `pytoui/ui/_utils.py`

```python
def begin_image_context(width: float, height: float, scale: float = 1.0) -> None:
    """Begin offscreen image context.
    
    Глобальна версія ImageContext. Зберігає контекст в thread-local змінній.
    Використовується для сумісності з кодом, який очікує глобальний контекст.
    
    Після виклику, всі малювальні операції будуть спрямовані в offscreen buffer.
    
    Приклад:
        ui.begin_image_context(100, 100)
        ui.set_color("red")
        ui.Path.oval(0, 0, 100, 100).fill()
        img = ui.end_image_context()
    """

def end_image_context() -> Image:
    """End offscreen context and return image.
    
    Завершує глобальний контекст і повертає зображення.
    Повертає Image з намальованим вмістом.
    Якщо контекст не було розпочато, повертає пусте зображення.
    """

def close_all() -> None:
    """Close all presented views.
    
    Закриває всі вікна/в'ю, відкриті через present().
    Корисно для cleanup при виході з програми.
    Проходить по всіх зареєстрованих runtime і викликає close().
    """

def dump_view(view: View, recurse: bool = True) -> str:
    """Dump view hierarchy as string for debugging.
    
    Формат:
        <View: 0x123456> (100x200) name="main"
          <Button: 0x123457> (80x44) title="OK"
          <Label: 0x123458> (100x20) text="Hello"
    
    Аргументи:
        view: коренева view для дампу
        recurse: якщо True, рекурсивно дампить всі subviews
    
    Повертає багаторядковий рядок з ієрархією.
    """

def end_editing() -> None:
    """End editing in all text fields.
    
    Проходить по всій ієрархії view і викликає resignFirstResponder
    для всіх текстових полів, ховаючи клавіатуру.
    
    Корисно викликати при тапі на фон, щоб сховати клавіатуру.
    """

def get_keyboard_frame() -> Rect:
    """Get current keyboard frame.
    
    Повертає Rect з поточними розмірами клавіатури в координатах екрану.
    
    На десктопі завжди повертає Rect(0,0,0,0)
    На iOS повертає фактичні розміри клавіатури, коли вона показана,
    або Rect(0,0,0,0) коли клавіатура схована.
    
    Використовується для анімації при появі клавіатури.
    """

def load_view(view_name: str) -> View | None:
    """Load view from .ui.json or .py file.
    
    Алгоритм:
    1. Шукає {view_name}.ui.json в поточній директорії
    2. Якщо знайдено, парсить JSON через _view_from_dict
    3. Якщо не знайдено, шукає {view_name}.py
    4. Імпортує модуль і шукає клас з іменем view_name
    5. Створює екземпляр класу
    6. Повертає екземпляр view або None
    
    Приклад:
        # my_button.ui.json
        {
            "class": "Button",
            "frame": [0, 0, 100, 44],
            "title": "OK",
            "action": "button_tapped"
        }
        
        button = load_view("my_button")  # завантажує з JSON
    """

def load_view_str(json_str: str) -> View:
    """Load view from JSON string.
    
    Парсить JSON рядок і створює view ієрархію через _view_from_dict.
    
    Формат JSON:
    {
        "class": "Button",
        "frame": [0, 0, 100, 44],
        "title": "OK",
        "subviews": [...]
    }
    
    Повертає створену view.
    """

def settrace(func: Callable | None) -> None:
    """Set trace function for debugging UI events.
    
    Встановлює функцію трасування для дебагінгу подій.
    Аналогічно sys.settrace, але для UI подій.
    
    Функція отримує словник з інформацією про подію:
    - "type": "touch", "action", "layout", "draw"
    - "view": view, яка отримала подію
    - "timestamp": час події
    - Додаткові поля в залежності від типу:
      * touch: "phase", "location"
      * action: "sender"
      * layout: "frame"
      * draw: "rect"
    
    Приклад:
        def trace(event):
            print(f"{event['timestamp']}: {event['type']} on {event['view']}")
        ui.settrace(trace)
    
    Якщо func is None, вимикає трасування.
    Використовується для профілювання та дебагінгу.
    """
```

## 4. ВИПРАВЛЕННЯ PYTHONISTA-СУМІСНОСТІ

### 4.1 Конструктори з *args, **kwargs

**Проблема:** Зараз у Pythonista-режимі конструктори порожні:
```python
class View(ui.View):
    def __init__(self):
        # NOTE: override cause we can't handle *args, **kwargs for a while
        pass
```

**Рішення:** Реалізувати універсальний парсер аргументів

```python
def _parse_view_args(*args, **kwargs):
    """Парсить аргументи конструктора View.
    
    Повертає (frame, flex, bg_color, name, rest_kwargs)
    """
    frame = None
    flex = ""
    bg_color = None
    name = None
    
    # Обробка позиційних аргументів
    if len(args) == 1:
        # Один аргумент - може бути tuple або frame як один об'єкт
        if isinstance(args[0], (tuple, list, Rect)):
            frame = Rect(*args[0])
        else:
            # Можливо це name? Але frame обов'язковий, тому ігноруємо
            frame = Rect(0, 0, 100, 100)
    elif len(args) == 2:
        # (x, y) - використовуємо дефолтні розміри
        frame = Rect(args[0], args[1], 100, 100)
    elif len(args) == 4:
        # (x, y, w, h)
        frame = Rect(*args)
    
    # Обробка keyword аргументів
    frame = kwargs.get('frame', frame)
    if frame is not None and not isinstance(frame, Rect):
        frame = Rect(*frame)
    
    flex = kwargs.get('flex', flex)
    bg_color = kwargs.get('background_color', bg_color)
    name = kwargs.get('name', name)
    
    # Все інше зберігаємо для підкласів
    rest = {k: v for k, v in kwargs.items() 
            if k not in ('frame', 'flex', 'background_color', 'name')}
    
    # Якщо frame досі не встановлений - використовуємо дефолт
    if frame is None:
        frame = Rect(0, 0, 100, 100)
    
    return frame, flex, bg_color, name, rest


def _parse_button_args(*args, **kwargs):
    """Парсить аргументи конструктора Button."""
    frame, flex, bg_color, name, rest = _parse_view_args(*args, **kwargs)
    
    title = rest.pop('title', None)
    action = rest.pop('action', None)
    image = rest.pop('image', None)
    background_image = rest.pop('background_image', None)
    font = rest.pop('font', ('<system>', 17.0))
    enabled = rest.pop('enabled', True)
    
    # Якщо є позиційні аргументи після frame
    args_list = list(args)
    if len(args_list) > 4:  # Після 4 чисел для frame
        remaining = args_list[4:]
        if remaining and title is None:
            title = remaining[0]
        if len(remaining) > 1 and action is None:
            action = remaining[1]
    
    return frame, title, action, image, background_image, font, enabled, rest


# Аналогічно для інших класів
```

### 4.2 Оновлення Pythonista-класів

```python
if IS_PYTHONISTA:
    import ui
    
    class View(ui.View):
        def __init__(self, *args, **kwargs):
            # Викликаємо super() першим для ініціалізації ObjC
            super().__init__()
            
            # Парсимо аргументи
            frame, flex, bg_color, name, rest = _parse_view_args(*args, **kwargs)
            
            # Створюємо внутрішню імплементацію
            self._pytoui = _View()
            
            # Встановлюємо атрибути
            self._pytoui.frame = frame
            self.frame = frame.as_tuple()  # для ObjC
            
            self._pytoui.flex = flex
            self._pytoui.background_color = bg_color
            if bg_color:
                # Конвертуємо в UIColor для ObjC
                # Це складно, тому поки пропускаємо
                pass
                
            self._pytoui.name = name or str(id(self))
            self.name = self._pytoui.name
            
            # Додаткові kwargs
            for key, value in rest.items():
                if hasattr(self._pytoui, key):
                    setattr(self._pytoui, key, value)
        
        def __getattr__(self, name):
            """Делегування до pytoui імплементації."""
            if name.startswith('__') and name.endswith('__'):
                raise AttributeError(name)
            
            # Спочатку шукаємо в ObjC
            try:
                return super().__getattr__(name)
            except AttributeError:
                # Потім в pytoui
                return getattr(self._pytoui, name)
        
        def __setattr__(self, name, value):
            """Синхронізація атрибутів."""
            if name in ('_pytoui', '__dict__'):
                super().__setattr__(name, value)
                return
            
            # Встановлюємо в pytoui
            if hasattr(self, '_pytoui') and hasattr(self._pytoui, name):
                setattr(self._pytoui, name, value)
            
            # Встановлюємо в ObjC
            super().__setattr__(name, value)
        
        def draw(self):
            self._pytoui.draw()
        
        def layout(self):
            self._pytoui.layout()
        
        def update(self):
            self._pytoui.update()
        
        # ... інші методи
```

## 5. ТЕХНІЧНІ ДЕТАЛІ

### 5.1 Чому конструктори мають `*args, **kwargs`?
**Пояснення:** В Pythonista багато класів можна створювати різними способами:
```python
# За позиційними аргументами
view = View(0, 0, 100, 100)  # frame як позиційні

# За ключовими аргументами
view = View(frame=(0,0,100,100), name="test")

# Змішано
view = View(0, 0, 100, 100, name="test")

# З одним tuple
view = View((0,0,100,100))
```

### 5.2 Специфічні для класів позиційні аргументи

| Клас | Позиційні аргументи після frame |
|------|----------------------------------|
| Button | title, action |
| Label | text |
| ImageView | image |
| TextField | text, placeholder |
| Switch | value |
| Slider | value |
| SegmentedControl | segments, selected_index |
| DatePicker | mode, date |
| ActivityIndicator | style |

## 6. ЕТАПИ РЕАЛІЗАЦІЇ

### Етап 1 (2-3 тижні) - Базові класи
- [ ] Виправити конструктори для всіх класів (найважливіше!)
- [ ] Додати `TableView` та `TableViewCell`
- [ ] Додати `ListDataSource` та `ListDataSourceList`

### Етап 2 (1-2 тижні) - Текстові класи
- [ ] Додати `TextField`
- [ ] Додати `TextView`
- [ ] Додати `DatePicker`

### Етап 3 (1 тиждень) - Web та утиліти
- [ ] Додати `WebView`
- [ ] Додати глобальні функції серіалізації
- [ ] Додати утиліти (`load_view`, `dump_view` тощо)

### Етап 4 (3-5 днів) - Доповнення
- [ ] Додати методи до `Image` (`clip_to_mask`, `draw_as_pattern`, `resizable_image`)
- [ ] Додати решту ObjC-заглушок

## 7. ТЕСТУВАННЯ

### 7.1 Тести для конструкторів
```python
def test_view_constructors():
    # Тестуємо різні способи створення View
    v1 = View(10, 20, 200, 100)
    assert v1.frame == (10, 20, 200, 100)
    
    v2 = View((10, 20, 200, 100))
    assert v2.frame == (10, 20, 200, 100)
    
    v3 = View(frame=(10, 20, 200, 100), name="test")
    assert v3.frame == (10, 20, 200, 100)
    assert v3.name == "test"
    
    v4 = View(10, 20, 200, 100, name="test")
    assert v4.frame == (10, 20, 200, 100)
    assert v4.name == "test"

def test_button_constructors():
    b1 = Button("OK")
    assert b1.title == "OK"
    
    def action(sender): pass
    b2 = Button("OK", action)
    assert b2.title == "OK"
    assert b2.action == action
    
    b3 = Button(10, 20, 100, 44, "OK")
    assert b3.frame == (10, 20, 100, 44)
    assert b3.title == "OK"
```

### 7.2 Тести для Pythonista-сумісності
```python
def test_view_pythonista_compatibility():
    # Тест, що клас працює в обох режимах
    with patch('pytoui._platform.IS_PYTHONISTA', True):
        view = View(frame=(0,0,100,100), name="test")
        assert isinstance(view, ui.View)
        assert view._pytoui is not None
        assert view.name == "test"
        assert view._pytoui.name == "test"
```

------------------------------------------------------------------------


# Ці класи є в Pythonista, але відсутні в pytoui: -- поки не реалізовано
DatePicker
ListDataSource
ListDataSourceList
TableView
TableViewCell
TextView
TextField  # -- пробували але поки ні
WebView

# В Pythonista View має: -- тимчасово не реалізовано, поки додам прості проперті
left_button_items: Any  # підтримується через ButtonItem, але не в View
right_button_items: Any  # підтримується через ButtonItem, але не в View
objc_instance: Any  # відсутній (специфічний для Pythonista)


# Функції серіалізації/десеріалізації: -- є частково в стабах, дещо не документовано 
_color2str, _rect2str, _str2color, _str2rect
_view_from_dict, _view_to_dict
_bind_action

# Утиліти: -- треба опис функцій - не документовано
begin_image_context  # є ImageContext, але не глобальна функція
end_image_context    # є ImageContext, але не глобальна функція
close_all()
dump_view()
end_editing()
get_keyboard_frame()
load_view(), load_view_str()
settrace()

#
-- це шим тож тут так і треба
-- треба отримати сигнатури конструкторів що б повторити логіку, не документовано
```python
class View(ui.View):  # type: ignore[assignment,misc,no-redef]
    def __init__(self):
        # NOTE: override cause we can't handle *args, **kwargs for a while
        pass
```

-- це ще не реалізована внутрішня логіка
# Pythonista:
```python
def become_first_responder(self) -> None: ...
```

# pytoui:
```python
def become_first_responder(self) -> None: ...
```

# В Image відсутні:
clip_to_mask()
draw_as_pattern()
resizable_image()
