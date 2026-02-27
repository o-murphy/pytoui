use crate::font::{get_default_font, with_font};
use crate::framebuffer::{with_fb, FrameBuffer};
use crate::helpers::{hex_to_rgba, parse_c_str};
use std::os::raw::c_char;

// --- Text alignment constants (match Pythonista) ---
pub(crate) const ALIGN_LEFT: u32 = 0;
pub(crate) const ALIGN_CENTER: u32 = 1;
pub(crate) const ALIGN_RIGHT: u32 = 2;
pub(crate) const ALIGN_JUSTIFIED: u32 = 3;
pub(crate) const ALIGN_NATURAL: u32 = 4;

// --- Line break modes ---
pub(crate) const LB_WORD_WRAP: u32 = 0;
pub(crate) const LB_CHAR_WRAP: u32 = 1;
pub(crate) const LB_CLIP: u32 = 2;
pub(crate) const LB_TRUNCATE_HEAD: u32 = 3;
pub(crate) const LB_TRUNCATE_TAIL: u32 = 4;
pub(crate) const LB_TRUNCATE_MIDDLE: u32 = 5;

pub(crate) fn calculate_anchor_pos(
    anchor: u32,
    base_x: f32,
    base_y: f32,
    width: f32,
    height: f32,
    ascent: f32,
) -> (f32, f32) {
    let left = (anchor & 0b0100) != 0;
    let right = (anchor & 0b1000) != 0;
    let x = if left && !right {
        base_x
    } else if right && !left {
        base_x - width
    } else {
        base_x - width / 2.0
    };

    let top = (anchor & 0b0001) != 0;
    let bottom = (anchor & 0b0010) != 0;
    let y = if top && !bottom {
        base_y + ascent
    } else if bottom && !top {
        base_y + ascent - height
    } else {
        base_y + (ascent - height / 2.0)
    };
    (x, y)
}

