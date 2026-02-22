NOTE:
* continuing work on the src/ui/ module
* This is an free implementation of Pythonista.ui with a compatible public interface, and emulating core logic, drawn to the buffer via osdbuf/src/lib.rs (based on tiny-skia and fontdue)
* we should be maximum close to original Pythonista.ui public API and it's internal behaviour
* original Pythonista.ui stubs got using inspect and miroring in src/ui/stubgen/
* Pythinista.ui docs at https://omz-software.com/pythonista/docs/ios/ui.html
* original Pythonista.ui references, inspected stubs are in the src/ui/resources
* osdbuf.py is in src/osdbuf/__init__.py

HOT:
* ~~maybe instead of check IS_PYTHONISTA every time we should create some _ViewMixin class~~ (done: _BaseView)
* touch redirection from runtime to target (traked) view now managed by runtime itself, maybe touch event should be sent to each view, and the view should manage it itself? For dnd support or for events that can be started out of target view? we need implement hit_test strategy or use the `Path.hit_test`
* View
  * View.present.style
    * View.present("sheet") - default, uses popower location, on "present" as a second window blocks the first one till opened (like modal view) i think.
    * View.present("fullscreen") - fullscreen
    * View.present("popover") - uses popower location
    * View.present("panel") - uses popower location, as second window not blocks the first one till opened
  * which View.present() args are not completely used?

Runtime
* Pillow can be not always available, so maybe we are need some rust based fallback like an "image" crate for ui.ImageContext, ui.ImageView ui.Image
* Add raw FrameBuffer runtime but with loop and possibility to use external pointer to fb
* Add keyboard events for View that supports input or hot-keys binding (idk if Pythonista ) (for sdl for now)
  * get_key_commands
  * key_command
* does Viev.wait_modal implemented right?
* WinitRuntime macOS support: EventLoop must run on main thread — needs separate #[cfg(target_os="macos")] code path in lib.rs (no background thread, first winit_run runs loop inline)
* Add possibility to add custom runtimes, not build it to the library (for overriding etc)
* maybe add View _global_dirty_counter to skip some rerenders?

---------------------------------------------------------

_a public classes that is full/partially or not implemented bellow, after core problems will be resolved we should fully review and research it_

---------------------------------------------------------

View classes:
* ~~View~~
* ~~Button~~
* ButtonItem
* ImageView
* ~~Label~~
* NavigationView
* ScrollView
* ~~SegmentedControl~~
* ~~Slider~~
* ~~Switch~~
* TableView
* TableViewCell
* TextField
* TextView
* WebView
* DatePicker
* ~~ActivityIndicator~~

Other Classes:
* Image
* ImageContext
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
* load_view
* load_view_str
* dump_view
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
* KeyboardType
* ~~ViewContentMode~~
* ~~LineBrakeMode~~
* ~~TextAlignment~~
* TextAutoCapitalization
* DatePickerMode
* ~~ActivityIndicatorStyle~~
* ~~RenderingMode~~

--------------------------------------------------------
