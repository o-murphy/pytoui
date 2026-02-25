// --- Helpers ---
use std::ffi::CStr;
use std::os::raw::c_char;
use tiny_skia::{BlendMode, LineCap, LineJoin, Paint, Path, PathBuilder, Rect};

#[inline]
pub fn hex_to_rgba(c: u32) -> (u8, u8, u8, u8) {
    (
        ((c >> 24) & 0xFF) as u8,
        ((c >> 16) & 0xFF) as u8,
        ((c >> 8) & 0xFF) as u8,
        (c & 0xFF) as u8,
    )
}

pub unsafe fn parse_c_str<'a>(ptr: *const c_char) -> Option<&'a str> {
    if ptr.is_null() {
        return None;
    }
    CStr::from_ptr(ptr).to_str().ok()
}

pub fn map_cap(cap: u8) -> LineCap {
    match cap {
        1 => LineCap::Round,
        2 => LineCap::Square,
        _ => LineCap::Butt,
    }
}

pub fn map_join(join: u8) -> LineJoin {
    match join {
        1 => LineJoin::Round,
        2 => LineJoin::Bevel,
        _ => LineJoin::Miter,
    }
}

/// Map u8 blend mode value to tiny-skia BlendMode.
/// Values match the Python BlendMode enum (0-27).
pub fn map_blend_mode(mode: u8) -> BlendMode {
    match mode {
        0 => BlendMode::SourceOver, // NORMAL
        1 => BlendMode::Multiply,
        2 => BlendMode::Screen,
        3 => BlendMode::Overlay,
        4 => BlendMode::Darken,
        5 => BlendMode::Lighten,
        6 => BlendMode::ColorDodge,
        7 => BlendMode::ColorBurn,
        8 => BlendMode::SoftLight,
        9 => BlendMode::HardLight,
        10 => BlendMode::Difference,
        11 => BlendMode::Exclusion,
        12 => BlendMode::Hue,
        13 => BlendMode::Saturation,
        14 => BlendMode::Color,
        15 => BlendMode::Luminosity,
        16 => BlendMode::Clear,
        17 => BlendMode::Source, // COPY
        18 => BlendMode::SourceIn,
        19 => BlendMode::SourceOut,
        20 => BlendMode::SourceAtop,
        21 => BlendMode::DestinationOver,
        22 => BlendMode::DestinationIn,
        23 => BlendMode::DestinationOut,
        24 => BlendMode::DestinationAtop,
        25 => BlendMode::Xor,
        26 => BlendMode::Modulate, // PLUS_DARKER approximation
        27 => BlendMode::Plus,     // PLUS_LIGHTER
        _ => BlendMode::SourceOver,
    }
}

/// Create a tiny-skia Paint with the given color and blend mode.
#[inline]
pub(crate) fn make_paint(r: u8, g: u8, b: u8, a: u8, blend: BlendMode, aa: bool) -> Paint<'static> {
    let mut paint = Paint::default();
    paint.set_color_rgba8(r, g, b, a);
    paint.blend_mode = blend;
    paint.anti_alias = aa;
    paint
}

/// Build a rounded rect path using cubic bezier curves.
pub(crate) fn rounded_rect_path(x: f32, y: f32, w: f32, h: f32, radius: f32) -> Option<Path> {
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
pub(crate) fn ellipse_arc_path(
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

/// Sample points along an arc (clockwise = positive sweep).
pub(crate) fn arc_points_f32(
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
