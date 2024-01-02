from PyQt5 import QtWidgets

class ToggleButton(QtWidgets.QPushButton):
    def __init__(self, parent=None):
        super(ToggleButton, self).__init__(parent)
        self.setCheckable(True)
        self.setChecked(False)
        self.toggled.connect(self.onToggle)

        # Styling the button
        self.setStyleSheet("""
        QPushButton {
            border: 1px solid #555;
            border-radius: 10px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #eee, stop:1 #ccc);
            padding: 5px;
        }
        QPushButton:checked {
            border: 1px solid #555;
            border-radius: 10px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #89b, stop:1 #678);
            padding: 5px;
        }
        """)

    def onToggle(self, checked):
        if checked:
            self.setText("ON")
        else:
            self.setText("OFF")


app = QtWidgets.QApplication([])
window = QtWidgets.QWidget()

toggle_button = ToggleButton()
toggle_button.setText("OFF")  # Initial state

layout = QtWidgets.QVBoxLayout(window)
layout.addWidget(toggle_button)

window.show()
app.exec_()
