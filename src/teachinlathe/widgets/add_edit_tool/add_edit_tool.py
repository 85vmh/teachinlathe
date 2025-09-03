import os

from PyQt5 import QtCore
from qtpy import uic
from qtpy.QtWidgets import QWidget
from qtpyvcp.utilities import logger

from teachinlathe.widgets.smart_numpad_dialog import SmartNumPadDialog

LOG = logger.getLogger(__name__)

UI_FILE = os.path.join(os.path.dirname(__file__), "add_edit_tool.ui")


class AddEditToolWidget(QWidget):
    onSaved = QtCore.pyqtSignal()
    onCanceled = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(AddEditToolWidget, self).__init__(parent)
        uic.loadUi(UI_FILE, self)
        self._tool_data = None
        self._tool_model = None
        self._tool_no = None

        self.tipRadiusInput.settingName = 'smart_numpad.input-tip_radius'
        self.tipRadiusInput.initialize()

        self.toolNoInput.mousePressEvent = lambda _: self.openNumPad(self.toolNoInput)
        self.tipRadiusInput.mousePressEvent = lambda _: self.openNumPad(self.tipRadiusInput)
        self.frontAngleInput.mousePressEvent = lambda _: self.openNumPad(self.frontAngleInput)
        self.backAngleInput.mousePressEvent = lambda _: self.openNumPad(self.backAngleInput)

        self.saveButton.clicked.connect(self.onSaveClicked)
        self.cancelButton.clicked.connect(self.onCanceled.emit)

    def openNumPad(self, fake_edit_text, on_value_selected_callback=None):
        setting_name = getattr(fake_edit_text, 'settingName', None)
        dialog = SmartNumPadDialog(setting_name)

        def handle_value(value):
            self.setSelectedValue(fake_edit_text, value)
            if on_value_selected_callback:
                on_value_selected_callback(value)

        dialog.valueSelected.connect(handle_value)
        dialog.exec_()

    @staticmethod
    def setSelectedValue(fake_edit_text, value):
        fake_edit_text.setText(value)

    def setEditToolData(self, tool_data: dict, tool_model, tool_no: int):
        self._tool_data = tool_data
        self._tool_model = tool_model
        self._tool_no = tool_no

        print("tool_data:", tool_data)

        self.toolNoInput.setText(str(tool_no))
        self.tipRadiusInput.setText(str(tool_data.get('D', 0.0)))
        self.frontAngleInput.setText(str(tool_data.get('I', 0.0)))
        self.backAngleInput.setText(str(tool_data.get('J', 0.0)))
        self.toolDescription.setText(str(tool_data.get('R', '')))
        toolOrientation = tool_data.get('Q', 0)

        self.orient1.setProperty("orient_val", 1)
        self.orient2.setProperty("orient_val", 2)
        self.orient3.setProperty("orient_val", 3)
        self.orient4.setProperty("orient_val", 4)
        self.orient5.setProperty("orient_val", 5)
        self.orient6.setProperty("orient_val", 6)
        self.orient7.setProperty("orient_val", 7)
        self.orient8.setProperty("orient_val", 8)
        self.orient9.setProperty("orient_val", 9)

        self.orient1.setChecked(toolOrientation == 1)
        self.orient2.setChecked(toolOrientation == 2)
        self.orient3.setChecked(toolOrientation == 3)
        self.orient4.setChecked(toolOrientation == 4)
        self.orient5.setChecked(toolOrientation == 5)
        self.orient6.setChecked(toolOrientation == 6)
        self.orient7.setChecked(toolOrientation == 7)
        self.orient8.setChecked(toolOrientation == 8)
        self.orient9.setChecked(toolOrientation == 9)

    def setAddToolData(self, tool_data: dict, tool_model):
        self._tool_data = tool_data
        self._tool_model = tool_model

        print("tool_data:", tool_data)

        self.orient1.setProperty("orient_val", 1)
        self.orient2.setProperty("orient_val", 2)
        self.orient3.setProperty("orient_val", 3)
        self.orient4.setProperty("orient_val", 4)
        self.orient5.setProperty("orient_val", 5)
        self.orient6.setProperty("orient_val", 6)
        self.orient7.setProperty("orient_val", 7)
        self.orient8.setProperty("orient_val", 8)
        self.orient9.setProperty("orient_val", 9)


    def onSaveClicked(self):
        if not self._tool_model or self._tool_no is None:
            return

        btn = self.orientButtonGroup.checkedButton()

        self._tool_model._tool_table[self._tool_no]['D'] = float(self.tipRadiusInput.text())
        self._tool_model._tool_table[self._tool_no]['I'] = float(self.frontAngleInput.text())
        self._tool_model._tool_table[self._tool_no]['J'] = float(self.backAngleInput.text())
        self._tool_model._tool_table[self._tool_no]['R'] = str(self.toolDescription.toPlainText())
        self._tool_model._tool_table[self._tool_no]['Q'] = btn.property("orient_val")

        self._tool_model.saveToolTable()
        self._tool_model.loadToolTable()
        self.onSaved.emit()
