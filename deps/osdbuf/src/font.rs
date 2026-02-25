use fontdue::{Font, FontSettings};
use once_cell::sync::Lazy;
use parking_lot::RwLock;
use std::collections::HashMap;
use std::ffi::CStr;
use std::os::raw::{c_char, c_int, c_uchar};
use std::slice;
use std::sync::Arc;

pub(crate) static FONT_MAP: Lazy<RwLock<HashMap<i32, Arc<Font>>>> =
    Lazy::new(|| RwLock::new(HashMap::new()));
pub(crate) static mut NEXT_FONT_ID: i32 = 1;

pub(crate) fn with_font<F, R>(handle: i32, f: F) -> R
where
    F: FnOnce(&Font) -> R,
    R: Default,
{
    let map = FONT_MAP.read();
    if let Some(font) = map.get(&handle) {
        f(font)
    } else {
        R::default()
    }
}

pub(crate) unsafe fn register_font(data: *const c_uchar, len: c_int) -> i32 {
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

pub(crate) unsafe fn load_font(path_ptr: *const c_char) -> i32 {
    if let Ok(p) = CStr::from_ptr(path_ptr).to_str() {
        if let Ok(data) = std::fs::read(p) {
            return register_font(data.as_ptr(), data.len() as i32);
        }
    }
    -1
}

pub(crate) fn unload_font(handle: i32) -> i32 {
    let mut map = FONT_MAP.write();
    if map.remove(&handle).is_some() {
        0
    } else {
        -1
    }
}

pub(crate) fn get_default_font() -> i32 {
    let map = FONT_MAP.read();
    if map.contains_key(&1) {
        1
    } else {
        -1
    }
}

pub(crate) fn get_font_count() -> i32 {
    FONT_MAP.read().len() as i32
}

pub(crate) unsafe fn get_font_ids(buf: *mut c_int, max_count: c_int) -> i32 {
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
