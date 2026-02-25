use once_cell::sync::Lazy;
use parking_lot::RwLock;
use std::collections::HashMap;

pub(crate) static TRANSFORM_MAP: Lazy<RwLock<HashMap<i32, (f32, f32, f32, f32, f32, f32)>>> =
    Lazy::new(|| RwLock::new(HashMap::new()));
pub(crate) static mut NEXT_TRANSFORM_ID: i32 = 1;

pub(crate) unsafe fn create_transform(a: f32, b: f32, c: f32, d: f32, tx: f32, ty: f32) -> i32 {
    let mut map = TRANSFORM_MAP.write();
    let id = NEXT_TRANSFORM_ID;
    NEXT_TRANSFORM_ID += 1;
    map.insert(id, (a, b, c, d, tx, ty));
    id
}

pub(crate) fn destroy_transform(handle: i32) -> i32 {
    match TRANSFORM_MAP.write().remove(&handle) {
        Some(_) => 0,
        None => -1,
    }
}

pub(crate) unsafe fn transform_rotation(radians: f32) -> i32 {
    let cos_a = radians.cos();
    let sin_a = radians.sin();
    create_transform(cos_a, sin_a, -sin_a, cos_a, 0.0, 0.0)
}

pub(crate) unsafe fn transform_scale(sx: f32, sy: f32) -> i32 {
    create_transform(sx, 0.0, 0.0, sy, 0.0, 0.0)
}

pub(crate) unsafe fn transform_translation(tx: f32, ty: f32) -> i32 {
    create_transform(1.0, 0.0, 0.0, 1.0, tx, ty)
}

pub(crate) unsafe fn transform_concat(handle_a: i32, handle_b: i32) -> i32 {
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
    create_transform(a, b, c, d, tx, ty)
}

pub(crate) unsafe fn transform_invert(handle: i32) -> i32 {
    let (a, b, c, d, tx, ty) = match TRANSFORM_MAP.read().get(&handle) {
        Some(&t) => t,
        None => return -1,
    };
    let det = a * d - b * c;
    if det.abs() < 1e-10 {
        return -1;
    }
    let inv = 1.0 / det;
    create_transform(
        d * inv,
        -b * inv,
        -c * inv,
        a * inv,
        (c * ty - d * tx) * inv,
        (b * tx - a * ty) * inv,
    )
}

pub(crate) unsafe fn transform_get(
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
