"""The UI: a directory per tab under ``tabs/``, and the QML and assets they
share.

The shared directories are QML modules, so a screen anywhere in the package
can say ``import theme 1.0``, ``import common 1.0`` or
``import common.touchable_input 1.0`` once :data:`QML_IMPORT_DIR` is on its
engine's import path.
"""

import os

QML_IMPORT_DIR = os.path.dirname(os.path.abspath(__file__))
