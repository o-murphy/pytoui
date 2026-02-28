use std::os::raw::{c_char, c_int, c_uchar};

use framebuffer::with_fb;
use helpers::{hex_to_rgba, map_blend_mode};
use path::with_path;

mod font;
mod framebuffer;
mod helpers;
mod path;
mod text;
mod transform;

// --- Font management ---

#[no_mangle]
pub unsafe extern "C" fn RegisterFont(data: *const c_uchar, len: c_int) -> i32 {
    font::register_font(data, len)
}

#[no_mangle]
pub unsafe extern "C" fn LoadFont(path: *const c_char) -> i32 {
    font::load_font(path)
}

#[no_mangle]
pub extern "C" fn UnloadFont(handle: i32) -> i32 {
    font::unload_font(handle)
}

#[no_mangle]
pub extern "C" fn GetDefaultFont() -> i32 {
    font::get_default_font()
}

#[no_mangle]
pub extern "C" fn GetFontCount() -> i32 {
    font::get_font_count()
}

#[no_mangle]
pub unsafe extern "C" fn GetFontIDs(buf: *mut c_int, max_count: c_int) -> i32 {
    font::get_font_ids(buf, max_count)
}

// --- Framebuffer ---

#[no_mangle]
pub unsafe extern "C" fn CreateFrameBuffer(
    data: *mut c_uchar,
    width: c_int,
    height: c_int,
) -> c_int {
    framebuffer::create_framebuffer(data, width, height)
}

#[no_mangle]
pub extern "C" fn DestroyFrameBuffer(handle: c_int) {
    framebuffer::destroy_framebuffer(handle)
}

// --- Drawing exports ---

#[no_mangle]
pub extern "C" fn Fill(handle: i32, color: u32) {
    let (r, g, b, a) = hex_to_rgba(color);
    with_fb(handle, |fb| fb.fill_solid(r, g, b, a));
}

#[no_mangle]
pub extern "C" fn FillOver(handle: i32, color: u32) {
    framebuffer::fill_over(handle, color)
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
        fb.stroke_rounded_rect(x, y, w, h, radius, bw, join, r, g, b, a, bm)
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
        fb.stroke_ellipse(cx, cy, rx, ry, width, r, g, b, a, bm)
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
    with_fb(handle, |fb| fb.fill_rect(x, y, w, h, r, g, b, a, bm));
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
        fb.blit(src_pixels, src_w, src_h, dst_x, dst_y, blend != 0)
    });
}

#[no_mangle]
pub unsafe extern "C" fn BlitRGBAScaled(
    handle: i32,
    src_data: *const u8,
    src_w: i32,
    src_h: i32,
    dst_x: i32,
    dst_y: i32,
    dst_w: i32,
    dst_h: i32,
    blend: i32,
) {
    let size = (src_w * src_h * 4) as usize;
    let src_pixels = std::slice::from_raw_parts(src_data, size);
    with_fb(handle, |fb| {
        fb.blit_scaled(src_pixels, src_w, src_h, dst_x, dst_y, dst_w, dst_h, blend != 0)
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

#[no_mangle]
pub extern "C" fn SetCTM(handle: i32, a: f32, b: f32, c: f32, d: f32, tx: f32, ty: f32) {
    use tiny_skia::Transform;
    with_fb(handle, |fb| {
        fb.ctm = Transform::from_row(a, b, c, d, tx, ty);
    });
}

#[no_mangle]
pub extern "C" fn ApplyYUV422Compensation(handle: i32, x: i32, y: i32, w: i32, h: i32) {
    with_fb(handle, |fb| fb.apply_yuv422_compensation(x, y, w, h));
}

// --- Text rendering ---

#[no_mangle]
pub unsafe extern "C" fn DrawText(
    handle: i32,
    font_handle: i32,
    size: f32,
    text: *const c_char,
    x: f32,
    y: f32,
    anchor: u32,
    color: u32,
    spacing: f32,
) -> i32 {
    text::draw_text_c(
        handle,
        font_handle,
        size,
        text,
        x,
        y,
        anchor,
        color,
        spacing,
    )
}

#[no_mangle]
pub unsafe extern "C" fn MeasureText(
    font_handle: i32,
    size: f32,
    text: *const c_char,
    spacing: f32,
) -> i32 {
    text::measure_text_c(font_handle, size, text, spacing)
}

#[no_mangle]
pub unsafe extern "C" fn GetTextMetrics(
    font_handle: i32,
    size: f32,
    ascent: *mut i32,
    descent: *mut i32,
    height: *mut i32,
) -> i32 {
    text::get_text_metrics_c(font_handle, size, ascent, descent, height)
}

#[no_mangle]
pub extern "C" fn GetTextHeight(font_handle: i32, size: f32) -> i32 {
    text::get_text_height_c(font_handle, size)
}

// --- GState ---

#[no_mangle]
pub extern "C" fn GStatePush(handle: i32) {
    framebuffer::gstate_push(handle)
}

#[no_mangle]
pub extern "C" fn GStatePop(handle: i32) {
    framebuffer::gstate_pop(handle)
}

// --- Transforms ---

#[no_mangle]
pub unsafe extern "C" fn CreateTransform(a: f32, b: f32, c: f32, d: f32, tx: f32, ty: f32) -> i32 {
    transform::create_transform(a, b, c, d, tx, ty)
}

#[no_mangle]
pub extern "C" fn DestroyTransform(handle: i32) -> i32 {
    transform::destroy_transform(handle)
}

#[no_mangle]
pub unsafe extern "C" fn TransformRotation(radians: f32) -> i32 {
    transform::transform_rotation(radians)
}

#[no_mangle]
pub unsafe extern "C" fn TransformScale(sx: f32, sy: f32) -> i32 {
    transform::transform_scale(sx, sy)
}

#[no_mangle]
pub unsafe extern "C" fn TransformTranslation(tx: f32, ty: f32) -> i32 {
    transform::transform_translation(tx, ty)
}

#[no_mangle]
pub unsafe extern "C" fn TransformConcat(handle_a: i32, handle_b: i32) -> i32 {
    transform::transform_concat(handle_a, handle_b)
}

#[no_mangle]
pub unsafe extern "C" fn TransformInvert(handle: i32) -> i32 {
    transform::transform_invert(handle)
}

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
    transform::transform_get(handle, a, b, c, d, tx, ty)
}

// --- Path ---

#[no_mangle]
pub unsafe extern "C" fn CreatePath() -> i32 {
    path::create_path()
}

#[no_mangle]
pub extern "C" fn DestroyPath(handle: i32) -> i32 {
    path::destroy_path(handle)
}

#[no_mangle]
pub extern "C" fn PathMoveTo(handle: i32, x: f32, y: f32) {
    with_path(handle, |p| p.cmds.push(path::PathCmd::MoveTo(x, y)));
}

#[no_mangle]
pub extern "C" fn PathLineTo(handle: i32, x: f32, y: f32) {
    with_path(handle, |p| p.cmds.push(path::PathCmd::LineTo(x, y)));
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
        p.cmds
            .push(path::PathCmd::CubicTo(cp1x, cp1y, cp2x, cp2y, x, y))
    });
}

