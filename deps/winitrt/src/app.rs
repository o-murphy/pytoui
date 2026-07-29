//! The `ApplicationHandler` that drives the shared winit EventLoop: owns all
//! open windows and dispatches OS events to their Python-side callbacks.

use std::collections::HashMap;
use std::num::NonZeroU32;
use std::sync::Arc;

use softbuffer::{Context, Surface};
use winit::application::ApplicationHandler;
use winit::dpi::LogicalSize;
use winit::event::*;
use winit::event_loop::{ActiveEventLoop, ControlFlow};
use winit::window::{Window, WindowId};

use crate::keyboard::{key_to_code, mod_flags};
use crate::state::{close_window, AppEvent, WinState};

// ── Application handler (winit 0.30 ApplicationHandler-based event loop) ──────
pub(crate) struct App {
    pub(crate) windows: HashMap<WindowId, WinState>,
}

impl App {
    fn sync_control_flow(&self, event_loop: &ActiveEventLoop) {
        event_loop.set_control_flow(if self.windows.is_empty() {
            ControlFlow::Wait // no windows → sleep until next UserEvent
        } else {
            ControlFlow::Poll
        });
    }
}

impl ApplicationHandler<AppEvent> for App {
    fn resumed(&mut self, _event_loop: &ActiveEventLoop) {}

    fn user_event(&mut self, event_loop: &ActiveEventLoop, event: AppEvent) {
        match event {
            // ── Screen size request from Python ───────────────────────────────
            AppEvent::GetScreenSize { tx } => {
                let size = event_loop
                    .primary_monitor()
                    .or_else(|| event_loop.available_monitors().next())
                    .map(|m| {
                        let s = m.size();
                        (s.width, s.height)
                    })
                    .unwrap_or((1920, 1080));
                tx.send(size).ok();
            }

            // ── Toggle IME/text-input mode (focus-driven, from Python) ────────
            AppEvent::SetImeAllowed(cb, allowed) => {
                for (_, st) in self.windows.iter() {
                    if st.event_cb as usize == cb as usize {
                        st.window.set_ime_allowed(allowed);
                    }
                }
            }

            // ── New window request from Python ────────────────────────────────
            AppEvent::AddWindow(req) => {
                let attrs = Window::default_attributes()
                    .with_inner_size(LogicalSize::new(req.width, req.height))
                    .with_min_inner_size(LogicalSize::new(120u32, 36u32))
                    .with_decorations(req.decorations)
                    .with_title(&req.title);
                let window = Arc::new(
                    event_loop.create_window(attrs).expect("Failed to create window"),
                );
                let scale = window.scale_factor();
                // Physical size for framebuffer
                let phys = window.inner_size();
                let pw = phys.width.max(1);
                let ph = phys.height.max(1);
                unsafe {
                    *req.width_ptr = pw;
                    *req.height_ptr = ph;
                    *req.scale_factor_ptr = scale;
                }
                let ctx = Context::new(Arc::clone(&window)).unwrap();
                let mut surface = Surface::new(&ctx, Arc::clone(&window)).unwrap();
                surface
                    .resize(NonZeroU32::new(pw).unwrap(), NonZeroU32::new(ph).unwrap())
                    .unwrap();

                self.windows.insert(
                    window.id(),
                    WinState {
                        window,
                        surface,
                        pixel_ptr: req.pixel_ptr,
                        width_ptr: req.width_ptr,
                        height_ptr: req.height_ptr,
                        scale_factor_ptr: req.scale_factor_ptr,
                        scale_factor: scale,
                        render_cb: req.render_cb,
                        event_cb: req.event_cb,
                        ime_cb: req.ime_cb,
                        done_tx: req.done_tx,
                        cursor_pos: (0.0, 0.0),
                        modifiers: Modifiers::default(),
                        ime_composing: false,
                    },
                );
                self.sync_control_flow(event_loop);
            }
        }
    }

