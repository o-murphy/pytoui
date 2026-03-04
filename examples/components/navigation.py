from pytoui import ui


class TestView(ui.View):
    def __init__(self):
        self.parent = None
        self.btn = ui.Button()
        self.btn.corner_radius = 8
        self.btn.background_color = "red"
        self.btn.title = "Close"
        self.btn.action = lambda sender: self.parent and self.parent.close()
        self.add_subview(self.btn)

    def layout(self):
        x, y = self.frame.center()
        self.btn.center = (x, y)

    def touch_began(self, touch):
        print(touch)


def main():

    v1 = TestView()
    v1.background_color = "blue"
    v1.name = "View 1"

    v2 = TestView()
    v2.background_color = "green"
    v2.name = "View 2"

    root = ui.NavigationView(v1)
    v1.parent = root
    v2.parent = root

    root.background_color = "gray"
    root.frame = (0.0, 0.0, 400.0, 600.0)
    root.title_color = "red"

    root.present()

    root.push_view(v1)
    root.push_view(v2)


if __name__ == "__main__":
    main()
