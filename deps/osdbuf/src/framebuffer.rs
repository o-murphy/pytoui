use once_cell::sync::Lazy;
use parking_lot::{Mutex, RwLock};
use std::collections::HashMap;
use std::os::raw::{c_int, c_uchar};
use std::slice;
use tiny_skia::{
    BlendMode, Color, FillRule, Mask, PathBuilder, PixmapMut, Rect, Stroke, Transform,
};

use crate::helpers::{
    ellipse_arc_path, hex_to_rgba, make_paint, map_cap, map_join, rounded_rect_path,
};

// --- Structures ---

pub(crate) struct FrameBuffer {
    pub(crate) pixels: &'static mut [u8], // premultiplied RGBA
    /// Non-None when this FB owns its pixel buffer (created via CreateOwnedFB).
    /// Keeps the allocation alive for the lifetime of the FrameBuffer.
    pub(crate) _owned_pixels: Option<Vec<u8>>,
    pub(crate) w: i32,
    pub(crate) h: i32,
    pub antialias: bool,
    pub ctm: Transform,
    pub clip_mask: Option<Mask>,
    pub(crate) gstate_stack: Vec<FrameState>,
}

pub(crate) struct FrameState {
    pub(crate) ctm: Transform,
    pub(crate) clip_data: Option<Vec<u8>>,
}

pub(crate) static FB_MAP: Lazy<RwLock<HashMap<i32, Mutex<FrameBuffer>>>> =
    Lazy::new(|| RwLock::new(HashMap::new()));
pub(crate) static mut NEXT_FB_ID: i32 = 1;

pub(crate) fn with_fb<F, R>(handle: i32, f: F) -> R
where
    F: FnOnce(&mut FrameBuffer) -> R,
    R: Default,
{
    let map = FB_MAP.read();
    if let Some(fb_lock) = map.get(&handle) {
        f(&mut fb_lock.lock())
    } else {
        R::default()
    }
}

// --- FrameBuffer implementation ---

