"""The list models behind the Tool Library tab.

Each model's rows are a frozen dataclass, and the dataclass is the model's
role list: its field names are what QML sees as roles, so adding a role is
adding a field.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from typing import Any, List, Optional, Set, Type

from PyQt6.QtCore import (QAbstractListModel, QModelIndex, QObject, Qt,
                          pyqtProperty, pyqtSignal, pyqtSlot)

from teachinlathe.tooling.data_types import CuttingToolType, to_json
from teachinlathe.tooling.tool_library_store import ToolLibraryStore
from teachinlathe.widgets.tools_qml.BladeToolView import BladeToolView
from teachinlathe.widgets.tools_qml.DrillingToolView import DrillingToolView
from teachinlathe.widgets.tools_qml.ReamingToolView import ReamingToolView
from teachinlathe.widgets.tools_qml.TappingToolView import TappingToolView
from teachinlathe.widgets.tools_qml.ThreadingToolView import ThreadingToolView
from teachinlathe.widgets.tools_qml.TurningToolView import TurningToolView

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


# ── Tool holders ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class HolderRow:
    holderId: int
    text: str        # the holder as it is stored, one "key: value" per field
    toolText: str    # what is clamped in it, or empty
    ready: bool


class ToolHolderListModel(DataclassListModel):
    def __init__(self, store: ToolLibraryStore, parent=None):
        super().__init__(HolderRow, parent)
        self._store = store
        self.refresh()

    def refresh(self) -> None:
        rows = []
        for holder in self._store.holders:
            tool = self._store.find_tool(holder.cutting_tool_id)
            rows.append(HolderRow(
                holderId=holder.tool_holder_id,
                # A no-break space keeps each "key: value" on one line.
                text="   ".join(f"{key}:\u00a0{json.dumps(value)}"
                                for key, value in to_json(holder).items()),
                toolText=f"{tool.tool_type.label}: {tool.summary()}" if tool else "",
                ready=holder.is_ready,
            ))
        self.setRows(rows)


# ── Cutting tools ───────────────────────────────────────────────────────────


class CuttingToolSummary(QObject):
    """A cutting tool of a kind that has no card of its own yet: its id and
    a line of text."""

    def __init__(self, tool, parent=None):
        super().__init__(parent)
        self._tool = tool

    @pyqtProperty(int, constant=True)
    def cuttingToolId(self):
        return self._tool.cutting_tool_id

    @pyqtProperty(str, constant=True)
    def text(self):
        return self._tool.summary()


@dataclass(frozen=True)
class CategoryRow:
    toolType: str        # the CuttingToolType value, for the header's actions
    label: str           # the heading
    count: int
    expanded: bool
    card: str            # how the tools are drawn: "turning" (TurningToolViews),
                         # "threading" (ThreadingToolViews), "blade"
                         # (BladeToolViews), "drilling" (DrillingToolViews),
                         # "reaming" (ReamingToolViews), "tapping" (TappingToolViews) or "summary"
                         # (CuttingToolSummary, a line of text)
    tools: list          # the views, one per tool, in file order


#: The categories drawn as full cards, and the view each card reads. A
#: boring bar is a turning tool with a body: the same insert, angles and
#: card. The rest are CuttingToolSummary lines.
_CARDS = {
    CuttingToolType.TURNING: ("turning", TurningToolView),
    CuttingToolType.BORING: ("turning", TurningToolView),
    CuttingToolType.THREADING: ("threading", ThreadingToolView),
    CuttingToolType.BLADE: ("blade", BladeToolView),
    CuttingToolType.DRILLING: ("drilling", DrillingToolView),
    CuttingToolType.REAMING: ("reaming", ReamingToolView),
    CuttingToolType.TAPPING: ("tapping", TappingToolView),
}


class CuttingToolCategoriesModel(DataclassListModel):
    """The cutting tools, one row per category, the category's tools inside
    it - so the screen can lay a category's tools out as cards, side by
    side, under its header."""

    #: A category was folded or unfolded: allExpanded and allCollapsed may
    #: have changed.
    expansionChanged = pyqtSignal()

    def __init__(self, store: ToolLibraryStore, parent=None):
        super().__init__(CategoryRow, parent)
        self._store = store
        self._collapsed: Set[CuttingToolType] = set()
        self._views: List[QObject] = []
        self.refresh()

    @pyqtSlot(str)
    def toggle(self, tool_type: str) -> None:
        """Fold or unfold a category. Only that row changes, so the list
        keeps where it was scrolled to."""
        tool_type = CuttingToolType(tool_type)
        self._collapsed ^= {tool_type}
        for index, row in enumerate(self._rows):
            if row.toolType == tool_type.value:
                self.replaceRow(index, dataclasses.replace(
                    row, expanded=self.isExpanded(tool_type)))
        self.expansionChanged.emit()

    @pyqtSlot(bool)
    def setAllExpanded(self, expanded: bool) -> None:
        """Unfold, or fold, every category at once. The rows are changed in
        place, like toggle(), so the list keeps where it was scrolled to."""
        self._collapsed = set() if expanded else set(CuttingToolType)
        for index, row in enumerate(self._rows):
            if row.expanded != expanded:
                self.replaceRow(index, dataclasses.replace(row, expanded=expanded))
        self.expansionChanged.emit()

    @pyqtProperty(bool, notify=expansionChanged)
    def allExpanded(self):
        """Every category unfolded: nothing left for "expand all" to do."""
        return not self._collapsed

    @pyqtProperty(bool, notify=expansionChanged)
    def allCollapsed(self):
        """Every category folded: nothing left for "collapse all" to do."""
        return self._collapsed >= set(CuttingToolType)

    def isExpanded(self, tool_type: CuttingToolType) -> bool:
        return tool_type not in self._collapsed

    def refresh(self) -> None:
        """Read the store again. A category whose tools are the same objects
        as before keeps its views, and so its row: the store replaces a
        tool it saves, so only the categories that were edited are redrawn,
        and the list stays where it was scrolled to."""
        old_rows = {row.toolType: row for row in self._rows}
        rows = []
        views = []
        for tool_type in CuttingToolType:
            tools = self._store.tools_of(tool_type)
            card, view_class = _CARDS.get(tool_type, ("summary", CuttingToolSummary))
            old = old_rows.get(tool_type.value)
            if old is not None and len(old.tools) == len(tools) \
                    and all(view._tool is tool for view, tool in zip(old.tools, tools)):
                tool_views = old.tools
            else:
                tool_views = [view_class(tool, self) for tool in tools]
            views.extend(tool_views)
            rows.append(CategoryRow(
                toolType=tool_type.value, label=tool_type.label, count=len(tools),
                expanded=self.isExpanded(tool_type), card=card,
                tools=tool_views))
        kept = {id(view) for view in views}
        old_views, self._views = self._views, views
        self.setRows(rows)
        for view in old_views:
            if id(view) not in kept:
                view.deleteLater()

    def categoryRow(self, tool_type: CuttingToolType) -> Optional[CategoryRow]:
        return next((r for r in self._rows if r.toolType == tool_type.value), None)
