"""The application shell: start-up, the window, the app-wide QML.

The QML here - app_shell_qml, dev_panel_qml - is imported as modules, so
:data:`APP_QML_IMPORT_DIR` goes on an engine's import path beside
``teachinlathe.ui.QML_IMPORT_DIR``.
"""

import os

APP_QML_IMPORT_DIR = os.path.dirname(os.path.abspath(__file__))
