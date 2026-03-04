from pytoui import ui


def main():

    v1 = ui.View()
    v1.background_color = "darkblue"
    v1.name = "View 1"

    v2 = ui.View()
    v2.background_color = "green"
    v2.name = "View 2"

    v3 = ui.View()
    v3.background_color = "yellow"
    v3.name = "View 3"

    root = ui.NavigationView(v1)

    root.push_view(v1)
    root.push_view(v2)
    root.push_view(v3)

    def add_push_btn(to_view, next_view):
        btn = ui.Button()
        btn.corner_radius = 8
        btn.background_color = "black"
        btn.title = "Next"
        btn.action = lambda _: root.push_view(next_view)
        btn.center = (v1.center.x, v1.center.y)
        to_view.add_subview(btn)

    add_push_btn(v1, v2)
    add_push_btn(v2, v3)

    root.background_color = "black"
    root.frame = (0.0, 0.0, 400.0, 600.0)
    root.title_color = "red"
    root.bar_tint_color = "yellow"

    root.present()


if __name__ == "__main__":
    main()
