import os

import linuxcnc
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, pyqtProperty
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from .GCodeSyntaxHighlighter import GCodeSyntaxHighlighter


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
        if not os.path.isfile(path):
            return
        if not self._prepare_for_file_change(path):
            return
        self.programLoadRequested.emit(path)
        load_or_reload_program(path)
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

        current_machine_file = os.path.abspath(stat.file) if stat.file else ''
        current_view_file = os.path.abspath(self._current_file_path)
        if not current_machine_file or current_machine_file != current_view_file:
            return False

        if getattr(stat, 'state', None) != linuxcnc.RCS_EXEC:
            return False

        exec_state = getattr(stat, 'exec_state', None)
        idle_states = {
            getattr(linuxcnc, 'EXEC_DONE', None),
            getattr(linuxcnc, 'EXEC_WAITING_FOR_MOTION', None),
            getattr(linuxcnc, 'EXEC_WAITING_FOR_MOTION_QUEUE', None),
            getattr(linuxcnc, 'EXEC_WAITING_FOR_IO', None),
            getattr(linuxcnc, 'EXEC_WAITING_FOR_MOTION_AND_IO', None),
        }
        return exec_state not in idle_states

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
        if self._dirty:
            answer = QMessageBox.question(
                None,
                'Unsaved changes',
                'Discard unsaved changes?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return False
        self._current_file_path = filepath
        self.filePathChanged.emit(self._current_file_path)
        self._set_dirty(False)
        self.setEditMode(False)
        return True

    def _emit_content(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as fh:
                content = fh.read()
        except Exception:
            content = ''
        self._current_content = content
        self._saved_content = content
        self.fileContentChanged.emit(self._current_content)
        self.filePathChanged.emit(self._current_file_path)
        self._set_dirty(False)

    def _write_file(self, filepath):
        try:
            with open(filepath, 'w', encoding='utf-8') as fh:
                fh.write(self._current_content)
        except Exception as exc:
            QMessageBox.critical(None, 'Save failed', str(exc))
            return False
        self._notify_folder_change(filepath)
        return True

    def _notify_folder_change(self, filepath):
        abs_path = os.path.abspath(filepath)
        for name, folder_path in self._folders:
            base = os.path.abspath(folder_path)
            if abs_path == base or abs_path.startswith(base + os.sep):
                self.folderFilesChanged.emit(name)
                break

    def _set_dirty(self, dirty):
        dirty = bool(dirty)
        if self._dirty == dirty:
            return
        self._dirty = dirty
        self.dirtyChanged.emit(self._dirty)
