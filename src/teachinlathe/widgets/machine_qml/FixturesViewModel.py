"""ViewModel for the chuck / fixture cards on the machine settings screen.

Replaces the ``LatheFixturesCards`` QWidget. The data is the same
``lathe_fixtures.json`` the widget read, through the same repository; only the
presentation moves.

Teaching the Z-minus limit takes the current Z position, stores it on the
active fixture and tells whoever is enforcing limits about it - which is why
this emits a signal rather than reaching into the DRO view-model itself.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.fixtures import LatheFixturesRepository
from teachinlathe.repositories.positions_repository import Positions

log = logging.getLogger(__name__)

#: Where fixture images live, looked up by file name when the path recorded in
#: lathe_fixtures.json does not exist. Those paths are absolute and were
#: written on whichever machine last edited the file, so they rarely survive.
IMAGE_DIRS = (
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), 'images'),
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))), 'images'),
)


def resolve_image(path: str) -> str:
    """The usable path for a fixture image, or "" when there is none."""
    if not path:
        return ""
    if os.path.isfile(path):
        return path
    name = os.path.basename(path)
    for directory in IMAGE_DIRS:
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate):
            return candidate
    log.debug("fixture image not found: %s", path)
    return ""


class FixturesViewModel(QObject):
    fixturesChanged = pyqtSignal()
    #: The active fixture's Z-minus limit, whenever it is selected or taught.
    chuckLimitChanged = pyqtSignal(float)

    def __init__(self, parent: Optional[QObject] = None,
                 repository=None, positions=None) -> None:
        super().__init__(parent)
        self._repository = LatheFixturesRepository() if repository is None else repository
        self._positions = positions
        self._refresh()

    def _refresh(self) -> None:
        self._fixtures = self._repository.getFixtures()
        self._active_index = self._repository.getCurrentIndex()
        self.fixturesChanged.emit()

    @property
    def positions(self) -> Positions:
        # Built on first use: the status channel has to exist by then.
        if self._positions is None:
            self._positions = Positions()
        return self._positions

    @pyqtProperty('QVariantList', notify=fixturesChanged)
    def fixtures(self):
        return [{
            "index": f.fixture_index,
            "description": f.description,
            "diameter": "" if f.diameter is None else str(f.diameter),
            "units": "" if f.units is None else str(f.units),
            "maxRpm": f.max_rpm,
            "zMinusLimit": float(f.z_minus_limit),
            "imageUrl": resolve_image(f.image_url or ""),
            "active": f.fixture_index == self._active_index,
        } for f in self._fixtures]

    @pyqtProperty(int, notify=fixturesChanged)
    def activeIndex(self):
        return self._active_index

    @pyqtSlot(int)
    def selectFixture(self, index):
        index = int(index)
        fixture = next((f for f in self._fixtures if f.fixture_index == index), None)
        if fixture is None:
            log.warning("no fixture with index %d", index)
            return
        log.info("fixture selected: %s", fixture.description)
        self._repository.updateCurrentFixtureIndex(index)
        self._refresh()
        self.chuckLimitChanged.emit(float(fixture.z_minus_limit))

    @pyqtSlot()
    def teachZMinusLimit(self):
        """Set the active fixture's Z-minus limit from the current position."""
        value = float(self.positions.teachInZ())
        self._repository.updateZMinusLimit(self._active_index, value)
        log.info("fixture %d Z-minus limit taught as %.3f", self._active_index, value)
        self._refresh()
        self.chuckLimitChanged.emit(value)

    @pyqtSlot(int, float)
    def setZMinusLimit(self, index, value):
        self._repository.updateZMinusLimit(int(index), float(value))
        self._refresh()
        if int(index) == self._active_index:
            self.chuckLimitChanged.emit(float(value))