    fn window_event(
        &mut self,
        event_loop: &ActiveEventLoop,
        window_id: WindowId,
        event: WindowEvent,
    ) {
        let windows = &mut self.windows;
        match event {
            WindowEvent::CloseRequested => {
                close_window(windows, window_id);
                self.sync_control_flow(event_loop);
            }

            WindowEvent::ModifiersChanged(new_mods) => {
                if let Some(st) = windows.get_mut(&window_id) {
                    st.modifiers = new_mods;
                }
            }

            WindowEvent::KeyboardInput {
                event:
                    KeyEvent {
                        logical_key,
                        physical_key,
                        text,
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
                    // Fallback commit path: winit derives `text` from the
                    // platform's own key->text translation (xkbcommon on
                    // Wayland/X11), independent of the compositor's
                    // text-input-v3 IME protocol. Only used while NOT in
                    // the middle of a genuine IME composition, so a
                    // working IME (CJK) still goes through Ime::Commit
                    // without duplicate insertion.
                    //
                    // xkbcommon's keysym->UTF-8 table maps legacy control keys
                    // (BackSpace, Tab, Return, Escape, Delete) to their ASCII
                    // control-code equivalents instead of None — those are
                    // already handled above via key_to_code(), so any control
                    // character here must be filtered out or it gets inserted
                    // into the text buffer as an invisible junk character
                    // (breaking repeated Backspace: each press both deletes a
                    // real char via the key-code path AND re-inserts one via
                    // this fallback, so only the first press has visible effect).
                    if !st.ime_composing {
                        if let Some(t) = &text {
                            if !t.is_empty() && !t.chars().any(|c| c.is_control()) {
                                (st.ime_cb)(2, t.as_ptr(), t.len() as i64, -1, -1);
                            }
                        }
                    }
                }
            }

            WindowEvent::Ime(ime) => {
                if let Some(st) = windows.get_mut(&window_id) {
                    match ime {
                        Ime::Enabled => {
                            (st.ime_cb)(0, std::ptr::null(), 0, -1, -1);
                        }
                        Ime::Preedit(text, cursor) => {
                            st.ime_composing = !text.is_empty();
                            let (s, e) = cursor
                                .map(|(a, b)| (a as i64, b as i64))
                                .unwrap_or((-1, -1));
                            (st.ime_cb)(1, text.as_ptr(), text.len() as i64, s, e);
                        }
                        Ime::Commit(text) => {
                            st.ime_composing = false;
                            (st.ime_cb)(2, text.as_ptr(), text.len() as i64, -1, -1);
                        }
                        Ime::Disabled => {
                            st.ime_composing = false;
                            (st.ime_cb)(3, std::ptr::null(), 0, -1, -1);
                        }
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
                                    let r = (px >> 0) & 0xFF;
                                    let g = (px >> 8) & 0xFF;
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
                    close_window(windows, window_id);
                    self.sync_control_flow(event_loop);
                }
            }

            WindowEvent::Resized(size) => {
                if let Some(st) = windows.get_mut(&window_id) {
                    let nw = size.width.max(1);
                    let nh = size.height.max(1);
                    unsafe {
                        *st.width_ptr = nw;
                        *st.height_ptr = nh;
                    }
                    st.surface
                        .resize(NonZeroU32::new(nw).unwrap(), NonZeroU32::new(nh).unwrap())
                        .ok();
                    st.window.request_redraw();
                }
            }

            WindowEvent::ScaleFactorChanged { scale_factor, .. } => {
                if let Some(st) = windows.get_mut(&window_id) {
                    st.scale_factor = scale_factor;
                    unsafe {
                        *st.scale_factor_ptr = scale_factor;
                    }
                    // Resized event follows with new physical size
                }
            }

            // Mouse — divide physical positions by scale_factor → logical coords
            WindowEvent::CursorMoved { position, .. } => {
                if let Some(st) = windows.get_mut(&window_id) {
                    let lx = position.x / st.scale_factor;
                    let ly = position.y / st.scale_factor;
                    st.cursor_pos = (lx, ly);
                    (st.event_cb)(2, lx, ly, -1);
                }
            }

            WindowEvent::MouseInput { state: btn, button, .. } => {
                let tid: i64 = match button {
                    MouseButton::Left => -1,
                    MouseButton::Right => -2,
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
                        MouseScrollDelta::LineDelta(x, y) => (x as f64, y as f64, 0i64),
                        // PixelDelta is physical — convert to logical
                        MouseScrollDelta::PixelDelta(pos) => {
                            (pos.x / st.scale_factor, pos.y / st.scale_factor, 1i64)
                        }
                    };
                    (st.event_cb)(4, dx, dy, is_pixel);
                }
            }

            // Touch (multitouch touchscreen / touchpad)
            WindowEvent::Touch(touch) => {
                if let Some(st) = windows.get(&window_id) {
                    let etype: i32 = match touch.phase {
                        TouchPhase::Started => 0,
                        TouchPhase::Ended => 1,
                        TouchPhase::Moved => 2,
                        TouchPhase::Cancelled => 3,
                    };
                    let lx = touch.location.x / st.scale_factor;
                    let ly = touch.location.y / st.scale_factor;
                    (st.event_cb)(etype, lx, ly, touch.id as i64);
                }
            }

            _ => {}
        }
    }

    // ── Request redraw every frame (for animations) ───────────────────────────
    fn about_to_wait(&mut self, _event_loop: &ActiveEventLoop) {
        for (_, st) in &self.windows {
            st.window.request_redraw();
        }
    }
}
