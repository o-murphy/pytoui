"""
Demo2: multiple View.present() windows.

Run: python -m ui.demo2

  "Open Second Window"  — opens one extra window (guard: only one at a time)
  "Spawn Window"        — opens a new window on every click

Each window runs its own runtime + framebuffer, launched from present().
Press ESC or close any window to close it.
"""

import threading
import ui


class SecondView(ui.View):
    def __init__(self):
        self.background_color = (0.1, 0.2, 0.4, 1.0)
        self.name = "Second Window"

        self.label = ui.Label()
        self.label.text = self.name
        self.label.font = ("<system>", 24.0)
        self.label.text_color = "white"
        self.label.alignment = ui.ALIGN_CENTER
        self.add_subview(self.label)

        self.close_btn = ui.Button()
        self.close_btn.title = "Close"
        self.close_btn.background_color = (0.8, 0.2, 0.2, 1.0)
        self.close_btn.corner_radius = 8
        self.close_btn.action = lambda s: self.close()
        self.add_subview(self.close_btn)

    def layout(self):
        self.label.frame = (0, 0, self.width, 60)
        self.label.y = self.height // 2 - 30
        self.close_btn.frame = (self.width // 2 - 60, self.height // 2 + 40, 120, 36)


class MainView(ui.View):
    def __init__(self):
        self.background_color = (0.15, 0.15, 0.15, 1.0)
        self.name = "Demo2 Main"
        self._second_open = False

        self.title = ui.Label()
        self.title.text = "Demo2 — Two Windows"
        self.title.font = ("<system-bold>", 22.0)
        self.title.text_color = "white"
        self.title.alignment = ui.ALIGN_CENTER
        self.add_subview(self.title)

        self._btn = ui.Button()
        self._btn.title = "Open Second Window"
        self._btn.background_color = (0.2, 0.6, 1.0, 1.0)
        self._btn.corner_radius = 10
        self._btn.action = self._open_second
        self.add_subview(self._btn)

        self.spawn_btn = ui.Button()
        self.spawn_btn.title = "Spawn Window"
        self.spawn_btn.background_color = (0.2, 0.7, 0.3, 1.0)
        self.spawn_btn.corner_radius = 10
        self.spawn_btn.action = self._spawn_window
        self.add_subview(self.spawn_btn)
        self._spawn_count = 0

    def layout(self):
        self.title.frame = (0, 20, self.width, 40)
        self._btn.frame = (self.width // 2 - 110, self.height // 2 - 20, 220, 40)
        self.spawn_btn.frame = (self.width // 2 - 110, self.height // 2 + 30, 220, 40)

    def _open_second(self, sender):
        if self._second_open:
            return
        self._second_open = True
        self._btn.title = "Second window is open..."

        def _run():
            v = SecondView()
            v.frame = (0, 0, 400, 300)
            v.present()
            # Window closed
            self._second_open = False
            self._btn.title = "Open Second Window"

        threading.Thread(target=_run, daemon=True).start()

    def _spawn_window(self, sender):
        self._spawn_count += 1
        n = self._spawn_count

        def _run():
            v = SecondView()
            v.name = f"Window #{n}"
            v.frame = (0, 0, 400, 300)
            v.present()

        threading.Thread(target=_run, daemon=True).start()


def main():
    root = MainView()
    root.frame = (0, 0, 600, 400)
    root.present()


if __name__ == "__main__":
    main()
