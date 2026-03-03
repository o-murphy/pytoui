from __future__ import annotations

from pytoui._platform import IS_PYTHONISTA
from pytoui.ui._constants import RENDERING_MODE_AUTOMATIC
from pytoui.ui._types import Size

__all__ = ("Image",)


class _Image:
    """Lightweight image wrapper holding raw RGBA pixel data."""

    __slots__ = (
        "_data",  # bytes — raw RGBA pixels, or None
        "_name",
        "_rendering_mode",
        "_scale",
        "_size",
    )

    def __init__(
        self,
        *,
        width: float = 0,
        height: float = 0,
        scale: float = 1.0,
        data: bytes | None = None,
        name: str | None = None,
    ):
        self._name: str | None = name
        self._scale: float = scale
        self._size: Size = Size(float(width), float(height))
        self._data: bytes | None = data
        self._rendering_mode: int = RENDERING_MODE_AUTOMATIC

    # -- Class constructors ---------------------------------------------------

    @classmethod
    def from_data(cls, image_data: bytes, scale: float = 1.0) -> _Image:
        """Create an image from binary data (png, jpeg, etc.)."""
        try:
            import io

            from PIL import Image as _PILImage

            pil = _PILImage.open(io.BytesIO(image_data)).convert("RGBA")
            w, h = pil.size
            return cls(
                width=w / scale,
                height=h / scale,
                scale=scale,
                data=pil.tobytes(),
            )
        except ImportError:
            return cls()

    @classmethod
    def from_image_context(cls) -> Image:
        """Capture the current ImageContext buffer as an Image."""
        from pytoui.ui._draw import _get_draw_ctx

        ctx = _get_draw_ctx()
        ic = getattr(ctx, "_image_context", None)
        if ic is not None:
            return ic.get_image()
        return cls()

    @classmethod
    def named(cls, image_name: str, scale: float = 1.0) -> Image:
        """Create an Image from a built-in image name or local file path."""
        try:
            from PIL import Image as _PILImage

            pil = _PILImage.open(image_name).convert("RGBA")
            w, h = pil.size
            return cls(
                width=w / scale,
                height=h / scale,
                scale=scale,
                data=pil.tobytes(),
                name=image_name,
            )
        except Exception:
            return cls(name=image_name)

    # -- Properties -----------------------------------------------------------

    @property
    def name(self) -> str | None:
        return self._name

    @property
    def scale(self) -> float:
        """(readonly) The scale factor of the image."""
        return self._scale

    @property
    def size(self) -> Size:
        """(readonly) The image's size in points (pixels / scale)."""
        return self._size

    # -- Drawing --------------------------------------------------------------

    def draw(self, *args):
        """Draw the image into the current drawing context.

        Signatures:
            draw()                 — draw at (0, 0) with natural size
            draw(x, y)             — draw at (x, y) with natural size
            draw(x, y, width, height) — draw at (x, y) scaled to (width, height)
            draw(rect)             — draw in rect (Rect / 4-tuple), scaled to fit
        """
        if self._data is None:
            return

        import ctypes

        from pytoui.ui._draw import _get_draw_ctx

        ctx = _get_draw_ctx()
        fb = ctx.backend
        if fb is None:
            return

        pw = int(self._size.w * self._scale)
        ph = int(self._size.h * self._scale)

        # Parse arguments
        if len(args) == 0:
            x, y, dw, dh = 0.0, 0.0, float(pw), float(ph)
        elif len(args) == 2:
            x, y = float(args[0]), float(args[1])
            dw, dh = float(pw), float(ph)
        elif len(args) == 4:
            x, y, dw, dh = (
                float(args[0]),
                float(args[1]),
                float(args[2]),
                float(args[3]),
            )
        elif len(args) == 1:
            r = args[0]
            x, y, dw, dh = float(r[0]), float(r[1]), float(r[2]), float(r[3])
        else:
            x, y, dw, dh = 0.0, 0.0, float(pw), float(ph)

        ox, oy = ctx.origin
        dst_x = int(ox + x)
        dst_y = int(oy + y)
        dst_w = int(dw)
        dst_h = int(dh)

        buf = (ctypes.c_ubyte * len(self._data)).from_buffer_copy(self._data)
        if dst_w == pw and dst_h == ph:
            fb.blit(buf, pw, ph, dst_x, dst_y, blend=True)
        else:
            fb.blit_scaled(buf, pw, ph, dst_x, dst_y, dst_w, dst_h, blend=True)

    def clip_to_mask(self, x, y, width, height):
        """Use the image as a mask for following drawing operations."""

    def draw_as_pattern(self, x: float, y: float, width: float, height: float):
        """Fill a rectangle with the image as a repeating pattern."""

    def resizable_image(self, top: float, left: float, bottom: float, right: float):
        """Create a 9-patch image with the given edges."""

    def show(self):
        """Show the image in the console (stub)."""
        print(f"<Image {self._size.w}x{self._size.h} scale={self._scale}>")

    def to_jpeg(self, quality: int = 75) -> bytes:
        """Return the image as JPEG bytes."""
        if self._data is None:
            return b""
        try:
            import io

            from PIL import Image as _PILImage

            pw = int(self._size.w * self._scale)
            ph = int(self._size.h * self._scale)
            pil = _PILImage.frombytes("RGBA", (pw, ph), self._data).convert("RGB")
            buf = io.BytesIO()
            pil.save(buf, format="JPEG", quality=quality)
            return buf.getvalue()
        except ImportError:
            return b""

    def to_png(self) -> bytes:
        """Return the image as PNG bytes."""
        if self._data is None:
            return b""
        try:
            from PIL import Image as _PILImage

            pw = int(self._size.w * self._scale)
            ph = int(self._size.h * self._scale)
            pil = _PILImage.frombytes("RGBA", (pw, ph), self._data)
            import io

            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            return buf.getvalue()
        except ImportError:
            return b""

    @property
    def rendering_mode(self) -> int:
        """The image's rendering mode (RENDERING_MODE_*)."""
        return self._rendering_mode

    def with_rendering_mode(self, mode: int) -> _Image:
        """Return a copy of this image with the specified rendering mode."""
        img = _Image(
            width=self._size.w,
            height=self._size.h,
            scale=self._scale,
            data=self._data,
            name=self._name,
        )
        img._rendering_mode = mode
        return img


if not IS_PYTHONISTA:
    Image = _Image

else:
    import ui  # type: ignore[import-not-found]

    Image = ui.Image  # type: ignore[assignment,misc]
