"""Keyboard shortcuts demo (get_key_commands / key_command).

Demonstrates hardware keyboard shortcut support:
- Override get_key_commands() to register shortcuts
- Override key_command(sender) to handle them
- Call become_first_responder() so the view receives keyboard events

Registered shortcuts:
  Cmd+N        New (increments counter)
  Cmd+Z        Undo (decrements counter)
  Cmd+Shift+Z  Redo (increments counter)
  Up / Down    Select previous / next color
  Esc          Reset

On desktop:
  - Click the view to focus it (become_first_responder)
  - Linux/Windows: use Ctrl instead of Cmd
  - macOS: use ⌘ as usual

Run:
    python examples/key_commands.py
"""

from pytoui import ui

_INPUT_LABELS = {
    ui.KEY_INPUT_UP: "Up",
    ui.KEY_INPUT_DOWN: "Down",
    ui.KEY_INPUT_LEFT: "Left",
    ui.KEY_INPUT_RIGHT: "Right",
    ui.KEY_INPUT_ESC: "Esc",
    ui.KEY_INPUT_RETURN: "Return",
    ui.KEY_INPUT_BACKSPACE: "Backspace",
    ui.KEY_INPUT_TAB: "Tab",
    ui.KEY_INPUT_SPACE: "Space",
    ui.KEY_INPUT_DELETE: "Del",
    ui.KEY_INPUT_HOME: "Home",
    ui.KEY_INPUT_END: "End",
    ui.KEY_INPUT_PAGE_UP: "PgUp",
    ui.KEY_INPUT_PAGE_DOWN: "PgDn",
}
for _i in range(1, 13):
    _INPUT_LABELS[f"f{_i}"] = f"F{_i}"

_MOD_LABELS = {
    ui.KEY_MOD_CMD: "Cmd",
    ui.KEY_MOD_CTRL: "Ctrl",
    ui.KEY_MOD_ALT: "Alt",
    ui.KEY_MOD_SHIFT: "Shift",
}


def _format_shortcut(cmd: dict) -> str:
    """Format a key-command dict as a human-readable shortcut string."""
    mods_str = cmd.get("modifiers", "")
    parts = [
        _MOD_LABELS.get(m.strip(), m.strip().capitalize())
        for m in mods_str.split(",")
        if m.strip()
    ]
    inp = cmd.get("input", "")
    key = _INPUT_LABELS.get(inp, inp.upper() if len(inp) == 1 else inp)
    parts.append(key)
    return "+".join(parts)


_COLORS = [
    ((0.20, 0.55, 1.00, 1.0), "Blue"),
    ((0.25, 0.80, 0.45, 1.0), "Green"),
    ((1.00, 0.35, 0.35, 1.0), "Red"),
    ((1.00, 0.75, 0.20, 1.0), "Yellow"),
    ((0.70, 0.35, 1.00, 1.0), "Purple"),
]

_MAX_LOG = 8


