use fontdue::{Font, FontSettings};
use once_cell::sync::Lazy;
use parking_lot::{Mutex, RwLock};
use std::collections::HashMap;
use std::ffi::CStr;
use std::os::raw::{c_char, c_int, c_uchar};
use std::slice;
use std::sync::Arc;

use tiny_skia::{
    BlendMode, Color, FillRule, Mask, Paint, Path, PathBuilder, PixmapMut, Rect,
    Stroke, StrokeDash, Transform,
};

mod helpers;
use helpers::{hex_to_rgba, map_blend_mode, map_cap, map_join, parse_c_str};

// --- Structures ---

pub struct FrameBuffer {
    pixels: &'static mut [u8], // premultiplied RGBA
    w: i32,
    h: i32,
    pub cx: i32,
    pub cy: i32,
    pub antialias: bool,
    pub ctm: Transform,
    pub clip_mask: Option<Mask>,
    gstate_stack: Vec<FrameState>,
}

static FB_MAP: Lazy<RwLock<HashMap<i32, Mutex<FrameBuffer>>>> =
    Lazy::new(|| RwLock::new(HashMap::new()));
static mut NEXT_FB_ID: i32 = 1;

static FONT_MAP: Lazy<RwLock<HashMap<i32, Arc<Font>>>> = Lazy::new(|| RwLock::new(HashMap::new()));
static mut NEXT_FONT_ID: i32 = 1;

// --- Font management ---

#[no_mangle]
pub unsafe extern "C" fn RegisterFont(data: *const c_uchar, len: c_int) -> i32 {
    let font_data = slice::from_raw_parts(data, len as usize);
    if let Ok(font) = Font::from_bytes(font_data, FontSettings::default()) {
        let mut map = FONT_MAP.write();
        let id = NEXT_FONT_ID;
        NEXT_FONT_ID += 1;
        map.insert(id, Arc::new(font));
        return id;
    }
    -1
}

#[no_mangle]
pub unsafe extern "C" fn LoadFont(path: *const c_char) -> i32 {
    if let Ok(p) = CStr::from_ptr(path).to_str() {
        if let Ok(data) = std::fs::read(p) {
            return RegisterFont(data.as_ptr(), data.len() as i32);
        }
    }
    -1
}

#[no_mangle]
pub extern "C" fn UnloadFont(handle: i32) -> i32 {
    let mut map = FONT_MAP.write();
    if map.remove(&handle).is_some() {
        0
    } else {
        -1
    }
}

#[no_mangle]
pub extern "C" fn GetDefaultFont() -> i32 {
    let map = FONT_MAP.read();
    if map.contains_key(&1) {
        1
    } else {
        -1
    }
}

#[no_mangle]
pub extern "C" fn GetFontCount() -> i32 {
    FONT_MAP.read().len() as i32
}

#[no_mangle]
pub unsafe extern "C" fn GetFontIDs(buf: *mut c_int, max_count: c_int) -> i32 {
    if buf.is_null() || max_count <= 0 {
        return 0;
    }
    let map = FONT_MAP.read();
    let mut keys: Vec<i32> = map.keys().cloned().collect();
    keys.sort_unstable();
    let count = (keys.len() as i32).min(max_count);
    let out = slice::from_raw_parts_mut(buf, count as usize);
    for i in 0..count as usize {
        out[i] = keys[i];
    }
    count
}

// --- Helpers ---

/// Create a tiny-skia Paint with the given color and blend mode.
#[inline]
fn make_paint(r: u8, g: u8, b: u8, a: u8, blend: BlendMode, aa: bool) -> Paint<'static> {
    let mut paint = Paint::default();
    paint.set_color_rgba8(r, g, b, a);
    paint.blend_mode = blend;
    paint.anti_alias = aa;
    paint
}

/// Build a rounded rect path using cubic bezier curves.
fn rounded_rect_path(x: f32, y: f32, w: f32, h: f32, radius: f32) -> Option<Path> {
    let r = radius.min(w / 2.0).min(h / 2.0).max(0.0);
    if r < 0.5 {
        // Plain rect
        let rect = Rect::from_xywh(x, y, w, h)?;
        return Some(PathBuilder::from_rect(rect));
    }
    const K: f32 = 0.5522847498; // kappa for quarter-circle cubic bezier
    let kr = K * r;
    let mut pb = PathBuilder::new();
    // Start at top-left after corner
    pb.move_to(x + r, y);
    // Top edge
    pb.line_to(x + w - r, y);
    // Top-right corner
    pb.cubic_to(x + w - r + kr, y, x + w, y + r - kr, x + w, y + r);
    // Right edge
    pb.line_to(x + w, y + h - r);
    // Bottom-right corner
    pb.cubic_to(
        x + w,
        y + h - r + kr,
        x + w - r + kr,
        y + h,
        x + w - r,
        y + h,
    );
    // Bottom edge
    pb.line_to(x + r, y + h);
    // Bottom-left corner
    pb.cubic_to(x + r - kr, y + h, x, y + h - r + kr, x, y + h - r);
    // Left edge
    pb.line_to(x, y + r);
    // Top-left corner
    pb.cubic_to(x, y + r - kr, x + r - kr, y, x + r, y);
    pb.close();
    pb.finish()
}

/// Build an ellipse arc path (angles in degrees).
fn ellipse_arc_path(
    cx: f32,
    cy: f32,
    rx: f32,
    ry: f32,
    start_deg: f64,
    end_deg: f64,
) -> Option<Path> {
    let pi2 = 2.0 * std::f64::consts::PI;
    let deg2rad = std::f64::consts::PI / 180.0;

    let normalize = |mut rad: f64| {
        rad %= pi2;
        if rad < 0.0 {
            rad += pi2;
        }
        rad
    };
    let s = normalize(start_deg * deg2rad);
    let e = normalize(end_deg * deg2rad);

    // Determine sweep
    let sweep = if e > s { e - s } else { e - s + pi2 };
    let steps = ((sweep / 0.05) as usize).max(8);

    let mut pb = PathBuilder::new();
    for i in 0..=steps {
        let t = s + sweep * (i as f64 / steps as f64);
        let px = cx as f64 + rx as f64 * t.sin();
        let py = cy as f64 - ry as f64 * t.cos();
        if i == 0 {
            pb.move_to(px as f32, py as f32);
        } else {
            pb.line_to(px as f32, py as f32);
        }
    }
    pb.finish()
}

