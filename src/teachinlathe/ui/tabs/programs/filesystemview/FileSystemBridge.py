import os

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, pyqtProperty

from teachinlathe.ui.tabs.programs.gcode_viewer.GCodeSyntaxHighlighter import GCodeSyntaxHighlighter


def load_or_reload_program(path: str) -> None:
    """Open *path*, reloading in place when it is already the open program."""
    from teachinlathe.core.program_repository import program_repository

    program_repository().load_or_reload(path)


class FileSystemBridge(QObject):
    """The selected program's path, text and syntax highlighting, and the
    requests to load it or switch between the Programs panes.

    Signals
    -------
    fileContentChanged(str)  — new text content to display in the code viewer
    filePathChanged(str)     — full path of the file just opened/selected
    screenChangeRequested(int) — 0 = Files screen, 1 = Gremlin screen
    """

    fileContentChanged   = pyqtSignal(str,  arguments=['content'])
    filePathChanged      = pyqtSignal(str,  arguments=['path'])
    screenChangeRequested = pyqtSignal(int, arguments=['screen'])
    programLoadRequested = pyqtSignal(str,  arguments=['path'])

    def __init__(self, parent=None):
        super().__init__(parent)
        self._syntax_highlighter = GCodeSyntaxHighlighter(self)
        self._current_file_path = ''
        self._current_content = ''

    # ------------------------------------------------------------------
    # Properties (read by QML)
    # ------------------------------------------------------------------

    @pyqtProperty(str, notify=filePathChanged)
    def currentFilePath(self):
        return self._current_file_path

    @pyqtSlot(int)
    def navigateTo(self, screen):
        """Called from QML to request a screen switch (0=Files, 1=Gremlin)."""
        if screen == 1:
            self.refreshCurrentFile()
        self.screenChangeRequested.emit(screen)

    @pyqtSlot(QObject)
    def attachHighlighter(self, quick_document):
        self._syntax_highlighter.attach(quick_document)

    def setOptionalStop(self, enabled):
        self._syntax_highlighter.set_optional_stop(enabled)

    def setBlockDelete(self, enabled):
        self._syntax_highlighter.set_block_delete(enabled)

    @pyqtSlot(str)
    def selectFileByAbsolutePath(self, path: str) -> None:
        """Select a file by its absolute path and display its content."""
        if not os.path.isfile(path):
            return
        if not self._prepare_for_file_change(path):
            return
        self._emit_content(path)

    @pyqtSlot(str)
    def openFileByAbsolutePath(self, path: str) -> None:
        """Load a file into LinuxCNC by absolute path and switch to Gremlin screen."""
        if not os.path.isfile(path):
            return
        if not self._prepare_for_file_change(path):
            return
        self.programLoadRequested.emit(path)
        load_or_reload_program(path)
        self._emit_content(path)
        self.screenChangeRequested.emit(1)

    def refreshCurrentFile(self):
        if self._current_file_path:
            self._emit_content(self._current_file_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _prepare_for_file_change(self, filepath):
        if not filepath or not os.path.isfile(filepath):
            return False
        self._current_file_path = filepath
        self.filePathChanged.emit(self._current_file_path)
        return True

    def _emit_content(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as fh:
                content = fh.read()
        except Exception:
            content = ''
        self._current_content = content
        self.fileContentChanged.emit(self._current_content)
        self.filePathChanged.emit(self._current_file_path)
