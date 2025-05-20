from PyQt5.QtWidgets import QWidget
from teachinlathe.conversational.data_types import Facing
from teachinlathe.widgets.conversational.facing_detail import Ui_FacingDetailForm


class FacingDetailsWidget(QWidget, Ui_FacingDetailForm):
    def __init__(self, facing_data: Facing, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.facing_data = facing_data  # Store the Facing object
        print("FacingDetailsWidget: ", facing_data)

        # Populate UI fields with Facing data
        self.cssValue.setText(str(facing_data.css_value))
        self.maxSpeed.setText(str(facing_data.max_speed))
        self.feedRate.setText(str(facing_data.feed_rate))

        self.xStart.setText(str(facing_data.x_start))
        self.zStart.setText(str(facing_data.z_start))
        self.xEnd.setText(str(facing_data.x_end))
        self.zEnd.setText(str(facing_data.z_end))
        self.doc.setText(str(facing_data.doc))
        self.retract.setText(str(facing_data.retract))

        # Set the checkbox based on z_end_becomes_new_z0
        self.zEndAsZero.setChecked(facing_data.z_end_becomes_new_z0)
