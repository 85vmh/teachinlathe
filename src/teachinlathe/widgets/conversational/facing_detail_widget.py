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

    def update_model(self):
        """Update the facing_data model with values from the UI."""
        try:
            self.facing_data.css_value = int(self.cssValue.text())
        except ValueError:
            self.facing_data.css_value = 0

        try:
            self.facing_data.max_speed = int(self.maxSpeed.text())
        except ValueError:
            self.facing_data.max_speed = 0

        try:
            self.facing_data.feed_rate = float(self.feedRate.text())
        except ValueError:
            self.facing_data.feed_rate = 0.0

        try:
            self.facing_data.x_start = float(self.xStart.text())
        except ValueError:
            self.facing_data.x_start = 0.0

        try:
            self.facing_data.z_start = float(self.zStart.text())
        except ValueError:
            self.facing_data.z_start = 0.0

        try:
            self.facing_data.x_end = float(self.xEnd.text())
        except ValueError:
            self.facing_data.x_end = 0.0

        try:
            self.facing_data.z_end = float(self.zEnd.text())
        except ValueError:
            self.facing_data.z_end = 0.0

        try:
            self.facing_data.doc = float(self.doc.text())
        except ValueError:
            self.facing_data.doc = 0.0

        try:
            self.facing_data.retract = float(self.retract.text())
        except ValueError:
            self.facing_data.retract = 0.0

        # Checkbox for Z0 update
        self.facing_data.z_end_becomes_new_z0 = self.zEndAsZero.isChecked()
