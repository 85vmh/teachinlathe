from PyQt5 import QtCore, QtGui, QtWidgets
from teachinlathe.widgets.QFlowLayout import QFlowLayout
from teachinlathe.widgets.numpad_dialog_ui import Ui_NumPadDialog


class SmartNumPadDialog(QtWidgets.QDialog, Ui_NumPadDialog):
    def __init__(self, parent=None):
        super(SmartNumPadDialog, self).__init__(parent)
        showSuggestions = True

        self.setupUi(self)
        self.lineEdit.setText("0.1234")

        if showSuggestions:
            self.flowLayout = QFlowLayout(self)
            for i in range(7):
                button = QtWidgets.QPushButton(self)
                button.setObjectName("suggestPushButton_%d" % i)
                button.setText("Btn%d" % i)
                button.setFocusPolicy(QtCore.Qt.NoFocus)
                self.flowLayout.addWidget(button)

            self.suggestedValuesBox.setStyleSheet("QPushButton {\n"
                                                  "min-height: 24px;\n"
                                                  "min-width: 24px;\n"
                                                  "font: 10pt \"DejaVu Sans\";\n"
                                                  "}")
            self.suggestedValuesBox.setLayout(self.flowLayout)
        else:
            self.suggestedValuesBox.hide()
            self.numpadGroupBox.setGeometry(QtCore.QRect(5, 130, 381, 301))
            self.resize(394, 440)

    def resizeEvent(self, event):
        # Override resize event to prevent resizing
        pass