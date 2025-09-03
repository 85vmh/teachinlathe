from PyQt5.QtCore import Qt, QAbstractListModel, QModelIndex, QVariant


class ProgramListModel(QAbstractListModel):
    ProgramNameRole = Qt.UserRole + 1
    LastEditDateRole = Qt.UserRole + 2

    def __init__(self, programs=None):
        super().__init__()
        self._programs = programs or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._programs)

    def get(self, index):
        if 0 <= index < len(self._programs):
            return self._programs[index]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        program = self._programs[index.row()]
        if role == self.ProgramNameRole:
            return program.header.name
        if role == self.LastEditDateRole:
            return program.header.last_edit
        return QVariant()

    def roleNames(self):
        return {
            self.ProgramNameRole: b'programName',
            self.LastEditDateRole: b'lastEditDate',
        }