#[no_mangle]
pub extern "C" fn PathAddQuadCurve(handle: i32, cpx: f32, cpy: f32, x: f32, y: f32) {
    with_path(handle, |p| {
        p.cmds.push(path::PathCmd::QuadTo(cpx, cpy, x, y))
    });
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
        p.cmds.push(path::PathCmd::Arc {
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
    with_path(handle, |p| p.cmds.push(path::PathCmd::Close));
}

#[no_mangle]
pub extern "C" fn PathAppend(dst: i32, src: i32) {
    path::path_append(dst, src)
}

#[no_mangle]
pub unsafe extern "C" fn PathRect(x: f32, y: f32, w: f32, h: f32) -> i32 {
    path::path_rect(x, y, w, h)
}

#[no_mangle]
pub unsafe extern "C" fn PathOval(x: f32, y: f32, w: f32, h: f32) -> i32 {
    path::path_oval(x, y, w, h)
}

#[no_mangle]
pub unsafe extern "C" fn PathRoundedRect(x: f32, y: f32, w: f32, h: f32, r: f32) -> i32 {
    path::path_rounded_rect(x, y, w, h, r)
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
    path::path_set_line_dash(handle, intervals, count, phase)
}

#[no_mangle]
pub extern "C" fn PathFill(fb_handle: i32, path_handle: i32, color: u32, blend: u8) {
    path::path_fill(fb_handle, path_handle, color, blend)
}

#[no_mangle]
pub extern "C" fn PathSetEoFillRule(handle: i32, value: i32) {
    with_path(handle, |p| p.eo_fill_rule = value != 0);
}

#[no_mangle]
pub extern "C" fn PathStroke(fb_handle: i32, path_handle: i32, color: u32, blend: u8) {
    path::path_stroke(fb_handle, path_handle, color, blend)
}

#[no_mangle]
pub extern "C" fn PathHitTest(path_handle: i32, x: f32, y: f32) -> i32 {
    path::path_hit_test(path_handle, x, y)
}

#[no_mangle]
pub unsafe extern "C" fn PathGetBounds(
    path_handle: i32,
    x_out: *mut f32,
    y_out: *mut f32,
    w_out: *mut f32,
    h_out: *mut f32,
) -> i32 {
    path::path_get_bounds(path_handle, x_out, y_out, w_out, h_out)
}

#[no_mangle]
pub extern "C" fn PathAddClip(fb_handle: i32, path_handle: i32) {
    path::path_add_clip(fb_handle, path_handle)
}

#[no_mangle]
pub extern "C" fn DrawCheckerBoard(fb_handle: i32, size: i32) {
    with_fb(fb_handle, |fb| fb.draw_checkerboard(size));
}

#[no_mangle]
pub unsafe extern "C" fn DrawStringCoreGraphics(
    fb_handle: i32,
    font_handle: i32,
    text: *const c_char,
    x: f32,
    y: f32,
    w: f32,
    h: f32,
    size: f32,
    color: u32,
    alignment: u32,
    line_break_mode: u32,
) -> i32 {
    text::draw_string_cg(
        fb_handle,
        font_handle,
        text,
        x,
        y,
        w,
        h,
        size,
        color,
        alignment,
        line_break_mode,
    )
}

#[no_mangle]
pub unsafe extern "C" fn MeasureStringCoreGraphics(
    font_handle: i32,
    text: *const c_char,
    max_width: f32,
    size: f32,
    line_break_mode: u32,
    out_width: *mut f32,
    out_height: *mut f32,
) -> i32 {
    text::measure_string_cg(
        font_handle,
        text,
        max_width,
        size,
        line_break_mode,
        out_width,
        out_height,
    )
}
