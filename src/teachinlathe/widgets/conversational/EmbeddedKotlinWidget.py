import os
import subprocess

from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QWidget
from PyQt5.QtGui import QWindow
from Xlib import display


def find_window_by_title(title):
    dsp = display.Display()
    root = dsp.screen().root
    for win in root.query_tree().children:
        try:
            if win.get_wm_name() == title:
                return win.id
        except:
            continue
    return None

class EmbeddedKotlinWidget(QWidget):
    def __init__(self, binary_path, window_title, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)

        # # Pornește aplicația Kotlin
        # self.process = subprocess.Popen(
        #     [binary_path],
        #     env=dict(os.environ, DISPLAY=":0")
        # )
        # self.window_title = window_title

        # Încearcă să o embedezi după 1.5 secunde
        QTimer.singleShot(1500, self.try_embed)

    def try_embed(self):
        # win_id = find_window_by_title(self.window_title)
        # print("Found win_id:", win_id)
        #
        # if not win_id:
        #     print("Fereastra Kotlin nu a fost găsită.")
        #     return

        qwindow = QWindow.fromWinId(0x6000001)
        qwindow.setFlags(QtCore.Qt.FramelessWindowHint)
        qwindow.setGeometry(0, 0, self.width(), self.height())
        qwindow.show()

        container = QWidget.createWindowContainer(qwindow, self)
        container.setMinimumSize(800, 600)
        container.setFocusPolicy(QtCore.Qt.TabFocus)
        container.setContentsMargins(0, 0, 0, 0)

        self.layout().addWidget(container)

