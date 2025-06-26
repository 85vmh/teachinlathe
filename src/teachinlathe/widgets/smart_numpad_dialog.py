from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QValidator
from qtpyvcp import SETTINGS

from teachinlathe.widgets.QFlowLayout import QFlowLayout
from teachinlathe.widgets.numpad_dialog_ui import Ui_NumPadDialog


class SmartNumPadDialog(QtWidgets.QDialog, Ui_NumPadDialog):
    valueSelected = QtCore.pyqtSignal(str)

    WINDOW_WIDTH = 500
    SELECT_VALUES_HEIGHT = 355
    ENTER_VALUES_HEIGHT = 500

    def __init__(self, settings_key, enter_values=False, parent=None):
        super(SmartNumPadDialog, self).__init__(parent)
        self.setupUi(self)
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

                if self.title_prefix is not None:
                    self.setWindowTitle("Select " + self.title_prefix)

                self.suggestedValuesBox.setStyleSheet("QPushButton {\n"
                                                      "height: 50px;\n"
                                                      "width: 80px;\n"
                                                      "font: 14pt \"DejaVu Sans\";\n"
                                                      "}")
                self.suggestedValuesBox.setLayout(self.flowLayout)
                self.resize(self.WINDOW_WIDTH, self.SELECT_VALUES_HEIGHT)
        else:
            self.selectValuesWidget.hide()
            self.enterValuesWidget.show()

            self.plusMinusBtn.setText(u"\u00B1")

            # validator = QtGui.QDoubleValidator()
            # validator.setRange(-9999.999, 9999.999, 3)
            # self.inputField.setValidator(validator)
            self.inputField.setValidator(self.SingleDotValidator())

            if self.title_prefix is not None:
                self.setWindowTitle("Enter " + self.title_prefix)

            self.enterValuesWidget.setGeometry(QtCore.QRect(0, 0, self.WINDOW_WIDTH - 3, self.ENTER_VALUES_HEIGHT - 20))
            self.resize(self.WINDOW_WIDTH, self.ENTER_VALUES_HEIGHT)

            self.numbersGroup.buttonClicked.connect(self.numberKeys)
            self.backBtn.clicked.connect(self.backKey)
            self.clearBtn.clicked.connect(self.clearKey)
            self.inputBtn.clicked.connect(self.inputKey)
            self.plusMinusBtn.clicked.connect(self.togglePlusMinus)

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

    def togglePlusMinus(self):
        text = self.inputField.text()
        if text.startswith('-'):
            text = text[1:]
        else:
            text = '-' + text
        self.inputField.setText(text)

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
