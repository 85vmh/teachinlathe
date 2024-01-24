import os

from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QColor, QPalette
from qtpy import uic
from qtpy.QtWidgets import QWidget
from qtpyvcp.utilities import logger

LOG = logger.getLogger(__name__)

UI_FILE = os.path.join(os.path.dirname(__file__), "lathe_fixture.ui")


class LatheFixture(QWidget):
    zMinusLimitUpdated = QtCore.pyqtSignal(float)
    onFixtureSelected = QtCore.pyqtSignal(int)

    def __init__(self, fixture, is_active=False, parent=None):
        super(LatheFixture, self).__init__(parent)
        uic.loadUi(UI_FILE, self)
        self.fixture = fixture

        if fixture.image_url:
            print("image_url: ", fixture.image_url)
            pixmap = QPixmap(fixture.image_url)
            if not pixmap.isNull():
                # Optional: Scale the pixmap to fit the label (if needed)
                pixmap = pixmap.scaled(self.imageView.width(), self.imageView.height(), Qt.KeepAspectRatio)
                self.imageView.setPixmap(pixmap)
                self.imageView.setAlignment(Qt.AlignCenter)
            else:
                LOG.warning(f"Unable to load image: {fixture.image_url}")

        diameter_value = str(fixture.diameter) if fixture.diameter is not None else "N/A"
        units_value = str(fixture.units) if fixture.units is not None else "--"

        self.description.setText(fixture.description)
        self.diameter.setText(diameter_value)
        self.units.setText(units_value)
        self.maxRpm.setText(str(fixture.max_rpm))
        self.zMinusLimit.setText(str(fixture.z_minus_limit))
        self.teachZMinus.currentValue.connect(self._teachZMinusClicked)
        self._setActive(is_active)

    def mousePressEvent(self, event):
        # Emit the signal with the fixture object when the widget is clicked
        self.onFixtureSelected.emit(self.fixture.fixture_index)

    def _setActive(self, active):
        if active:
            # Change appearance for active state
            palette = self.palette()
            palette.setColor(QPalette.Window, QColor('lightblue'))  # Example color
            self.setPalette(palette)
            self.setAutoFillBackground(True)
        else:
            # Reset appearance for inactive state
            self.setAutoFillBackground(False)

    def _teachZMinusClicked(self, value):
        self.zMinusLimit.setText(str(value))
        self.fixture.z_minus_limit = value
        self.zMinusLimitUpdated.emit(value)