impl FrameBuffer {
    /// Get a PixmapMut wrapping the pixel buffer (premultiplied RGBA).
    pub(crate) fn pixmap_mut(&mut self) -> Option<PixmapMut<'_>> {
        PixmapMut::from_bytes(self.pixels, self.w as u32, self.h as u32)
    }

    /// Write a single pixel (premultiplied) - Source blend.
    pub(crate) fn set_pixel(&mut self, x: i32, y: i32, r: u8, g: u8, b: u8, a: u8) {
        if x >= 0 && x < self.w && y >= 0 && y < self.h {
            let off = ((y * self.w + x) * 4) as usize;
            // Premultiply
            let af = a as u16;
            self.pixels[off] = ((r as u16 * af) / 255) as u8;
            self.pixels[off + 1] = ((g as u16 * af) / 255) as u8;
            self.pixels[off + 2] = ((b as u16 * af) / 255) as u8;
            self.pixels[off + 3] = a;
        }
    }

    /// Alpha-blend a pixel using SrcOver on premultiplied data.
    pub(crate) fn set_pixel_over(&mut self, x: i32, y: i32, r: u8, g: u8, b: u8, a: u8) {
        if a == 0 {
            return;
        }
        if x >= 0 && x < self.w && y >= 0 && y < self.h {
            if let Some(mask) = &self.clip_mask {
                if mask.data()[y as usize * self.w as usize + x as usize] == 0 {
                    return;
                }
            }
            let off = ((y * self.w + x) * 4) as usize;
            // Premultiply source
            let sa = a as f32 / 255.0;
            let sr = r as f32 * sa;
            let sg = g as f32 * sa;
            let sb = b as f32 * sa;
            let inv_sa = 1.0 - sa;

            // SrcOver on premultiplied: dst' = src + dst * (1 - src_a)
            let dr = self.pixels[off] as f32;
            let dg = self.pixels[off + 1] as f32;
            let db = self.pixels[off + 2] as f32;
            let da = self.pixels[off + 3] as f32;

            self.pixels[off] = (sr + dr * inv_sa) as u8;
            self.pixels[off + 1] = (sg + dg * inv_sa) as u8;
            self.pixels[off + 2] = (sb + db * inv_sa) as u8;
            self.pixels[off + 3] = (a as f32 + da * inv_sa) as u8;
        }
    }

    pub(crate) fn get_pixel_raw(&self, x: i32, y: i32) -> u32 {
        if x >= 0 && x < self.w && y >= 0 && y < self.h {
            let i = ((y * self.w + x) * 4) as usize;
            let pr = self.pixels[i] as u32;
            let pg = self.pixels[i + 1] as u32;
            let pb = self.pixels[i + 2] as u32;
            let a = self.pixels[i + 3] as u32;
            // Un-premultiply to return 0xRRGGBBAA
            if a == 0 {
                return 0;
            }
            let r = ((pr * 255) / a).min(255);
            let g = ((pg * 255) / a).min(255);
            let b = ((pb * 255) / a).min(255);
            (r << 24) | (g << 16) | (b << 8) | a
        } else {
            0
        }
    }

    // --- tiny-skia drawing methods ---

    pub(crate) fn fill_solid(&mut self, r: u8, g: u8, b: u8, a: u8) {
        if let Some(mut pm) = self.pixmap_mut() {
            pm.fill(Color::from_rgba8(r, g, b, a));
        }
    }

    pub(crate) fn fill_rect(
        &mut self,
        x: f32,
        y: f32,
        w: f32,
        h: f32,
        r: u8,
        g: u8,
        b: u8,
        a: u8,
        blend: BlendMode,
    ) {
        let aa = self.antialias;
        if let Some(rect) = Rect::from_xywh(x, y, w, h) {
            let ctm = self.ctm;
            if let Some(mut pm) = self.pixmap_mut() {
                let paint = make_paint(r, g, b, a, blend, aa);
                pm.fill_rect(rect, &paint, ctm, None);
            }
        }
    }

    pub(crate) fn fill_rounded_rect(
        &mut self,
        x: f32,
        y: f32,
        w: f32,
        h: f32,
        radius: f32,
        rv: u8,
        g: u8,
        b: u8,
        a: u8,
        blend: BlendMode,
    ) {
        let aa = self.antialias;
        if let Some(path) = rounded_rect_path(x, y, w, h, radius) {
            let ctm = self.ctm;
            if let Some(mut pm) = self.pixmap_mut() {
                let paint = make_paint(rv, g, b, a, blend, aa);
                pm.fill_path(&path, &paint, FillRule::Winding, ctm, None);
            }
        }
    }

    pub(crate) fn draw_line(
        &mut self,
        x0: i32,
        y0: i32,
        x1: i32,
        y1: i32,
        r: u8,
        g: u8,
        b: u8,
        a: u8,
        blend: BlendMode,
    ) {
        let aa = self.antialias;
        let mut pb = PathBuilder::new();
        pb.move_to(x0 as f32 + 0.5, y0 as f32 + 0.5);
        pb.line_to(x1 as f32 + 0.5, y1 as f32 + 0.5);
        if let Some(path) = pb.finish() {
            if let Some(mut pm) = self.pixmap_mut() {
                let paint = make_paint(r, g, b, a, blend, aa);
                let mut stroke = Stroke::default();
                stroke.width = 1.0;
                pm.stroke_path(&path, &paint, &stroke, Transform::identity(), None);
            }
        }
    }

    pub(crate) fn draw_hline(
        &mut self,
        x: i32,
        y: i32,
        w: i32,
        r: u8,
        g: u8,
        b: u8,
        a: u8,
        blend: BlendMode,
    ) {
        if let Some(rect) = Rect::from_xywh(x as f32, y as f32, w as f32, 1.0) {
            if let Some(mut pm) = self.pixmap_mut() {
                let paint = make_paint(r, g, b, a, blend, false);
                pm.fill_rect(rect, &paint, Transform::identity(), None);
            }
        }
    }

    pub(crate) fn draw_vline(
        &mut self,
        x: i32,
        y: i32,
        h: i32,
        r: u8,
        g: u8,
        b: u8,
        a: u8,
        blend: BlendMode,
    ) {
        if let Some(rect) = Rect::from_xywh(x as f32, y as f32, 1.0, h as f32) {
            if let Some(mut pm) = self.pixmap_mut() {
                let paint = make_paint(r, g, b, a, blend, false);
                pm.fill_rect(rect, &paint, Transform::identity(), None);
            }
        }
    }

    pub(crate) fn draw_rounded_rect(
        &mut self,
        x: i32,
        y: i32,
        w: i32,
        h: i32,
        radius: i32,
        rv: u8,
        g: u8,
        b: u8,
        a: u8,
        blend: BlendMode,
    ) {
        let aa = self.antialias;
        if let Some(path) = rounded_rect_path(
            x as f32 + 0.5,
            y as f32 + 0.5,
            w as f32 - 1.0,
            h as f32 - 1.0,
            radius as f32,
        ) {
            if let Some(mut pm) = self.pixmap_mut() {
                let paint = make_paint(rv, g, b, a, blend, aa);
                let mut stroke = Stroke::default();
                stroke.width = 1.0;
                pm.stroke_path(&path, &paint, &stroke, Transform::identity(), None);
            }
        }
    }

    pub(crate) fn draw_circle(
        &mut self,
        cx: i32,
        cy: i32,
        r: i32,
        rv: u8,
        g: u8,
        b: u8,
        a: u8,
        blend: BlendMode,
    ) {
        let aa = self.antialias;
        if let Some(path) = PathBuilder::from_circle(cx as f32 + 0.5, cy as f32 + 0.5, r as f32) {
            if let Some(mut pm) = self.pixmap_mut() {
                let paint = make_paint(rv, g, b, a, blend, aa);
                let mut stroke = Stroke::default();
                stroke.width = 1.0;
                pm.stroke_path(&path, &paint, &stroke, Transform::identity(), None);
            }
        }
    }

    pub(crate) fn fill_circle(
        &mut self,
        cx: f32,
        cy: f32,
        r: f32,
        rv: u8,
        g: u8,
        b: u8,
        a: u8,
        blend: BlendMode,
    ) {
        let aa = self.antialias;
        if let Some(path) = PathBuilder::from_circle(cx, cy, r) {
            let ctm = self.ctm;
            if let Some(mut pm) = self.pixmap_mut() {
                let paint = make_paint(rv, g, b, a, blend, aa);
                pm.fill_path(&path, &paint, FillRule::Winding, ctm, None);
            }
        }
    }

    pub(crate) fn draw_ellipse(
        &mut self,
        cx: i32,
        cy: i32,
        rx: i32,
        ry: i32,
        rv: u8,
        g: u8,
        b: u8,
        a: u8,
        blend: BlendMode,
    ) {
        let aa = self.antialias;
        let rect = Rect::from_xywh(
            (cx - rx) as f32 + 0.5,
            (cy - ry) as f32 + 0.5,
            (rx * 2) as f32,
            (ry * 2) as f32,
        );
        if let Some(rect) = rect {
            if let Some(path) = PathBuilder::from_oval(rect) {
                if let Some(mut pm) = self.pixmap_mut() {
                    let paint = make_paint(rv, g, b, a, blend, aa);
                    let mut stroke = Stroke::default();
                    stroke.width = 1.0;
                    pm.stroke_path(&path, &paint, &stroke, Transform::identity(), None);
                }
            }
        }
    }

    pub(crate) fn fill_ellipse(
        &mut self,
        cx: f32,
        cy: f32,
        rx: f32,
        ry: f32,
        rv: u8,
        g: u8,
        b: u8,
        a: u8,
        blend: BlendMode,
    ) {
        let aa = self.antialias;
        let rect = Rect::from_xywh(cx - rx, cy - ry, rx * 2.0, ry * 2.0);
        if let Some(rect) = rect {
            if let Some(path) = PathBuilder::from_oval(rect) {
                let ctm = self.ctm;
                if let Some(mut pm) = self.pixmap_mut() {
                    let paint = make_paint(rv, g, b, a, blend, aa);
                    pm.fill_path(&path, &paint, FillRule::Winding, ctm, None);
                }
            }
        }
    }

    pub(crate) fn draw_ellipse_arc(
        &mut self,
        cx: i32,
        cy: i32,
        rx: i32,
        ry: i32,
        start_angle: f64,
        end_angle: f64,
        rv: u8,
        g: u8,
        b: u8,
        a: u8,
        blend: BlendMode,
    ) {
        let aa = self.antialias;
        if let Some(path) = ellipse_arc_path(
            cx as f32,
            cy as f32,
            rx as f32,
            ry as f32,
            start_angle,
            end_angle,
        ) {
            if let Some(mut pm) = self.pixmap_mut() {
                let paint = make_paint(rv, g, b, a, blend, aa);
                let mut stroke = Stroke::default();
                stroke.width = 1.0;
                pm.stroke_path(&path, &paint, &stroke, Transform::identity(), None);
            }
        }
    }

    pub(crate) fn blit(
        &mut self,
        src_pixels: &[u8],
        src_w: i32,
        src_h: i32,
        dst_x: i32,
        dst_y: i32,
        blend: bool,
    ) {
        // src_pixels is in straight RGBA from Python. Convert to premultiplied for tiny-skia.
        let len = (src_w * src_h * 4) as usize;
        let mut premul = vec![0u8; len];
        for i in (0..len).step_by(4) {
            let r = src_pixels[i] as u16;
            let g = src_pixels[i + 1] as u16;
            let b = src_pixels[i + 2] as u16;
            let a = src_pixels[i + 3] as u16;
            premul[i] = ((r * a) / 255) as u8;
            premul[i + 1] = ((g * a) / 255) as u8;
            premul[i + 2] = ((b * a) / 255) as u8;
            premul[i + 3] = a as u8;
        }
        if let Some(src_pm) = PixmapMut::from_bytes(&mut premul, src_w as u32, src_h as u32) {
            let clip_mask = self.clip_mask.take();
            if let Some(mut dst_pm) = self.pixmap_mut() {
                let mode = if blend {
                    BlendMode::SourceOver
                } else {
                    BlendMode::Source
                };
                dst_pm.draw_pixmap(
                    dst_x,
                    dst_y,
                    src_pm.as_ref(),
                    &tiny_skia::PixmapPaint {
                        opacity: 1.0,
                        blend_mode: mode,
                        quality: tiny_skia::FilterQuality::Nearest,
                    },
                    Transform::identity(),
                    clip_mask.as_ref(),
                );
            }
            self.clip_mask = clip_mask;
        }
    }

    /// Like `blit`, but scales the source to `(dst_w × dst_h)` in the destination.
    pub(crate) fn blit_scaled(
        &mut self,
        src_pixels: &[u8],
        src_w: i32,
        src_h: i32,
        dst_x: i32,
        dst_y: i32,
        dst_w: i32,
        dst_h: i32,
        blend: bool,
    ) {
        if src_w <= 0 || src_h <= 0 || dst_w <= 0 || dst_h <= 0 {
            return;
        }
        let len = (src_w * src_h * 4) as usize;
        let mut premul = vec![0u8; len];
        for i in (0..len).step_by(4) {
            let r = src_pixels[i] as u16;
            let g = src_pixels[i + 1] as u16;
            let b = src_pixels[i + 2] as u16;
            let a = src_pixels[i + 3] as u16;
            premul[i]     = ((r * a) / 255) as u8;
            premul[i + 1] = ((g * a) / 255) as u8;
            premul[i + 2] = ((b * a) / 255) as u8;
            premul[i + 3] = a as u8;
        }
        if let Some(src_pm) = PixmapMut::from_bytes(&mut premul, src_w as u32, src_h as u32) {
            let clip_mask = self.clip_mask.take();
            if let Some(mut dst_pm) = self.pixmap_mut() {
                let mode = if blend { BlendMode::SourceOver } else { BlendMode::Source };
                let sx = dst_w as f32 / src_w as f32;
                let sy = dst_h as f32 / src_h as f32;
                // Encode position in the transform so tiny-skia doesn't
                // scale the (dst_x, dst_y) offset along with the pixels.
                dst_pm.draw_pixmap(
                    0,
                    0,
                    src_pm.as_ref(),
                    &tiny_skia::PixmapPaint {
                        opacity: 1.0,
                        blend_mode: mode,
                        quality: tiny_skia::FilterQuality::Bilinear,
                    },
                    Transform::from_row(sx, 0.0, 0.0, sy, dst_x as f32, dst_y as f32),
                    clip_mask.as_ref(),
                );
            }
            self.clip_mask = clip_mask;
        }
    }

    pub(crate) fn scroll(&mut self, dx: i32, dy: i32) {
        if dx == 0 && dy == 0 {
            return;
        }
        let w = self.w as usize;
        let h = self.h as usize;
        let row_size = w * 4;

        unsafe {
            let ptr = self.pixels.as_mut_ptr();

            if dy != 0 {
                let abs_dy = dy.unsigned_abs() as usize;
                if abs_dy < h {
                    if dy > 0 {
                        for y in (abs_dy..h).rev() {
                            let src = ptr.add((y - abs_dy) * row_size);
                            let dst = ptr.add(y * row_size);
                            std::ptr::copy(src, dst, row_size);
                        }
                        self.pixels[0..abs_dy * row_size].fill(0);
                    } else {
                        for y in 0..(h - abs_dy) {
                            let src = ptr.add((y + abs_dy) * row_size);
                            let dst = ptr.add(y * row_size);
                            std::ptr::copy(src, dst, row_size);
                        }
                        self.pixels[(h - abs_dy) * row_size..h * row_size].fill(0);
                    }
                } else {
                    self.pixels.fill(0);
                }
            }

            if dx != 0 {
                let abs_dx = dx.unsigned_abs() as usize;
                let shift_bytes = (abs_dx * 4).min(row_size);
                if shift_bytes < row_size {
                    for y in 0..h {
                        let row_ptr = ptr.add(y * row_size);
                        if dx > 0 {
                            std::ptr::copy(
                                row_ptr,
                                row_ptr.add(shift_bytes),
                                row_size - shift_bytes,
                            );
                            std::ptr::write_bytes(row_ptr, 0, shift_bytes);
                        } else {
                            std::ptr::copy(
                                row_ptr.add(shift_bytes),
                                row_ptr,
                                row_size - shift_bytes,
                            );
                            std::ptr::write_bytes(
                                row_ptr.add(row_size - shift_bytes),
                                0,
                                shift_bytes,
                            );
                        }
                    }
                } else {
                    self.pixels.fill(0);
                }
            }
        }
    }

    pub fn apply_yuv422_compensation(&mut self, x: i32, y: i32, w: i32, h: i32) {
        let x1 = (x.max(0)) & !1;
        let x2 = ((x + w).min(self.w)) & !1;
        let y1 = y.max(0);
        let y2 = (y + h).min(self.h);
        let fade: f32 = 0.2;

        for iy in y1..y2 {
            for ix in (x1..x2).step_by(2) {
                let i1 = ((iy * self.w + ix) * 4) as usize;
                let i2 = ((iy * self.w + ix + 1) * 4) as usize;
                let a1 = self.pixels[i1 + 3];
                let a2 = self.pixels[i2 + 3];
                if a1 == 0 && a2 == 0 {
                    continue;
                }
                if a1 > 0 && a2 > 0 {
                    continue;
                }
                let (vi, ti) = if a1 > 0 { (i1, i2) } else { (i2, i1) };
                self.pixels[ti] = self.pixels[vi];
                self.pixels[ti + 1] = self.pixels[vi + 1];
                self.pixels[ti + 2] = self.pixels[vi + 2];
                self.pixels[ti + 3] = (self.pixels[vi + 3] as f32 * fade) as u8;
            }
        }
    }

    pub fn stroke_line(
        &mut self,
        x0: f32,
        y0: f32,
        x1: f32,
        y1: f32,
        width: f32,
        cap: u8,
        join: u8,
        r: u8,
        g: u8,
        b: u8,
        a: u8,
        blend: BlendMode,
    ) {
        let mut pb = PathBuilder::new();
        let aa = self.antialias;

        pb.move_to(x0, y0);
        pb.line_to(x1, y1);

        if let Some(path) = pb.finish() {
            let ctm = self.ctm;
            if let Some(mut pm) = self.pixmap_mut() {
                let paint = make_paint(r, g, b, a, blend, aa);
                let mut stroke = Stroke::default();
                stroke.width = width;
                stroke.line_cap = map_cap(cap);
                stroke.line_join = map_join(join);
                pm.stroke_path(&path, &paint, &stroke, ctm, None);
            }
        }
    }

    pub fn stroke_rect(
        &mut self,
        x: f32,
        y: f32,
        w: f32,
        h: f32,
        width: f32,
        join: u8,
        r: u8,
        g: u8,
        b: u8,
        a: u8,
        blend: BlendMode,
    ) {
        let half = width / 2.0;
        let aa = self.antialias;

        if let Some(rect) = Rect::from_xywh(
            x + half,
            y + half,
            (w - width).max(0.0),
            (h - width).max(0.0),
        ) {
            let path = PathBuilder::from_rect(rect);
            let ctm = self.ctm;

            if let Some(mut pm) = self.pixmap_mut() {
                let paint = make_paint(r, g, b, a, blend, aa);
                let mut stroke = Stroke::default();
                stroke.width = width;
                stroke.line_join = map_join(join);
                pm.stroke_path(&path, &paint, &stroke, ctm, None);
            }
        }
    }

    pub fn stroke_rounded_rect(
        &mut self,
        x: f32,
        y: f32,
        w: f32,
        h: f32,
        radius: f32,
        bw: f32,
        join: u8,
        r: u8,
        g: u8,
        b: u8,
        a: u8,
        blend: BlendMode,
    ) {
        let half_bw = bw / 2.0;
        if let Some(path) = rounded_rect_path(
            x + half_bw,
            y + half_bw,
            (w - bw).max(0.0),
            (h - bw).max(0.0),
            (radius - half_bw).max(0.0),
        ) {
            let aa = self.antialias;
            let ctm = self.ctm;

            if let Some(mut pm) = self.pixmap_mut() {
                let paint = make_paint(r, g, b, a, blend, aa);
                let mut stroke = Stroke::default();
                stroke.width = bw;
                stroke.line_join = map_join(join);
                pm.stroke_path(&path, &paint, &stroke, ctm, None);
            }
        }
    }

    pub fn stroke_ellipse(
        &mut self,
        cx: f32,
        cy: f32,
        rx: f32,
        ry: f32,
        width: f32,
        r: u8,
        g: u8,
        b: u8,
        a: u8,
        blend: BlendMode,
    ) {
        let aa = self.antialias;

        if let Some(rect) = Rect::from_xywh(cx - rx, cy - ry, rx * 2.0, ry * 2.0) {
            if let Some(path) = PathBuilder::from_oval(rect) {
                let ctm = self.ctm;
                if let Some(mut pm) = self.pixmap_mut() {
                    let paint = make_paint(r, g, b, a, blend, aa);
                    let mut stroke = Stroke::default();
                    stroke.width = width;
                    pm.stroke_path(&path, &paint, &stroke, ctm, None);
                }
            }
        }
    }

    // FOR TESTING ONLY
    pub fn draw_checkerboard(&mut self, size: i32) {
        let w = self.w as usize;
        let h = self.h as usize;
        let size = size as usize;

        // Make sure the length is a multiple of 4
        assert_eq!(self.pixels.len(), w * h * 4);

        // reinterpret as u32 slice
        let pixels: &mut [u32] =
            unsafe { std::slice::from_raw_parts_mut(self.pixels.as_mut_ptr() as *mut u32, w * h) };

        let light: u32 = 0xFFCCCCCC; // RGBA little endian
        let dark: u32 = 0xFF999999;

        for y in 0..h {
            for x in 0..w {
                let tile = ((y / size) + (x / size)) & 1;
                pixels[y * w + x] = if tile == 0 { light } else { dark };
            }
        }
    }
}

