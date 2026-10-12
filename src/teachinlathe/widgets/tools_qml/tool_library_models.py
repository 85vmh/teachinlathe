"""The list models behind the Tool Library tab.

Each model's rows are a frozen dataclass, and the dataclass is the model's
role list: its field names are what QML sees as roles, so adding a role is
adding a field.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Type

from PyQt6.QtCore import (QAbstractListModel, QModelIndex, QObject, Qt,
                          pyqtProperty, pyqtSignal, pyqtSlot)

from teachinlathe.tooling.data_types import CuttingToolType
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
    ready: bool          # a tool, touched off: the holder can be used
    toolId: int          # the mounted cutting tool's id, 0 when empty
    toolCard: str        # which thumbnail and title draw it - CategoryRow.card's values
    toolComment: str     # the operator's note on the tool, or empty
    toolView: Any        # the view the thumbnail reads, or None
    xOffset: str         # as shown: "123.123", or "—" until touched off
    zOffset: str


class MountedToolViews:
    """The views of the tools mounted in the holders, for a list that shows
    them. Its own - not the cutting-tool list's, which throws its away on
    its own refreshes - and kept while the store holds the same tool, as
    the cutting-tool list keeps its.

    Call begin(), then view_for() for each tool shown, then end()."""

    def __init__(self, parent: QObject):
        self._parent = parent
        self._views: Dict[int, QObject] = {}
        self._next: Dict[int, QObject] = {}

    def begin(self) -> None:
        self._next = {}

    def view_for(self, tool) -> tuple:
        """(card kind, view) for a tool, ("", None) for none."""
        if tool is None:
            return "", None
        card, view_class = _CARDS.get(tool.tool_type, ("summary", CuttingToolSummary))
        view = self._views.get(tool.cutting_tool_id)
        if view is None or view._tool is not tool:
            view = view_class(tool, self._parent)
        self._next[tool.cutting_tool_id] = view
        return card, view

    def end(self) -> None:
        """Let go of the views no longer shown - once the rows that held
        them are gone."""
        old, self._views = self._views, self._next
        kept = {id(view) for view in self._views.values()}
        for view in old.values():
            if id(view) not in kept:
                view.deleteLater()


class ToolHolderListModel(DataclassListModel):
    """The tool holders, each with the cutting tool mounted in it."""

    def __init__(self, store: ToolLibraryStore, parent=None):
        super().__init__(HolderRow, parent)
        self._store = store
        self._views = MountedToolViews(self)
        self.refresh()

    def refresh(self) -> None:
        rows = []
        self._views.begin()
        for holder in self._store.holders:
            tool = self._store.find_tool(holder.cutting_tool_id)
            card, view = self._views.view_for(tool)
            rows.append(HolderRow(
                holderId=holder.tool_holder_id,
                ready=holder.is_ready,
                toolId=tool.cutting_tool_id if tool else 0,
                toolCard=card,
                toolComment=tool.comment if tool else "",
                toolView=view,
                xOffset=_offset_text(holder.x_offset),
                zOffset=_offset_text(holder.z_offset),
            ))
        self.setRows(rows)
        self._views.end()


def _offset_text(value: Optional[float]) -> str:
    return "\u2014" if value is None else f"{value:.3f}"


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
    #: A tool was mounted in a holder, or taken out of one.
    mountedChanged = pyqtSignal()

    def __init__(self, store: ToolLibraryStore, parent=None):
        super().__init__(CategoryRow, parent)
        self._store = store
        self._collapsed: Set[CuttingToolType] = set()
        self._views: List[QObject] = []
        self._mounted: List[int] = []
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

    @pyqtProperty("QVariantList", notify=mountedChanged)
    def mountedToolIds(self):
        """The ids of the tools mounted in a holder, whose cards say so."""
        return list(self._mounted)

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
        mounted = sorted(h.cutting_tool_id for h in self._store.holders if h.has_tool)
        if mounted != self._mounted:
            self._mounted = mounted
            self.mountedChanged.emit()
        for view in old_views:
            if id(view) not in kept:
                view.deleteLater()

    @pyqtSlot(int, result="QVariantList")
    def locate(self, cutting_tool_id: int):
        """[category row, position in it, the category's tool type] of a
        tool, or [] when it is not listed."""
        for row_index, row in enumerate(self._rows):
            for position, view in enumerate(row.tools):
                if view.cuttingToolId == cutting_tool_id:
                    return [row_index, position, row.toolType]
        return []

    @pyqtSlot(str)
    def expand(self, tool_type: str) -> None:
        if not self.isExpanded(CuttingToolType(tool_type)):
            self.toggle(tool_type)

    def categoryRow(self, tool_type: CuttingToolType) -> Optional[CategoryRow]:
        return next((r for r in self._rows if r.toolType == tool_type.value), None)
