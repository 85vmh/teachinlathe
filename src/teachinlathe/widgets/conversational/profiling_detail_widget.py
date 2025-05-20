from PyQt5.QtWidgets import QWidget
from teachinlathe.conversational.data_types import Profiling, Strategy
from teachinlathe.widgets.conversational.profiling_detail import Ui_ProfilingDetailForm


class ProfilingDetailsWidget(QWidget, Ui_ProfilingDetailForm):
    def __init__(self, profiling_data: Profiling, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.profiling_data = profiling_data  # Store the Profiling object
        print("ProfilingDetailsWidget: ", profiling_data)

        # Populate UI fields with Profiling data
        self.cssValue.setText(str(profiling_data.css_value))
        self.maxSpeed.setText(str(profiling_data.max_speed))
        self.feedRate.setText(str(profiling_data.feed_rate))
        self.profileId.setText(str(profiling_data.profileId))

        self.xStart.setText(str(profiling_data.x_start))
        self.zStart.setText(str(profiling_data.z_start))
        self.doc.setText(str(profiling_data.doc))
        self.retract.setText(str(profiling_data.retract))

        # Handle optional fields
        stock_x = profiling_data.stock_to_leave.get("x", 0) if profiling_data.stock_to_leave else 0
        self.stockToLeave.setText(str(stock_x))
        self.springPasses.setText(str(profiling_data.spring_passes if profiling_data.spring_passes else 0))

        # Set initial visibility based on strategy
        self.set_roughing_visible(profiling_data.strategy == Strategy.ROUGH)

        # Connect radio buttons to switch stacked widget pages
        self.radioRoughing.toggled.connect(lambda: self.set_roughing_visible(self.radioRoughing.isChecked()))
        self.radioFinishing.toggled.connect(lambda: self.set_roughing_visible(not self.radioRoughing.isChecked()))

    def set_roughing_visible(self, is_roughing: bool):
        """Set stacked widget and button visibility based on strategy."""
        if is_roughing:
            self.stackedWidget.setCurrentWidget(self.pageRoughing)
        else:
            self.stackedWidget.setCurrentWidget(self.pageFinishing)

        self.btnFinishSameTool.setVisible(is_roughing)
        self.btnFinishDifferentTool.setVisible(is_roughing)
