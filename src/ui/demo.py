"""
Demo app: python -m ui

Press ESC or close the window to exit.
"""

import ui
from ui._constants import ALIGN_CENTER


WIDTH = 720
HEIGHT = 576


def _make_test_image():
    from PIL import Image as PILImage

    try:
        from pathlib import Path

        pil = PILImage.open(Path("ui/ui_files/ui_switch.png").resolve(), "r").convert(
            "RGBA"
        )
    except OSError:
        # Fallback if image file is missing
        pil = PILImage.new("RGBA", (80, 60))
        for y in range(20):
            for x in range(80):
                pil.putpixel((x, y), (0, 128, 0, 255))
        for y in range(20, 40):
            for x in range(80):
                pil.putpixel((x, y), (0, 255, 255, 255))
        for y in range(40, 60):
            for x in range(80):
                pil.putpixel((x, y), (255, 0, 0, 255))
    w, h = pil.size
    return ui.Image(width=w, height=h, data=pil.tobytes())


class DrawTestView(ui.View):
    """Test widget that exercises CSS colors, GState, fill_rect, and Path."""

    def draw(self):
        colors = ["red", "orange", "yellow", "green", "cyan", "blue", "purple"]
        sq, pad = 24, 4
        for i, name in enumerate(colors):
            ui.set_color(name)
            ui.fill_rect(pad + i * (sq + pad), pad, sq, sq)

        y0 = 40
        ui.set_color("navy")
        ui.fill_rect(pad, y0, 100, 60)
        with ui.GState():
            ui.set_color("lime")
            ui.fill_rect(pad + 10, y0 + 10, 80, 40)
        ui.fill_rect(pad + 110, y0, 20, 60)

        ui.set_color("magenta")
        ui.Path.oval(140, y0, 60, 60).fill()

        ui.set_color("teal")
        ui.Path.rect(pad, y0 + 70, 100, 50).fill()

        ui.set_color("maroon")
        ui.Path.rect(pad + 110, y0 + 70, 100, 50).stroke()

        ui.draw_string(
            "draw_string!",
            rect=(pad, y0 + 130, 220, 20),
            font=("<system>", 14.0),
            color="black",
            alignment=ui.ALIGN_LEFT,
        )


