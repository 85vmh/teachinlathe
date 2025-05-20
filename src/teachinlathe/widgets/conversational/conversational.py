import os
from enum import Enum

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QListWidgetItem
from qtpy import uic
from qtpy.QtWidgets import QWidget
from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities import logger

from teachinlathe.conversational.data_types import SetTool, Header, Facing, Profiling
from teachinlathe.widgets.conversational.facing_detail_widget import FacingDetailsWidget
from teachinlathe.widgets.conversational.header_detail_widget import HeaderDetailWidget
from teachinlathe.widgets.conversational.profiling_detail_widget import ProfilingDetailsWidget
from teachinlathe.widgets.conversational.program_details_widget import ProgramDetailsWidget
from teachinlathe.widgets.conversational.program_loader import load_programs_from_folder
from teachinlathe.widgets.conversational.tool_change_detail_widget import SetToolDetailsWidget

LOG = logger.getLogger(__name__)

UI_FILE = os.path.join(os.path.dirname(__file__), "conversational.ui")
STATUS = getPlugin('status')


class MainPage(Enum):
    def __init__(self, index, title, next_btn_text="Load"):
        self.index = index
        self.title = title
        self.next_btn_text = next_btn_text

    PROGRAMS = (0, "Conversational programs", "Load")
    DETAILS = (1, "Program Details")


class DetailsPage(Enum):
    def __init__(self, index):
        self.index = index

    HEADER = 0
    SET_TOOL = 1
    DEFINE_PROFILE = 2


from PyQt5.QtWidgets import QStyledItemDelegate


class ProgramItemDelegate(QStyledItemDelegate):
    """Custom delegate to ensure proper item height in QListView."""

    def sizeHint(self, option, index):
        # Ensure each item has a minimum size
        return QSize(300, 60)


class Conversational(QWidget):
    onLoadClicked = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(Conversational, self).__init__(parent)
        uic.loadUi(UI_FILE, self)

        self.folder_path = "/home/cnc/Work/teachinlathe/conversational"

        self.current_program = None
        self.btnBack.clicked.connect(self.btnOnBackClicked)
        self.btnTurning.clicked.connect(lambda: self.load_programs())
        self.switchMainPage(MainPage.PROGRAMS)

    def load_programs(self):
        """Load all programs from JSON files in the specified folder."""
        programs = load_programs_from_folder(self.folder_path)
        print(f"Loaded {len(programs)} programs.")
        self.listWidget_programs.clear()  # Clear existing items

        self.listWidget_programs.setStyleSheet("""
            QListWidget::item {
                border-bottom: 1px solid #ccc;  /* Thin gray line */
                padding: 1px;
            }
        """)

        for program in programs:
            self.add_program_to_list(program)

    def add_program_to_list(self, program_data):
        from teachinlathe.widgets.conversational.program_item_widget import ProgramItemWidget
        """Add a program item to the list."""
        self.listWidget_programs.setItemDelegate(ProgramItemDelegate())  # Apply delegate

        item = QListWidgetItem(self.listWidget_programs)
        widget = ProgramItemWidget(program_data)

        widget.edit_clicked.connect(self.edit_program)
        widget.delete_clicked.connect(self.delete_program)

        item.setSizeHint(widget.sizeHint())
        self.listWidget_programs.addItem(item)
        self.listWidget_programs.setItemWidget(item, widget)

    def edit_program(self, program_data):
        """Handle the edit program signal."""
        LOG.debug(f"Edit program {program_data}")
        self.current_program = program_data
        self.switchMainPage(MainPage.DETAILS)

    def delete_program(self, program_id):
        """Handle the delete program signal."""
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
        if page == MainPage.DETAILS:
            print("Switching to details page")
            if self.current_program is not None:
                self.load_program_contents(self.current_program)

    def load_program_contents(self, program):
        self.details_manager = ProgramDetailsWidget(program, self.listWidget_steps)
        self.details_manager.item_selected.connect(self.load_details_page)

    def load_details_page(self, selected_item):
        print(f"Selected item: {selected_item}")
        # stepDetails

        # set_tool_widget = SetToolDetailsWidget(program.operations[0])
        # self.stepDetails.addWidget(set_tool_widget)
        # self.stepDetails.setCurrentWidget(set_tool_widget)

        """Loads the appropriate details page when an item is selected."""
        if isinstance(selected_item, Header):
            details_widget = HeaderDetailWidget(selected_item)
            self.stepDetails.addWidget(details_widget)
            self.stepDetails.setCurrentWidget(details_widget)

        elif isinstance(selected_item, SetTool):
            details_widget = SetToolDetailsWidget(selected_item)
            self.stepDetails.addWidget(details_widget)
            self.stepDetails.setCurrentWidget(details_widget)

        elif isinstance(selected_item, Facing):
            details_widget = FacingDetailsWidget(selected_item)
            self.stepDetails.addWidget(details_widget)
            self.stepDetails.setCurrentWidget(details_widget)

        elif isinstance(selected_item, Profiling):
            details_widget = ProfilingDetailsWidget(selected_item)
            self.stepDetails.addWidget(details_widget)
            self.stepDetails.setCurrentWidget(details_widget)





