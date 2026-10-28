# ProgramListModel.py
from datetime import datetime

from PyQt6.QtCore import Qt, QAbstractListModel, QModelIndex, QVariant, pyqtSlot

from teachinlathe.conversational.model.qml_adapter import OperationRow, operation_title
from teachinlathe.ui.common.dataclass_list_model import DataclassListModel
from teachinlathe.core.date_utils import format_recent_datetime_string

class ProgramListModel(QAbstractListModel):
    ProgramNameRole = Qt.ItemDataRole.UserRole + 1
    CreatedDateRole = Qt.ItemDataRole.UserRole + 2
    LastEditDateRole = Qt.ItemDataRole.UserRole + 3
    ProgramOperationsRole = Qt.ItemDataRole.UserRole + 4
    ProgramIdRole = Qt.ItemDataRole.UserRole + 5

    def __init__(self, programs=None):
        super().__init__()
        self._programs = programs or []
        self._sort_field = ""
        self._sort_ascending = True

    def rowCount(self, parent=QModelIndex()):
        return len(self._programs)

    def get(self, index):
        if 0 <= index < len(self._programs):
            return self._programs[index]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return QVariant()
        program = self._programs[index.row()]
        if role == self.ProgramNameRole:
            return program.header.name
        if role == self.ProgramIdRole:
            return program.id
        if role == self.CreatedDateRole:
            return format_recent_datetime_string(program.header.created_date)
        if role == self.LastEditDateRole:
            return format_recent_datetime_string(program.header.last_edit)
        if role == self.ProgramOperationsRole:
            return self._operations_summary(program)
        return QVariant()

    def roleNames(self):
        return {
            self.ProgramNameRole: b'programName',
            self.ProgramIdRole: b'programId',
            self.CreatedDateRole: b'createdDate',
            self.LastEditDateRole: b'lastEditDate',
            self.ProgramOperationsRole: b'programOperations',
        }

    def setProgramAt(self, row, program):
        if not (0 <= row < len(self._programs)):
            return False
        self._programs[row] = program
        top = self.index(row)
        bottom = self.index(row)
        self.dataChanged.emit(
            top,
            bottom,
            [self.ProgramNameRole, self.CreatedDateRole, self.LastEditDateRole, self.ProgramOperationsRole],
        )
        return True

    def appendProgram(self, program):
        row = len(self._programs)
        self.beginInsertRows(QModelIndex(), row, row)
        self._programs.append(program)
        self.endInsertRows()
        if self._sort_field:
            self.sortPrograms(self._sort_field, self._sort_ascending)
            return self.indexOfFilename(getattr(program, "filename", None))
        return row

    def removeProgramAt(self, row):
        if not (0 <= row < len(self._programs)):
            return False
        self.beginRemoveRows(QModelIndex(), row, row)
        self._programs.pop(row)
        self.endRemoveRows()
        return True

    def indexOfFilename(self, filename):
        for idx, program in enumerate(self._programs):
            if getattr(program, "filename", None) == filename:
                return idx
        return -1

    def _sort_key(self, program, field):
        header = getattr(program, "header", None)
        if header is None:
            return datetime.min
        raw_value = getattr(header, field, "") or ""
        try:
            return datetime.strptime(str(raw_value), "%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.min

    @pyqtSlot(str, bool)
    def sortPrograms(self, field, ascending):
        if field not in ("created_date", "last_edit"):
            return
        self.layoutAboutToBeChanged.emit()
        self._programs.sort(key=lambda program: self._sort_key(program, field), reverse=not ascending)
        self._sort_field = field
        self._sort_ascending = ascending
        self.layoutChanged.emit()

    def _operations_summary(self, program):
        ops = getattr(program, "operations", []) or []
        if not ops:
            return "No operations yet, tap to change that"
        return "||".join(
            f"{1 if bool(getattr(op, 'generate_gcode', False)) else 0}::"
            f"{operation_title(op, program)}"
            for op in ops
        )


class OperationListModel(DataclassListModel):
    """The open program's operations as the editor lists them, an
    OperationRow each, in order: a row's index is its operation's."""

    def __init__(self, parent=None):
        super().__init__(OperationRow, parent)
