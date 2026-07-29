//! winit + softbuffer runtime for ui.
//!
//! Multi-window support:
//!   winit does not allow creating an EventLoop twice in the same process.
//!   Therefore, one global EventLoop lives in a background thread (winit on Linux
//!   does not require the main thread). Python threads register windows via UserEvent
//!   and block on an mpsc channel until their window is closed.

mod app;
mod event_loop;
mod keyboard;
mod state;

use std::ffi::CStr;
use std::os::raw::c_char;
use std::sync::mpsc;

use event_loop::proxy;
use state::{AddWindowReq, AppEvent, EventCb, ImeCb, RenderCb};

// ── Public C API ───────────────────────────────────────────────────────────────

/// Create a window and block until it is closed.
/// Can be called from multiple threads simultaneously — each will get its own window.
/// title can be NULL (empty string will be used).
///
/// scale_factor_ptr is written with the initial display scale factor after the window
/// is created, and updated whenever ScaleFactorChanged fires.
/// All event coordinates reported via event_callback are in logical pixels
/// (physical / scale_factor).  width_ptr / height_ptr report physical pixels
/// (used for the pixel framebuffer).
///
/// # Safety
/// `pixel_ptr`, `width_ptr`, `height_ptr`, `scale_factor_ptr` must be valid,
/// writable for the lifetime of the window (managed by the Python/ctypes
/// caller). `title` must be either null or a valid NUL-terminated C string.
#[no_mangle]
pub unsafe extern "C" fn winit_run(
    initial_width: u32,
    initial_height: u32,
    pixel_ptr: *mut u32,
    width_ptr: *mut u32,
    height_ptr: *mut u32,
    scale_factor_ptr: *mut f64,
    render_callback: RenderCb,
    event_callback: EventCb,
    ime_callback: ImeCb,
    decorations: u8,
    title: *const c_char,
) {
    let title_str = if title.is_null() {
        String::new()
    } else {
        CStr::from_ptr(title).to_string_lossy().into_owned()
    };

    let (done_tx, done_rx) = mpsc::sync_channel::<()>(1);
    proxy()
        .lock()
        .unwrap()
        .send_event(AppEvent::AddWindow(AddWindowReq {
            width: initial_width,
            height: initial_height,
            title: title_str,
            pixel_ptr,
            width_ptr,
            height_ptr,
            scale_factor_ptr,
            render_cb: render_callback,
            event_cb: event_callback,
            ime_cb: ime_callback,
            decorations: decorations != 0,
            done_tx,
        }))
        .ok();

    // Block until the window is closed
    done_rx.recv().ok();
}

/// Toggle IME/text-input mode for the window registered with a matching
/// event_cb (see AppEvent::SetImeAllowed). Safe to call from any thread.
#[no_mangle]
pub extern "C" fn winit_set_ime_allowed(event_cb: EventCb, allowed: i32) {
    proxy()
        .lock()
        .unwrap()
        .send_event(AppEvent::SetImeAllowed(event_cb, allowed != 0))
        .ok();
}

/// Return the size of the primary monitor (w, h).
/// Starts EventLoop if not already running.
///
/// # Safety
/// `w_out` and `h_out` must be valid, writable `u32` pointers.
#[no_mangle]
pub unsafe extern "C" fn winit_screen_size(w_out: *mut u32, h_out: *mut u32) {
    let (tx, rx) = mpsc::sync_channel::<(u32, u32)>(1);
    proxy().lock().unwrap().send_event(AppEvent::GetScreenSize { tx }).ok();
    let (w, h) = rx.recv().unwrap_or((1920, 1080));
    *w_out = w;
    *h_out = h;
}