class KeyCommandsView(ui.View):
    def __init__(self):
        self.name = "Key Commands Demo"
        self.background_color = (0.07, 0.07, 0.10, 1.0)
        self.touch_enabled = True

        self._counter = 0
        self._color_idx = 0
        self._log: list[str] = []
        self._focused = False

        # Status label (top)
        self._status = ui.Label()
        self._status.background_color = (0.0, 0.0, 0.0, 0.55)
        self._status.text_color = (0.9, 0.9, 0.9, 1.0)
        self._status.font = ("<system>", 15.0)
        self._status.alignment = ui.ALIGN_CENTER
        self._status.touch_enabled = False
        self.add_subview(self._status)

        # Shortcuts hint label (middle) — built from get_key_commands()
        self._hints = ui.Label()
        self._hints.background_color = (0.10, 0.10, 0.16, 0.85)
        self._hints.text_color = (0.75, 0.75, 0.85, 1.0)
        self._hints.font = ("<monospace>", 13.0)
        self._hints.alignment = ui.ALIGN_LEFT
        self._hints.number_of_lines = 20
        self._hints.touch_enabled = False
        self._hints.text = self._build_shortcuts_text()
        self.add_subview(self._hints)

        # Log label (bottom)
        self._log_label = ui.Label()
        self._log_label.background_color = (0.0, 0.0, 0.0, 0.45)
        self._log_label.text_color = (0.55, 1.0, 0.55, 1.0)
        self._log_label.font = ("<monospace>", 13.0)
        self._log_label.alignment = ui.ALIGN_LEFT
        self._log_label.number_of_lines = _MAX_LOG
        self._log_label.touch_enabled = False
        self.add_subview(self._log_label)

        self._refresh_status()

    # ── Layout ─────────────────────────────────────────────────────────────────

    def layout(self):
        w, h = self.width, self.height
        self._status.frame = (0, 0, w, 44)
        log_h = _MAX_LOG * 18 + 12
        hints_lines = len(self.get_key_commands()) + 4  # header + footer + padding
        hints_h = hints_lines * 18 + 12
        self._hints.frame = (8, 52, w - 16, hints_h)
        self._log_label.frame = (8, h - log_h - 8, w - 16, log_h)

    # ── Touch: grab focus ──────────────────────────────────────────────────────

    def touch_began(self, touch):
        self._focused = self.become_first_responder()
        self.set_needs_display()

    def did_become_first_responder(self):
        self._focused = True
        self.set_needs_display()

    def did_resign_first_responder(self):
        self._focused = False
        self.set_needs_display()

    # ── Keyboard shortcuts ─────────────────────────────────────────────────────

    def get_key_commands(self):
        return [
            {"input": "n", "modifiers": ui.KEY_MOD_CMD, "title": "Increment"},
            {"input": "z", "modifiers": ui.KEY_MOD_CMD, "title": "Decrement"},
            {
                "input": "z",
                "modifiers": f"{ui.KEY_MOD_CMD},{ui.KEY_MOD_SHIFT}",
                "title": "Re-increment",
            },
            {"input": ui.KEY_INPUT_UP, "title": "Previous color"},
            {"input": ui.KEY_INPUT_DOWN, "title": "Next color"},
            {"input": ui.KEY_INPUT_ESC, "title": "Reset"},
        ]

    def key_command(self, sender):
        inp = sender["input"]
        mods = sender.get("modifiers", "")
        title = sender.get("title", inp)

        if inp == "n":
            self._counter += 1
        elif inp == "z" and "shift" in mods:
            self._counter += 1
        elif inp == "z":
            self._counter -= 1
        elif inp == ui.KEY_INPUT_UP:
            self._color_idx = (self._color_idx - 1) % len(_COLORS)
        elif inp == ui.KEY_INPUT_DOWN:
            self._color_idx = (self._color_idx + 1) % len(_COLORS)
        elif inp == ui.KEY_INPUT_ESC:
            self._counter = 0
            self._color_idx = 0

        self._add_log(f"{title}  [{inp!r}  {mods or '—'}]")
        self._refresh_status()

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _build_shortcuts_text(self) -> str:
        lines = ["  Shortcut        Action", "  " + "-" * 30]
        for cmd in self.get_key_commands():
            shortcut = _format_shortcut(cmd)
            title = cmd.get("title", "")
            lines.append(f"  {shortcut:<16} {title}")
        lines.append("")
        lines.append("  (Linux/Win: Ctrl = Cmd)")
        return "\n".join(lines)

    def _add_log(self, entry: str):
        self._log.append(entry)
        if len(self._log) > _MAX_LOG:
            self._log.pop(0)
        self._log_label.text = "\n".join(self._log)

    def _refresh_status(self):
        _, color_name = _COLORS[self._color_idx]
        focus_str = "● focused" if self._focused else "○ click to focus"
        self._status.text = f"counter={self._counter}  color={color_name}  {focus_str}"
        self.set_needs_display()

    # ── Drawing ────────────────────────────────────────────────────────────────

    def draw(self):
        w, h = self.width, self.height
        log_h = _MAX_LOG * 18 + 28
        hints_h = (len(self.get_key_commands()) + 4) * 18 + 12
        area_y = 52 + hints_h + 8
        area_h = h - area_y - log_h

        if area_h < 10:
            return

        # Background for indicator area
        ui.set_color((0.12, 0.12, 0.18, 1.0))
        ui.fill_rect(0, area_y, w, area_h)

        # Color indicator circle
        color, _ = _COLORS[self._color_idx]
        cx, cy = w / 2, area_y + area_h / 2
        r = min(area_h / 2 - 16, 60)

        ui.set_color(color)
        ui.Path.oval(cx - r, cy - r, r * 2, r * 2).fill()

        # Counter text inside circle
        ui.draw_string(
            str(self._counter),
            rect=(cx - r, cy - 16, r * 2, 32),
            font=("<system-bold>", 26.0),
            color=(1, 1, 1, 1),
            alignment=ui.ALIGN_CENTER,
        )

        # Focus ring
        ring = ui.Path.oval(cx - r - 4, cy - r - 4, (r + 4) * 2, (r + 4) * 2)
        ring.line_width = 2.5
        if self._focused:
            ui.set_color((1.0, 1.0, 1.0, 0.7))
        else:
            ui.set_color((1.0, 1.0, 1.0, 0.15))
        ring.stroke()


def main():
    v = KeyCommandsView()
    v.frame = (0, 0, 420, 620)
    v.present()


if __name__ == "__main__":
    main()
