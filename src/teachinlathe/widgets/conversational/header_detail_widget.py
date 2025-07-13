from PyQt5.QtWidgets import QWidget
from teachinlathe.conversational.data_types import Header
from teachinlathe.widgets.conversational.header_detail import Ui_HeaderDetailForm


class HeaderDetailWidget(QWidget, Ui_HeaderDetailForm):
    def __init__(self, header: Header, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.header = header
        self.populate_fields()

    def populate_fields(self):
        """Populate the UI fields with header data."""
        self.lineEdit.setText(self.header.name)
        self.lineEdit_5.setText(str(self.header.datum))
        self.radioButton.setChecked(self.header.workpiece.material == "mm")
        self.radioButton_2.setChecked(self.header.workpiece.material == "in")
        self.lineEdit_2.setText(str(self.header.workpiece.external_diameter))
        self.lineEdit_3.setText(str(self.header.workpiece.internal_diameter))
        self.lineEdit_4.setText(str(self.header.workpiece.stickout_length))

    def update_model(self):
        """Update the header model with the values from the UI fields."""
        self.header.name = self.lineEdit.text()

        try:
            self.header.datum = int(self.lineEdit_5.text())
        except ValueError:
            self.header.datum = 0  # sau poți emite un warning/log

        self.header.units = "mm" if self.radioButton.isChecked() else "in"

        try:
            self.header.workpiece.external_diameter = float(self.lineEdit_2.text())
        except ValueError:
            self.header.workpiece.external_diameter = 0.0

        try:
            self.header.workpiece.internal_diameter = float(self.lineEdit_3.text())
        except ValueError:
            self.header.workpiece.internal_diameter = 0.0

        try:
            self.header.workpiece.stickout_length = float(self.lineEdit_4.text())
        except ValueError:
            self.header.workpiece.stickout_length = 0.0

