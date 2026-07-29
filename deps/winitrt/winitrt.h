#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>

typedef int32_t (*RenderCb)(void);

typedef void (*EventCb)(int32_t, double, double, int64_t);

typedef void (*ImeCb)(int32_t, const uint8_t*, int64_t, int64_t, int64_t);

/**
 * Create a window and block until it is closed.
 * Can be called from multiple threads simultaneously — each will get its own window.
 * title can be NULL (empty string will be used).
 *
 * scale_factor_ptr is written with the initial display scale factor after the window
 * is created, and updated whenever ScaleFactorChanged fires.
 * All event coordinates reported via event_callback are in logical pixels
 * (physical / scale_factor).  width_ptr / height_ptr report physical pixels
 * (used for the pixel framebuffer).
 */
void winit_run(uint32_t initial_width,
               uint32_t initial_height,
               uint32_t *pixel_ptr,
               uint32_t *width_ptr,
               uint32_t *height_ptr,
               double *scale_factor_ptr,
               RenderCb render_callback,
               EventCb event_callback,
               ImeCb ime_callback,
               uint8_t decorations,
               const char *title);

/**
 * Toggle IME/text-input mode for the window registered with a matching
 * event_cb (see AppEvent::SetImeAllowed). Safe to call from any thread.
 */
void winit_set_ime_allowed(EventCb event_cb, int32_t allowed);

/**
 * Return the size of the primary monitor (w, h).
 * Starts EventLoop if not already running.
 */
void winit_screen_size(uint32_t *w_out, uint32_t *h_out);
