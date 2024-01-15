from PyQt5 import QtCore, QtGui, QtWidgets
from qtpyvcp import SETTINGS
from PyQt5.QtGui import QValidator

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

            self.plusMinusBtn.setText(u"\u00B1")

            # validator = QtGui.QDoubleValidator()
            # validator.setRange(-9999.999, 9999.999, 3)
            # self.inputField.setValidator(validator)
            self.inputField.setValidator(self.SingleDotValidator())

            self.enterValueLabel.setText("Enter " + self.title_prefix)
            self.enterValuesWidget.setGeometry(QtCore.QRect(0, 0, 391, 420))
            self.resize(394, self.enter_values_height)

            self.numbersGroup.buttonClicked.connect(self.numberKeys)
            self.backBtn.clicked.connect(self.backKey)
            self.clearBtn.clicked.connect(self.clearKey)
            self.inputBtn.clicked.connect(self.inputKey)

    def numberKeys(self, button):
        text = self.inputField.text()  # copy the label text to the variable
        if len(text) > 0:  # if there is something in the label
            text += button.text()  # add the button text to the text variable
        else:  # if the label is empty
            text = button.text()  # assign the button text to the text variable
        self.inputField.setText(text)  # set the text in label

    def backKey(self):
        text = self.inputField.text()[:-1]  # assign all but the last char to text
        self.inputField.setText(text)

    def clearKey(self):
        self.inputField.setText("")

    def inputKey(self):
        self.valueSelected.emit(self.inputField.text())
        self.close()

    def quickValueSelected(self):
        selected_value = self.sender().text()  # Get text of the clicked button
        self.valueSelected.emit(selected_value)  # Emit the signal with the selected value
        self.close()

    def resizeEvent(self, event):
        # Override resize event to prevent resizing
        pass

    class SingleDotValidator(QValidator):
        def validate(self, string, pos):
            if string.count('.') > 1:
                return (QValidator.Invalid, string, pos)
            return (QValidator.Acceptable, string, pos)