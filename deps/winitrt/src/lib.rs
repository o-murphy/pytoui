//! winit + softbuffer runtime for ui.
//!
//! Multi-window support:
//!   winit does not allow creating an EventLoop twice in the same process.
//!   Therefore, one global EventLoop lives in a background thread (winit on Linux
//!   does not require the main thread). Python threads register windows via UserEvent
//!   and block on an mpsc channel until their window is closed.

use std::collections::HashMap;
use std::ffi::CStr;
use std::num::NonZeroU32;
use std::os::raw::c_char;
use std::sync::{Arc, Mutex, OnceLock};
use std::sync::mpsc;

use softbuffer::{Context, Surface};
use winit::{
    dpi::LogicalSize,
    event::*,
    event_loop::{ControlFlow, EventLoopBuilder, EventLoopProxy, EventLoopWindowTarget},
    keyboard::{Key, KeyCode, NamedKey, PhysicalKey},
    window::{Window, WindowBuilder, WindowId},
};

// ── Callback types ─────────────────────────────────────────────────────────────
// render_callback returns 0 = continue, != 0 = close window (view.close())
type RenderCb = extern "C" fn() -> i32;
type EventCb  = extern "C" fn(i32, f64, f64, i64);

// ── UserEvent: request to add a new window ────────────────────────────────────
struct AddWindowReq {
    width:      u32,
    height:     u32,
    title:      String,
    pixel_ptr:  *mut u32,
    width_ptr:  *mut u32,
    height_ptr: *mut u32,
    render_cb:  RenderCb,
    event_cb:   EventCb,
    /// Python thread blocks on done_rx; we send () when the window closes
    done_tx:    mpsc::SyncSender<()>,
}

// Raw pointers are managed by the Python/ctypes side — this is safe
unsafe impl Send for AddWindowReq {}

enum AppEvent {
    AddWindow(AddWindowReq),
    GetScreenSize { tx: mpsc::SyncSender<(u32, u32)> },
}

// ── Single window state (lives on the EventLoop thread) ───────────────────────
struct WinState {
    window:     Arc<Window>,
    surface:    Surface<Arc<Window>, Arc<Window>>,
    pixel_ptr:  *mut u32,
    width_ptr:  *mut u32,
    height_ptr: *mut u32,
    render_cb:  RenderCb,
    event_cb:   EventCb,
    done_tx:    mpsc::SyncSender<()>,
    cursor_pos: (f64, f64),  // last known cursor position
    modifiers:  Modifiers,   // current modifier state
}

// ── Keyboard helpers ──────────────────────────────────────────────────────────