/// Decode a path from a compact byte buffer.
///
/// Segment format (little-endian f32 coords):
///   0x00  MoveTo   x y          (8 bytes)
///   0x01  LineTo   x y          (8 bytes)
///   0x02  CubicTo  cp1x cp1y cp2x cp2y x y  (24 bytes)
///   0x03  QuadTo   cpx cpy x y (16 bytes)
///   0x04  Close    (0 bytes)
fn decode_path(data: &[u8]) -> Option<Path> {
    let mut pb = PathBuilder::new();
    let mut i = 0usize;
    while i < data.len() {
        let op = data[i];
        i += 1;
        match op {
            0x00 => {
                if i + 8 > data.len() {
                    break;
                }
                let x = f32::from_le_bytes(data[i..i + 4].try_into().ok()?);
                let y = f32::from_le_bytes(data[i + 4..i + 8].try_into().ok()?);
                pb.move_to(x, y);
                i += 8;
            }
            0x01 => {
                if i + 8 > data.len() {
                    break;
                }
                let x = f32::from_le_bytes(data[i..i + 4].try_into().ok()?);
                let y = f32::from_le_bytes(data[i + 4..i + 8].try_into().ok()?);
                pb.line_to(x, y);
                i += 8;
            }
            0x02 => {
                if i + 24 > data.len() {
                    break;
                }
                let cp1x = f32::from_le_bytes(data[i..i + 4].try_into().ok()?);
                let cp1y = f32::from_le_bytes(data[i + 4..i + 8].try_into().ok()?);
                let cp2x = f32::from_le_bytes(data[i + 8..i + 12].try_into().ok()?);
                let cp2y = f32::from_le_bytes(data[i + 12..i + 16].try_into().ok()?);
                let x = f32::from_le_bytes(data[i + 16..i + 20].try_into().ok()?);
                let y = f32::from_le_bytes(data[i + 20..i + 24].try_into().ok()?);
                pb.cubic_to(cp1x, cp1y, cp2x, cp2y, x, y);
                i += 24;
            }
            0x03 => {
                if i + 16 > data.len() {
                    break;
                }
                let cpx = f32::from_le_bytes(data[i..i + 4].try_into().ok()?);
                let cpy = f32::from_le_bytes(data[i + 4..i + 8].try_into().ok()?);
                let x = f32::from_le_bytes(data[i + 8..i + 12].try_into().ok()?);
                let y = f32::from_le_bytes(data[i + 12..i + 16].try_into().ok()?);
                pb.quad_to(cpx, cpy, x, y);
                i += 16;
            }
            0x04 => {
                pb.close();
            }
            _ => break,
        }
    }
    pb.finish()
}

// --- Path / Transform handle types ---

#[derive(Clone)]
enum PathCmd {
    MoveTo(f32, f32),
    LineTo(f32, f32),
    CubicTo(f32, f32, f32, f32, f32, f32),
    QuadTo(f32, f32, f32, f32),
    Arc {
        cx: f32,
        cy: f32,
        r: f32,
        start: f32,
        end: f32,
        clockwise: bool,
    },
    Close,
}

struct RustPath {
    cmds: Vec<PathCmd>,
    line_width: f32,
    line_cap: u8,
    line_join: u8,
    dash_intervals: Vec<f32>,
    dash_phase: f32,
    eo_fill_rule: bool,
}

impl RustPath {
    fn new() -> Self {
        RustPath {
            cmds: Vec::new(),
            line_width: 1.0,
            line_cap: 0,
            line_join: 0,
            dash_intervals: Vec::new(),
            dash_phase: 0.0,
            eo_fill_rule: false,
        }
    }
}

struct FrameState {
    ctm: Transform,
    clip_data: Option<Vec<u8>>,
}

static PATH_MAP: Lazy<RwLock<HashMap<i32, Mutex<RustPath>>>> =
    Lazy::new(|| RwLock::new(HashMap::new()));
static mut NEXT_PATH_ID: i32 = 1;

static TRANSFORM_MAP: Lazy<RwLock<HashMap<i32, (f32, f32, f32, f32, f32, f32)>>> =
    Lazy::new(|| RwLock::new(HashMap::new()));
static mut NEXT_TRANSFORM_ID: i32 = 1;

/// Sample points along an arc (clockwise = positive sweep).
fn arc_points_f32(
    cx: f32,
    cy: f32,
    r: f32,
    start: f32,
    end: f32,
    clockwise: bool,
) -> Vec<(f32, f32)> {
    let sweep = if clockwise {
        let s = end - start;
        if s < 0.0 {
            s + 2.0 * std::f32::consts::PI
        } else {
            s
        }
    } else {
        let s = end - start;
        if s > 0.0 {
            s - 2.0 * std::f32::consts::PI
        } else {
            s
        }
    };
    let steps = ((sweep.abs() * r.max(1.0) / 2.0) as usize).max(4);
    (0..=steps)
        .map(|i| {
            let t = start + sweep * i as f32 / steps as f32;
            (cx + r * t.cos(), cy + r * t.sin())
        })
        .collect()
}

fn build_path_from_cmds(cmds: &[PathCmd]) -> Option<Path> {
    let mut pb = PathBuilder::new();
    for cmd in cmds {
        match cmd {
            PathCmd::MoveTo(x, y) => pb.move_to(*x, *y),
            PathCmd::LineTo(x, y) => pb.line_to(*x, *y),
            PathCmd::CubicTo(cp1x, cp1y, cp2x, cp2y, x, y) => {
                pb.cubic_to(*cp1x, *cp1y, *cp2x, *cp2y, *x, *y)
            }
            PathCmd::QuadTo(cpx, cpy, x, y) => pb.quad_to(*cpx, *cpy, *x, *y),
            PathCmd::Arc {
                cx,
                cy,
                r,
                start,
                end,
                clockwise,
            } => {
                let pts = arc_points_f32(*cx, *cy, *r, *start, *end, *clockwise);
                if let Some(&(fx, fy)) = pts.first() {
                    pb.move_to(fx, fy);
                }
                for &(x, y) in pts.iter().skip(1) {
                    pb.line_to(x, y);
                }
            }
            PathCmd::Close => pb.close(),
        }
    }
    pb.finish()
}