// --- C-export logic helpers ---

pub(crate) unsafe fn create_framebuffer(data: *mut c_uchar, width: c_int, height: c_int) -> i32 {
    let size = (width * height * 4) as usize;
    let pixels = slice::from_raw_parts_mut(data, size);
    let fb = FrameBuffer {
        pixels,
        _owned_pixels: None,
        w: width,
        h: height,
        antialias: true,
        ctm: Transform::identity(),
        clip_mask: None,
        gstate_stack: Vec::new(),
    };
    let mut map = FB_MAP.write();
    let id = NEXT_FB_ID;
    NEXT_FB_ID += 1;
    map.insert(id, Mutex::new(fb));
    id
}

pub(crate) fn destroy_framebuffer(handle: i32) {
    FB_MAP.write().remove(&handle);
}

pub(crate) fn fill_over(handle: i32, color: u32) {
    let (r, g, b, a) = hex_to_rgba(color);
    if a == 255 {
        with_fb(handle, |fb| fb.fill_solid(r, g, b, a));
        return;
    }
    with_fb(handle, |fb| {
        if let Some(rect) = Rect::from_xywh(0.0, 0.0, fb.w as f32, fb.h as f32) {
            if let Some(mut pm) = fb.pixmap_mut() {
                let paint = make_paint(r, g, b, a, BlendMode::SourceOver, false);
                pm.fill_rect(rect, &paint, Transform::identity(), None);
            }
        }
    });
}

