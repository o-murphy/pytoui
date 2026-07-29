//! Keyboard event → integer code mapping shared by the `ApplicationHandler`.

use winit::event::Modifiers;
use winit::keyboard::{Key, KeyCode, NamedKey, PhysicalKey};

/// Map winit key event fields to an integer code for etype=5 events.
/// Letter/digit keys → lowercase ASCII codepoint (physical_key wins, checked first).
/// Named special keys → codes 1-15 / 1001-1012 (logical_key, checked second).
///
/// Checking physical_key first ensures that modifier combos like Ctrl+J don't get
/// dispatched as Enter (NamedKey::Enter) — they always yield 'j' (KeyCode::KeyJ).
pub(crate) fn key_to_code(logical_key: &Key, physical_key: &PhysicalKey) -> Option<i64> {
    // Physical key for letter/digit positions always wins — modifier- and
    // layout-independent (Ctrl+J stays 'j', Ctrl+H stays 'h', etc.).
    if let PhysicalKey::Code(code) = physical_key {
        match code {
            KeyCode::KeyA => return Some(b'a' as i64),
            KeyCode::KeyB => return Some(b'b' as i64),
            KeyCode::KeyC => return Some(b'c' as i64),
            KeyCode::KeyD => return Some(b'd' as i64),
            KeyCode::KeyE => return Some(b'e' as i64),
            KeyCode::KeyF => return Some(b'f' as i64),
            KeyCode::KeyG => return Some(b'g' as i64),
            KeyCode::KeyH => return Some(b'h' as i64),
            KeyCode::KeyI => return Some(b'i' as i64),
            KeyCode::KeyJ => return Some(b'j' as i64),
            KeyCode::KeyK => return Some(b'k' as i64),
            KeyCode::KeyL => return Some(b'l' as i64),
            KeyCode::KeyM => return Some(b'm' as i64),
            KeyCode::KeyN => return Some(b'n' as i64),
            KeyCode::KeyO => return Some(b'o' as i64),
            KeyCode::KeyP => return Some(b'p' as i64),
            KeyCode::KeyQ => return Some(b'q' as i64),
            KeyCode::KeyR => return Some(b'r' as i64),
            KeyCode::KeyS => return Some(b's' as i64),
            KeyCode::KeyT => return Some(b't' as i64),
            KeyCode::KeyU => return Some(b'u' as i64),
            KeyCode::KeyV => return Some(b'v' as i64),
            KeyCode::KeyW => return Some(b'w' as i64),
            KeyCode::KeyX => return Some(b'x' as i64),
            KeyCode::KeyY => return Some(b'y' as i64),
            KeyCode::KeyZ => return Some(b'z' as i64),
            KeyCode::Digit0 => return Some(b'0' as i64),
            KeyCode::Digit1 => return Some(b'1' as i64),
            KeyCode::Digit2 => return Some(b'2' as i64),
            KeyCode::Digit3 => return Some(b'3' as i64),
            KeyCode::Digit4 => return Some(b'4' as i64),
            KeyCode::Digit5 => return Some(b'5' as i64),
            KeyCode::Digit6 => return Some(b'6' as i64),
            KeyCode::Digit7 => return Some(b'7' as i64),
            KeyCode::Digit8 => return Some(b'8' as i64),
            KeyCode::Digit9 => return Some(b'9' as i64),
            KeyCode::Numpad0 => return Some(b'0' as i64),
            KeyCode::Numpad1 => return Some(b'1' as i64),
            KeyCode::Numpad2 => return Some(b'2' as i64),
            KeyCode::Numpad3 => return Some(b'3' as i64),
            KeyCode::Numpad4 => return Some(b'4' as i64),
            KeyCode::Numpad5 => return Some(b'5' as i64),
            KeyCode::Numpad6 => return Some(b'6' as i64),
            KeyCode::Numpad7 => return Some(b'7' as i64),
            KeyCode::Numpad8 => return Some(b'8' as i64),
            KeyCode::Numpad9 => return Some(b'9' as i64),
            _ => {}
        }
    }

    // Printable ASCII punctuation/symbol keys — use logical_key Character.
    // Punctuation is not remapped by Ctrl (unlike letters which become control chars),
    // and Shift changes the character (Shift+, → '<' on QWERTY), matching SDL behaviour.
    if let Key::Character(ch) = logical_key {
        if let Some(c) = ch.chars().next() {
            if c.is_ascii_graphic() && !c.is_ascii_alphanumeric() {
                return Some(c as i64);
            }
        }
    }

    // Named keys for special positions (arrows, Esc, Enter, Backspace, F-keys, etc.)
    if let Key::Named(named) = logical_key {
        return match named {
            NamedKey::ArrowUp => Some(1),
            NamedKey::ArrowDown => Some(2),
            NamedKey::ArrowLeft => Some(3),
            NamedKey::ArrowRight => Some(4),
            NamedKey::Escape => Some(5),
            NamedKey::Enter => Some(6),
            NamedKey::Backspace => Some(7),
            NamedKey::Tab => Some(8),
            NamedKey::Space => Some(9),
            NamedKey::Delete => Some(10),
            NamedKey::Home => Some(11),
            NamedKey::End => Some(12),
            NamedKey::PageUp => Some(13),
            NamedKey::PageDown => Some(14),
            NamedKey::Insert => Some(15),
            NamedKey::F1 => Some(1001),
            NamedKey::F2 => Some(1002),
            NamedKey::F3 => Some(1003),
            NamedKey::F4 => Some(1004),
            NamedKey::F5 => Some(1005),
            NamedKey::F6 => Some(1006),
            NamedKey::F7 => Some(1007),
            NamedKey::F8 => Some(1008),
            NamedKey::F9 => Some(1009),
            NamedKey::F10 => Some(1010),
            NamedKey::F11 => Some(1011),
            NamedKey::F12 => Some(1012),
            _ => None,
        };
    }

    None
}

/// Encode modifier state as a bitmask: bit0=shift, bit1=ctrl, bit2=alt, bit3=super.
pub(crate) fn mod_flags(modifiers: &Modifiers) -> i64 {
    let s = modifiers.state();
    let mut flags: i64 = 0;
    if s.shift_key() {
        flags |= 1;
    }
    if s.control_key() {
        flags |= 2;
    }
    if s.alt_key() {
        flags |= 4;
    }
    if s.super_key() {
        flags |= 8;
    }
    flags
}
