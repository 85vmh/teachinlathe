# ProgramListModel.py
from datetime import datetime

from PyQt5.QtCore import Qt, QAbstractListModel, QModelIndex, QVariant, pyqtSlot

from teachinlathe.date_utils import format_recent_datetime_string

class ProgramListModel(QAbstractListModel):
    ProgramNameRole = Qt.UserRole + 1
    CreatedDateRole = Qt.UserRole + 2
    LastEditDateRole = Qt.UserRole + 3
    ProgramOperationsRole = Qt.UserRole + 4
    ProgramIdRole = Qt.UserRole + 5

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

    def data(self, index, role=Qt.DisplayRole):
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

    def _display_name_for_op(self, op):
        op_type = getattr(op, "type", "") or ""
        if op_type == "changeTool":
            tool_no = getattr(op, "tool_no", None)
            return f"Tool Change (T{tool_no})" if tool_no is not None else "Tool Change"
        if op_type == "positionAt":
            return "Position At"
        if op_type == "facing":
            return "Facing"
        if op_type == "defineProfile":
            profile_id = getattr(op, "profile_id", None)
            profile_type = getattr(op, "profile_type", None)
            pt = profile_type.value if hasattr(profile_type, "value") else str(profile_type or "od").lower()
            type_str = "OD" if pt == "od" else "ID"
            return f"Define {type_str} Profile (P{profile_id})" if profile_id is not None else f"Define {type_str} Profile"
        if op_type == "profiling":
            profile_id = getattr(getattr(op, "profilingParameters", None), "profile_id", None)
            strategy = getattr(getattr(op, "profilingOptions", None), "strategy", None)
            strategy_value = strategy.value if hasattr(strategy, "value") else str(strategy or "").lower()
            prefix = "G71 " if strategy_value == "rough" else "G70 " if strategy_value == "finish" else ""
            if profile_id is not None and strategy:
                strategy_str = strategy.value.capitalize() if hasattr(strategy, "value") else str(strategy).capitalize()
                return f"{prefix}Cut Profile (P{profile_id}, {strategy_str})"
            if profile_id is not None:
                return f"{prefix}Cut Profile (P{profile_id})"
            return f"{prefix}Cut Profile" if prefix else "Cut Profile"
        if op_type == "profileRoughing":
            profile_id = getattr(getattr(op, "profilingParameters", None), "profile_id", None)
            profiling_type = getattr(getattr(op, "profileRoughingStrategy", None), "profiling_type", None)
            pt = profiling_type.value if hasattr(profiling_type, "value") else str(profiling_type or "od").lower()
            prefix = "OD" if pt == "od" else "ID"
            return f"{prefix} Profile Roughing (P{profile_id})" if profile_id is not None else f"{prefix} Profile Roughing"
        if op_type == "profileContour":
            profile_id = getattr(getattr(op, "profilingParameters", None), "profile_id", None)
            profiling_type = getattr(getattr(op, "profileContourStrategy", None), "profiling_type", None)
            pt = profiling_type.value if hasattr(profiling_type, "value") else str(profiling_type or "od").lower()
            prefix = "OD" if pt == "od" else "ID"
            return f"{prefix} Profile Contour (P{profile_id})" if profile_id is not None else f"{prefix} Profile Contour"
        if op_type == "threading":
            pitch = getattr(op, "pitch", None)
            return f"G76 Threading (P: {pitch})" if pitch is not None else "G76 Threading"
        if op_type == "g33Threading":
            pitch = getattr(op, "pitch", None)
            return f"G33 Threading (P: {pitch})" if pitch is not None else "G33 Threading"
        if op_type == "drilling":
            return "Drilling"
        if op_type == "tapping":
            return "Tapping"
        if op_type == "parting":
            return "Parting"
        return op_type or "Unknown"

    def _operations_summary(self, program):
        ops = getattr(program, "operations", []) or []
        visible_ops = [op for op in ops if getattr(op, "type", "") != "changeTool"]
        if not visible_ops:
            return "No operations yet, tap to change that"
        return "||".join(
            f"{1 if bool(getattr(op, 'generate_gcode', False)) else 0}::{self._display_name_for_op(op)}"
            for op in visible_ops
        )