/// Create a framebuffer with its own pixel allocation (not backed by Python).
/// Returns a handle like CreateFrameBuffer. Pixels are zeroed (transparent).
pub(crate) unsafe fn create_owned_framebuffer(width: i32, height: i32) -> i32 {
    let size = (width * height * 4) as usize;
    let mut owned: Vec<u8> = vec![0u8; size];
    let ptr = owned.as_mut_ptr();
    // SAFETY: owned is stored in fb._owned_pixels (same struct), never reallocated.
    let pixels: &'static mut [u8] = std::slice::from_raw_parts_mut(ptr, size);
    let fb = FrameBuffer {
        pixels,
        _owned_pixels: Some(owned),
        w: width,
        h: height,
        antialias: true,
        ctm: Transform::identity(),
        clip_mask: None,
        gstate_stack: Vec::new(),
    };
    let mut map = FB_MAP.write();
    let id = NEXT_FB_ID;
    NEXT_FB_ID += 1;
    map.insert(id, Mutex::new(fb));
    id
}

/// Clear the framebuffer to transparent (all zeros) and reset clip/gstate.
pub(crate) fn clear_framebuffer(handle: i32) {
    with_fb(handle, |fb| {
        fb.pixels.fill(0);
        fb.clip_mask = None;
        fb.gstate_stack.clear();
        fb.ctm = Transform::identity();
    });
}

