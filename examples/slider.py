"""
Demo app: python -m ui

Press ESC or close the window to exit.
"""

from pytoui import ui


def main():
    value = 0.3

    label = ui.Label()
    label.text = f"{value:.2f}"
    label.frame = (0, 0, 100, 50)
    label.center = (200, 400)
    label.flex = "W"
    label.alignment = ui.ALIGN_CENTER
    label.text_color = "black"
    label.background_color = "white"
    label.corner_radius = 16

    def action(sender: ui.Slider):
        label.text = f"{sender.value:.2f}"

    slider = ui.Slider()
    slider.value = 0.3
    slider.frame = (0, 0, 300, 50)
    slider.center = (200, 300)
    slider.flex = "W"
    slider.background_color = "white"
    slider.corner_radius = 16
    slider.action = action

    root = ui.View()
    root.frame = (0, 0, 400, 600)
    root.background_color = "black"
    root.name = f"Demo: {slider.__class__.name}"
    root.add_subview(slider)
    root.add_subview(label)
    root.present("fullscreen")


if __name__ == "__main__":
    main()
