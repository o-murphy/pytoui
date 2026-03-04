from __future__ import annotations

import ctypes
from typing import TYPE_CHECKING

from pytoui._platform import IS_PYTHONISTA
from pytoui.ui._constants import (
    CONTENT_BOTTOM,
    CONTENT_BOTTOM_LEFT,
    CONTENT_BOTTOM_RIGHT,
    CONTENT_CENTER,
    CONTENT_LEFT,
    CONTENT_REDRAW,
    CONTENT_RIGHT,
    CONTENT_SCALE_ASPECT_FILL,
    CONTENT_SCALE_ASPECT_FIT,
    CONTENT_SCALE_TO_FILL,
    CONTENT_TOP,
    CONTENT_TOP_LEFT,
    CONTENT_TOP_RIGHT,
    RENDERING_MODE_TEMPLATE,
)
from pytoui.ui._internals import _final_
from pytoui.ui._view import View

if TYPE_CHECKING:
    from pytoui.ui._image import Image
    from pytoui.ui._types import _ContentMode

__all__ = ("ImageView",)


@_final_
class _ImageView(View):
    """An ImageView presents a ui.Image.

    The scaling behavior is determined by the inherited
    View.content_mode attribute.
    """

    __slots__ = ("_image", "_content_mode")

    def __init__(self):
        self._image: Image | None = None
        self._content_mode: _ContentMode = CONTENT_SCALE_TO_FILL
        self.touch_enabled = False
        # pytoui_render must always call draw() without applying any CTM transform —
        # ImageView handles all content_mode layout internally inside draw().
        self._internals_.content_mode = CONTENT_REDRAW

    @property
    def content_mode(self) -> _ContentMode:
        """
        The image content mode (CONTENT_SCALE_TO_FILL, CONTENT_SCALE_ASPECT_FIT, etc.).
        """
        return self._content_mode

    @content_mode.setter
    def content_mode(self, value: _ContentMode):
        # Store the image-layout mode in _content_mode (used by draw()).
        # _internals_.content_mode stays CONTENT_REDRAW so pytoui_render never
        # applies its own CTM transform on top of the image.
        self._content_mode = value
        self.set_needs_display()

    @property
    def image(self) -> Image | None:
        """The view's image (a ui.Image object), or None."""
        return self._image

    @image.setter
    def image(self, value: Image | None):
        self._image = value
        self.set_needs_display()

    def load_from_url(self, url: str):
        """Asynchronously load an image from a URL and set self.image."""
        import threading

        def _fetch():
            try:
                from urllib.request import urlopen

                from pytoui.ui._image import Image

                data = urlopen(url).read()
                self.image = Image.from_data(data)
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()

    def draw(self):
        img = self._image
        if img is None or img._data is None:
            return

        from pytoui.ui._draw import _get_draw_ctx

        ctx = _get_draw_ctx()
        fb = ctx.backend
        if fb is None:
            return

        # Image pixel buffer dimensions
        iw = int(img._size.w * img._scale)
        ih = int(img._size.h * img._scale)
        # Image and view logical (point) dimensions
        img_pw, img_ph = img._size.w, img._size.h
        fw, fh = self.frame.w, self.frame.h

        if iw <= 0 or ih <= 0 or fw <= 0 or fh <= 0:
            return

        mode = self._content_mode

        # Calculate draw position and target size based on content_mode.
        # All values (x, y, draw_w, draw_h) are in POINTS.
        if mode == CONTENT_SCALE_TO_FILL:
            x, y = 0.0, 0.0
            draw_w, draw_h = fw, fh
        elif mode == CONTENT_SCALE_ASPECT_FIT:
            sc = min(fw / img_pw, fh / img_ph)
            draw_w, draw_h = img_pw * sc, img_ph * sc
            x, y = (fw - draw_w) / 2, (fh - draw_h) / 2
        elif mode == CONTENT_SCALE_ASPECT_FILL:
            sc = max(fw / img_pw, fh / img_ph)
            draw_w, draw_h = img_pw * sc, img_ph * sc
            x, y = (fw - draw_w) / 2, (fh - draw_h) / 2
        elif mode == CONTENT_CENTER:
            x, y = (fw - img_pw) / 2, (fh - img_ph) / 2
            draw_w, draw_h = img_pw, img_ph
        elif mode == CONTENT_TOP:
            x, y = (fw - img_pw) / 2, 0.0
            draw_w, draw_h = img_pw, img_ph
        elif mode == CONTENT_BOTTOM:
            x, y = (fw - img_pw) / 2, fh - img_ph
            draw_w, draw_h = img_pw, img_ph
        elif mode == CONTENT_LEFT:
            x, y = 0.0, (fh - img_ph) / 2
            draw_w, draw_h = img_pw, img_ph
        elif mode == CONTENT_RIGHT:
            x, y = fw - img_pw, (fh - img_ph) / 2
            draw_w, draw_h = img_pw, img_ph
        elif mode == CONTENT_TOP_LEFT:
            x, y = 0.0, 0.0
            draw_w, draw_h = img_pw, img_ph
        elif mode == CONTENT_TOP_RIGHT:
            x, y = fw - img_pw, 0.0
            draw_w, draw_h = img_pw, img_ph
        elif mode == CONTENT_BOTTOM_LEFT:
            x, y = 0.0, fh - img_ph
            draw_w, draw_h = img_pw, img_ph
        elif mode == CONTENT_BOTTOM_RIGHT:
            x, y = fw - img_pw, fh - img_ph
            draw_w, draw_h = img_pw, img_ph
        else:
            x, y = 0.0, 0.0
            draw_w, draw_h = fw, fh

        # Convert points → physical pixels for blit
        pxscale = getattr(fb, "scale_factor", 1.0)
        ox, oy = ctx.origin
        dst_x = int((ox + x) * pxscale)
        dst_y = int((oy + y) * pxscale)
        dst_w = max(1, int(draw_w * pxscale))
        dst_h = max(1, int(draw_h * pxscale))

        pixel_data = img._data
        if img._rendering_mode == RENDERING_MODE_TEMPLATE:
            tint = self.tint_color or (0.0, 0.0, 0.0, 1.0)
            tr, tg, tb, ta = tint
            raw = bytearray(pixel_data)
            for i in range(0, len(raw), 4):
                img_a = raw[i + 3] / 255.0
                raw[i] = int(tr * 255)
                raw[i + 1] = int(tg * 255)
                raw[i + 2] = int(tb * 255)
                raw[i + 3] = int(img_a * ta * 255)
            pixel_data = bytes(raw)

        buf = (ctypes.c_ubyte * len(pixel_data)).from_buffer_copy(pixel_data)
        if dst_w == iw and dst_h == ih:
            fb.blit(buf, iw, ih, dst_x, dst_y, blend=True)
        else:
            fb.blit_scaled(buf, iw, ih, dst_x, dst_y, dst_w, dst_h, blend=True)


if not IS_PYTHONISTA:
    ImageView = _ImageView

else:
    import ui  # type: ignore[import-not-found]

    ImageView = ui.ImageView  # type: ignore[assignment,misc,no-redef]
