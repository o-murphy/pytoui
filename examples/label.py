"""Demo app: python -m ui

Press ESC or close the window to exit.
"""

from pytoui import ui


def main():

    label = ui.Label()
    label.text = "Sample text"
    label.frame = (0, 0, 300, 100)
    label.center = (200, 300)
    label.flex = "WH"
    label.font = ("<system>", 20)
    label.alignment = ui.ALIGN_CENTER
    label.background_color = "white"
    label.text_color = "black"
    label.corner_radius = 16

    root = ui.View()
    root.frame = (0, 0, 400, 600)
    root.name = f"Demo: {label.__class__.name}"
    root.add_subview(label)
    root.present("fullscreen")


if __name__ == "__main__":
    main()
