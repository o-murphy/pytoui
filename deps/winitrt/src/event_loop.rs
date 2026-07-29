//! Spawns and owns the single, process-lifetime winit EventLoop thread.
//!
//! winit does not allow creating an EventLoop twice in the same process.
//! Therefore, one global EventLoop lives in a background thread (winit on Linux
//! does not require the main thread). Python threads register windows via UserEvent
//! and block on an mpsc channel until their window is closed.

use std::collections::HashMap;
use std::sync::mpsc;
use std::sync::{Arc, Mutex, OnceLock};

use winit::event_loop::{ControlFlow, EventLoop, EventLoopProxy};

use crate::app::App;
use crate::state::AppEvent;

// ── Global proxy (initialized once, lives for the duration of the process) ────
pub(crate) type Proxy = Arc<Mutex<EventLoopProxy<AppEvent>>>;
static GLOBAL_PROXY: OnceLock<Proxy> = OnceLock::new();

// ── Event loop thread body ─────────────────────────────────────────────────────
fn event_loop_thread(proxy_tx: mpsc::SyncSender<Proxy>) {
    // Allow EventLoop on any thread (non-main-thread).
    // Platform extensions are imported locally via cfg and called via UFCS
    // to avoid trait name conflicts.
    let mut el_builder = EventLoop::<AppEvent>::with_user_event();

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

    event_loop.set_control_flow(ControlFlow::Wait);
    let mut app = App { windows: HashMap::new() };
    let _ = event_loop.run_app(&mut app);
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
pub(crate) fn proxy() -> Proxy {
    GLOBAL_PROXY.get_or_init(start_event_loop).clone()
}
