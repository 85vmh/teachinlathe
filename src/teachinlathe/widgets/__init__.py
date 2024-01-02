from qtpyvcp.widgets.qtdesigner import _DesignerPlugin

from .teachin_lathe_dro import TeachInLatheDro
class TeachInLatheDro_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return TeachInLatheDro

from .joystick_status import JoystickStatus
class JoystickStatus_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return JoystickStatus