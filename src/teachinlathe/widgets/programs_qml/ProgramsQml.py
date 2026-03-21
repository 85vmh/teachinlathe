import os

from PyQt5.QtCore import QPoint, QPointF, QTimer, QUrl
from PyQt5.QtQuick import QQuickItem
from PyQt5.QtQuickWidgets import QQuickWidget

from teachinlathe.data import ProgramsViewModel
from teachinlathe.widgets.gremlin.gremlin_widget import GremlinWidget


class ProgramsQml(QQuickWidget):
    _QML_DIR = os.path.dirname(__file__)

    def __init__(self, folders, parent=None):
        super().__init__(parent)
        self.setResizeMode(QQuickWidget.SizeRootObjectToView)

        self.viewmodel = ProgramsViewModel(folders, self)
        gremlin_parent = parent if parent is not None else self
        self.gremlin = GremlinWidget(self.viewmodel.runtime_store, gremlin_parent)
        self.gremlin.enable_panning(True)
        self.gremlin.hide()

        self._pending_fit_path = ''
        self._gremlin_placeholder = None
        self._root_item = None

        context = self.engine().rootContext()
        context.setContextProperty('programsViewModel', self.viewmodel)

        self.statusChanged.connect(self._on_status_changed)
        self.setSource(QUrl.fromLocalFile(os.path.join(self._QML_DIR, 'ProgramsRoot.qml')))

        self.viewmodel.programLoadRequested.connect(self._prepareGremlinForLoad)
        self.viewmodel.screenIndexChanged.connect(lambda _index: QTimer.singleShot(0, self._sync_gremlin_widget))
        self.viewmodel.gremlinZoomInRequested.connect(self._zoom_gremlin_in)
        self.viewmodel.gremlinZoomOutRequested.connect(self._zoom_gremlin_out)
        self.viewmodel.gremlinClearRequested.connect(self._clear_gremlin_plot)
        self.viewmodel.gremlinFitRequested.connect(self._fit_gremlin_to_window)
        self.viewmodel.runtime_store.machineFileChanged.connect(self._on_machine_file_changed)
        self.viewmodel.runtime_store.callLevelChanged.connect(self._on_call_level_changed)

    def _on_status_changed(self, status):
        if status != QQuickWidget.Ready:
            return

        self._root_item = self.rootObject()
        if not self._root_item:
            return

        self._gremlin_placeholder = self._root_item.findChild(QQuickItem, 'gremlinViewport')
        if self._gremlin_placeholder is not None:
            for signal_name in ('xChanged', 'yChanged', 'widthChanged', 'heightChanged', 'visibleChanged'):
                try:
                    getattr(self._gremlin_placeholder, signal_name).connect(self._schedule_gremlin_sync)
                except Exception:
                    pass
        self._schedule_gremlin_sync()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_gremlin_sync()

    def showEvent(self, event):
        super().showEvent(event)
        self._schedule_gremlin_sync()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.gremlin.hide()

    def _schedule_gremlin_sync(self):
        QTimer.singleShot(0, self._sync_gremlin_widget)

    def _sync_gremlin_widget(self):
        if self.viewmodel.screenIndex != 1 or self._gremlin_placeholder is None:
            self.gremlin.hide()
            return

        item = self._gremlin_placeholder
        if item.width() <= 0 or item.height() <= 0 or not item.isVisible():
            self.gremlin.hide()
            return

        scene_pos = item.mapToScene(QPointF(0, 0))
        top_left = self.mapTo(self.gremlin.parentWidget(), QPoint(int(scene_pos.x()), int(scene_pos.y())))
        self.gremlin.setGeometry(
            int(top_left.x()),
            int(top_left.y()),
            int(item.width()),
            int(item.height()),
        )
        self.gremlin.show()
        self.gremlin.raise_()
        self.gremlin.update()

    def _prepareGremlinForLoad(self, path):
        self._pending_fit_path = os.path.abspath(path) if path else ''
        self._clear_gremlin_plot()

    def _fit_gremlin_to_window(self):
        self._sync_gremlin_widget()
        self.gremlin.setViewXZ2()
        self.gremlin.update()

    def _zoom_gremlin_in(self):
        self.gremlin.zoomIn()
        self.gremlin.update()

    def _zoom_gremlin_out(self):
        self.gremlin.zoomOut()
        self.gremlin.update()

    def _clear_gremlin_plot(self):
        self.gremlin.clearLivePlot()
        self.gremlin.update()

    def _on_machine_file_changed(self, path):
        machine_path = os.path.abspath(path) if path else ''
        if not machine_path:
            return
        if self._pending_fit_path and machine_path != self._pending_fit_path:
            return
        QTimer.singleShot(150, self._fit_gremlin_to_window)
        self._pending_fit_path = ''

    def _on_call_level_changed(self, _call_level):
        QTimer.singleShot(0, self._fit_gremlin_to_window)
