NOTE:
* continuing work on the src/ui/ module
* This is an free implementation of Pythonista.ui with a compatible public interface, and emulating core logic, drawn to the buffer via osdbuf/src/lib.rs (based on tiny-skia and fontdue)
* we should be maximum close to original Pythonista.ui public API and it's internal behaviour
* original Pythonista.ui stubs got using inspect and miroring in src/ui/stubgen/
* Pythinista.ui docs at https://omz-software.com/pythonista/docs/ios/ui.html
* original Pythonista.ui references, docs and inspected stubs are in the src/ui/reference
* osdbuf.py is in src/osdbuf/__init__.py

HOT:
* View
  * View.present.style (for sdl for now)
    * View.present("sheet") - default, uses popower location, on "present" as a second window blocks the first one till opened (like modal view) i think.
    * View.present("fullscreen") - fullscreen
    * View.present("popover") - uses popower location
    * View.present("panel") - uses popower location, as second window not blocks the first one till opened
  * which View.present() args are not completely used?

Runtime
* ~~Need update ui.View.present() to allow it automatically grep available runtime like SDLRuntime now? or better to create SDLRuntime based launcher? I do not want write SDLRuntime for every testing ui project~~
* Pillow can be not always available, so maybe we are need some rust based fallback like an "image" crate for ui.ImageContext, ui.ImageView ui.Image
* multitouch support: Touch.touch_id is not unique for the single touch? but should be! it's for multitouch (not for mouse) (for sdl for now)
* Add raw FrameBuffer runtime but with loop and possibility to use external pointer to fb
* ~~Add runtime alternative for SDLRuntime but thin winit+softbuffer~~ (src/rt/ — WinitRuntime, multi-window via global EventLoop thread, Linux/Windows)
* Add keyboard events for View that supports input or hot-keys binding (idk if Pythonista ) (for sdl for now)
  * get_key_commands
  * key_command
* This functions does same,but shoud do different things
  * get_screen_size
  * get_window_size
* does Viev.wait_modal implemented right?
* 
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
* ~~ImageView~~
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

DONE:
* ~~tint_color should be from superview if None~~
* ~~need fix all FIXME's in ui.draw~~
* ~~some drawing methods in Path and lib.rs still do not support stroke / fill~~
* ~~need implement full ui.draw.Transform support~~
* ~~ui.draw._layout_lines maybe should use ctx.fb automatically or it's inner calls can be optimized?~~
* ~~maybe ui.draw.render_view_tree, ui.draw._render_view should be inside View draw method? or as a separate View._render~~
* ~~use constants_._UI_RUNTIME (one of SDLRuntime or RawFrameBufferRuntime), render_view_tree now seems like useless, we need to make the View find runtime itself during .present() to launch the application identically to Pythonista ui~~
* ~~implement ui.animate - fix imports because it's currently animate for runtime~~
* ~~implement ui._draw.animate (ui.animate) like in pythonista.ui~~
* ~~need add set_alpha in _draw.py and implement usage~~
* ~~there are no set_origin in Pythonista.ui so maybe not needed or should not be in _ctx and be internal only~~
* ~~big refactoring, we should move to rust osdbuf / osdbuf.FrameBuffer this implementations~~
  * ~~need add Path.add_clip, Path.hit_test, Path.set_line_dash, Path.append_path in _draw.py~~
  * ~~Transform~~
  * ~~GState~~
  * ~~Path~~
* ~~add Path.eo_fill_rule as is in Pythonista.ui~~ (Rust: eo_fill_rule field + PathSetEoFillRule + FillRule::EvenOdd; Python: property on Path; GState clip save/restore; PathHitTest uses eo_fill_rule)
* ~~add Path.add_clip as is in Pythonista.ui~~ (Rust: PathAddClip + Mask in FrameBuffer + GState clip save/restore; Python: Path.add_clip(); PathStroke/PathFill pass clip to tiny-skia)
* ~~Path.add_curve / add_quad_curve argument order wrong vs Pythonista~~ — fixed: Python API now end-point-FIRST matching Pythonista; Rust call reorders internally
* ~~Path.bounds property~~ — PathGetBounds in Rust (tiny-skia path.bounds()); Python Path.bounds returns Rect
* ~~View.update / update_interval vs Pythonista~~ — SDLRuntime matches; RawFrameBufferRuntime intentionally single-frame
* ~~ui.ActivityIndicator frame should not change, but bounds should and indicator should be centered~~ — fixed: style setter no longer changes frame; draw() uses fixed pixel geometry per style (not proportional to frame); indicator is centered within frame via cx=width/2, cy=height/2
* ~~does View should use content_mode to adjust bounds to frame and frame to bounds?~~ — NO, content_mode does not affect frame/bounds sync (they always mirror dimensions by UIKit design)
* ~~Need update/optimize ui.View subcalsses .draw methods~~
* ~~Need draw much better styled views~~
* ~~HOT#1 RESOLVED: View.content_mode does NOT affect frame↔bounds sync — they always mirror dimensions. content_mode only governs how draw()-content is visually scaled/placed within bounds (CONTENT_REDRAW calls draw() on resize, scale modes cache and transform existing content). Current implementation is correct.~~
* ~~Path.add_curve / add_quad_curve argument order was WRONG vs Pythonista~~ — fixed in _draw.py only (Rust order unchanged); Python API now end-point-FIRST: add_curve(end_x, end_y, cp1_x, cp1_y, cp2_x, cp2_y), add_quad_curve(end_x, end_y, cp_x, cp_y); Python reorders args before Rust call
* ~~Path.bounds property missing~~ — added PathGetBounds(handle, x_out, y_out, w_out, h_out)->i32 in Rust (tiny-skia path.bounds()); Python Path.bounds property returns Rect via ctypes output pointers
* ~~View.content_mode not used during draw()~~ — implemented: _render() applies CTM pre-transform via _content_mode_transform() for non-REDRAW modes; first render records (fw,fh) as content size; subsequent renders scale/position content accordingly; CONTENT_REDRAW (default for all subclasses) unchanged
* ~~Problem with ui.Switch it is lagging and not always complete it's animation, also it should be bounded to left top corner of it's bound if other is not defined~~ — animation moved to update() driven by update_interval=1/60; draw() is now pure rendering; bounding changed to top-left (ox=0, oy=0)
* ~~Problem: differend drawing style of ui.ActivityIndicator on first render~~ — start() now calls update() immediately so first visible frame shows step=1 (not frozen step=0)