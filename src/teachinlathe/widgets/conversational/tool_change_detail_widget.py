from PyQt5.QtWidgets import QWidget
from teachinlathe.conversational.data_types import SetTool
from teachinlathe.widgets.conversational.tool_change_detail import Ui_ToolChangeDetailForm


class SetToolDetailsWidget(QWidget, Ui_ToolChangeDetailForm):
    def __init__(self, set_tool_data: SetTool, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.set_tool_data = set_tool_data  # Store the SetTool object
        print("SetToolDetailsWidget: ", set_tool_data)

        # Populate UI fields with SetTool data
        self.toolNo.setText(str(set_tool_data.tool_no))
        self.toolDescription.setPlainText(f"Tool Orientation: {set_tool_data.tool_orientation}\n"
                                          f"Back Angle: {set_tool_data.back_angle}°\n"
                                          f"Front Angle: {set_tool_data.front_angle}°")

        print("Tool Change Details: ", set_tool_data.toolchange_details)

        # Access values using dictionary keys
        self.xChangePos.setText(str(set_tool_data.toolchange_details["x_pos"]))
        self.zChangePos.setText(str(set_tool_data.toolchange_details["z_pos"]))

        # Set the radio buttons based on move sequence
        if set_tool_data.toolchange_details["move_sequence"] == "simultaneous":
            self.radioButton_4.setChecked(True)
        elif set_tool_data.toolchange_details["move_sequence"] == "x_first":
            self.radioButton_5.setChecked(True)
        elif set_tool_data.toolchange_details["move_sequence"] == "z_first":
            self.radioButton_6.setChecked(True)

        # Set spindle stop option
        if set_tool_data.toolchange_details["stop_spindle"]:
            self.radioButton_3.setChecked(True)  # Yes
        else:
            self.radioButton_7.setChecked(True)  # No
