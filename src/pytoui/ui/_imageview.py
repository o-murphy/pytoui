from __future__ import annotations

import ctypes
from typing import TYPE_CHECKING

from pytoui._platform import _UI_FORCE_PYTOUI_VIEWS, IS_PYTHONISTA
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
from pytoui.ui._final import _final_
from pytoui.ui._view import View

if TYPE_CHECKING:
    from pytoui.ui._image import Image

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
        self._content_mode = CONTENT_SCALE_TO_FILL
        self.touch_enabled = False
        # Tell pytoui_render to always call draw() directly without applying
        # any CTM transform — ImageView handles all content_mode logic internally.
        self.content_mode = CONTENT_REDRAW

    @property
    def content_mode(self) -> int:
        """
        The image content mode (CONTENT_SCALE_TO_FILL, CONTENT_SCALE_ASPECT_FIT, etc.).
        """
        return self._content_mode

    @content_mode.setter
    def content_mode(self, value: int):
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

        iw = int(img._size.w * img._scale)
        ih = int(img._size.h * img._scale)
        fw, fh = self.frame.w, self.frame.h

        if iw <= 0 or ih <= 0 or fw <= 0 or fh <= 0:
            return

        mode = self._content_mode

        # Calculate draw position and target size based on content_mode.
        # draw_w / draw_h are the pixel dimensions to render; x / y are offsets
        # within the view's coordinate space (may be fractional / negative).
        if mode == CONTENT_SCALE_TO_FILL:
            x, y = 0.0, 0.0
            draw_w, draw_h = fw, fh
        elif mode == CONTENT_SCALE_ASPECT_FIT:
            scale = min(fw / iw, fh / ih)
            draw_w, draw_h = iw * scale, ih * scale
            x, y = (fw - draw_w) / 2, (fh - draw_h) / 2
        elif mode == CONTENT_SCALE_ASPECT_FILL:
            scale = max(fw / iw, fh / ih)
            draw_w, draw_h = iw * scale, ih * scale
            x, y = (fw - draw_w) / 2, (fh - draw_h) / 2
        elif mode == CONTENT_CENTER:
            x, y = (fw - iw) / 2, (fh - ih) / 2
            draw_w, draw_h = iw, ih
        elif mode == CONTENT_TOP:
            x, y = (fw - iw) / 2, 0.0
            draw_w, draw_h = iw, ih
        elif mode == CONTENT_BOTTOM:
            x, y = (fw - iw) / 2, fh - ih
            draw_w, draw_h = iw, ih
        elif mode == CONTENT_LEFT:
            x, y = 0.0, (fh - ih) / 2
            draw_w, draw_h = iw, ih
        elif mode == CONTENT_RIGHT:
            x, y = fw - iw, (fh - ih) / 2
            draw_w, draw_h = iw, ih
        elif mode == CONTENT_TOP_LEFT:
            x, y = 0.0, 0.0
            draw_w, draw_h = iw, ih
        elif mode == CONTENT_TOP_RIGHT:
            x, y = fw - iw, 0.0
            draw_w, draw_h = iw, ih
        elif mode == CONTENT_BOTTOM_LEFT:
            x, y = 0.0, fh - ih
            draw_w, draw_h = iw, ih
        elif mode == CONTENT_BOTTOM_RIGHT:
            x, y = fw - iw, fh - ih
            draw_w, draw_h = iw, ih
        else:
            x, y = 0.0, 0.0
            draw_w, draw_h = fw, fh

        ox, oy = ctx.origin
        dst_x = int(ox + x)
        dst_y = int(oy + y)
        dst_w = max(1, int(draw_w))
        dst_h = max(1, int(draw_h))

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


if not IS_PYTHONISTA or _UI_FORCE_PYTOUI_VIEWS:
    ImageView = _ImageView

else:
    import ui  # type: ignore[import-not-found]

    ImageView = ui.ImageView  # type: ignore[assignment,misc,no-redef]