/// Composite src framebuffer into dst at pixel position (x, y) with given opacity.
/// Respects dst's current clip_mask (take/restore pattern).
/// src pixels must be premultiplied RGBA (as produced by tiny-skia rendering).
pub(crate) fn composite_framebuffer(
    dst_handle: i32,
    src_handle: i32,
    x: i32,
    y: i32,
    alpha: f32,
) {
    // Copy src pixels first to avoid holding two FB locks simultaneously.
    let (mut src_data, src_w, src_h) = {
        let map = FB_MAP.read();
        let Some(lock) = map.get(&src_handle) else {
            return;
        };
        let src = lock.lock();
        (src.pixels.to_vec(), src.w, src.h)
    };

    if src_w <= 0 || src_h <= 0 {
        return;
    }

    with_fb(dst_handle, |dst| {
        // Respect dst's clip_mask (take/restore to avoid clone).
        let clip_mask = dst.clip_mask.take();
        if let Some(src_pm) =
            PixmapMut::from_bytes(&mut src_data, src_w as u32, src_h as u32)
        {
            if let Some(mut dst_pm) = dst.pixmap_mut() {
                dst_pm.draw_pixmap(
                    x,
                    y,
                    src_pm.as_ref(),
                    &tiny_skia::PixmapPaint {
                        opacity: alpha,
                        blend_mode: BlendMode::SourceOver,
                        quality: tiny_skia::FilterQuality::Nearest,
                    },
                    Transform::identity(),
                    clip_mask.as_ref(),
                );
            }
        }
        dst.clip_mask = clip_mask;
    });
}

