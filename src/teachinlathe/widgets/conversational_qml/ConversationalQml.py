import os
from PyQt5.QtCore import QUrl, QObject
from PyQt5.QtQuickWidgets import QQuickWidget

from teachinlathe.widgets.conversational_qml.Program import Program
from teachinlathe.widgets.conversational_qml.ProgramListModel import ProgramListModel

programs_list = [
    Program("Drill Hole", "2025-05-01", "2025-05-10"),
    Program("Lathe Turn", "2025-04-20", "2025-05-08"),
    Program("Lathe Groove", "2025-04-20", "2025-05-08"),
    Program("Lathe Parting", "2025-04-20", "2025-05-08"),
    Program("Piesa Bogdan", "2025-04-20", "2025-05-08"),
    Program("Cut Groove", "2025-03-15", "2025-04-12"),
]

class ConversationalQml(QQuickWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setResizeMode(QQuickWidget.SizeRootObjectToView)

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        root_path = os.path.join(self.base_dir, "Root.qml")

        self.statusChanged.connect(self.onStatusChanged)
        self.setSource(QUrl.fromLocalFile(root_path))

    def onStatusChanged(self, status):
        if status == QQuickWidget.Ready:
            self.root = self.rootObject()
            if not self.root:
                print("Failed to load Root.qml")
                return

            model = ProgramListModel(programs_list)
            print("----Model count:", model.rowCount())
            self.engine().rootContext().setContextProperty("programsModel", model)

            main_url = QUrl.fromLocalFile(os.path.join(self.base_dir, "MainScreen.qml")).toString()
            self.root.loadScreen(main_url, {"programsModel": model})

            loader = self.root.findChild(QObject, "loader")
            if loader is None:
                print("Failed to find Loader object with id 'loader'")
                return
            loader.itemChanged.connect(self.onLoaderItemChanged)

    def onLoaderItemChanged(self, item):
        if not item:
            return
        try:
            item.addNewProgramRequested.connect(lambda: self.openChildScreen())
            item.editProgramRequested.connect(lambda prog: self.openChildScreen(prog))
            item.backRequested.connect(self.goBack)
        except Exception:
            pass

    def openChildScreen(self, program=None):
        child_url = QUrl.fromLocalFile(os.path.join(self.base_dir, "ChildScreen.qml")).toString()
        params = {}
        if program:
            params["selectedProgram"] = program
        self.root.loadScreen(child_url, params)

    def goBack(self):
        self.root.goBack()
