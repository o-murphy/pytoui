//! Shared data types: FFI callback signatures, the per-window UserEvent request,
//! and the per-window state that lives on the EventLoop thread.

use std::collections::HashMap;
use std::sync::mpsc;

use softbuffer::Surface;
use winit::event::Modifiers;
use winit::window::{Window, WindowId};
use std::sync::Arc;

// ── Callback types ─────────────────────────────────────────────────────────────
// render_callback returns 0 = continue, != 0 = close window (view.close())
pub(crate) type RenderCb = extern "C" fn() -> i32;
pub(crate) type EventCb = extern "C" fn(i32, f64, f64, i64);
// IME/text-input callback — kept separate from EventCb so its richer (string)
// payload never touches the existing numeric touch/mouse/scroll/key call sites.
// kind: 0=Enabled, 1=Preedit, 2=Commit, 3=Disabled.
// text_ptr/text_len: valid only for Preedit/Commit — raw UTF-8 bytes, NOT
// NUL-terminated (the call is fully synchronous, so the Python callback must
// copy the bytes before returning).
// cursor_start/cursor_end: BYTE offsets within the preedit text; -1,-1 if none.
pub(crate) type ImeCb = extern "C" fn(i32, *const u8, i64, i64, i64);

// ── UserEvent: request to add a new window ────────────────────────────────────
pub(crate) struct AddWindowReq {
    pub(crate) width: u32,
    pub(crate) height: u32,
    pub(crate) title: String,
    pub(crate) pixel_ptr: *mut u32,
    pub(crate) width_ptr: *mut u32,
    pub(crate) height_ptr: *mut u32,
    pub(crate) scale_factor_ptr: *mut f64,
    pub(crate) render_cb: RenderCb,
    pub(crate) event_cb: EventCb,
    pub(crate) ime_cb: ImeCb,
    pub(crate) decorations: bool,
    /// Python thread blocks on done_rx; we send () when the window closes
    pub(crate) done_tx: mpsc::SyncSender<()>,
}

// Raw pointers are managed by the Python/ctypes side — this is safe
unsafe impl Send for AddWindowReq {}

pub(crate) enum AppEvent {
    AddWindow(AddWindowReq),
    GetScreenSize { tx: mpsc::SyncSender<(u32, u32)> },
    /// Toggle IME/text-input mode for whichever window was registered with a
    /// matching event_cb (each window has a distinct Python callback object,
    /// so pointer identity is enough to find it — no window-id plumbing needed).
    SetImeAllowed(EventCb, bool),
}

// ── Single window state (lives on the EventLoop thread) ───────────────────────
pub(crate) struct WinState {
    pub(crate) window: Arc<Window>,
    pub(crate) surface: Surface<Arc<Window>, Arc<Window>>,
    pub(crate) pixel_ptr: *mut u32,
    pub(crate) width_ptr: *mut u32,
    pub(crate) height_ptr: *mut u32,
    pub(crate) scale_factor_ptr: *mut f64,
    pub(crate) scale_factor: f64,
    pub(crate) render_cb: RenderCb,
    pub(crate) event_cb: EventCb,
    pub(crate) ime_cb: ImeCb,
    pub(crate) done_tx: mpsc::SyncSender<()>,
    pub(crate) cursor_pos: (f64, f64), // logical coords (physical / scale_factor)
    pub(crate) modifiers: Modifiers,   // current modifier state
    // True while a real IME composition is in progress (non-empty Preedit).
    // Some Wayland compositors (e.g. KWin) fire Enabled -> Preedit("") ->
    // Disabled immediately for plain physical-keyboard typing without ever
    // producing a Commit — so KeyEvent.text (winit's own xkbcommon-based
    // key->text translation, independent of the compositor's IME protocol)
    // is used as the authoritative commit source whenever we are NOT in the
    // middle of genuine composition, to avoid relying on a text-input-v3
    // implementation that may never actually commit anything.
    pub(crate) ime_composing: bool,
}

unsafe impl Send for WinState {}

pub(crate) fn close_window(windows: &mut HashMap<WindowId, WinState>, window_id: WindowId) {
    if let Some(st) = windows.remove(&window_id) {
        st.done_tx.send(()).ok();
    }
}