pub(crate) fn composite_framebuffer_rounded(
    dst_handle: i32,
    src_handle: i32,
    x: i32,
    y: i32,
    alpha: f32,
    radius: f32,
) {
    let (mut src_data, src_w, src_h) = {
        let map = FB_MAP.read();
        let Some(lock) = map.get(&src_handle) else {
            return;
        };
        let src = lock.lock();
        (src.pixels.to_vec(), src.w, src.h)
    };

    if src_w <= 0 || src_h <= 0 {
        return;
    }

    // Apply rounded-rect alpha mask to the src copy (source-space, origin at 0,0).
    if radius > 0.0 {
        if let Some(path) =
            rounded_rect_path(0.0, 0.0, src_w as f32, src_h as f32, radius)
        {
            if let Some(mut mask) = Mask::new(src_w as u32, src_h as u32) {
                mask.fill_path(&path, FillRule::Winding, true, Transform::identity());
                let mask_data = mask.data();
                // Premultiplied RGBA: scale all channels by mask coverage
                for (i, chunk) in src_data.chunks_mut(4).enumerate() {
                    let m = mask_data[i] as u32;
                    if m < 255 {
                        chunk[0] = ((chunk[0] as u32 * m) / 255) as u8;
                        chunk[1] = ((chunk[1] as u32 * m) / 255) as u8;
                        chunk[2] = ((chunk[2] as u32 * m) / 255) as u8;
                        chunk[3] = ((chunk[3] as u32 * m) / 255) as u8;
                    }
                }
            }
        }
    }

    with_fb(dst_handle, |dst| {
        let clip_mask = dst.clip_mask.take();
        if let Some(src_pm) =
            PixmapMut::from_bytes(&mut src_data, src_w as u32, src_h as u32)
        {
            if let Some(mut dst_pm) = dst.pixmap_mut() {
                dst_pm.draw_pixmap(
                    x,
                    y,
                    src_pm.as_ref(),
                    &tiny_skia::PixmapPaint {
                        opacity: alpha,
                        blend_mode: BlendMode::SourceOver,
                        quality: tiny_skia::FilterQuality::Nearest,
                    },
                    Transform::identity(),
                    clip_mask.as_ref(),
                );
            }
        }
        dst.clip_mask = clip_mask;
    });
}

pub(crate) fn gstate_push(handle: i32) {
    with_fb(handle, |fb| {
        let clip_data = fb.clip_mask.as_ref().map(|m| m.data().to_vec());
        fb.gstate_stack.push(FrameState {
            ctm: fb.ctm,
            clip_data,
        });
    });
}

pub(crate) fn gstate_pop(handle: i32) {
    with_fb(handle, |fb| {
        if let Some(state) = fb.gstate_stack.pop() {
            fb.ctm = state.ctm;
            fb.clip_mask = state.clip_data.and_then(|data| {
                let w = fb.w as u32;
                let h = fb.h as u32;
                let mut m = Mask::new(w, h)?;
                m.data_mut().copy_from_slice(&data);
                Some(m)
            });
        }
    });
}
