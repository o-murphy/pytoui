"""Demo app: python -m ui

Press ESC or close the window to exit.
"""

from pytoui import ui


def main():
    seg = ui.SegmentedControl()
    seg.name = f"Demo: {seg.__class__.name}"
    seg.frame = (0, 0, 300, 30)
    seg.center = (200, 300)
    seg.segments = ["Segment1", "Segment2", "Segment3"]
    seg.flex = "WH"

    root = ui.View()
    root.frame = (0, 0, 400, 600)
    root.name = f"Demo: {seg.__class__.name}"
    root.add_subview(seg)
    root.present("default")


if __name__ == "__main__":
    main()
