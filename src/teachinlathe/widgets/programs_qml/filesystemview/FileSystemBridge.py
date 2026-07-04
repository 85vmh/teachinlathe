import os

import linuxcnc
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, pyqtProperty

from teachinlathe.widgets.programs_qml.gcode_viewer.GCodeSyntaxHighlighter import GCodeSyntaxHighlighter


def load_or_reload_program(path: str) -> None:
    from qtpyvcp.actions.program_actions import load as load_program
    from qtpyvcp.actions.program_actions import reload as reload_program

    if not path or not os.path.isfile(path):
        return

    requested_path = os.path.abspath(path)
    stat = linuxcnc.stat()
    try:
        stat.poll()
    except Exception:
        load_program(requested_path)
        return

    current_path = os.path.abspath(stat.file) if getattr(stat, "file", None) else ""
    if current_path and requested_path == current_path:
        reload_program()
    else:
        load_program(requested_path)


class FileSystemBridge(QObject):
    """
    QObject bridge between QML file-system screens and Python/LinuxCNC.

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

    GCODE_EXTENSIONS = ('.ngc', '.nc', '.gcode', '.G', '.NGC', '.NC')

    def __init__(self, folders, parent=None):
        """
        Parameters
        ----------
        folders : list of (name, path) tuples  — in display order
        """
        super().__init__(parent)
        self._folders = folders          # [(name, path), ...]
        self._folder_map = dict(folders) # name -> path
        self._syntax_highlighter = GCodeSyntaxHighlighter(self)
        self._current_file_path = ''
        self._current_content = ''

    # ------------------------------------------------------------------
    # Properties (read by QML)
    # ------------------------------------------------------------------

    @pyqtProperty('QVariantList', constant=True)
    def folderNames(self):
        return [name for name, _ in self._folders]

    @pyqtProperty(str, notify=filePathChanged)
    def currentFilePath(self):
        return self._current_file_path

    @pyqtSlot(str, result='QVariantList')
    def getFiles(self, folder_name):
        """Return sorted list of entries at the root of *folder_name*."""
        return self.getFilesInPath(folder_name, '')

    @pyqtSlot(str, str, result='QVariantList')
    def getFilesInPath(self, folder_name, relative_path):
        """Return sorted directory entries for *relative_path* inside *folder_name*."""
        path = self._folder_map.get(folder_name, '')
        if not os.path.isdir(path):
            return []
        target_dir = self._resolve_folder_path(path, relative_path)
        if not target_dir or not os.path.isdir(target_dir):
            return []

        entries = []
        try:
            for name in sorted(os.listdir(target_dir), key=str.lower):
                full_path = os.path.join(target_dir, name)
                if os.path.isdir(full_path):
                    entries.append({
                        'name': name,
                        'path': self._join_relative_path(relative_path, name),
                        'isDir': True,
                    })
                elif os.path.isfile(full_path) and name.endswith(self.GCODE_EXTENSIONS):
                    entries.append({
                        'name': name,
                        'path': self._join_relative_path(relative_path, name),
                        'isDir': False,
                    })
        except Exception:
            return []

        if relative_path:
            entries.insert(0, {
                'name': '..',
                'path': self._parent_relative_path(relative_path),
                'isDir': True,
                'isUp': True,
            })
        return entries

    @pyqtSlot(str, result=str)
    def getFolderPath(self, folder_name):
        return self._folder_map.get(folder_name, '')

    @pyqtSlot(str, str)
    def selectFile(self, folder_name, filename):
        """Read *filename* and emit its content for the text viewer."""
        path = self._folder_map.get(folder_name, '')
        filepath = self._resolve_folder_path(path, filename)
        if not self._prepare_for_file_change(filepath):
            return
        self._emit_content(filepath)

    @pyqtSlot(str, str)
    def openFile(self, folder_name, filename):
        """Load *filename* into LinuxCNC and switch to the Gremlin screen."""
        path = self._folder_map.get(folder_name, '')
        filepath = self._resolve_folder_path(path, filename)
        if not os.path.isfile(filepath):
            return
        if not self._prepare_for_file_change(filepath):
            return
        self.programLoadRequested.emit(filepath)
        load_or_reload_program(filepath)
        self._emit_content(filepath)
        self.screenChangeRequested.emit(1)

    @pyqtSlot(int)
    def navigateTo(self, screen):
        """Called from QML to request a screen switch (0=Files, 1=Gremlin)."""
        if screen == 1:
            self.refreshCurrentFile()
        self.screenChangeRequested.emit(screen)

    @pyqtSlot(QObject)
    def attachHighlighter(self, quick_document):
        self._syntax_highlighter.attach(quick_document)

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

    def _resolve_folder_path(self, folder_path, relative_path):
        base_path = os.path.abspath(folder_path or '')
        candidate = os.path.abspath(os.path.join(base_path, relative_path or ''))
        if candidate == base_path or candidate.startswith(base_path + os.sep):
            return candidate
        return ''

    def _join_relative_path(self, current_path, entry_name):
        if not current_path:
            return entry_name
        return os.path.join(current_path, entry_name)

    def _parent_relative_path(self, relative_path):
        parent = os.path.dirname(relative_path.rstrip(os.sep))
        return parent if parent != '.' else ''

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
