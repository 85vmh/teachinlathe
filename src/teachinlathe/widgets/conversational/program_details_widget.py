from PyQt5.QtCore import QObject, pyqtSignal, QSize
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QCheckBox, QWidget, QHBoxLayout, QLabel, QFrame, QVBoxLayout

from teachinlathe.conversational.data_types import Program, display_names

checkbox_style = "QCheckBox::indicator { width: 30px; height: 30px; }"

class ProgramDetailsWidget(QObject):
    item_selected = pyqtSignal(object)  # Emit the object when an item is clicked
    program_modified = pyqtSignal(Program)  # Emit entire program when modified

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
        header_item = QListWidgetItem()
        header_item.setSizeHint(QSize(300, 60))
        header_widget = QLabel("Program Header")
        header_widget.setMargin(10)
        header_widget.setStyleSheet("font-family: Cantarell; font-size: 18px;")
        self.list_widget.addItem(header_item)
        self.list_widget.setItemWidget(header_item, header_widget)

        # Add divider after header
        divider_item = QListWidgetItem()
        divider_item.setSizeHint(QSize(300, 2))
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setStyleSheet("color: #ccc;")
        self.list_widget.addItem(divider_item)
        self.list_widget.setItemWidget(divider_item, divider)
        header_item.setData(256, self.program.header)  # Store the Header object

        # Sort and add only the operation names
        sorted_operations = sorted(self.program.operations, key=lambda op: op.order)
        for operation in sorted_operations:
            op_item = QListWidgetItem()
            op_item.setSizeHint(QSize(300, 60))

            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)

            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(10, 5, 10, 5)

            gcode_checkbox = QCheckBox()
            gcode_checkbox.setFixedSize(QSize(40, 40))
            gcode_checkbox.setStyleSheet(checkbox_style)
            gcode_checkbox.setChecked(operation.generate_gcode)

            name_label = QLabel(display_names[operation.type])
            name_label.setEnabled(operation.generate_gcode)  # Grayed out if unchecked
            name_label.setStyleSheet("font-family: Cantarell; font-size: 18px;")

            optional_checkbox = QCheckBox()
            optional_checkbox.setFixedSize(QSize(40, 40))
            optional_checkbox.setStyleSheet(checkbox_style)
            optional_checkbox.setChecked(operation.is_optional_block)
            optional_checkbox.setEnabled(operation.generate_gcode)

            # Connect signals to emit events and notify parent
            gcode_checkbox.toggled.connect(
                lambda checked, op=operation, name_lbl=name_label, opt_cb=optional_checkbox:
                self.on_gcode_toggled(op, checked, name_lbl, opt_cb))

            optional_checkbox.toggled.connect(
                lambda checked, op=operation:
                self.on_optional_toggled(op, checked))

            layout.addWidget(gcode_checkbox)
            layout.addWidget(name_label)
            layout.addStretch()
            layout.addWidget(optional_checkbox)
            widget.setLayout(layout)

            # Divider
            divider = QFrame()
            divider.setFrameShape(QFrame.HLine)
            divider.setFrameShadow(QFrame.Sunken)
            divider.setStyleSheet("color: #ccc;")

            container_layout.addWidget(widget)
            container_layout.addWidget(divider)

            self.list_widget.addItem(op_item)
            self.list_widget.setItemWidget(op_item, container)
            op_item.setData(256, operation)  # Store the full Operation object

    def on_gcode_toggled(self, operation, checked, name_label, optional_checkbox):
        operation.generate_gcode = checked
        name_label.setEnabled(checked)
        optional_checkbox.setEnabled(checked)
        self.program_modified.emit(self.program)

    def on_optional_toggled(self, operation, checked):
        operation.is_optional_block = checked
        self.program_modified.emit(self.program)

    def on_item_clicked(self, item):
        """Emit the stored object when an item is clicked."""
        selected_object = item.data(256)  # Retrieve stored Header or Operation
        self.item_selected.emit(selected_object)  # Emit object to be loaded in right pane
