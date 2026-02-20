// --- Helpers ---
use std::ffi::CStr;
use std::os::raw::c_char;
use tiny_skia::{BlendMode, LineCap, LineJoin};

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
