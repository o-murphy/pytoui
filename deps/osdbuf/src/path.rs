use once_cell::sync::Lazy;
use parking_lot::{Mutex, RwLock};
use std::collections::HashMap;
use std::slice;
use tiny_skia::{
    BlendMode, FillRule, Mask, Paint, Path, PathBuilder, PixmapMut, Stroke, StrokeDash, Transform,
};

use crate::framebuffer::with_fb;
use crate::helpers::{arc_points_f32, hex_to_rgba, make_paint, map_blend_mode, map_cap, map_join};

// --- Path / Transform handle types ---

#[derive(Clone)]
pub(crate) enum PathCmd {
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

pub(crate) struct RustPath {
    pub(crate) cmds: Vec<PathCmd>,
    pub(crate) line_width: f32,
    pub(crate) line_cap: u8,
    pub(crate) line_join: u8,
    pub(crate) dash_intervals: Vec<f32>,
    pub(crate) dash_phase: f32,
    pub(crate) eo_fill_rule: bool,
}

impl RustPath {
    pub(crate) fn new() -> Self {
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

pub(crate) static PATH_MAP: Lazy<RwLock<HashMap<i32, Mutex<RustPath>>>> =
    Lazy::new(|| RwLock::new(HashMap::new()));
pub(crate) static mut NEXT_PATH_ID: i32 = 1;

pub(crate) fn with_path<F, R>(handle: i32, f: F) -> R
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

pub(crate) fn build_path_from_cmds(cmds: &[PathCmd]) -> Option<Path> {
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

// --- C-export logic helpers ---

pub(crate) unsafe fn create_path() -> i32 {
    let mut map = PATH_MAP.write();
    let id = NEXT_PATH_ID;
    NEXT_PATH_ID += 1;
    map.insert(id, Mutex::new(RustPath::new()));
    id
}

pub(crate) fn destroy_path(handle: i32) -> i32 {
    match PATH_MAP.write().remove(&handle) {
        Some(_) => 0,
        None => -1,
    }
}

pub(crate) fn path_append(dst: i32, src: i32) {
    let src_cmds: Vec<PathCmd> = {
        let map = PATH_MAP.read();
        match map.get(&src) {
            Some(p) => p.lock().cmds.clone(),
            None => return,
        }
    };
    with_path(dst, |p| p.cmds.extend(src_cmds));
}

pub(crate) unsafe fn path_rect(x: f32, y: f32, w: f32, h: f32) -> i32 {
    let id = create_path();
    with_path(id, |p| {
        p.cmds.push(PathCmd::MoveTo(x, y));
        p.cmds.push(PathCmd::LineTo(x + w, y));
        p.cmds.push(PathCmd::LineTo(x + w, y + h));
        p.cmds.push(PathCmd::LineTo(x, y + h));
        p.cmds.push(PathCmd::Close);
    });
    id
}

pub(crate) unsafe fn path_oval(x: f32, y: f32, w: f32, h: f32) -> i32 {
    const K: f32 = 0.5522847498;
    let id = create_path();
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

pub(crate) unsafe fn path_rounded_rect(x: f32, y: f32, w: f32, h: f32, r: f32) -> i32 {
    const K: f32 = 0.5522847498;
    let id = create_path();
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

pub(crate) unsafe fn path_set_line_dash(
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

pub(crate) fn path_fill(fb_handle: i32, path_handle: i32, color: u32, blend: u8) {
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
        if let Some(path) = build_path_from_cmds(&cmds) {
            let ctm = fb.ctm;
            let aa = fb.antialias;
            // Temporarily take clip_mask to avoid cloning it — avoids O(w*h) allocation.
            // Restored unconditionally below regardless of pixmap_mut success.
            let clip_mask = fb.clip_mask.take();
            if let Some(mut pm) = fb.pixmap_mut() {
                let paint = make_paint(r, g, b, a, bm, aa);
                pm.fill_path(&path, &paint, fill_rule, ctm, clip_mask.as_ref());
            }
            fb.clip_mask = clip_mask;
        }
    });
}

pub(crate) fn path_stroke(fb_handle: i32, path_handle: i32, color: u32, blend: u8) {
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
        if let Some(path) = build_path_from_cmds(&cmds) {
            let ctm = fb.ctm;
            let aa = fb.antialias;
            let clip_mask = fb.clip_mask.take();
            if let Some(mut pm) = fb.pixmap_mut() {
                let paint = make_paint(r, g, b, a, bm, aa);
                let mut stroke = Stroke::default();
                stroke.width = lw;
                stroke.line_cap = map_cap(lcap);
                stroke.line_join = map_join(ljoin);
                if !dash_iv.is_empty() {
                    stroke.dash = StrokeDash::new(dash_iv, dash_ph);
                }
                pm.stroke_path(&path, &paint, &stroke, ctm, clip_mask.as_ref());
            }
            fb.clip_mask = clip_mask;
        }
    });
}

pub(crate) fn path_hit_test(path_handle: i32, x: f32, y: f32) -> i32 {
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

pub(crate) unsafe fn path_get_bounds(
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
        0
    } else {
        -1
    }
}

pub(crate) fn path_add_clip(fb_handle: i32, path_handle: i32) {
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
        let w = fb.w as u32;
        let h = fb.h as u32;
        let ctm = fb.ctm;
        if let Some(path) = build_path_from_cmds(&cmds) {
            let aa = fb.antialias;
            if let Some(existing) = &mut fb.clip_mask {
                existing.intersect_path(&path, fill_rule, aa, ctm);
            } else if let Some(mut mask) = Mask::new(w, h) {
                mask.fill_path(&path, fill_rule, aa, ctm);
                fb.clip_mask = Some(mask);
            }
        }
    });
}
