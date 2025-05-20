from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QListWidget, QListWidgetItem
from teachinlathe.conversational.data_types import Program, Operation, Header


class ProgramDetailsWidget(QObject):
    item_selected = pyqtSignal(object)  # Emit the object when an item is clicked

    def __init__(self, program: Program, list_widget: QListWidget):
        super().__init__()  # Call QObject constructor
        self.program = program
        self.list_widget = list_widget
        self.populate_list()

        # Connect selection event
        self.list_widget.itemClicked.connect(self.on_item_clicked)

    def populate_list(self):
        """Populate listWidget_steps with header and operation names only."""
        self.list_widget.clear()  # Clear existing items

        # Add header as first item
        header_item = QListWidgetItem(f"📌 {self.program.header.name}")
        header_item.setData(256, self.program.header)  # Store the Header object
        self.list_widget.addItem(header_item)

        # Sort and add only the operation names
        sorted_operations = sorted(self.program.operations, key=lambda op: op.order)
        for operation in sorted_operations:
            op_item = QListWidgetItem(f"🔧 {operation.type}")  # Display only the operation type
            op_item.setData(256, operation)  # Store the full Operation object
            self.list_widget.addItem(op_item)

    def on_item_clicked(self, item):
        """Emit the stored object when an item is clicked."""
        selected_object = item.data(256)  # Retrieve stored Header or Operation
        self.item_selected.emit(selected_object)  # Emit object to be loaded in right pane
