NOTE:
* continuing work on the src/ui/ module
* This is an free implementation of Pythonista.ui with a compatible public interface, and emulating core logic, drawn to the buffer via osdbuf/src/lib.rs (based on tiny-skia and fontdue)
* we should be maximum close to original Pythonista.ui public API and it's internal behaviour
* original Pythonista.ui stubs got using inspect and miroring in src/ui/stubgen/
* Pythinista.ui docs at https://omz-software.com/pythonista/docs/ios/ui.html
* original Pythonista.ui references, inspected stubs are in the src/ui/resources
* osdbuf.py is in src/osdbuf/__init__.py

HOT:
* Image: implement methods with the rust backend

NEXT:
* possibly: add Numpad / punctuation keys support (maybe optional through _runtime/_platform env variable)
* add keyboard input support (for future text input functionality)
* dialogs.alert() and other
* View
  * View.present.style
    * View.present("sheet") - default, uses popower location, on "present" as a second should be drawn in same window
    * View.present("fullscreen") - fullscreen
    * View.present("popover") - uses popower location
    * View.present("panel") - uses popower location, as second window not blocks the first one till opened
  * which View.present() args are not completely used?
  * code after View.present should continue to run
* Ideas how to implement View.right_button_items/View.left_button_items, maybe with _pytoui_systemSubviews or kinda, but we need somehow handle the touch and mouse clicks

Runtime
* ~~ImageView, Image shims~~ (fixed: _ImageView + _Image desktop classes; on Pythonista ImageView=ui.ImageView with load_from_url preserved, Image=ui.Image; ImageContext already shimmed in _draw.py)
* Pillow can be not always available, so maybe we are need some rust based fallback like an "image" crate for ui.ImageContext, ui.ImageView ui.Image
* Add keyboard events for View that supports input or hot-keys binding (idk if Pythonista ) (for sdl for now)
* does Viev.wait_modal implemented right?
* Add raw FrameBuffer runtime but with loop and possibility to use external pointer to fb
* WinitRuntime macOS support: EventLoop must run on main thread — needs separate #[cfg(target_os="macos")] code path in lib.rs (no background thread, first winit_run runs loop inline)
* Add possibility to add custom runtimes, not build it to the library (for overriding etc)
* maybe add View _global_dirty_counter to skip some rerenders?
* CALayer-style per-view backing store: each view renders into its own pixel buffer and is composited into the parent only when dirty — enables true per-view dirty skip. Heavy architectural change: requires a separate FrameBuffer or rgba array per view + compositor pass.

---------------------------------------------------------

_a public classes that is full/partially or not implemented bellow, after core problems will be resolved we should fully review and research it_

---------------------------------------------------------

View classes:
* ~~View~~
* ~~Button~~
* ButtonItem (not yet implemented in View)
* ~~ImageView - _make_test_image works only on PC~~
* ~~Label~~
* ~~NavigationView~~
* ~~ScrollView~~
* ~~SegmentedControl~~
* ~~Slider~~
* ~~Switch~~
* TableView
* TableViewCell
* TextField
* TextView
* WebView
* DatePicker (in progress, almost, the countdown mode is not done)
* ~~ActivityIndicator~~

Other Classes:
* Image (idk how it works but not implemented)
* ~~ImageContext~~
* ~~Path~~
* ~~Touch~~
* ~~Transform~~
* ~~GState~~
* ListDataSource

Funcs:
* ~~animate~~
* ~~cancel_delays~~
* ~~convert_point~~
* ~~convert_rect~~
* ~~delay~~
* ~~in_background~~
* ~~_color2str~~
* ~~_rect2str~~
* ~~_str2color~~
* ~~_str2rect~~
* ~~_bind_action~~
* ~~load_view~~
* ~~load_view_str~~
* ~~dump_view~~
* _view_to_dict
* _view_from_dict
* settrace
* ~~get_screen_size~~
* ~~get_window_size~~
* ~~get_ui_style~~

Drawing:
* ~~parse_color~~
* ~~fill_rect~~
* ~~set_blend_mode~~
* ~~set_color~~
* ~~set_shadow~~
* ~~concat_ctm~~
* ~~measure_string~~
* ~~draw_string~~

Enums:
* ~~BlendMode~~
* ~~LineCapStyle~~
* ~~LineJoinStyle~~
* ~~KeyboardType~~
* ~~ViewContentMode~~
* ~~LineBrakeMode~~
* ~~TextAlignment~~
* ~~TextAutoCapitalization~~
* ~~DatePickerMode~~
* ~~ActivityIndicatorStyle~~
* ~~RenderingMode~~

--------------------------------------------------------
