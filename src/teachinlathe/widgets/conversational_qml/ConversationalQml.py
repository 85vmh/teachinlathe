import os
from PyQt5.QtCore import QUrl, QObject
from PyQt5.QtQuick import QQuickItem
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

        # Put the model in QML context before loading Root.qml
        self.model = ProgramListModel(programs_list)
        self.engine().rootContext().setContextProperty("programsModel", self.model)

        root_path = os.path.join(self.base_dir, "Root.qml")
        self.statusChanged.connect(self.onStatusChanged)
        self.setSource(QUrl.fromLocalFile(root_path))

    def onStatusChanged(self, status):
        if status == QQuickWidget.Ready:
            self.root = self.rootObject()
            if not self.root:
                print("Failed to load Root.qml")
                return

            print("----Model count:", self.model.rowCount())

            # Load main screen; showBack=False on first screen
            main_url = QUrl.fromLocalFile(os.path.join(self.base_dir, "MainScreen.qml")).toString()
            self.root.loadScreen(main_url, {"programsModel": self.model, "showBack": False})

            # Find the Loader by objectName
            loader = self.root.findChild(QQuickItem, "loader")
            if loader is None:
                loader = self.root.findChild(QObject, "loader")
            if loader is None:
                print("Failed to find Loader object with objectName 'loader'")
                return

            # Connect to itemChanged (Qt5: no args)
            try:
                loader.itemChanged.connect(self.onLoaderItemChanged)
            except Exception as e:
                print("Failed to connect itemChanged:", e)

            # If the item already exists, hook immediately
            current_item = loader.property("item")
            if current_item:
                self._hook_screen_item(current_item)

    def onLoaderItemChanged(self):
        sender = self.sender()
        if not sender:
            return
        item = sender.property("item")
        if item:
            self._hook_screen_item(item)

    def _hook_screen_item(self, item):
        """Connect expected QML signals from the loaded screen."""
        try:
            if hasattr(item, "addNewProgramRequested"):
                item.addNewProgramRequested.connect(self.openChildScreen)
            if hasattr(item, "editProgramRequested"):
                item.editProgramRequested.connect(self.openChildScreen)
            if hasattr(item, "backRequested"):
                item.backRequested.connect(self.goBack)
            print("Screen signals connected.")
        except Exception as e:
            print("Failed to hook screen item signals:", e)

    def addNewProgram(self):
        print("add new program clicked")

    def openChildScreen(self, program=None):
        child_url = QUrl.fromLocalFile(os.path.join(self.base_dir, "ChildScreen.qml")).toString()
        params = {"showBack": True}
        print("openChild Screen with program:", str(program))
        if program:
            params["selectedProgram"] = program
        self.root.loadScreen(child_url, params)

    def goBack(self):
        print("back button clicked")
        self.root.goBack()
