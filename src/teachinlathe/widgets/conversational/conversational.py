import os
import subprocess
from enum import Enum

from PyQt5 import QtCore
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QListWidgetItem, QMessageBox
from qtpy import uic
from qtpy.QtWidgets import QWidget
from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities import logger
from Xlib import display

from teachinlathe.conversational.data_types import ChangeTool, Header, Facing, Profiling, Program
from teachinlathe.widgets.conversational.SaveableOperationForm import SavableOperationForm
from teachinlathe.widgets.conversational.facing.facing_details_widget import FacingDetailsWidget
from teachinlathe.widgets.conversational.headerDetails.header_details_widget import HeaderDetailWidget
from teachinlathe.widgets.conversational.profiling.profiling_details_widget import ProfilingDetailsWidget
from teachinlathe.widgets.conversational.program_details_widget import ProgramDetailsWidget
from teachinlathe.widgets.conversational.program_loader import load_programs_from_folder
from teachinlathe.widgets.conversational.toolChange.tool_change_details_widget import ChangeToolDetailsWidget

LOG = logger.getLogger(__name__)

UI_FILE = os.path.join(os.path.dirname(__file__), "conversational.ui")
STATUS = getPlugin('status')


class MainPage(Enum):
    def __init__(self, index, title, next_btn_text="Generate G-code"):
        self.index = index
        self.title = title
        self.next_btn_text = next_btn_text

    PROGRAMS = (0, "Conversational programs", "Generate G-code")
    DETAILS = (1, "Program Details")


class DetailsPage(Enum):
    def __init__(self, index):
        self.index = index

    HEADER = 0
    SET_TOOL = 1
    DEFINE_PROFILE = 2


from PyQt5.QtWidgets import QStyledItemDelegate


class ProgramItemDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(300, 60)


class Conversational(QWidget):
    onLoadClicked = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(Conversational, self).__init__(parent)
        self.details_manager = None
        uic.loadUi(UI_FILE, self)

        self.folder_path = "/home/cnc/Work/teachinlathe/conversational"
        self.current_program = None

        self.btnBack.clicked.connect(self.btnOnBackClicked)
        self.setToolBtn.clicked.connect(self.btnOnSetToolClicked)
        self.switchMainPage(MainPage.PROGRAMS)

    def btnOnSetToolClicked(self):
        pass

    def find_window_by_title(title):
        dsp = display.Display()
        root = dsp.screen().root
        for win in root.query_tree().children:
            try:
                if win.get_wm_name() == title:
                    return win.id
            except:
                continue
        return None

    def load_programs(self):
        programs = load_programs_from_folder(self.folder_path)
        print(f"Loaded {len(programs)} programs.")
        self.listWidget_programs.clear()

        self.listWidget_programs.setStyleSheet("""
            QListWidget::item {
                border-bottom: 1px solid #ccc;
                padding: 1px;
            }
        """)

        for program in programs:
            self.add_program_to_list(program)

    def add_program_to_list(self, program):
        from teachinlathe.widgets.conversational.program_item_widget import ProgramItemWidget

        self.listWidget_programs.setItemDelegate(ProgramItemDelegate())

        item = QListWidgetItem(self.listWidget_programs)
        widget = ProgramItemWidget(program)
        widget.edit_clicked.connect(self.edit_program)
        widget.delete_clicked.connect(self.delete_program)

        item.setSizeHint(widget.sizeHint())
        self.listWidget_programs.addItem(item)
        self.listWidget_programs.setItemWidget(item, widget)

    def edit_program(self, program):
        LOG.debug(f"Edit program {program}")
        self.current_program = program
        self.switchMainPage(MainPage.DETAILS)

    def delete_program(self, program_id):
        LOG.debug(f"Delete program {program_id}")

    def btnOnBackClicked(self):
        self.switchMainPage(MainPage.PROGRAMS)

    def switchMainPage(self, page: MainPage):
        self.mainStackedWidget.setCurrentIndex(page.index)
        self.title.setText(page.title)
        self.btnBack.setVisible(page != MainPage.PROGRAMS)
        self.btnNext.setVisible(page != MainPage.PROGRAMS and page.next_btn_text is not None)
        if page.next_btn_text is not None:
            self.btnNext.setText(page.next_btn_text)

        if page == MainPage.PROGRAMS:
            print("Switching to programs page")
            self.load_programs()
        if page == MainPage.DETAILS:
            print("Switching to details page")
            if self.current_program is not None:
                self.load_program_contents(self.current_program)

    def load_program_contents(self, program):
        self.details_manager = ProgramDetailsWidget(program, self.listWidget_steps)
        self.details_manager.item_selected.connect(self.load_details_page)
        self.details_manager.program_operation_changed.connect(self.save_program)

    def load_details_page(self, selected_item):
        self.maybe_save_current_changes()

        if isinstance(selected_item, Header):
            details_widget = HeaderDetailWidget(selected_item)
        elif isinstance(selected_item, ChangeTool):
            details_widget = ChangeToolDetailsWidget(selected_item)
        elif isinstance(selected_item, Facing):
            details_widget = FacingDetailsWidget(selected_item)
        elif isinstance(selected_item, Profiling):
            details_widget = ProfilingDetailsWidget(selected_item)
        else:
            LOG.warning(f"Unknown operation type: {type(selected_item)}")
            return

        self.stepDetails.addWidget(details_widget)
        self.stepDetails.setCurrentWidget(details_widget)

    def maybe_save_current_changes(self):
        current_widget = self.stepDetails.currentWidget()
        if current_widget and isinstance(current_widget, SavableOperationForm):
            current_widget.operation_changed.connect(self.update_current_operation)

            if current_widget.hasUnsavedData():
                reply = QMessageBox.question(
                    self,
                    "Just a moment",
                    "This operation has unsaved changes. Do you want to save them?",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    current_widget.handleSave()
                elif reply == QMessageBox.No:
                    pass

    def update_current_operation(self, updated_operation):
        print("Updating current operation:", updated_operation)
        for idx, op in enumerate(self.current_program.operations):
            if op.order == updated_operation.order:
                self.current_program.operations[idx] = updated_operation
                break

        self.save_program(self.current_program)

    # def apply_current_step_changes(self):
    #     current_widget = self.stepDetails.currentWidget()
    #     if current_widget and hasattr(current_widget, "update_model"):
    #         current_widget.update_model()

    def save_program(self, updated_program: Program):
        # self.apply_current_step_changes()
        path = os.path.join(self.folder_path, updated_program.filename)
        try:
            for op in updated_program.operations:
                if not hasattr(op, "to_dict"):
                    raise AttributeError(f"Missing to_dict() in {type(op).__name__}")
            with open(path, "w") as f:
                f.write(updated_program.to_json())
            print(f"Saved program to {path}")
        except Exception as e:
            LOG.error(f"Failed to save program {updated_program.id}: {e}")