/// Map winit key event fields to an integer code for etype=5 events.
/// Named keys → codes 1-15 / 101-112; letter/digit keys → lowercase codepoint.
///
/// physical_key is used for letter/digit keys so the result is modifier- and
/// layout-independent (Ctrl+N always yields 'n', not the control character).
fn key_to_code(logical_key: &Key, physical_key: &PhysicalKey) -> Option<i64> {
    // Named keys are not affected by modifier state — use logical_key.
    if let Key::Named(named) = logical_key {
        return match named {
            NamedKey::ArrowUp    => Some(1),
            NamedKey::ArrowDown  => Some(2),
            NamedKey::ArrowLeft  => Some(3),
            NamedKey::ArrowRight => Some(4),
            NamedKey::Escape     => Some(5),
            NamedKey::Enter      => Some(6),
            NamedKey::Backspace  => Some(7),
            NamedKey::Tab        => Some(8),
            NamedKey::Space      => Some(9),
            NamedKey::Delete     => Some(10),
            NamedKey::Home       => Some(11),
            NamedKey::End        => Some(12),
            NamedKey::PageUp     => Some(13),
            NamedKey::PageDown   => Some(14),
            NamedKey::Insert     => Some(15),
            NamedKey::F1         => Some(1001),
            NamedKey::F2         => Some(1002),
            NamedKey::F3         => Some(1003),
            NamedKey::F4         => Some(1004),
            NamedKey::F5         => Some(1005),
            NamedKey::F6         => Some(1006),
            NamedKey::F7         => Some(1007),
            NamedKey::F8         => Some(1008),
            NamedKey::F9         => Some(1009),
            NamedKey::F10        => Some(1010),
            NamedKey::F11        => Some(1011),
            NamedKey::F12        => Some(1012),
            _                    => None,
        };
    }

    // For letter/digit keys use physical_key — modifier- and layout-independent.
    if let PhysicalKey::Code(code) = physical_key {
        return match code {
            KeyCode::KeyA => Some(b'a' as i64),
            KeyCode::KeyB => Some(b'b' as i64),
            KeyCode::KeyC => Some(b'c' as i64),
            KeyCode::KeyD => Some(b'd' as i64),
            KeyCode::KeyE => Some(b'e' as i64),
            KeyCode::KeyF => Some(b'f' as i64),
            KeyCode::KeyG => Some(b'g' as i64),
            KeyCode::KeyH => Some(b'h' as i64),
            KeyCode::KeyI => Some(b'i' as i64),
            KeyCode::KeyJ => Some(b'j' as i64),
            KeyCode::KeyK => Some(b'k' as i64),
            KeyCode::KeyL => Some(b'l' as i64),
            KeyCode::KeyM => Some(b'm' as i64),
            KeyCode::KeyN => Some(b'n' as i64),
            KeyCode::KeyO => Some(b'o' as i64),
            KeyCode::KeyP => Some(b'p' as i64),
            KeyCode::KeyQ => Some(b'q' as i64),
            KeyCode::KeyR => Some(b'r' as i64),
            KeyCode::KeyS => Some(b's' as i64),
            KeyCode::KeyT => Some(b't' as i64),
            KeyCode::KeyU => Some(b'u' as i64),
            KeyCode::KeyV => Some(b'v' as i64),
            KeyCode::KeyW => Some(b'w' as i64),
            KeyCode::KeyX => Some(b'x' as i64),
            KeyCode::KeyY => Some(b'y' as i64),
            KeyCode::KeyZ => Some(b'z' as i64),
            KeyCode::Digit0 => Some(b'0' as i64),
            KeyCode::Digit1 => Some(b'1' as i64),
            KeyCode::Digit2 => Some(b'2' as i64),
            KeyCode::Digit3 => Some(b'3' as i64),
            KeyCode::Digit4 => Some(b'4' as i64),
            KeyCode::Digit5 => Some(b'5' as i64),
            KeyCode::Digit6 => Some(b'6' as i64),
            KeyCode::Digit7 => Some(b'7' as i64),
            KeyCode::Digit8 => Some(b'8' as i64),
            KeyCode::Digit9 => Some(b'9' as i64),
            _ => None,
        };
    }

    None
}

/// Encode modifier state as a bitmask: bit0=shift, bit1=ctrl, bit2=alt, bit3=super.
fn mod_flags(modifiers: &Modifiers) -> i64 {
    let s = modifiers.state();
    let mut flags: i64 = 0;
    if s.shift_key()   { flags |= 1; }
    if s.control_key() { flags |= 2; }
    if s.alt_key()     { flags |= 4; }
    if s.super_key()   { flags |= 8; }
    flags
}

unsafe impl Send for WinState {}

// ── Global proxy (initialized once, lives for the duration of the process) ────
type Proxy = Arc<Mutex<EventLoopProxy<AppEvent>>>;
static GLOBAL_PROXY: OnceLock<Proxy> = OnceLock::new();

fn close_window(windows: &mut HashMap<WindowId, WinState>, window_id: WindowId) {
    if let Some(st) = windows.remove(&window_id) {
        st.done_tx.send(()).ok();
    }
}

