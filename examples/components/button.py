"""Demo app: python -m ui

Press ESC or close the window to exit.
"""

from pytoui import ui


def main():
    counter = 0

    def action(sender: ui.Button):
        nonlocal counter
        counter += 1
        sender.title = f"Clicks: {counter}"

    button = ui.Button()
    button.title = f"Clicks: {counter}"
    button.frame = (0, 0, 300, 100)
    button.center = (200, 300)
    button.action = action
    button.flex = "WH"
    button.background_color = "dark_blue"
    button.corner_radius = 16
    button.tint_color = "white"

    root = ui.View()
    root.frame = (0, 0, 400, 600)
    root.name = f"Demo: {button.__class__.name}"
    root.add_subview(button)
    root.present("default")


if __name__ == "__main__":
    main()
