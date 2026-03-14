import os

import linuxcnc
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, pyqtProperty
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from .GCodeSyntaxHighlighter import GCodeSyntaxHighlighter


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
    editModeChanged      = pyqtSignal(bool, arguments=['editing'])
    dirtyChanged         = pyqtSignal(bool, arguments=['dirty'])
    folderFilesChanged   = pyqtSignal(str,  arguments=['folderName'])
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
        self._saved_content = ''
        self._edit_mode = False
        self._dirty = False

    # ------------------------------------------------------------------
    # Properties (read by QML)
    # ------------------------------------------------------------------

    @pyqtProperty('QVariantList', constant=True)
    def folderNames(self):
        return [name for name, _ in self._folders]

    @pyqtProperty(str, notify=filePathChanged)
    def currentFilePath(self):
        return self._current_file_path

    @pyqtProperty(bool, notify=editModeChanged)
    def editMode(self):
        return self._edit_mode

    @pyqtProperty(bool, notify=dirtyChanged)
    def dirty(self):
        return self._dirty

    # ------------------------------------------------------------------
    # Slots (called from QML)
    # ------------------------------------------------------------------

    @pyqtSlot(str, result='QVariantList')
    def getFiles(self, folder_name):
        """Return sorted list of G-code file names in *folder_name*."""
        path = self._folder_map.get(folder_name, '')
        if not os.path.isdir(path):
            return []
        return sorted(
            f for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f))
            and f.endswith(self.GCODE_EXTENSIONS)
        )

    @pyqtSlot(str, result=str)
    def getFolderPath(self, folder_name):
        return self._folder_map.get(folder_name, '')

    @pyqtSlot(str, str)
    def selectFile(self, folder_name, filename):
        """Read *filename* and emit its content for the text viewer."""
        path = self._folder_map.get(folder_name, '')
        filepath = os.path.join(path, filename)
        if not self._prepare_for_file_change(filepath):
            return
        self._emit_content(filepath)

    @pyqtSlot(str, str)
    def openFile(self, folder_name, filename):
        """Load *filename* into LinuxCNC and switch to the Gremlin screen."""
        from qtpyvcp.actions.program_actions import load as load_program
        path = self._folder_map.get(folder_name, '')
        filepath = os.path.join(path, filename)
        if not os.path.isfile(filepath):
            return
        if not self._prepare_for_file_change(filepath):
            return
        self.programLoadRequested.emit(filepath)
        load_program(filepath)
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
    def updateCurrentContent(self, content):
        if content == self._current_content:
            return
        self._current_content = content
        self.fileContentChanged.emit(self._current_content)
        self._set_dirty(self._current_content != self._saved_content)

    @pyqtSlot(bool)
    def setEditMode(self, editing):
        if self._edit_mode == editing:
            return
        self._edit_mode = editing
        self.editModeChanged.emit(self._edit_mode)

    def saveCurrentFile(self, parent=None):
        if not self._current_file_path:
            return self.saveCurrentFileAs(parent)
        if self._write_file(self._current_file_path):
            self._saved_content = self._current_content
            self._set_dirty(False)
            return True
        return False

    def saveCurrentFileAs(self, parent=None):
        initial_path = self._current_file_path or ''
        file_path, _ = QFileDialog.getSaveFileName(
            parent,
            'Save G-code As',
            initial_path,
            'G-code Files (*.ngc *.nc *.gcode *.G *.NGC *.NC);;All Files (*)',
        )
        if not file_path:
            return False
        if self._write_file(file_path):
            self._current_file_path = file_path
            self._saved_content = self._current_content
            self.filePathChanged.emit(self._current_file_path)
            self._set_dirty(False)
            self._notify_folder_change(file_path)
            return True
        return False

    def attachHighlighterToDocument(self, text_document):
        self._syntax_highlighter.attach_document(text_document)

    def isMachineFileRunning(self):
        if not self._current_file_path:
            return False

        try:
            stat = linuxcnc.stat()
            stat.poll()
        except Exception:
            return False

        if stat.state != linuxcnc.RCS_EXEC or stat.paused:
            return False

        machine_path = stat.file or ''
        if not machine_path:
            return False

        try:
            current_path = os.path.abspath(self._current_file_path)
            machine_path = os.path.abspath(machine_path)
        except Exception:
            return False

        return current_path == machine_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def refreshCurrentFile(self):
        """Re-read the currently loaded LinuxCNC program and emit its content."""
        import linuxcnc
        stat = linuxcnc.stat()
        try:
            stat.poll()
            if stat.file:
                self._emit_content(stat.file)
        except Exception:
            pass

    def _emit_content(self, filepath):
        if not os.path.isfile(filepath):
            return
        try:
            with open(filepath, 'r', errors='replace') as fh:
                content = fh.read()
        except Exception as exc:
            content = f'; Error reading file: {exc}'
        self._current_file_path = filepath
        self._current_content = content
        self._saved_content = content
        self.fileContentChanged.emit(content)
        self.filePathChanged.emit(filepath)
        self._set_dirty(False)
        self.setEditMode(False)

    def _set_dirty(self, dirty):
        if self._dirty == dirty:
            return
        self._dirty = dirty
        self.dirtyChanged.emit(self._dirty)

    def _prepare_for_file_change(self, filepath):
        if filepath == self._current_file_path:
            return True
        if not self._dirty:
            return True

        result = QMessageBox.question(
            None,
            'Discard changes?',
            'You have unsaved changes. Discard them and load another file?',
            QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        return result == QMessageBox.Discard

    def _write_file(self, filepath):
        try:
            with open(filepath, 'w', encoding='utf-8', errors='replace') as fh:
                fh.write(self._current_content)
            return True
        except Exception as exc:
            QMessageBox.critical(None, 'Save failed', f'Could not save file:\n{exc}')
            return False

    def _notify_folder_change(self, filepath):
        parent_dir = os.path.dirname(filepath)
        for folder_name, folder_path in self._folders:
            if os.path.abspath(folder_path) == os.path.abspath(parent_dir):
                self.folderFilesChanged.emit(folder_name)
                break
