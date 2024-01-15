from PyQt5 import QtCore, QtGui, QtWidgets
from qtpyvcp import SETTINGS

from teachinlathe.widgets.QFlowLayout import QFlowLayout
from teachinlathe.widgets.numpad_dialog_ui import Ui_NumPadDialog


class SmartNumPadDialog(QtWidgets.QDialog, Ui_NumPadDialog):
    valueSelected = QtCore.pyqtSignal(str)

    def __init__(self, settings_key, enter_values=False, parent=None):
        super(SmartNumPadDialog, self).__init__(parent)
        self.setupUi(self)
        self.select_values_height = 311
        self.enter_values_height = 440
        self.enter_values_mode = enter_values

        self._setting = SETTINGS.get(settings_key)
        self.title_prefix = self._setting.__doc__

        self.btnOtherValues.clicked.connect(self.otherValuesClicked)
        self.setupLayout()

    def otherValuesClicked(self):
        self.enter_values_mode = True
        self.setupLayout()

    def setupLayout(self):
        if self._setting is not None and not self.enter_values_mode:
            self.enterValuesWidget.hide()
            self.selectValuesWidget.show()

            options = self._setting.enum_options
            if isinstance(options, list):
                self.flowLayout = QFlowLayout(self)
                for i, value in enumerate(options):
                    button = QtWidgets.QPushButton(self)
                    button.setObjectName("suggestPushButton_%d" % i)
                    button.setText(str(value))
                    button.clicked.connect(self.quickValueSelected)
                    button.setFocusPolicy(QtCore.Qt.NoFocus)
                    self.flowLayout.addWidget(button)

                self.suggestedValuesBox.setTitle("Select " + self.title_prefix)
                self.suggestedValuesBox.setStyleSheet("QPushButton {\n"
                                                      "min-height: 30px;\n"
                                                      "min-width: 24px;\n"
                                                      "font: 11pt \"DejaVu Sans\";\n"
                                                      "}")
                self.suggestedValuesBox.setLayout(self.flowLayout)
                self.resize(394, self.select_values_height)
        else:
            self.selectValuesWidget.hide()
            self.enterValuesWidget.show()

            self.lineEdit.setText("0.1234")
            self.enterValueLabel.setText("Enter " + self.title_prefix)
            self.enterValuesWidget.setGeometry(QtCore.QRect(0, 0, 391, 420))
            self.resize(394, self.enter_values_height)

    def quickValueSelected(self):
        selected_value = self.sender().text()  # Get text of the clicked button
        self.valueSelected.emit(selected_value)  # Emit the signal with the selected value
        self.close()

    def resizeEvent(self, event):
        # Override resize event to prevent resizing
        pass
