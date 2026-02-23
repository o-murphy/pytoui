from pytoui import ui


root = ui.View()  # frame=(0, 0, 400, 400))
root.frame = (0, 0, 400, 400)
root.background_color = "white"

btn1 = ui.Label()
btn1.text = "NO FLEX"
btn1.alignment = ui.ALIGN_CENTER
btn1.frame = (20, 20, 120, 60)
btn1.background_color = "blue"
btn1.flex = ""
root.add_subview(btn1)

btn2 = ui.Label()
btn2.text = "L"
btn2.alignment = ui.ALIGN_CENTER
btn2.frame = (260, 20, 120, 60)
btn2.background_color = "green"
btn2.flex = "L"
root.add_subview(btn2)

btn3 = ui.Label()
btn3.text = "W"
btn3.alignment = ui.ALIGN_CENTER
btn3.frame = (20, 100, 360, 40)
btn3.background_color = "red"
btn3.flex = "W"
root.add_subview(btn3)

btn4 = ui.Label()
btn4.text = "WH"
btn4.alignment = ui.ALIGN_CENTER
btn4.frame = (20, 200, 360, 150)
btn4.background_color = "grey"
btn4.flex = "WH"
root.add_subview(btn4)

root.present("sheet")
