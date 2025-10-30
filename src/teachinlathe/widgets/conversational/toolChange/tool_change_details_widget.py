from PyQt5.QtWidgets import QWidget
from teachinlathe.conversational.data_types import ChangeTool
from teachinlathe.widgets.conversational.toolChange.tool_change_details import Ui_ToolChangeDetailForm


class ChangeToolDetailsWidget(QWidget, Ui_ToolChangeDetailForm):
    def __init__(self, set_tool_data: ChangeTool, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.set_tool_data = set_tool_data  # Store the SetTool object
        print("SetToolDetailsWidget: ", set_tool_data)

        # Populate UI fields with SetTool data
        self.toolNo.setText(str(set_tool_data.tool_no))
        self.toolDescription.setPlainText(f"Tool Orientation: {set_tool_data.tool_orientation}\n"
                                          f"Back Angle: {set_tool_data.back_angle}°\n"
                                          f"Front Angle: {set_tool_data.front_angle}°")

        print("Tool Change Details: ", set_tool_data.toolchange_rules)

        # Access values using dictionary keys
        self.xChangePos.setText(str(set_tool_data.toolchange_rules.x_pos))
        self.zChangePos.setText(str(set_tool_data.toolchange_rules.z_pos))

        # Set the radio buttons based on move sequence
        if set_tool_data.toolchange_rules.move_sequence == "both":
            self.radioButton_4.setChecked(True)
        elif set_tool_data.toolchange_rules.move_sequence == "xz":
            self.radioButton_5.setChecked(True)
        elif set_tool_data.toolchange_rules.move_sequence == "zx":
            self.radioButton_6.setChecked(True)

        # Set spindle stop option
        if set_tool_data.toolchange_rules.stop_spindle:
            self.radioButton_3.setChecked(True)  # Yes
        else:
            self.radioButton_7.setChecked(True)  # No

    def update_model(self):
        """Update the set_tool_data model with values from the UI."""
        try:
            self.set_tool_data.tool_no = int(self.toolNo.text())
        except ValueError:
            self.set_tool_data.tool_no = 0

        try:
            self.set_tool_data.toolchange_rules.x_pos = float(self.xChangePos.text())
        except ValueError:
            self.set_tool_data.toolchange_rules.x_pos = 0.0

        try:
            self.set_tool_data.toolchange_rules.z_pos = float(self.zChangePos.text())
        except ValueError:
            self.set_tool_data.toolchange_rules.z_pos = 0.0

        if self.radioButton_4.isChecked():
            self.set_tool_data.toolchange_rules.move_sequence = "both"
        elif self.radioButton_5.isChecked():
            self.set_tool_data.toolchange_rules.move_sequence = "xz"
        elif self.radioButton_6.isChecked():
            self.set_tool_data.toolchange_rules.move_sequence = "zx"
        else:
            self.set_tool_data.toolchange_rules.move_sequence = "both"  # default

        self.set_tool_data.toolchange_rules.stop_spindle = self.radioButton_3.isChecked()
