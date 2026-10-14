"""QML and assets shared by every feature.

Each directory here is a QML module, so a screen anywhere in the package can
say ``import theme 1.0``, ``import touchable_input 1.0`` or ``import common 1.0``
once :data:`QML_IMPORT_DIR` is on its engine's import path.
"""

import os

QML_IMPORT_DIR = os.path.dirname(os.path.abspath(__file__))
