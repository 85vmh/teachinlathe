import os

from qtpy import uic
from qtpy.QtWidgets import QWidget
from qtpyvcp.utilities import logger

LOG = logger.getLogger(__name__)

UI_FILE = os.path.join(os.path.dirname(__file__), "joystick_status.ui")


class JoystickStatus(QWidget):
    def __init__(self, parent=None):
        super(JoystickStatus, self).__init__(parent)
        uic.loadUi(UI_FILE, self)
