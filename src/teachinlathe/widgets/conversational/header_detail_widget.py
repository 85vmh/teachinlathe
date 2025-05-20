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