// ── Event loop thread body ─────────────────────────────────────────────────────
fn event_loop_thread(proxy_tx: mpsc::SyncSender<Proxy>) {
    // Allow EventLoop on any thread (non-main-thread).
    // Platform extensions are imported locally via cfg and called via UFCS
    // to avoid trait name conflicts.
    let mut el_builder = EventLoopBuilder::<AppEvent>::with_user_event();

    #[cfg(target_os = "linux")]
    {
        use winit::platform::wayland::EventLoopBuilderExtWayland;
        use winit::platform::x11::EventLoopBuilderExtX11;
        EventLoopBuilderExtWayland::with_any_thread(&mut el_builder, true);
        EventLoopBuilderExtX11::with_any_thread(&mut el_builder, true);
    }
    #[cfg(target_os = "windows")]
    {
        use winit::platform::windows::EventLoopBuilderExtWindows;
        EventLoopBuilderExtWindows::with_any_thread(&mut el_builder, true);
    }
    // macOS: EventLoop requires the main thread — not supported in a background
    // thread; on macOS winit_run must be called from main.

    let event_loop = el_builder.build().expect("Failed to create EventLoop");
    proxy_tx.send(Arc::new(Mutex::new(event_loop.create_proxy()))).unwrap();

    let mut windows: HashMap<WindowId, WinState> = HashMap::new();

    let _ = event_loop.run(move |event, elwt: &EventLoopWindowTarget<AppEvent>| {
        elwt.set_control_flow(if windows.is_empty() {
            ControlFlow::Wait   // no windows → sleep until next UserEvent
        } else {
            ControlFlow::Poll
        });

        match event {
            // ── Screen size request from Python ───────────────────────────────
            Event::UserEvent(AppEvent::GetScreenSize { tx }) => {
                let size = elwt.primary_monitor()
                    .or_else(|| elwt.available_monitors().next())
                    .map(|m| { let s = m.size(); (s.width, s.height) })
                    .unwrap_or((1920, 1080));
                tx.send(size).ok();
            }

            // ── New window request from Python ────────────────────────────────
            Event::UserEvent(AppEvent::AddWindow(req)) => {
                let window = Arc::new(
                    WindowBuilder::new()
                        .with_inner_size(LogicalSize::new(req.width, req.height))
                        .with_title(&req.title)
                        .build(elwt)
                        .expect("Failed to create window"),
                );
                // Use actual physical size — may differ from logical on HiDPI.
                let phys = window.inner_size();
                let pw = phys.width.max(1);
                let ph = phys.height.max(1);
                unsafe {
                    *req.width_ptr  = pw;
                    *req.height_ptr = ph;
                }
                let ctx = Context::new(Arc::clone(&window)).unwrap();
                let mut surface = Surface::new(&ctx, Arc::clone(&window)).unwrap();
                surface.resize(NonZeroU32::new(pw).unwrap(), NonZeroU32::new(ph).unwrap()).unwrap();

                windows.insert(window.id(), WinState {
                    window,
                    surface,
                    pixel_ptr:  req.pixel_ptr,
                    width_ptr:  req.width_ptr,
                    height_ptr: req.height_ptr,
                    render_cb:  req.render_cb,
                    event_cb:   req.event_cb,
                    done_tx:    req.done_tx,
                    cursor_pos: (0.0, 0.0),
                    modifiers:  Modifiers::default(),
                });
            }

            // ── Window events ─────────────────────────────────────────────────
            Event::WindowEvent { window_id, event } => {
                match event {
                    WindowEvent::CloseRequested => {
                        close_window(&mut windows, window_id);
                    }

                    WindowEvent::ModifiersChanged(new_mods) => {
                        if let Some(st) = windows.get_mut(&window_id) {
                            st.modifiers = new_mods;
                        }
                    }

                    WindowEvent::KeyboardInput {
                        event: KeyEvent {
                            logical_key,
                            physical_key,
                            state: ElementState::Pressed,
                            ..
                        },
                        ..
                    } => {
                        if let Some(st) = windows.get(&window_id) {
                            if let Some(code) = key_to_code(&logical_key, &physical_key) {
                                let flags = mod_flags(&st.modifiers);
                                (st.event_cb)(5, code as f64, flags as f64, 0);
                            }
                        }
                    }

                    WindowEvent::RedrawRequested => {
                        let should_close = if let Some(st) = windows.get_mut(&window_id) {
                            let w = unsafe { *st.width_ptr };
                            let h = unsafe { *st.height_ptr };
                            if w > 0 && h > 0 {
                                let signal = (st.render_cb)();
                                if signal == 0 {
                                    if let Ok(mut buf) = st.surface.buffer_mut() {
                                        let n = (w * h) as usize;
                                        // osdbuf: [R,G,B,A] LE (0xAABBGGRR)
                                        // softbuffer: 0x00RRGGBB → swap R↔B
                                        for i in 0..n {
                                            let px = unsafe { *st.pixel_ptr.add(i) };
                                            let r = (px >>  0) & 0xFF;
                                            let g = (px >>  8) & 0xFF;
                                            let b = (px >> 16) & 0xFF;
                                            buf[i] = (r << 16) | (g << 8) | b;
                                        }
                                        buf.present().ok();
                                    }
                                }
                                signal != 0
                            } else {
                                false
                            }
                        } else {
                            false
                        };
                        if should_close {
                            close_window(&mut windows, window_id);
                        }
                    }

                    WindowEvent::Resized(size) => {
                        if let Some(st) = windows.get_mut(&window_id) {
                            let nw = size.width.max(1);
                            let nh = size.height.max(1);
                            unsafe {
                                *st.width_ptr  = nw;
                                *st.height_ptr = nh;
                            }
                            st.surface.resize(
                                NonZeroU32::new(nw).unwrap(),
                                NonZeroU32::new(nh).unwrap(),
                            ).ok();
                            st.window.request_redraw();
                        }
                    }

                    // Mouse (touch_id == -1 signals "mouse pointer" on the Python side)
                    WindowEvent::CursorMoved { position, .. } => {
                        if let Some(st) = windows.get_mut(&window_id) {
                            st.cursor_pos = (position.x, position.y);
                            (st.event_cb)(2, position.x, position.y, -1);
                        }
                    }

                    WindowEvent::MouseInput { state: btn, button, .. } => {
                        let tid: i64 = match button {
                            MouseButton::Left   => -1,
                            MouseButton::Right  => -2,
                            MouseButton::Middle => -3,
                            _ => return,
                        };
                        if let Some(st) = windows.get(&window_id) {
                            let t = if btn == ElementState::Pressed { 0 } else { 1 };
                            (st.event_cb)(t, st.cursor_pos.0, st.cursor_pos.1, tid);
                        }
                    }

                    WindowEvent::CursorLeft { .. } => {
                        if let Some(st) = windows.get(&window_id) {
                            (st.event_cb)(3, 0.0, 0.0, -1);
                        }
                    }

                    // Mouse wheel / trackpad scroll
                    // etype=4: x=dx lines, y=dy lines (LineDelta) or pixels (PixelDelta)
                    // Python side multiplies by _SCROLL_LINE_PX for LineDelta.
                    WindowEvent::MouseWheel { delta, .. } => {
                        if let Some(st) = windows.get(&window_id) {
                            let (dx, dy, is_pixel) = match delta {
                                MouseScrollDelta::LineDelta(x, y) => {
                                    (x as f64, y as f64, 0i64)
                                }
                                MouseScrollDelta::PixelDelta(pos) => (pos.x, pos.y, 1i64),
                            };
                            (st.event_cb)(4, dx, dy, is_pixel);
                        }
                    }

                    // Touch (multitouch touchscreen / touchpad)
                    WindowEvent::Touch(touch) => {
                        if let Some(st) = windows.get(&window_id) {
                            let etype: i32 = match touch.phase {
                                TouchPhase::Started   => 0,
                                TouchPhase::Ended     => 1,
                                TouchPhase::Moved     => 2,
                                TouchPhase::Cancelled => 3,
                            };
                            (st.event_cb)(etype, touch.location.x, touch.location.y, touch.id as i64);
                        }
                    }

                    _ => {}
                }
            }

            // ── Request redraw every frame (for animations) ───────────────────
            Event::AboutToWait => {
                for (_, st) in &windows {
                    st.window.request_redraw();
                }
            }

            _ => {}
        }
    });
}