class MainView(ui.View):
    def __init__(self):
        self.background_color = (0.15, 0.15, 0.15, 0.85)
        self.header = ui.View()
        self.header.name = "header"
        self.header.background_color = (0.2, 0.6, 1.0, 1.0)
        self.header.flex = "W"
        self.add_subview(self.header)

        self.title = ui.Label()
        self.title.name = "title"
        self.title.text = "Hello, UI!"
        self.title.font = ("<system>", 20.0)
        self.title.text_color = (1.0, 1.0, 1.0, 1.0)
        self.title.alignment = ui.ALIGN_CENTER
        self.header.add_subview(self.title)

        self.button = ui.Button()
        self.button.title = "Press the button"
        self.button.background_color = "white"
        self.button.action = self.on_button_click
        self.add_subview(self.button)

        self.button2 = ui.Button()
        self.button2.title = "Press the button"
        self.button2.border_color = self.button2.background_color
        self.button2.border_width = 2
        self.button2.background_color = (0.1, 0.4, 0.8, 0.5)
        self.button2.corner_radius = 8
        self.button2.action = self.on_button2_click
        self.add_subview(self.button2)

        self.switch = ui.Switch()
        self.switch.action = self.on_switch_toggle
        self.switch.value = True
        self.add_subview(self.switch)

        self.activity = ui.ActivityIndicator()
        self.add_subview(self.activity)

        self.segmented = ui.SegmentedControl()
        self.segmented.name = "segmented"
        self.segmented.segments = ["Var1", "Var2", "Var3"]
        self.segmented.selected_index = 2
        self.segmented.action = self.on_segmented_change
        self.add_subview(self.segmented)

        self.activity.start()
        self.on_segmented_change(self.segmented)

        self.slider = ui.Slider()
        self.slider.action = self.on_slider_change
        self.add_subview(self.slider)

        self.slider_label = ui.Label()
        self.slider_label.text_color = "white"
        self.slider_label.alignment = ALIGN_CENTER
        self.slider_label.text = str(self.slider.value)
        self.add_subview(self.slider_label)

        self.box = ui.View()
        self.box.name = "box"
        self.box.background_color = (1.0, 0.3, 0.3, 1.0)
        self.box.border_color = (1.0, 1.0, 1.0, 1.0)
        self.box.border_width = 2
        self.add_subview(self.box)

        self.inner = ui.View()
        self.inner.name = "inner"
        self.inner.background_color = (1.0, 1.0, 0.2, 0.5)
        self.inner.corner_radius = 10
        self.inner.border_color = (1.0, 1.0, 1.0, 1.0)
        self.box.add_subview(self.inner)

        self.canvas = DrawTestView()
        self.canvas.name = "canvas"
        self.canvas.background_color = "white"
        self.canvas.border_color = "gray"
        self.canvas.border_width = 1
        self.add_subview(self.canvas)

        self.img_view = ui.ImageView()
        self.img_view.name = "img_view"
        self.img_view.background_color = "lightgray"
        self.img_view.border_color = "darkgray"
        self.img_view.image = _make_test_image()
        self.add_subview(self.img_view)

        self.sidebar = ui.View()
        self.sidebar.name = "sidebar"
        self.sidebar.background_color = (0.2, 0.8, 0.4, 0.5)
        self.sidebar.flex = "LH"
        self.add_subview(self.sidebar)

        self.clicks_count = 0
        self.button_toggled = False

    def layout(self):
        self.header.frame = (0, 0, self.width, 32)
        self.title.frame = (0, 0, self.width, 32)
        self.button.x, self.button.y, self.button.width = 100, 100, 150
        self.button2.x, self.button2.y, self.button2.width = 100, 150, 100
        self.switch.x, self.switch.y = 100, 200
        self.activity.frame = (200, 200, 30, 30)
        self.segmented.x, self.segmented.y, self.segmented.width = 100, 250, 200
        self.segmented.bounds = (0, 0, self.segmented.width, self.segmented.height)
        self.slider.x, self.slider.y, self.slider.width = 100, 300, 200
        self.slider_label.x, self.slider_label.y, self.slider_label.width = (
            100,
            350,
            200,
        )
        self.box.frame = (100, 400, 80, 80)
        self.inner.frame = (10, 10, 30, 30)
        self.canvas.frame = (400, 100, 240, 200)
        self.img_view.frame = (400, 350, 200, 160)
        self.sidebar.frame = (self.width - 60, 50, 50, self.height - 60)

    def on_button2_click(self, sender: ui.Button):
        print(f"button clicked: {sender.name}")
        self.clicks_count += 1
        sender.title = str(self.clicks_count)

    def on_button_click(self, sender: ui.Button):
        print(f"button clicked: {sender.name}")
        self.button_toggled = not self.button_toggled
        sender.title = "Disable" if self.button_toggled else "Enable"

    def on_switch_toggle(self, sender: ui.Switch):
        print(f"Switch: {sender.value}")
        if sender.value:
            self.activity.start()
        else:
            self.activity.stop()

    def on_segmented_change(self, sender: ui.SegmentedControl):
        index = sender.selected_index
        print(f"Segmented: {sender.segments[index]} ({index})")
        if 2 >= index >= 0:
            self.activity.style = index

    def on_slider_change(self, sender: ui.Slider):
        self.slider_label.text = f"{sender.value:.2f}"


def main():
    root = MainView()
    root.name = "Demo App"
    root.frame = (0, 0, WIDTH, HEIGHT)
    root.present()


if __name__ == "__main__":
    main()
