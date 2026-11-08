"""What the Events drawer shows: the Events list, filtered, newest first,
and how many errors came since the operator last looked."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import QModelIndex, QObject, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.events.logic.events_use_case import EventsUseCase, events_use_case
from teachinlathe.events.model.event import Category, Event, Severity
from teachinlathe.ui.common.dataclass_list_model import DataclassListModel

#: What the Events drawer calls each category.
CATEGORY_LABELS = {
    Category.MACHINE: "Machine",
    Category.PROGRAM: "Program",
    Category.CONNECTION: "Connection",
    Category.APP: "App",
}
#: The drawer's filters, its tabs left to right: "all", "errors", or a
#: Category's value.
FILTERS = [{"id": "all", "label": "All"}, {"id": "errors", "label": "Errors"}] + [
    {"id": category.value, "label": label} for category, label in CATEGORY_LABELS.items()]
_FILTER_IDS = {f["id"] for f in FILTERS}


@dataclass(frozen=True)
class EventRow:
    eventId: int
    time: str
    severity: str
    category: str
    categoryLabel: str
    text: str
    count: int


def _row(event: Event) -> EventRow:
    return EventRow(event.id, event.time.strftime("%H:%M:%S"), event.severity.value,
                    event.category.value, CATEGORY_LABELS[event.category], event.text, event.count)


def _passes(event: Event, filter_: str) -> bool:
    if filter_ == "all":
        return True
    if filter_ == "errors":
        return event.severity is Severity.ERROR
    return event.category.value == filter_


class EventListModel(DataclassListModel):
    """Rows added at the top, and changed or removed by event id, without a
    reset: the list stays where the operator scrolled it."""

    def prepend(self, row: EventRow) -> None:
        self.beginInsertRows(QModelIndex(), 0, 0)
        self._rows.insert(0, row)
        self.endInsertRows()

    def _find(self, event_id: int) -> int:
        # from the bottom: the one dropped at the cap is always the last
        for index in range(len(self._rows) - 1, -1, -1):
            if self._rows[index].eventId == event_id:
                return index
        return -1

    def replaceById(self, row: EventRow) -> None:
        index = self._find(row.eventId)
        if index >= 0:
            self.replaceRow(index, row)

    def removeById(self, event_id: int) -> None:
        index = self._find(event_id)
        if index >= 0:
            self.beginRemoveRows(QModelIndex(), index, index)
            del self._rows[index]
            self.endRemoveRows()


class EventsViewModel(QObject):
    filterChanged = pyqtSignal()
    unreadErrorsChanged = pyqtSignal()

    def __init__(self, app_shell_bridge, navigation_store,
                 use_case: Optional[EventsUseCase] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._shell = app_shell_bridge
        self._navigation = navigation_store
        self._use_case = events_use_case() if use_case is None else use_case
        self._filter = "all"
        self._unread_errors = 0
        self._model = EventListModel(EventRow, self)

        self._use_case.eventAdded.connect(self._on_added)
        self._use_case.eventUpdated.connect(self._on_updated)
        self._use_case.eventRemoved.connect(self._model.removeById)
        self._use_case.cleared.connect(self._refill)
        self._navigation.logsExpandedChanged.connect(self._on_drawer_toggled)
        self._refill()
        # what came before the screens: errors not seen yet
        self._set_unread(sum(1 for e in self._use_case.events() if e.severity is Severity.ERROR))

    @pyqtProperty(QObject, constant=True)
    def model(self):
        return self._model

    @pyqtProperty("QVariantList", constant=True)
    def filters(self):
        return FILTERS

    @pyqtProperty(str, notify=filterChanged)
    def filter(self):
        return self._filter

    @pyqtProperty(int, notify=unreadErrorsChanged)
    def unreadErrors(self):
        return self._unread_errors

    @pyqtSlot(str)
    def setFilter(self, filter_: str) -> None:
        if filter_ not in _FILTER_IDS or filter_ == self._filter:
            return
        self._filter = filter_
        self.filterChanged.emit()
        self._refill()

    @pyqtSlot()
    def clear(self) -> None:
        self._use_case.clear()
        self._set_unread(0)

    # -- the use case -------------------------------------------------------

    def _on_added(self, event: Event) -> None:
        if _passes(event, self._filter):
            self._model.prepend(_row(event))
        self._on_error(event)

    def _on_updated(self, event: Event) -> None:
        if _passes(event, self._filter):
            self._model.replaceById(_row(event))

    def _on_error(self, event: Event) -> None:
        if event.severity is not Severity.ERROR or self._navigation.logsExpanded:
            return
        self._set_unread(self._unread_errors + 1)
        self._shell.showToast(event.text)

    def _refill(self) -> None:
        self._model.setRows([_row(e) for e in reversed(self._use_case.events()) if _passes(e, self._filter)])

    def _on_drawer_toggled(self) -> None:
        if self._navigation.logsExpanded:
            self._set_unread(0)

    def _set_unread(self, count: int) -> None:
        if count != self._unread_errors:
            self._unread_errors = count
            self.unreadErrorsChanged.emit()