fn with_path<F, R>(handle: i32, f: F) -> R
where
    F: FnOnce(&mut RustPath) -> R,
    R: Default,
{
    let map = PATH_MAP.read();
    if let Some(p) = map.get(&handle) {
        f(&mut p.lock())
    } else {
        R::default()
    }
}

// --- FrameBuffer implementation ---

impl FrameBuffer {
    /// Get a PixmapMut wrapping the pixel buffer (premultiplied RGBA).
    fn pixmap_mut(&mut self) -> Option<PixmapMut<'_>> {
        PixmapMut::from_bytes(self.pixels, self.w as u32, self.h as u32)
    }

    /// Write a single pixel (premultiplied) - Source blend.
    fn set_pixel(&mut self, x: i32, y: i32, r: u8, g: u8, b: u8, a: u8) {
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
    fn set_pixel_over(&mut self, x: i32, y: i32, r: u8, g: u8, b: u8, a: u8) {
        if a == 0 {
            return;
        }
        if x >= 0 && x < self.w && y >= 0 && y < self.h {
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

    fn get_pixel_raw(&self, x: i32, y: i32) -> u32 {
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

    fn fill_solid(&mut self, r: u8, g: u8, b: u8, a: u8) {
        if let Some(mut pm) = self.pixmap_mut() {
            pm.fill(Color::from_rgba8(r, g, b, a));
        }
    }

    fn fill_rect(
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

    fn fill_rounded_rect(
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

    fn draw_line(
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

    fn draw_hline(&mut self, x: i32, y: i32, w: i32, r: u8, g: u8, b: u8, a: u8, blend: BlendMode) {
        if let Some(rect) = Rect::from_xywh(x as f32, y as f32, w as f32, 1.0) {
            if let Some(mut pm) = self.pixmap_mut() {
                let paint = make_paint(r, g, b, a, blend, false);
                pm.fill_rect(rect, &paint, Transform::identity(), None);
            }
        }
    }

    fn draw_vline(&mut self, x: i32, y: i32, h: i32, r: u8, g: u8, b: u8, a: u8, blend: BlendMode) {
        if let Some(rect) = Rect::from_xywh(x as f32, y as f32, 1.0, h as f32) {
            if let Some(mut pm) = self.pixmap_mut() {
                let paint = make_paint(r, g, b, a, blend, false);
                pm.fill_rect(rect, &paint, Transform::identity(), None);
            }
        }
    }

    fn draw_rounded_rect(
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

    fn draw_circle(
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

    fn fill_circle(
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

    fn draw_ellipse(
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

    fn fill_ellipse(
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

    fn draw_ellipse_arc(
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

    fn blit(
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
                    None,
                );
            }
        }
    }

    fn scroll(&mut self, dx: i32, dy: i32) {
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

    fn draw_text(
        &mut self,
        font: &fontdue::Font,
        text: &str,
        size: f32,
        start_x: f32,
        start_y: f32,
        color: (u8, u8, u8, u8),
        spacing: f32,
    ) {
        let (r, g, b, a) = color;
        let aa = self.antialias;
        let mut curr_x = start_x;

        for c in text.chars() {
            if c.is_control() {
                continue;
            }
            let (metrics, bitmap) = font.rasterize(c, size);
            let draw_x = curr_x + metrics.xmin as f32;
            let draw_y = start_y - (metrics.height as f32 + metrics.ymin as f32);

            for row in 0..metrics.height {
                for col in 0..metrics.width {
                    let coverage = bitmap[row * metrics.width + col];
                    if coverage == 0 {
                        continue;
                    }
                    if aa {
                        let pixel_a = ((a as u16 * coverage as u16) / 255) as u8;
                        self.set_pixel_over(
                            draw_x as i32 + col as i32,
                            draw_y as i32 + row as i32,
                            r,
                            g,
                            b,
                            pixel_a,
                        );
                    } else if coverage >= 128 {
                        self.set_pixel_over(
                            draw_x as i32 + col as i32,
                            draw_y as i32 + row as i32,
                            r,
                            g,
                            b,
                            a,
                        );
                    }
                }
            }
            curr_x += metrics.advance_width + spacing;
        }
    }

    fn draw_text_anchored(
        &mut self,
        font: &fontdue::Font,
        text: &str,
        size: f32,
        x: f32,
        y: f32,
        anchor: u32,
        color: (u8, u8, u8, u8),
        spacing: f32,
    ) {
        let (width, height, ascent) = get_text_layout(font, text, size, spacing);
        let (sx, sy) = calculate_anchor_pos(anchor, x, y, width, height, ascent);
        self.draw_text(font, text, size, sx, sy, color, spacing);
    }

    fn fill_path_data(&mut self, data: &[u8], r: u8, g: u8, b: u8, a: u8, blend: BlendMode) {
        let aa = self.antialias;
        if let Some(path) = decode_path(data) {
            let ctm = self.ctm;
            if let Some(mut pm) = self.pixmap_mut() {
                let paint = make_paint(r, g, b, a, blend, aa);
                pm.fill_path(&path, &paint, FillRule::Winding, ctm, None);
            }
        }
    }

    fn stroke_path_data(
        &mut self,
        data: &[u8],
        width: f32,
        cap: u8,
        join: u8,
        r: u8,
        g: u8,
        b: u8,
        a: u8,
        blend: BlendMode,
    ) {
        let aa = self.antialias;
        if let Some(path) = decode_path(data) {
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

// --- Exported C functions ---

#[no_mangle]
pub unsafe extern "C" fn CreateFrameBuffer(
    data: *mut c_uchar,
    width: c_int,
    height: c_int,
) -> c_int {
    let size = (width * height * 4) as usize;
    let pixels = slice::from_raw_parts_mut(data, size);
    let fb = FrameBuffer {
        pixels,
        w: width,
        h: height,
        cx: width / 2,
        cy: height / 2,
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

#[no_mangle]
pub unsafe extern "C" fn DestroyFrameBuffer(handle: c_int) {
    FB_MAP.write().remove(&handle);
}

fn with_fb<F, R>(handle: i32, f: F) -> R
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

// fn with_fb_centered<F, R>(handle: i32, f: F) -> R
// where
//     F: FnOnce(&mut FrameBuffer, i32, i32) -> R,
//     R: Default,
// {
//     with_fb(handle, |fb| {
//         let (cx, cy) = (fb.cx, fb.cy);
//         f(fb, cx, cy)
//     })
// }

// --- Drawing exports ---

#[no_mangle]
pub extern "C" fn Fill(handle: i32, color: u32) {
    let (r, g, b, a) = hex_to_rgba(color);
    with_fb(handle, |fb| fb.fill_solid(r, g, b, a));
}

#[no_mangle]
pub extern "C" fn FillOver(handle: i32, color: u32) {
    let (r, g, b, a) = hex_to_rgba(color);
    if a == 255 {
        Fill(handle, color);
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

#[no_mangle]
pub extern "C" fn SetPixel(handle: i32, x: i32, y: i32, color: u32) {
    let (r, g, b, a) = hex_to_rgba(color);
    with_fb(handle, |fb| fb.set_pixel(x, y, r, g, b, a));
}

#[no_mangle]
pub extern "C" fn GetPixel(handle: i32, x: i32, y: i32) -> u32 {
    with_fb(handle, |fb| fb.get_pixel_raw(x, y))
}

#[no_mangle]
pub extern "C" fn Line(handle: i32, x0: i32, y0: i32, x1: i32, y1: i32, color: u32, blend: u8) {
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| fb.draw_line(x0, y0, x1, y1, r, g, b, a, bm));
}

#[no_mangle]
pub extern "C" fn LineStroke(
    handle: i32,
    x0: f32,
    y0: f32,
    x1: f32,
    y1: f32,
    width: f32,
    cap: u8,
    join: u8,
    color: u32,
    blend: u8,
) {
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| {
        fb.stroke_line(x0, y0, x1, y1, width, cap, join, r, g, b, a, bm)
    });
}

#[no_mangle]
pub extern "C" fn RectStroke(
    handle: i32,
    x: f32,
    y: f32,
    w: f32,
    h: f32,
    width: f32,
    join: u8,
    color: u32,
    blend: u8,
) {
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| {
        fb.stroke_rect(x, y, w, h, width, join, r, g, b, a, bm)
    });
}

#[no_mangle]
pub extern "C" fn StrokeRoundedRect(
    handle: i32,
    x: f32,
    y: f32,
    w: f32,
    h: f32,
    radius: f32,
    bw: f32,
    join: u8,
    color: u32,
    blend: u8,
) {
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| {
        fb.stroke_rounded_rect(x, y, w, h, radius, bw, join, r, g, b, a, bm);
    });
}

#[no_mangle]
pub extern "C" fn EllipseStroke(
    handle: i32,
    cx: f32,
    cy: f32,
    rx: f32,
    ry: f32,
    width: f32,
    color: u32,
    blend: u8,
) {
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| {
        fb.stroke_ellipse(cx, cy, rx, ry, width, r, g, b, a, bm);
    });
}

#[no_mangle]
pub extern "C" fn HLine(handle: i32, x: i32, y: i32, w: i32, color: u32, blend: u8) {
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| fb.draw_hline(x, y, w, r, g, b, a, bm));
}

#[no_mangle]
pub extern "C" fn VLine(handle: i32, x: i32, y: i32, h: i32, color: u32, blend: u8) {
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| fb.draw_vline(x, y, h, r, g, b, a, bm));
}

#[no_mangle]
pub extern "C" fn Rect(handle: i32, x: i32, y: i32, w: i32, h: i32, color: u32, blend: u8) {
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| {
        if w <= 0 || h <= 0 {
            return;
        }
        fb.draw_hline(x, y, w, r, g, b, a, bm);
        fb.draw_hline(x, y + h - 1, w, r, g, b, a, bm);
        fb.draw_vline(x, y, h, r, g, b, a, bm);
        fb.draw_vline(x + w - 1, y, h, r, g, b, a, bm);
    });
}

#[no_mangle]
pub extern "C" fn FillRect(handle: i32, x: f32, y: f32, w: f32, h: f32, color: u32, blend: u8) {
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| {
        fb.fill_rect(x, y, w, h, r, g, b, a, bm);
    });
}

#[no_mangle]
pub extern "C" fn RoundedRect(
    handle: i32,
    x: i32,
    y: i32,
    w: i32,
    h: i32,
    radius: i32,
    color: u32,
    blend: u8,
) {
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| {
        fb.draw_rounded_rect(x, y, w, h, radius, r, g, b, a, bm)
    });
}

#[no_mangle]
pub extern "C" fn FillRoundedRect(
    handle: i32,
    x: f32,
    y: f32,
    w: f32,
    h: f32,
    radius: f32,
    color: u32,
    blend: u8,
) {
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| {
        fb.fill_rounded_rect(x, y, w, h, radius, r, g, b, a, bm)
    });
}

#[no_mangle]
pub extern "C" fn Circle(handle: i32, cx: i32, cy: i32, r: i32, color: u32, blend: u8) {
    let (rv, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| fb.draw_circle(cx, cy, r, rv, g, b, a, bm));
}

#[no_mangle]
pub extern "C" fn FillCircle(handle: i32, cx: f32, cy: f32, r: f32, color: u32, blend: u8) {
    let (rv, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| fb.fill_circle(cx, cy, r, rv, g, b, a, bm));
}

#[no_mangle]
pub extern "C" fn Ellipse(handle: i32, cx: i32, cy: i32, rx: i32, ry: i32, color: u32, blend: u8) {
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| fb.draw_ellipse(cx, cy, rx, ry, r, g, b, a, bm));
}

#[no_mangle]
pub extern "C" fn FillEllipse(
    handle: i32,
    cx: f32,
    cy: f32,
    rx: f32,
    ry: f32,
    color: u32,
    blend: u8,
) {
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| fb.fill_ellipse(cx, cy, rx, ry, r, g, b, a, bm));
}

#[no_mangle]
pub extern "C" fn EllipseArc(
    handle: i32,
    cx: i32,
    cy: i32,
    rx: i32,
    ry: i32,
    start_angle: f64,
    end_angle: f64,
    color: u32,
    blend: u8,
) {
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| {
        fb.draw_ellipse_arc(cx, cy, rx, ry, start_angle, end_angle, r, g, b, a, bm)
    });
}

#[no_mangle]
pub unsafe extern "C" fn FillPath(handle: i32, data: *const u8, len: i32, color: u32, blend: u8) {
    if data.is_null() || len <= 0 {
        return;
    }
    let data_slice = slice::from_raw_parts(data, len as usize);
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| fb.fill_path_data(data_slice, r, g, b, a, bm));
}

#[no_mangle]
pub unsafe extern "C" fn StrokePath(
    handle: i32,
    data: *const u8,
    len: i32,
    width: f32,
    cap: u8,
    join: u8,
    color: u32,
    blend: u8,
) {
    if data.is_null() || len <= 0 {
        return;
    }
    let data_slice = slice::from_raw_parts(data, len as usize);
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    with_fb(handle, |fb| {
        fb.stroke_path_data(data_slice, width, cap, join, r, g, b, a, bm)
    });
}

#[no_mangle]
pub unsafe extern "C" fn BlitRGBA(
    handle: i32,
    src_data: *const u8,
    src_w: i32,
    src_h: i32,
    dst_x: i32,
    dst_y: i32,
    blend: i32,
) {
    let size = (src_w * src_h * 4) as usize;
    let src_pixels = std::slice::from_raw_parts(src_data, size);
    with_fb(handle, |fb| {
        fb.blit(src_pixels, src_w, src_h, dst_x, dst_y, blend != 0);
    });
}

#[no_mangle]
pub extern "C" fn Scroll(handle: i32, dx: i32, dy: i32) {
    with_fb(handle, |fb| fb.scroll(dx, dy));
}

#[no_mangle]
pub extern "C" fn SetAntiAlias(handle: i32, enabled: i32) {
    with_fb(handle, |fb| {
        fb.antialias = enabled != 0;
    });
}

#[no_mangle]
pub extern "C" fn GetAntiAlias(handle: i32) -> i32 {
    with_fb(handle, |fb| fb.antialias as i32)
}

/// Set the current transformation matrix for the framebuffer.
/// Parameters map to the standard 2D affine matrix (a, b, c, d, tx, ty)
/// matching the CoreGraphics / Pythonista Transform convention.
/// tiny-skia from_row takes (sx=a, ky=b, kx=c, sy=d, tx, ty).
#[no_mangle]
pub extern "C" fn SetCTM(handle: i32, a: f32, b: f32, c: f32, d: f32, tx: f32, ty: f32) {
    with_fb(handle, |fb| {
        fb.ctm = Transform::from_row(a, b, c, d, tx, ty);
    });
}

#[no_mangle]
pub extern "C" fn ApplyYUV422Compensation(handle: i32, x: i32, y: i32, w: i32, h: i32) {
    with_fb(handle, |fb| fb.apply_yuv422_compensation(x, y, w, h));
}

// --- Text rendering ---

pub struct TextAnchor;

impl TextAnchor {
    pub const CENTER: u32 = 0;
    pub const TOP: u32 = 0b01;
    pub const BOTTOM: u32 = 0b10;
    pub const LEFT: u32 = 0b0100;
    pub const RIGHT: u32 = 0b1000;

    pub fn get_v(anchor: u32) -> u32 {
        anchor & 0b11
    }
    pub fn get_h(anchor: u32) -> u32 {
        (anchor >> 2) & 0b11
    }
}

fn with_font<F, R>(handle: i32, f: F) -> R
where
    F: FnOnce(&fontdue::Font) -> R,
    R: Default,
{
    let map = FONT_MAP.read();
    if let Some(font) = map.get(&handle) {
        f(font)
    } else {
        R::default()
    }
}

fn calculate_anchor_pos(
    anchor: u32,
    base_x: f32,
    base_y: f32,
    width: f32,
    height: f32,
    ascent: f32,
) -> (f32, f32) {
    let left = (anchor & TextAnchor::LEFT) != 0;
    let right = (anchor & TextAnchor::RIGHT) != 0;
    let x = if left && !right {
        base_x
    } else if right && !left {
        base_x - width
    } else {
        base_x - width / 2.0
    };

    let top = (anchor & TextAnchor::TOP) != 0;
    let bottom = (anchor & TextAnchor::BOTTOM) != 0;
    let y = if top && !bottom {
        base_y + ascent
    } else if bottom && !top {
        base_y + ascent - height
    } else {
        base_y + (ascent - height / 2.0)
    };
    (x, y)
}

fn get_text_layout(font: &fontdue::Font, text: &str, size: f32, spacing: f32) -> (f32, f32, f32) {
    let mut width = 0.0;
    let mut count = 0u32;
    for c in text.chars() {
        if !c.is_control() {
            width += font.metrics(c, size).advance_width;
            count += 1;
        }
    }
    if count > 1 {
        width += spacing * (count - 1) as f32;
    }
    let (height, ascent) = font
        .horizontal_line_metrics(size)
        .map(|m| (m.ascent - m.descent + m.line_gap, m.ascent))
        .unwrap_or((0.0, 0.0));
    (width, height, ascent)
}

#[no_mangle]
pub unsafe extern "C" fn DrawText(
    handle: i32,
    mut font_handle: i32,
    size: f32,
    text: *const c_char,
    x: f32,
    y: f32,
    anchor: u32,
    color: u32,
    spacing: f32,
) -> i32 {
    let input_text = match parse_c_str(text) {
        Some(s) => s,
        None => return 0,
    };
    let rgba = hex_to_rgba(color);
    if font_handle < 1 {
        font_handle = GetDefaultFont();
    }
    with_font(font_handle, |font| {
        with_fb(handle, |fb| {
            fb.draw_text_anchored(font, input_text, size, x, y, anchor, rgba, spacing);
            0
        })
    })
}

#[no_mangle]
pub unsafe extern "C" fn MeasureText(
    font_handle: i32,
    size: f32,
    text: *const c_char,
    spacing: f32,
) -> i32 {
    let input_text = match parse_c_str(text) {
        Some(s) => s,
        None => return 0,
    };
    with_font(font_handle, |font| {
        let (w, _, _) = get_text_layout(font, input_text, size, spacing);
        w.round() as i32
    })
}

#[no_mangle]
pub unsafe extern "C" fn GetTextMetrics(
    font_handle: i32,
    size: f32,
    ascent: *mut i32,
    descent: *mut i32,
    height: *mut i32,
) -> i32 {
    with_font(font_handle, |font| {
        if let Some(m) = font.horizontal_line_metrics(size) {
            if !ascent.is_null() {
                *ascent = m.ascent.round() as i32;
            }
            if !descent.is_null() {
                *descent = m.descent.round() as i32;
            }
            if !height.is_null() {
                *height = (m.ascent - m.descent + m.line_gap).round() as i32;
            }
            0
        } else {
            -1
        }
    })
}

#[no_mangle]
pub extern "C" fn GetTextHeight(font_handle: i32, size: f32) -> i32 {
    with_font(font_handle, |font| {
        font.horizontal_line_metrics(size)
            .map(|m| (m.ascent - m.descent + m.line_gap).round() as i32)
            .unwrap_or(-1)
    })
}

// --- GState exports ---

#[no_mangle]
pub extern "C" fn GStatePush(handle: i32) {
    with_fb(handle, |fb| {
        let clip_data = fb.clip_mask.as_ref().map(|m| m.data().to_vec());
        fb.gstate_stack.push(FrameState {
            ctm: fb.ctm,
            clip_data,
        });
    });
}

#[no_mangle]
pub extern "C" fn GStatePop(handle: i32) {
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

// --- Transform exports ---

#[no_mangle]
pub unsafe extern "C" fn CreateTransform(a: f32, b: f32, c: f32, d: f32, tx: f32, ty: f32) -> i32 {
    let mut map = TRANSFORM_MAP.write();
    let id = NEXT_TRANSFORM_ID;
    NEXT_TRANSFORM_ID += 1;
    map.insert(id, (a, b, c, d, tx, ty));
    id
}

#[no_mangle]
pub extern "C" fn DestroyTransform(handle: i32) {
    TRANSFORM_MAP.write().remove(&handle);
}

#[no_mangle]
pub unsafe extern "C" fn TransformRotation(radians: f32) -> i32 {
    let cos_a = radians.cos();
    let sin_a = radians.sin();
    CreateTransform(cos_a, sin_a, -sin_a, cos_a, 0.0, 0.0)
}

#[no_mangle]
pub unsafe extern "C" fn TransformScale(sx: f32, sy: f32) -> i32 {
    CreateTransform(sx, 0.0, 0.0, sy, 0.0, 0.0)
}

#[no_mangle]
pub unsafe extern "C" fn TransformTranslation(tx: f32, ty: f32) -> i32 {
    CreateTransform(1.0, 0.0, 0.0, 1.0, tx, ty)
}

#[no_mangle]
pub unsafe extern "C" fn TransformConcat(handle_a: i32, handle_b: i32) -> i32 {
    let map = TRANSFORM_MAP.read();
    let (a1, b1, c1, d1, tx1, ty1) = match map.get(&handle_a) {
        Some(&t) => t,
        None => return -1,
    };
    let (a2, b2, c2, d2, tx2, ty2) = match map.get(&handle_b) {
        Some(&t) => t,
        None => return -1,
    };
    drop(map);
    // Standard 2D affine concat: result = self * other
    let a = a1 * a2 + c1 * b2;
    let b = b1 * a2 + d1 * b2;
    let c = a1 * c2 + c1 * d2;
    let d = b1 * c2 + d1 * d2;
    let tx = a1 * tx2 + c1 * ty2 + tx1;
    let ty = b1 * tx2 + d1 * ty2 + ty1;
    CreateTransform(a, b, c, d, tx, ty)
}

#[no_mangle]
pub unsafe extern "C" fn TransformInvert(handle: i32) -> i32 {
    let (a, b, c, d, tx, ty) = match TRANSFORM_MAP.read().get(&handle) {
        Some(&t) => t,
        None => return -1,
    };
    let det = a * d - b * c;
    if det.abs() < 1e-10 {
        return -1;
    }
    let inv = 1.0 / det;
    CreateTransform(
        d * inv,
        -b * inv,
        -c * inv,
        a * inv,
        (c * ty - d * tx) * inv,
        (b * tx - a * ty) * inv,
    )
}

/// Get transform components into out-params. Returns 0 on success, -1 if handle invalid.
#[no_mangle]
pub unsafe extern "C" fn TransformGet(
    handle: i32,
    a: *mut f32,
    b: *mut f32,
    c: *mut f32,
    d: *mut f32,
    tx: *mut f32,
    ty: *mut f32,
) -> i32 {
    if let Some(&(va, vb, vc, vd, vtx, vty)) = TRANSFORM_MAP.read().get(&handle) {
        if !a.is_null() {
            *a = va;
        }
        if !b.is_null() {
            *b = vb;
        }
        if !c.is_null() {
            *c = vc;
        }
        if !d.is_null() {
            *d = vd;
        }
        if !tx.is_null() {
            *tx = vtx;
        }
        if !ty.is_null() {
            *ty = vty;
        }
        0
    } else {
        -1
    }
}

// --- Path exports ---

#[no_mangle]
pub unsafe extern "C" fn CreatePath() -> i32 {
    let mut map = PATH_MAP.write();
    let id = NEXT_PATH_ID;
    NEXT_PATH_ID += 1;
    map.insert(id, Mutex::new(RustPath::new()));
    id
}

#[no_mangle]
pub extern "C" fn DestroyPath(handle: i32) {
    PATH_MAP.write().remove(&handle);
}

#[no_mangle]
pub extern "C" fn PathMoveTo(handle: i32, x: f32, y: f32) {
    with_path(handle, |p| p.cmds.push(PathCmd::MoveTo(x, y)));
}

#[no_mangle]
pub extern "C" fn PathLineTo(handle: i32, x: f32, y: f32) {
    with_path(handle, |p| p.cmds.push(PathCmd::LineTo(x, y)));
}

#[no_mangle]
pub extern "C" fn PathAddCurve(
    handle: i32,
    cp1x: f32,
    cp1y: f32,
    cp2x: f32,
    cp2y: f32,
    x: f32,
    y: f32,
) {
    with_path(handle, |p| {
        p.cmds.push(PathCmd::CubicTo(cp1x, cp1y, cp2x, cp2y, x, y))
    });
}

#[no_mangle]
pub extern "C" fn PathAddQuadCurve(handle: i32, cpx: f32, cpy: f32, x: f32, y: f32) {
    with_path(handle, |p| p.cmds.push(PathCmd::QuadTo(cpx, cpy, x, y)));
}

#[no_mangle]
pub extern "C" fn PathAddArc(
    handle: i32,
    cx: f32,
    cy: f32,
    r: f32,
    start: f32,
    end: f32,
    clockwise: i32,
) {
    with_path(handle, |p| {
        p.cmds.push(PathCmd::Arc {
            cx,
            cy,
            r,
            start,
            end,
            clockwise: clockwise != 0,
        })
    });
}

#[no_mangle]
pub extern "C" fn PathClose(handle: i32) {
    with_path(handle, |p| p.cmds.push(PathCmd::Close));
}

#[no_mangle]
pub extern "C" fn PathAppend(dst: i32, src: i32) {
    let src_cmds: Vec<PathCmd> = {
        let map = PATH_MAP.read();
        match map.get(&src) {
            Some(p) => p.lock().cmds.clone(),
            None => return,
        }
    };
    with_path(dst, |p| p.cmds.extend(src_cmds));
}

#[no_mangle]
pub unsafe extern "C" fn PathRect(x: f32, y: f32, w: f32, h: f32) -> i32 {
    let id = CreatePath();
    with_path(id, |p| {
        p.cmds.push(PathCmd::MoveTo(x, y));
        p.cmds.push(PathCmd::LineTo(x + w, y));
        p.cmds.push(PathCmd::LineTo(x + w, y + h));
        p.cmds.push(PathCmd::LineTo(x, y + h));
        p.cmds.push(PathCmd::Close);
    });
    id
}

#[no_mangle]
pub unsafe extern "C" fn PathOval(x: f32, y: f32, w: f32, h: f32) -> i32 {
    const K: f32 = 0.5522847498;
    let id = CreatePath();
    with_path(id, |p| {
        let (cx, cy) = (x + w / 2.0, y + h / 2.0);
        let (rx, ry) = (w / 2.0, h / 2.0);
        let (kx, ky) = (K * rx, K * ry);
        p.cmds.push(PathCmd::MoveTo(cx, cy - ry));
        p.cmds.push(PathCmd::CubicTo(
            cx + kx,
            cy - ry,
            cx + rx,
            cy - ky,
            cx + rx,
            cy,
        ));
        p.cmds.push(PathCmd::CubicTo(
            cx + rx,
            cy + ky,
            cx + kx,
            cy + ry,
            cx,
            cy + ry,
        ));
        p.cmds.push(PathCmd::CubicTo(
            cx - kx,
            cy + ry,
            cx - rx,
            cy + ky,
            cx - rx,
            cy,
        ));
        p.cmds.push(PathCmd::CubicTo(
            cx - rx,
            cy - ky,
            cx - kx,
            cy - ry,
            cx,
            cy - ry,
        ));
        p.cmds.push(PathCmd::Close);
    });
    id
}

#[no_mangle]
pub unsafe extern "C" fn PathRoundedRect(x: f32, y: f32, w: f32, h: f32, r: f32) -> i32 {
    const K: f32 = 0.5522847498;
    let id = CreatePath();
    with_path(id, |p| {
        let r = r.min(w / 2.0).min(h / 2.0).max(0.0);
        let kr = K * r;
        p.cmds.push(PathCmd::MoveTo(x + r, y));
        p.cmds.push(PathCmd::LineTo(x + w - r, y));
        p.cmds.push(PathCmd::CubicTo(
            x + w - r + kr,
            y,
            x + w,
            y + r - kr,
            x + w,
            y + r,
        ));
        p.cmds.push(PathCmd::LineTo(x + w, y + h - r));
        p.cmds.push(PathCmd::CubicTo(
            x + w,
            y + h - r + kr,
            x + w - r + kr,
            y + h,
            x + w - r,
            y + h,
        ));
        p.cmds.push(PathCmd::LineTo(x + r, y + h));
        p.cmds.push(PathCmd::CubicTo(
            x + r - kr,
            y + h,
            x,
            y + h - r + kr,
            x,
            y + h - r,
        ));
        p.cmds.push(PathCmd::LineTo(x, y + r));
        p.cmds
            .push(PathCmd::CubicTo(x, y + r - kr, x + r - kr, y, x + r, y));
        p.cmds.push(PathCmd::Close);
    });
    id
}

#[no_mangle]
pub extern "C" fn PathSetLineWidth(handle: i32, width: f32) {
    with_path(handle, |p| p.line_width = width);
}

#[no_mangle]
pub extern "C" fn PathSetLineCap(handle: i32, cap: u8) {
    with_path(handle, |p| p.line_cap = cap);
}

#[no_mangle]
pub extern "C" fn PathSetLineJoin(handle: i32, join: u8) {
    with_path(handle, |p| p.line_join = join);
}

#[no_mangle]
pub unsafe extern "C" fn PathSetLineDash(
    handle: i32,
    intervals: *const f32,
    count: i32,
    phase: f32,
) {
    if intervals.is_null() || count <= 0 {
        with_path(handle, |p| {
            p.dash_intervals.clear();
            p.dash_phase = 0.0;
        });
        return;
    }
    let data = slice::from_raw_parts(intervals, count as usize).to_vec();
    with_path(handle, |p| {
        p.dash_intervals = data;
        p.dash_phase = phase;
    });
}

#[no_mangle]
pub extern "C" fn PathFill(fb_handle: i32, path_handle: i32, color: u32, blend: u8) {
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    let (cmds, eo_fill) = {
        let map = PATH_MAP.read();
        match map.get(&path_handle) {
            Some(p) => {
                let p = p.lock();
                (p.cmds.clone(), p.eo_fill_rule)
            }
            None => return,
        }
    };
    let fill_rule = if eo_fill {
        FillRule::EvenOdd
    } else {
        FillRule::Winding
    };
    with_fb(fb_handle, |fb| {
        // clone clip data before mutable borrow of fb
        let clip_bytes = fb
            .clip_mask
            .as_ref()
            .map(|m| (m.data().to_vec(), fb.w as u32, fb.h as u32));
        if let Some(path) = build_path_from_cmds(&cmds) {
            let ctm = fb.ctm;
            let aa = fb.antialias;
            if let Some(mut pm) = fb.pixmap_mut() {
                let paint = make_paint(r, g, b, a, bm, aa);
                let clip_mask = clip_bytes.as_ref().and_then(|(data, w, h)| {
                    let mut m = Mask::new(*w, *h)?;
                    m.data_mut().copy_from_slice(data);
                    Some(m)
                });
                pm.fill_path(&path, &paint, fill_rule, ctm, clip_mask.as_ref());
            }
        }
    });
}

#[no_mangle]
pub extern "C" fn PathSetEoFillRule(handle: i32, value: i32) {
    with_path(handle, |p| p.eo_fill_rule = value != 0);
}

#[no_mangle]
pub extern "C" fn PathStroke(fb_handle: i32, path_handle: i32, color: u32, blend: u8) {
    let (r, g, b, a) = hex_to_rgba(color);
    let bm = map_blend_mode(blend);
    let (cmds, lw, lcap, ljoin, dash_iv, dash_ph) = {
        let map = PATH_MAP.read();
        match map.get(&path_handle) {
            Some(lock) => {
                let p = lock.lock();
                (
                    p.cmds.clone(),
                    p.line_width,
                    p.line_cap,
                    p.line_join,
                    p.dash_intervals.clone(),
                    p.dash_phase,
                )
            }
            None => return,
        }
    };
    with_fb(fb_handle, |fb| {
        // clone clip data before mutable borrow of fb
        let clip_bytes = fb
            .clip_mask
            .as_ref()
            .map(|m| (m.data().to_vec(), fb.w as u32, fb.h as u32));
        if let Some(path) = build_path_from_cmds(&cmds) {
            let ctm = fb.ctm;
            let aa = fb.antialias;
            if let Some(mut pm) = fb.pixmap_mut() {
                let paint = make_paint(r, g, b, a, bm, aa);
                let mut stroke = Stroke::default();
                stroke.width = lw;
                stroke.line_cap = map_cap(lcap);
                stroke.line_join = map_join(ljoin);
                if !dash_iv.is_empty() {
                    stroke.dash = StrokeDash::new(dash_iv, dash_ph);
                }
                let clip_mask = clip_bytes.as_ref().and_then(|(data, w, h)| {
                    let mut m = Mask::new(*w, *h)?;
                    m.data_mut().copy_from_slice(data);
                    Some(m)
                });
                pm.stroke_path(&path, &paint, &stroke, ctm, clip_mask.as_ref());
            }
        }
    });
}

#[no_mangle]
pub extern "C" fn PathHitTest(path_handle: i32, x: f32, y: f32) -> i32 {
    let (cmds, eo_fill) = {
        let map = PATH_MAP.read();
        match map.get(&path_handle) {
            Some(p) => {
                let p = p.lock();
                (p.cmds.clone(), p.eo_fill_rule)
            }
            None => return 0,
        }
    };
    let fill_rule = if eo_fill {
        FillRule::EvenOdd
    } else {
        FillRule::Winding
    };
    if let Some(path) = build_path_from_cmds(&cmds) {
        let mut data = [0u8; 4];
        if let Some(mut pm) = PixmapMut::from_bytes(&mut data, 1, 1) {
            let mut paint = Paint::default();
            paint.set_color_rgba8(255, 255, 255, 255);
            paint.blend_mode = BlendMode::Source;
            let transform = Transform::from_translate(-x + 0.5, -y + 0.5);
            pm.fill_path(&path, &paint, fill_rule, transform, None);
            return if data[3] > 0 { 1 } else { 0 };
        }
    }
    0
}

/// Fill *x_out, *y_out, *w_out, *h_out with the path's tight bounding rect.
/// Returns 1 on success, 0 if path is empty or handle is invalid.
#[no_mangle]
pub unsafe extern "C" fn PathGetBounds(
    path_handle: i32,
    x_out: *mut f32,
    y_out: *mut f32,
    w_out: *mut f32,
    h_out: *mut f32,
) -> i32 {
    let cmds: Vec<PathCmd> = {
        let map = PATH_MAP.read();
        match map.get(&path_handle) {
            Some(p) => p.lock().cmds.clone(),
            None => return 0,
        }
    };
    if let Some(path) = build_path_from_cmds(&cmds) {
        let b = path.bounds();
        *x_out = b.left();
        *y_out = b.top();
        *w_out = b.width();
        *h_out = b.height();
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn PathAddClip(fb_handle: i32, path_handle: i32) {
    let cmds: Vec<PathCmd> = {
        let map = PATH_MAP.read();
        match map.get(&path_handle) {
            Some(p) => p.lock().cmds.clone(),
            None => return,
        }
    };
    with_fb(fb_handle, |fb| {
        let w = fb.w as u32;
        let h = fb.h as u32;
        if let Some(path) = build_path_from_cmds(&cmds) {
            let ctm = fb.ctm;
            let aa = fb.antialias;
            if let Some(mut mask) = Mask::new(w, h) {
                mask.fill_path(&path, FillRule::Winding, aa, ctm);
                fb.clip_mask = Some(mask);
            }
        }
    });
}

#[no_mangle]
pub extern "C" fn DrawCheckerBoard(fb_handle: i32, size: i32) {
    with_fb(fb_handle, |fb| {
        fb.draw_checkerboard(size);
    });
}
