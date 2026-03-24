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
        from qtpyvcp.actions.program_actions import load as load_program
        path = self._folder_map.get(folder_name, '')
        filepath = self._resolve_folder_path(path, filename)
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
        from qtpyvcp.actions.program_actions import load as load_program
        if not os.path.isfile(path):
            return
        if not self._prepare_for_file_change(path):
            return
        self.programLoadRequested.emit(path)
        load_program(path)
        self._emit_content(path)
        self.screenChangeRequested.emit(1)

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
            try:
                common_path = os.path.commonpath([os.path.abspath(parent_dir), os.path.abspath(folder_path)])
            except ValueError:
                continue
            if common_path == os.path.abspath(folder_path):
                self.folderFilesChanged.emit(folder_name)
                break

    def _resolve_folder_path(self, folder_path, relative_path):
        base_path = os.path.abspath(folder_path)
        target_path = os.path.abspath(os.path.join(base_path, relative_path))
        try:
            common_path = os.path.commonpath([base_path, target_path])
        except ValueError:
            return ''
        if common_path != base_path:
            return ''
        return target_path

    def _join_relative_path(self, relative_path, name):
        if not relative_path:
            return name
        return os.path.join(relative_path, name)

    def _parent_relative_path(self, relative_path):
        parent_path = os.path.dirname(relative_path)
        return '' if parent_path == '.' else parent_path
