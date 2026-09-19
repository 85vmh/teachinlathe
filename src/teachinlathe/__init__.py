#!/usr/bin/env python

"""TeachInLathe - a LinuxCNC control panel for TeachIn lathes.

Launched from the LinuxCNC config's ``[DISPLAY] DISPLAY`` line, or by hand::

    $ teachinlathe --ini=/path/to/config.ini

The INI path is also read from ``$INI_FILE_NAME``, which LinuxCNC sets for
whatever it starts, so the argument is only needed when running it directly.
"""

__version__ = '0.0.1'

import argparse
import logging
import os
import signal
import sys

# LinuxCNC's own Qt modules - qt5_graphics, and the qtvcp it pulls in - go
# through QtPy, which picks PyQt5 unless told otherwise. Two bindings loaded
# into one process do not survive contact with each other, so the binding is
# pinned here: this package's __init__ runs before any submodule can import
# them. ``setdefault`` leaves an explicit QT_API from the environment alone.
os.environ.setdefault("QT_API", "pyqt6")

# Qt6 picks the Fusion style for Quick Controls on desktop Linux, where Qt5
# used the plain "Default" style that this UI was drawn against. Fusion is not
# a repaint - it changes metrics: a Button drops from 40px to 26px high, which
# is the difference between hitting it with a glove on and not. "Basic" is the
# Qt6 name for the style Qt5 called "Default", and restores both the metrics
# and the palette text colour exactly.
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication

from teachinlathe.app_identity import APPLICATION_DISPLAY_NAME, APPLICATION_ID
from teachinlathe.logging_setup import configure as configure_logging

log = logging.getLogger(__name__)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog='teachinlathe', description=__doc__.splitlines()[0])
    parser.add_argument('--ini', metavar='PATH',
                        help='the LinuxCNC INI file (default: $INI_FILE_NAME)')
    parser.add_argument('--log-level', default='DEBUG',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='how much to log (default: DEBUG)')
    parser.add_argument('--log-file', metavar='PATH',
                        help='where to log (default: ~/teachinlathe.log)')
    parser.add_argument('--fullscreen', action='store_true',
                        help='start full screen rather than maximised')
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)
    # LinuxCNC appends its own arguments to the DISPLAY line; ignore what we
    # do not recognise rather than refusing to start because of it.
    args, unknown = parser.parse_known_args(argv)
    if unknown:
        log.debug("ignoring unrecognised arguments: %s", " ".join(unknown))
    return args


def main(argv=None):
    args = parse_args(argv)
    configure_logging(level=args.log_level, log_file=args.log_file)

    if args.ini:
        os.environ['INI_FILE_NAME'] = os.path.abspath(args.ini)
    if not os.environ.get('INI_FILE_NAME'):
        log.error("no INI file: pass --ini or set INI_FILE_NAME")
        return 2
    os.environ.setdefault('CONFIG_DIR',
                          os.path.dirname(os.environ['INI_FILE_NAME']))

    log.info("starting %s %s with %s", APPLICATION_DISPLAY_NAME, __version__,
             os.environ['INI_FILE_NAME'])

    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings, True)
    app = QApplication(sys.argv if argv is None else [sys.argv[0]])
    app.setApplicationName(APPLICATION_DISPLAY_NAME)
    app.setApplicationDisplayName(APPLICATION_DISPLAY_NAME)
    app.setApplicationVersion(__version__)
    app.setDesktopFileName(APPLICATION_ID)

    # Ctrl-C and `kill` should close the window, not tear the process down
    # under a running event loop: shutting down cleanly is what unloads the
    # HAL component, and a component that outlives its process blocks the
    # next start. The timer exists only so the interpreter gets a slice in
    # which to run the handler; Qt would otherwise sit in select().
    stopping = []

    def shutdown(signum, _frame):
        log.info("caught %s, closing", signal.Signals(signum).name)
        stopping.append(signum)
        # quit() does nothing before exec() has been reached, so a signal
        # during start-up would otherwise be swallowed and the window would
        # come up anyway. The flag is checked below.
        app.quit()

    def install_signal_handlers():
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, shutdown)

    install_signal_handlers()

    wake = QTimer()
    wake.start(200)
    wake.timeout.connect(lambda: None)

    from teachinlathe.mainwindow import MyMainWindow

    if stopping:
        log.info("interrupted while starting up")
        return 0

    window = MyMainWindow()

    # Again, on purpose. Creating a HAL component replaces the SIGTERM
    # handler with the one that raises KeyboardInterrupt - LinuxCNC's binding
    # does that so a userspace component dies when told to - and the window
    # creates ours. Left alone, `kill` would tear the process down mid-loop
    # and leave the HAL component registered, blocking the next start.
    install_signal_handlers()

    # Queued, not called straight away. The window builds its QML screens on
    # queued callbacks of its own, and under Qt6 adding a QQuickWidget to a
    # window that is already on screen forces the native window to be
    # recreated: the maximized state is lost and what is left is a 200x100
    # stub. Queueing the show behind those callbacks means every QQuickWidget
    # exists before the window is mapped. Qt5 did not care either way.
    show = window.showFullScreen if args.fullscreen else window.showMaximized
    QTimer.singleShot(0, show)

    if stopping:
        log.info("interrupted while starting up")
        return 0

    try:
        return app.exec()
    except KeyboardInterrupt:
        # Only reachable if the interpreter takes the signal between the
        # handler running and the loop noticing; exiting quietly is the whole
        # point of handling it.
        log.info("interrupted")
        return 0


if __name__ == '__main__':
    sys.exit(main())
