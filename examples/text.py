# import ui

from pytoui import ui


class DebugView(ui.View):
    def draw(self):
        self._draw_grid()

        x, y = 100, 100
        ui.set_color("red")
        ui.fill_rect(x - 2, y - 2, 4, 4)

        ui.set_color("black")
        ui.draw_string("Text 1", (x, y, 0, 0), font=("<system>", 20))

        ui.set_color("blue")
        rect_path = ui.Path.rect(100, 150, 150, 40)
        rect_path.stroke()

        ui.set_color("green")
        ui.draw_string(
            "Text 2",
            (100, 150, 150, 40),
            font=("<system>", 20),
            alignment=ui.ALIGN_CENTER,
        )

        ui.set_color("purple")
        line_path = ui.Path()
        line_path.move_to(50, 200)
        line_path.line_to(350, 200)
        line_path.line_width = 1
        line_path.stroke()

        ui.set_color("black")
        ui.draw_string("agqpy", (50, 200, 0, 0), font=("<system>", 30))

        ui.set_color("red")
        ui.fill_rect(48, 198, 4, 4)

        for i, size in enumerate([12, 16, 20, 24]):
            y_pos = 250 + i * 40

            ui.set_color((0.7, 0.7, 0.7))
            base_path = ui.Path()
            base_path.move_to(50, y_pos)
            base_path.line_to(350, y_pos)
            base_path.line_width = 0.5
            base_path.stroke()

            ui.set_color("black")
            ui.draw_string(f"Size {size}", (50, y_pos, 0, 0), font=("<system>", size))

        y_start = 420
        ui.set_color((0.5, 0.5, 0.5))

        r = (50, y_start, 150, 30)
        ui.set_color("yellow")
        ui.fill_rect(*r)
        ui.draw_string("Left", r, alignment=ui.ALIGN_LEFT)

        r = (50, y_start + 40, 150, 30)
        ui.set_color("yellow")
        ui.fill_rect(*r)
        ui.draw_string("Center", r, alignment=ui.ALIGN_CENTER)

        r = (50, y_start + 80, 150, 30)
        ui.set_color("yellow")
        ui.fill_rect(*r)
        ui.draw_string("Right", r, alignment=ui.ALIGN_RIGHT)

        r = (50, y_start + 120, 150, 30)
        ui.set_color("yellow")
        ui.fill_rect(*r)
        ui.draw_string("Natural", r, alignment=ui.ALIGN_NATURAL)

        r = (50, y_start + 160, 150, 40)
        ui.set_color("yellow")
        ui.fill_rect(*r)
        ui.draw_string("Multiline\n" * 3, r, alignment=ui.ALIGN_NATURAL)

    def _draw_grid(self):
        ui.set_color((0.9, 0.9, 0.9))

        for y in range(0, 600, 20):
            line_path = ui.Path()
            line_path.move_to(0, y)
            line_path.line_to(400, y)
            line_path.line_width = 0.5
            line_path.stroke()

        for x in range(0, 401, 20):
            line_path = ui.Path()
            line_path.move_to(x, 0)
            line_path.line_to(x, 600)
            line_path.line_width = 0.5
            line_path.stroke()


view = DebugView()
view.frame = (0, 0, 400, 600)
view.background_color = "white"
view.present("sheet")