// ── Spawn the event loop thread and return its proxy ──────────────────────────
fn start_event_loop() -> Proxy {
    let (proxy_tx, proxy_rx) = mpsc::sync_channel::<Proxy>(1);
    std::thread::Builder::new()
        .name("winit-event-loop".into())
        .spawn(move || event_loop_thread(proxy_tx))
        .expect("Failed to spawn winit event loop thread");
    proxy_rx.recv().expect("Event loop thread failed to start")
}

/// Return the global event-loop proxy, starting the loop on first call.
fn proxy() -> Proxy {
    GLOBAL_PROXY.get_or_init(start_event_loop).clone()
}

// ── Public C API ───────────────────────────────────────────────────────────────

/// Create a window and block until it is closed.
/// Can be called from multiple threads simultaneously — each will get its own window.
/// title can be NULL (empty string will be used).
#[no_mangle]
pub extern "C" fn winit_run(
    initial_width:   u32,
    initial_height:  u32,
    pixel_ptr:       *mut u32,
    width_ptr:       *mut u32,
    height_ptr:      *mut u32,
    render_callback: RenderCb,
    event_callback:  EventCb,
    title:           *const c_char,
) {
    let title_str = if title.is_null() {
        String::new()
    } else {
        unsafe { CStr::from_ptr(title).to_string_lossy().into_owned() }
    };

    let (done_tx, done_rx) = mpsc::sync_channel::<()>(1);
    proxy().lock().unwrap().send_event(AppEvent::AddWindow(AddWindowReq {
        width:      initial_width,
        height:     initial_height,
        title:      title_str,
        pixel_ptr,
        width_ptr,
        height_ptr,
        render_cb:  render_callback,
        event_cb:   event_callback,
        done_tx,
    })).ok();

    // Block until the window is closed
    done_rx.recv().ok();
}

/// Return the size of the primary monitor (w, h).
/// Starts EventLoop if not already running.
#[no_mangle]
pub extern "C" fn winit_screen_size(w_out: *mut u32, h_out: *mut u32) {
    let (tx, rx) = mpsc::sync_channel::<(u32, u32)>(1);
    proxy().lock().unwrap().send_event(AppEvent::GetScreenSize { tx }).ok();
    let (w, h) = rx.recv().unwrap_or((1920, 1080));
    unsafe {
        *w_out = w;
        *h_out = h;
    }
}
