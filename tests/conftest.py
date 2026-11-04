"""One Qt application for the whole run, made before any test asks for one.

Qt allows a single application object per process, and whichever test
module runs first would otherwise make it: a QCoreApplication from a
repository test leaves the QQuickWindow of a later test with no GUI to run
on, and the process aborts. A QGuiApplication is a QCoreApplication too, so
every module's ``QCoreApplication.instance() or ...`` finds this one.
"""

from PyQt6.QtGui import QGuiApplication

_APP = QGuiApplication.instance() or QGuiApplication([])