pub(crate) fn get_text_layout(
    font: &fontdue::Font,
    text: &str,
    size: f32,
    spacing: f32,
) -> (f32, f32, f32) {
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

// --- Standalone text layout helpers (no &self dependency) ---

pub(crate) fn measure_text_width(font: &fontdue::Font, text: &str, size: f32) -> f32 {
    let mut width = 0.0;
    for c in text.chars() {
        if !c.is_control() {
            width += font.metrics(c, size).advance_width;
        }
    }
    width
}

pub(crate) fn layout_text(
    font: &fontdue::Font,
    text: &str,
    max_width: f32,
    size: f32,
    mode: u32,
) -> Vec<String> {
    if max_width <= 0.0 {
        return text.split('\n').map(|s| s.to_string()).collect();
    }

    match mode {
        LB_CHAR_WRAP => wrap_chars(font, text, max_width, size),
        LB_WORD_WRAP => wrap_words(font, text, max_width, size),
        LB_TRUNCATE_HEAD => vec![truncate_head(font, text, max_width, size)],
        LB_TRUNCATE_TAIL => vec![truncate_tail(font, text, max_width, size)],
        LB_TRUNCATE_MIDDLE => vec![truncate_middle(font, text, max_width, size)],
        LB_CLIP => vec![clip_text(font, text, max_width, size)],
        _ => text.split('\n').map(|s| s.to_string()).collect(),
    }
}

fn truncate_head(font: &fontdue::Font, text: &str, max_width: f32, size: f32) -> String {
    let ellipsis = "\u{2026}";
    let ellipsis_width = measure_text_width(font, ellipsis, size);

    if measure_text_width(font, text, size) <= max_width {
        return text.to_string();
    }

    for (i, _) in text.char_indices() {
        let slice = &text[i..];
        if measure_text_width(font, slice, size) + ellipsis_width <= max_width {
            return format!("{}{}", ellipsis, slice);
        }
    }
    ellipsis.to_string()
}

fn truncate_tail(font: &fontdue::Font, text: &str, max_width: f32, size: f32) -> String {
    let ellipsis = "\u{2026}";
    let ellipsis_width = measure_text_width(font, ellipsis, size);

    if measure_text_width(font, text, size) <= max_width {
        return text.to_string();
    }

    let mut positions: Vec<usize> = text.char_indices().map(|(i, _)| i).collect();
    positions.push(text.len());
    for i in positions.into_iter().rev() {
        let slice = &text[..i];
        if measure_text_width(font, slice, size) + ellipsis_width <= max_width {
            return format!("{}{}", slice, ellipsis);
        }
    }
    ellipsis.to_string()
}

fn truncate_middle(font: &fontdue::Font, text: &str, max_width: f32, size: f32) -> String {
    let ellipsis = "\u{2026}";

    if measure_text_width(font, text, size) <= max_width {
        return text.to_string();
    }

    // Collect char-boundary byte positions for safe slicing
    let boundaries: Vec<usize> = text
        .char_indices()
        .map(|(i, _)| i)
        .chain(std::iter::once(text.len()))
        .collect();
    let num_chars = boundaries.len() - 1;

    for cut in 1..num_chars {
        let left_chars = (num_chars / 2).saturating_sub((cut + 1) / 2);
        let right_chars = num_chars / 2 + cut / 2;

        if right_chars >= num_chars {
            continue;
        }

        let left = &text[..boundaries[left_chars]];
        let right = &text[boundaries[right_chars]..];
        let candidate = format!("{}{}{}", left, ellipsis, right);

        if measure_text_width(font, &candidate, size) <= max_width {
            return candidate;
        }
    }
    ellipsis.to_string()
}

fn clip_text(font: &fontdue::Font, text: &str, max_width: f32, size: f32) -> String {
    let mut result = String::new();
    let mut current_width = 0.0;

    for c in text.chars() {
        if c.is_control() {
            continue;
        }
        let char_width = font.metrics(c, size).advance_width;
        if current_width + char_width <= max_width {
            result.push(c);
            current_width += char_width;
        } else {
            break;
        }
    }
    result
}

fn wrap_words(font: &fontdue::Font, text: &str, max_width: f32, size: f32) -> Vec<String> {
    let mut lines = Vec::new();
    let mut current_line = String::new();
    let mut current_width = 0.0;

    let words: Vec<&str> = text
        .split_inclusive('\n')
        .flat_map(|part| {
            if part.ends_with('\n') {
                vec![&part[..part.len() - 1], "\n"]
            } else {
                vec![part]
            }
        })
        .collect();

    for word in words {
        if word == "\n" {
            if !current_line.is_empty() {
                lines.push(current_line);
                current_line = String::new();
                current_width = 0.0;
            } else {
                lines.push(String::new());
            }
            continue;
        }

        let word_width = measure_text_width(font, word, size);

        if current_line.is_empty() {
            current_line = word.to_string();
            current_width = word_width;
        } else {
            let space_width = measure_text_width(font, " ", size);
            let test_width = current_width + space_width + word_width;

            if test_width <= max_width {
                current_line.push(' ');
                current_line.push_str(word);
                current_width = test_width;
            } else {
                lines.push(current_line);
                current_line = word.to_string();
                current_width = word_width;
            }
        }
    }

    if !current_line.is_empty() {
        lines.push(current_line);
    }

    lines
}

fn wrap_chars(font: &fontdue::Font, text: &str, max_width: f32, size: f32) -> Vec<String> {
    let mut lines = Vec::new();
    let mut current_line = String::new();
    let mut current_width = 0.0;

    for c in text.chars() {
        if c == '\n' {
            if !current_line.is_empty() {
                lines.push(current_line);
                current_line = String::new();
                current_width = 0.0;
            } else {
                lines.push(String::new());
            }
            continue;
        }

        if c.is_control() {
            continue;
        }

        let char_width = font.metrics(c, size).advance_width;

        if current_line.is_empty() || current_width + char_width <= max_width {
            current_line.push(c);
            current_width += char_width;
        } else {
            lines.push(current_line);
            current_line = c.to_string();
            current_width = char_width;
        }
    }

    if !current_line.is_empty() {
        lines.push(current_line);
    }

    lines
}

// --- FrameBuffer impl methods that rely on the standalone helpers ---

impl FrameBuffer {
    pub(crate) fn draw_text(
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

    pub(crate) fn draw_text_anchored(
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

    /// CoreGraphics-compatible text drawing
    pub(crate) fn draw_string_core_graphics(
        &mut self,
        font: &fontdue::Font,
        text: &str,
        rect: (f32, f32, f32, f32),
        size: f32,
        color: (u8, u8, u8, u8),
        alignment: u32,
        line_break_mode: u32,
    ) {
        let (r, g, b, a) = color;
        let (rect_x, rect_y, rect_w, rect_h) = rect;

        let line_metrics = match font.horizontal_line_metrics(size) {
            Some(m) => m,
            None => return,
        };
        let line_height = line_metrics.ascent - line_metrics.descent + line_metrics.line_gap;
        let ascent = line_metrics.ascent;

        let paragraphs: Vec<&str> = text.split('\n').collect();
        let mut all_lines = Vec::new();

        for paragraph in paragraphs {
            if paragraph.is_empty() {
                all_lines.push(String::new());
                continue;
            }

            let lines = layout_text(font, paragraph, rect_w, size, line_break_mode);
            all_lines.extend(lines);
        }

        if all_lines.is_empty() {
            return;
        }

        let _total_height = line_height * all_lines.len() as f32;

        let max_lines = (rect_h / line_height).floor() as usize;
        let visible_lines: Vec<String> = if all_lines.len() > max_lines && max_lines > 0 {
            match line_break_mode {
                LB_TRUNCATE_HEAD => {
                    let mut result = Vec::new();
                    result.push(truncate_head(
                        font,
                        &all_lines[all_lines.len() - 1],
                        rect_w,
                        size,
                    ));
                    result
                }
                LB_TRUNCATE_MIDDLE => {
                    vec![truncate_tail(font, &all_lines[max_lines - 1], rect_w, size)]
                }
                LB_TRUNCATE_TAIL | _ => {
                    let mut result = all_lines[..max_lines].to_vec();
                    if all_lines.len() > max_lines {
                        result[max_lines - 1] =
                            truncate_tail(font, &result[max_lines - 1], rect_w, size);
                    }
                    result
                }
            }
        } else {
            all_lines
        };

        let start_y = rect_y + ascent;

        for (i, line) in visible_lines.iter().enumerate() {
            if line.is_empty() {
                continue;
            }

            let mut line_width = 0.0;
            for c in line.chars() {
                if !c.is_control() {
                    line_width += font.metrics(c, size).advance_width;
                }
            }

            let start_x = match alignment {
                ALIGN_RIGHT => rect_x + rect_w - line_width,
                ALIGN_CENTER => rect_x + (rect_w - line_width) / 2.0,
                ALIGN_JUSTIFIED if i < visible_lines.len() - 1 => rect_x,
                ALIGN_JUSTIFIED | ALIGN_NATURAL | ALIGN_LEFT => rect_x,
                _ => rect_x,
            };

            let mut curr_x = start_x;
            for c in line.chars() {
                if c.is_control() {
                    continue;
                }

                let (metrics, bitmap) = font.rasterize(c, size);

                let draw_x = curr_x + metrics.xmin as f32;
                let draw_y = start_y + (i as f32 * line_height)
                    - metrics.height as f32
                    - metrics.ymin as f32;

                for row in 0..metrics.height {
                    for col in 0..metrics.width {
                        let coverage = bitmap[row * metrics.width + col];
                        if coverage == 0 {
                            continue;
                        }

                        let pixel_x = draw_x as i32 + col as i32;
                        let pixel_y = draw_y as i32 + row as i32;

                        if pixel_x >= 0 && pixel_x < self.w && pixel_y >= 0 && pixel_y < self.h {
                            if self.antialias {
                                let pixel_a = ((a as u16 * coverage as u16) / 255) as u8;
                                self.set_pixel_over(pixel_x, pixel_y, r, g, b, pixel_a);
                            } else if coverage >= 128 {
                                self.set_pixel_over(pixel_x, pixel_y, r, g, b, a);
                            }
                        }
                    }
                }

                curr_x += metrics.advance_width;
            }
        }
    }
}

// --- C-export logic helpers ---

pub(crate) unsafe fn draw_text_c(
    fb_handle: i32,
    mut font_handle: i32,
    size: f32,
    text_ptr: *const c_char,
    x: f32,
    y: f32,
    anchor: u32,
    color: u32,
    spacing: f32,
) -> i32 {
    let input_text = match parse_c_str(text_ptr) {
        Some(s) => s,
        None => return 0,
    };
    let rgba = hex_to_rgba(color);
    if font_handle < 1 {
        font_handle = get_default_font();
    }
    with_font(font_handle, |font| {
        with_fb(fb_handle, |fb| {
            fb.draw_text_anchored(font, input_text, size, x, y, anchor, rgba, spacing);
            0
        })
    })
}

pub(crate) unsafe fn measure_text_c(
    font_handle: i32,
    size: f32,
    text_ptr: *const c_char,
    spacing: f32,
) -> i32 {
    let input_text = match parse_c_str(text_ptr) {
        Some(s) => s,
        None => return 0,
    };
    with_font(font_handle, |font| {
        let (w, _, _) = get_text_layout(font, input_text, size, spacing);
        w.round() as i32
    })
}

pub(crate) unsafe fn get_text_metrics_c(
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

pub(crate) fn get_text_height_c(font_handle: i32, size: f32) -> i32 {
    with_font(font_handle, |font| {
        font.horizontal_line_metrics(size)
            .map(|m| (m.ascent - m.descent + m.line_gap).round() as i32)
            .unwrap_or(-1)
    })
}

pub(crate) unsafe fn draw_string_cg(
    fb_handle: i32,
    font_handle: i32,
    text_ptr: *const c_char,
    x: f32,
    y: f32,
    w: f32,
    h: f32,
    size: f32,
    color: u32,
    alignment: u32,
    line_break_mode: u32,
) -> i32 {
    let input_text = match parse_c_str(text_ptr) {
        Some(s) => s,
        None => return 0,
    };
    let rgba = hex_to_rgba(color);

    with_font(font_handle, |font| {
        with_fb(fb_handle, |fb| {
            fb.draw_string_core_graphics(
                font,
                input_text,
                (x, y, w, h),
                size,
                rgba,
                alignment,
                line_break_mode,
            );
            0
        })
    })
}

pub(crate) unsafe fn measure_string_cg(
    font_handle: i32,
    text_ptr: *const c_char,
    max_width: f32,
    size: f32,
    line_break_mode: u32,
    out_width: *mut f32,
    out_height: *mut f32,
) -> i32 {
    let input_text = match parse_c_str(text_ptr) {
        Some(s) => s,
        None => return -1,
    };

    with_font(font_handle, |font| {
        let line_metrics = match font.horizontal_line_metrics(size) {
            Some(m) => m,
            None => return -1,
        };
        let line_height = line_metrics.ascent - line_metrics.descent + line_metrics.line_gap;

        let lines = layout_text(font, input_text, max_width, size, line_break_mode);

        if lines.is_empty() {
            *out_width = 0.0;
            *out_height = 0.0;
            return 0;
        }

        let mut max_line_width = 0.0f32;
        for line in &lines {
            let line_width = measure_text_width(font, line, size);
            if line_width > max_line_width {
                max_line_width = line_width;
            }
        }

        let total_height = line_height * lines.len() as f32;

        *out_width = max_line_width;
        *out_height = total_height;
        0
    })
}
