#!/usr/bin/env python

"""Main entry point for TeachInLathe.

This module contains the code necessary to be able to launch QControl
directly from the command line, without using qtpyvcp. It handles
parsing command line args and starting the main application.

Example:
    Assuming the dir this file is located in is on the PATH, you can
    launch TeachInLathe by saying::

        $ teachinlathe --ini=/path/to/config.ini [options ...]

    Run with the --help option to print a full list of options.

"""

__version__ = '0.0.1'

import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
import qtpyvcp

from teachinlathe.app_identity import APPLICATION_DISPLAY_NAME, APPLICATION_ID

VCP_DIR = os.path.realpath(os.path.dirname(__file__))
VCP_CONFIG_FILE = os.path.join(VCP_DIR, 'teachinlathe.yml')
IN_DESIGNER = os.getenv('DESIGNER', False)

def main(opts=None):

    QApplication.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings, True)
    QApplication.setApplicationName(APPLICATION_DISPLAY_NAME)
    QApplication.setApplicationDisplayName(APPLICATION_DISPLAY_NAME)
    QApplication.setDesktopFileName(APPLICATION_ID)

    if opts is None:
        from qtpyvcp.utilities.opt_parser import parse_opts
        opts = parse_opts(vcp_cmd='teachinlathe',
                          vcp_name='TeachInLathe',
                          vcp_version=__version__)

    if not opts.get('command_line_args'):
        opts.command_line_args = 'teachinlathe'

    qtpyvcp.run_vcp(opts, VCP_CONFIG_FILE)


if __name__ == '__main__':
    main()
