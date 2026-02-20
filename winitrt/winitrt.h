#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>

typedef int32_t (*RenderCb)(void);

typedef void (*EventCb)(int32_t, double, double);

/**
 * Create a window and block until it is closed.
 * Can be called from multiple threads simultaneously — each will get its own window.
 * title can be NULL (empty string will be used).
 */
void winit_run(uint32_t initial_width,
               uint32_t initial_height,
               uint32_t *pixel_ptr,
               uint32_t *width_ptr,
               uint32_t *height_ptr,
               RenderCb render_callback,
               EventCb event_callback,
               const char *title);

/**
 * Return the size of the primary monitor (w, h).
 * Starts EventLoop if not already running.
 */
void winit_screen_size(uint32_t *w_out, uint32_t *h_out);
