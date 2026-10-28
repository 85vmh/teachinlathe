"""A list model whose rows are a frozen dataclass: the dataclass is the
model's role list - its field names are what QML sees as roles, so adding a
role is adding a field. The Tool Library's lists and the Conversational
tab's operation list are made of it."""

from __future__ import annotations

import dataclasses
from typing import Any, List, Type

from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt


class DataclassListModel(QAbstractListModel):
    """A list model whose roles are the fields of its row dataclass."""

    def __init__(self, row_type: Type[Any], parent=None):
        super().__init__(parent)
        self._fields = [f.name for f in dataclasses.fields(row_type)]
        self._rows: List[Any] = []

    def roleNames(self):
        first = Qt.ItemDataRole.UserRole + 1
        return {first + i: name.encode() for i, name in enumerate(self._fields)}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        field = role - (Qt.ItemDataRole.UserRole + 1)
        if not 0 <= field < len(self._fields):
            return None
        return getattr(self._rows[index.row()], self._fields[field])

    def rows(self) -> List[Any]:
        return list(self._rows)

    def setRows(self, rows: List[Any]) -> None:
        """Show these rows. As many as before, only the ones that differ are
        changed, in place: a reset would scroll the list back to its top,
        and a list refreshed after an edit should stay where it was."""
        if len(rows) != len(self._rows):
            self.beginResetModel()
            self._rows = list(rows)
            self.endResetModel()
            return
        for index, row in enumerate(rows):
            if row != self._rows[index]:
                self.replaceRow(index, row)

    def replaceRow(self, index: int, row: Any) -> None:
        self._rows[index] = row
        self.dataChanged.emit(self.index(index), self.index(index))
