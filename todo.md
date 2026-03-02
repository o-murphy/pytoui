NOTE:
* continuing work on the src/ui/ module
* This is an free implementation of Pythonista.ui with a compatible public interface, and emulating core logic, drawn to the buffer via osdbuf/src/lib.rs (based on tiny-skia and fontdue)
* we should be maximum close to original Pythonista.ui public API and it's internal behaviour
* original Pythonista.ui stubs got using inspect and miroring in src/ui/stubgen/
* Pythinista.ui docs at https://omz-software.com/pythonista/docs/ios/ui.html
* original Pythonista.ui references, inspected stubs are in the src/ui/resources
* osdbuf.py is in src/osdbuf/__init__.py

HOT:
* ~~ScrollView~~ (PC implementation complete)
  * ~~clips to bounds should work the render or for the draw?~~ (fixed: single GState clip)
  * ~~paging not working~~ (fixed: direction + debounce)
  * ~~ScrollView scroll displaying under the content~~ (fixed: _pytoui_system_subviews)
  * ~~ScrollView is not working as expected / subviews steal touch events~~ (fixed: UIKit-style interceptor — scroll has full priority, tap delivery is retroactive)
  * ~~scrollview scrolls too fast on wheel~~ (fixed: _SCROLL_LINE_PX = 8.0)
  * ~~mouse_scroll_enabled not tied to scroll_enabled~~ (fixed: property override)
  * ~~_draw_indicators crashes on Pythonista~~ (fixed: IS_PYTHONISTA guard)
  * ~~ScrollView shim implemented~~ (fixed: IS_PYTHONISTA → ui.ScrollView on Pythonista, _ScrollView on desktop)
  * ~~mouse_scroll_enabled getter had infinite recursion~~ (fixed: use _internals_._pytoui_mouse_scroll_enabled)
  * ~~implement animations for paging~~ (fixed: _start_page_anim + cubic easeOut in update(), 0.30s)
* ~~startup glitch when many views added~~ (resolved: was caused by missing clip, fixed with single-GState render)
* ~~issue: draws rects with negative height and width~~ (fixed: fw<=0 or fh<=0 guard in pytoui_render)
* SegmentedView and other scrollable widgets can steal scroll of ScrollView, Idk if we need to handle it and how
* ~~Button: draw_string not at button's vertical center~~ (fixed: frame setter resets _pytoui_content_draw_size on resize — global fix for all draw() views)
* ~~Allow close app with Ctrl+C~~ (fixed: signal.SIGINT handler in SDLRuntime.run() and WinitRuntime.run())
* Winit (wayland scaling) - some views not scale to the window scale factor (root cause: winit_run writes physical px to width_ptr/height_ptr; on HiDPI logical coords in subviews appear too small — needs Rust-side scale_factor output param)

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

Runtime
* Pillow can be not always available, so maybe we are need some rust based fallback like an "image" crate for ui.ImageContext, ui.ImageView ui.Image
* Add keyboard events for View that supports input or hot-keys binding (idk if Pythonista ) (for sdl for now)
* does Viev.wait_modal implemented right?
* Add raw FrameBuffer runtime but with loop and possibility to use external pointer to fb
* WinitRuntime macOS support: EventLoop must run on main thread — needs separate #[cfg(target_os="macos")] code path in lib.rs (no background thread, first winit_run runs loop inline)
* Add possibility to add custom runtimes, not build it to the library (for overriding etc)
* maybe add View _global_dirty_counter to skip some rerenders?

---------------------------------------------------------

_a public classes that is full/partially or not implemented bellow, after core problems will be resolved we should fully review and research it_

---------------------------------------------------------

View classes:
* ~~View~~
* ~~Button~~
* ButtonItem (not yet implemented in View)
* ~~ImageView - _make_test_image works only on PC~~
* ~~Label~~
* NavigationView
* ~~ScrollView~~ (PC implementation done)
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
* ~~Image~~
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
