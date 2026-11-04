"""The UI: a directory per tab under ``tabs/``, and the QML and assets they
share.

Every directory with QML in it is a QML module (its qmldir), named after its
path from here: ``import theme``, ``import common.touchable_input``,
``import tabs.conversational`` - from any file, once :data:`QML_IMPORT_DIR` is
on its engine's import path. Imports carry no version.
"""

import os

QML_IMPORT_DIR = os.path.dirname(os.path.abspath(__file__))
