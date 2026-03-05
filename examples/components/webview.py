"""Demo app: python -m ui

Press ESC or close the window to exit.
"""

from pytoui import ui


def main():

    root = ui.WebView()
    root.frame = (0, 0, 400, 600)
    root.name = "WebView"
    root.present("default")
    # root.load_url("https://google.com")


if __name__ == "__main__":
    main()
