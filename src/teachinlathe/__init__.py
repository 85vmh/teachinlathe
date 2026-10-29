#!/usr/bin/env python

"""TeachInLathe - a LinuxCNC control panel for TeachIn lathes.

Launched from the LinuxCNC config's ``[DISPLAY] DISPLAY`` line, or by hand::

    $ teachinlathe --ini=/path/to/config.ini

The INI path is also read from ``$INI_FILE_NAME``, which LinuxCNC sets for
whatever it starts, so the argument is only needed when running it directly.
"""

__version__ = '0.0.1'

import os

# LinuxCNC's own Qt modules - qt5_graphics, and the qtvcp it pulls in - go
# through QtPy, which picks PyQt5 unless told otherwise. Two bindings loaded
# into one process do not survive contact with each other, so the binding is
# pinned here: this package's __init__ runs before any submodule can import
# them. ``setdefault`` leaves an explicit QT_API from the environment alone.
#
# Only the environment is set here, nothing imported: the G-code generation
# and the domain under this package load this file too, and they need
# neither Qt nor LinuxCNC. The application itself is teachinlathe.app.main.
os.environ.setdefault("QT_API", "pyqt6")

# Qt6 picks the Fusion style for Quick Controls on desktop Linux, and Fusion
# is not a repaint - it changes metrics. Measured: a Button is 40px high under
# "Basic" and 24px under Fusion, which is the difference between hitting it
# with a glove on and not. "Basic" is the style this UI was drawn against, and
# it restores the palette text colour with the metrics.
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

# The G-code preview draws with the renderer LinuxCNC shares between its
# screens (rs274.glcanon_gl), straight into the Qt Quick scene graph. That
# needs the scene graph on OpenGL rather than whichever RHI backend Qt picks,
# and it needs to render on the GUI thread: the preview reads linuxcnc status
# and the position logger while it draws, neither of which is thread-safe.
os.environ.setdefault("QSG_RENDER_LOOP", "basic")


def main(argv=None):
    """Starts the application: teachinlathe.app.main."""
    from teachinlathe.app.main import main as start
    return start(argv)
