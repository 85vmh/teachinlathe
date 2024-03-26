import os

from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QScrollArea, QHBoxLayout, QVBoxLayout
from qtpyvcp.utilities import logger

from teachinlathe.widgets.lathe_fixtures.fixtures import LatheFixturesRepository
from teachinlathe.widgets.lathe_fixtures.lathe_fixture import LatheFixture

LOG = logger.getLogger(__name__)


class _ScrollableFixtures(QWidget):
    onFixtureSelected = QtCore.pyqtSignal(object)

    def __init__(self, lathe_fixtures_path, parent=None):
        super().__init__(parent)
        self.fixture_repository = LatheFixturesRepository(lathe_fixtures_path)

        # Create a QHBoxLayout to contain QLabel items horizontally
        self.layout = QHBoxLayout(self)

        self.loadFixtures()

        # Set layout for the widget
        self.setLayout(self.layout)

    def loadFixtures(self):
        fixtures = self.fixture_repository.getFixtures()
        active_index = self.fixture_repository.getCurrentIndex()
        self._clear_layout()
        for index, fixture in enumerate(fixtures):
            is_active = fixture.fixture_index == active_index
            widget = LatheFixture(fixture, is_active)
            widget.setFixedWidth(190)  # Set fixed width for each widget
            widget.setFixedHeight(220)  # Set fixed width for each widget
            widget.onFixtureSelected.connect(self.handleFixtureClicked)
            widget.zMinusLimitUpdated.connect(self.handleLimitUpdated)
            self.layout.addWidget(widget)

    def handleFixtureClicked(self, fixture):
        self.onFixtureSelected.emit(fixture)
        self.fixture_repository.updateCurrentFixtureIndex(fixture.fixture_index)
        self.loadFixtures()

    def handleLimitUpdated(self, z_minus_limit):
        active_index = self.fixture_repository.getCurrentIndex()
        self.fixture_repository.updateZMinusLimit(active_index, z_minus_limit)

    def _clear_layout(self):
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()


class LatheFixturesCards(QWidget):
    onFixtureSelected = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        root_dir = os.path.realpath(os.path.dirname(__file__))
        lathe_fixtures_path = os.path.join(root_dir, 'lathe_fixtures.json')

        # Create a QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Create the content widget and set it as the central widget of the scroll area

        content_widget = _ScrollableFixtures(lathe_fixtures_path)
        scroll_area.setWidget(content_widget)
        content_widget.onFixtureSelected.connect(self.handleFixtureSelected)

        # Set the scroll area's horizontal scrollbar policy
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # Set the scrollbar stylesheet to customize its appearance
        scroll_area.setStyleSheet("QScrollBar:horizontal {"
                                  "    height: 30px;"  # Set scrollbar height
                                  "}"
                                  "QScrollBar::handle:horizontal {"
                                  "    min-width: 30px;"  # Set minimum handle width
                                  "}")

        # Create a QVBoxLayout for the main widget and add the scroll area to it
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll_area)

    def handleFixtureSelected(self, fixture):
        self.onFixtureSelected.emit(fixture)
