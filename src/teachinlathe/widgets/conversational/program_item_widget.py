import os

from PyQt5 import uic
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal


from teachinlathe.conversational.data_types import Program

UI_FILE = os.path.join(os.path.dirname(__file__), "program_item.ui")


class ProgramItemWidget(QWidget):
    edit_clicked = pyqtSignal(object)
    delete_clicked = pyqtSignal(str)

    def __init__(self, program: Program, parent=None):
        super().__init__(parent)
        uic.loadUi(UI_FILE, self)

        self.program_data = program  # Store program data
        self.labelName.setText(f"{program.id} - {program.header.name}")
        self.labelLastEdited.setText(f"{program.header.last_edit}")

        # Connect button signals
        self.btnEdit.clicked.connect(self.edit_program)
        self.btnDelete.clicked.connect(self.delete_program)

    def edit_program(self):
        """Emit signal when the edit button is clicked."""
        self.edit_clicked.emit(self.program_data)

    def delete_program(self):
        """Emit signal when the delete button is clicked."""
        self.delete_clicked.emit(self.program_data.id)