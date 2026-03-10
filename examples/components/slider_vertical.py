from pytoui.ui import ALIGN_CENTER, Label, View
from pytoui.ui.custom import VerticalSlider


def main():
    value = 0.3

    label = Label()
    label.text = f"{value:.2f}"
    label.frame = (0, 0, 100, 50)
    label.center = (300, 300)
    label.flex = "W"
    label.alignment = ALIGN_CENTER
    label.text_color = "black"
    label.background_color = "white"
    label.corner_radius = 16

    def action(sender: VerticalSlider):
        label.text = f"{sender.value:.2f}"

    slider = VerticalSlider()
    slider.value = value
    slider.frame = (0, 0, 50, 300)
    slider.center = (200, 300)
    slider.flex = "W"
    slider.background_color = "white"
    slider.corner_radius = 16
    slider.action = action

    root = View()
    root.frame = (0, 0, 400, 600)
    root.background_color = "black"
    root.name = f"Demo: {slider.__class__.name}"
    root.add_subview(slider)
    root.add_subview(label)
    root.present("fullscreen")


if __name__ == "__main__":
    main()
