from pytoui import ui

if __name__ == "__main__":
    dp = ui.DatePicker(mode=ui.DATE_PICKER_MODE_DATE_AND_TIME)
    dp.tint_color = "red"
    dp.action = lambda sender: print(sender.date)

    root = ui.View()
    root.frame = (0, 0, 400, 600)
    root.add_subview(dp)
    root.present("fullscreen")
