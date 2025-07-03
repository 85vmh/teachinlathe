import sys
from PyQt5.QtCore import Qt, QAbstractListModel, QModelIndex, QVariant, pyqtProperty, QObject
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtQml import QQmlApplicationEngine, qmlRegisterType


# Clasa Program cu proprietăți PyQt
class Program(QObject):
    def __init__(self, programName, creationDate, lastEditDate, parent=None):
        super().__init__(parent)
        self._programName = programName
        self._creationDate = creationDate
        self._lastEditDate = lastEditDate

    @pyqtProperty(str)
    def programName(self):
        return self._programName

    @pyqtProperty(str)
    def creationDate(self):
        return self._creationDate

    @pyqtProperty(str)
    def lastEditDate(self):
        return self._lastEditDate


# Modelul listă pentru QML
class ProgramListModel(QAbstractListModel):
    ProgramNameRole = Qt.UserRole + 1
    CreationDateRole = Qt.UserRole + 2
    LastEditDateRole = Qt.UserRole + 3

    def __init__(self, programs=None):
        super().__init__()
        self._programs = programs or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._programs)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        program = self._programs[index.row()]
        if role == self.ProgramNameRole:
            return program.programName
        if role == self.CreationDateRole:
            return program.creationDate
        if role == self.LastEditDateRole:
            return program.lastEditDate
        return QVariant()

    def roleNames(self):
        return {
            self.ProgramNameRole: b'programName',
            self.CreationDateRole: b'creationDate',
            self.LastEditDateRole: b'lastEditDate',
        }


# Lista exemplu de programe
programs_list = [
    Program("Drill Hole", "2025-05-01", "2025-05-10"),
    Program("Lathe Turn", "2025-04-20", "2025-05-08"),
    Program("Lathe Groove", "2025-04-20", "2025-05-08"),
    Program("Lathe Parting", "2025-04-20", "2025-05-08"),
    Program("Piesa Bogdan", "2025-04-20", "2025-05-08"),
    Program("Cut Groove", "2025-03-15", "2025-04-12"),
]


# Cod QML inline pentru listă simplă
qml_code = """
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    visible: true
    width: 640
    height: 480
    title: "Programs List"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 10

        Label {
            text: "Programs"
            font.pixelSize: 24
            Layout.alignment: Qt.AlignHCenter
        }

        ListView {
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: programsModel
            delegate: Rectangle {
                height: 40
                width: listView.width
                color: index % 2 === 0 ? "#ffffff" : "#e6e6e6"

                RowLayout {
                    anchors.fill: parent
                    spacing: 10
                    Label { text: (index + 1).toString(); width: 30 }
                    Label { text: programName; width: 200 }
                    Label { text: creationDate; width: 120 }
                    Label { text: lastEditDate; width: 120 }
                }
            }
        }
    }
}
"""


def main():
    app = QGuiApplication(sys.argv)

    model = ProgramListModel(programs_list)

    engine = QQmlApplicationEngine()

    # Expune modelul în context
    engine.rootContext().setContextProperty("programsModel", model)

    # Încarcă QML din string
    engine.loadData(bytes(qml_code, encoding='utf-8'))

    if not engine.rootObjects():
        print("Error: no root objects loaded")
        return -1

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
