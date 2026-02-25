"""Demo app: python -m ui

Press ESC or close the window to exit.
"""

from pytoui import ui


def main():
    view = ui.View()
    view.name = f"Demo: {view.__class__.name}"
    view.background_color = "black"
    view.frame = (0, 0, 400, 600)

    sw = ui.Switch()
    sw.center = view.bounds.center()

    view.add_subview(sw)
    view.present("fullscreen")


if __name__ == "__main__":
    main()
