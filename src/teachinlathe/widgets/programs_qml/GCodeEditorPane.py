import os

from teachinlathe.widgets.programs_qml.filesystemview.FileSystemBridge import load_or_reload_program

from PyQt5.QtCore import QRect, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QTextBlockFormat, QTextCursor
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


EDITOR_FONT_FAMILY = 'DejaVu Sans Mono'
EDITOR_FONT_SIZE = 16
EDITOR_LINE_SPACING = 4
CURRENT_LINE_BORDER_COLOR = '#3A86FF'
CURRENT_LINE_BORDER_WIDTH = 1
SUBROUTINE_CALL_BORDER_COLOR = '#E51400'
SUBROUTINE_CALL_BORDER_WIDTH = 2


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self._editor.paintLineNumberArea(event)

    def mousePressEvent(self, event):
        self._editor.selectLineAt(event.pos().y())


class GCodeTextEdit(QTextEdit):
    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self._bridge = bridge
        self._line_number_area = LineNumberArea(self)
        self._applying_text = False
        self._applying_spacing = False
        self._highlight_line_number = 0
        self._highlight_border_color = CURRENT_LINE_BORDER_COLOR
        self._highlight_border_width = CURRENT_LINE_BORDER_WIDTH

        font = QFont(EDITOR_FONT_FAMILY)
        font.setPixelSize(EDITOR_FONT_SIZE)
        self.setFont(font)
        self.setFrameStyle(QFrame.NoFrame)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ') * 4)
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)
        self.setReadOnly(True)
        self.setStyleSheet(
            'QTextEdit {'
            'background: #1e1e1e;'
            'color: #d4d4d4;'
            'selection-background-color: #264F78;'
            'selection-color: #ffffff;'
            '}'
        )

        self.document().blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.textChanged.connect(self._refresh_gutter)
        self.verticalScrollBar().valueChanged.connect(self._refresh_gutter)
        self.horizontalScrollBar().valueChanged.connect(self._refresh_gutter)
        self.cursorPositionChanged.connect(self.viewport().update)
        self.cursorPositionChanged.connect(self._refresh_gutter)
        self.document().contentsChanged.connect(self._apply_line_spacing)

        self._bridge.attachHighlighterToDocument(self.document())
        self._apply_line_spacing()
        self.updateLineNumberAreaWidth()

    def lineNumberAreaWidth(self):
        digits = len(str(max(1, self.document().blockCount())))
        return 16 + self.fontMetrics().horizontalAdvance('9') * digits

    def updateLineNumberAreaWidth(self):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)
        self._line_number_area.update()

    def _refresh_gutter(self):
        self._line_number_area.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing, False)
        pen = painter.pen()
        pen.setColor(QColor(self._highlight_border_color))
        pen.setWidth(self._highlight_border_width)
        painter.setPen(pen)

        rect = self._line_rect_for_number(self._effective_highlight_line())
        if rect is None:
            return
        top_padding = max(0, EDITOR_LINE_SPACING // 2)
        bottom_padding = max(0, EDITOR_LINE_SPACING - top_padding)
        rect.setTop(max(0, rect.top() - top_padding))
        rect.setBottom(min(self.viewport().height() - 1, rect.bottom() + bottom_padding))
        rect.setLeft(0)
        rect.setRight(self.viewport().width() - 1)
        painter.drawRect(rect)

    def paintLineNumberArea(self, event):
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor('#252526'))

        block = self.cursorForPosition(self.viewport().rect().topLeft()).block()
        if not block.isValid():
            block = self.document().firstBlock()

        block_number = block.blockNumber()
        current_block = self._effective_highlight_line() - 1

        while block.isValid():
            cursor = QTextCursor(block)
            rect = self.cursorRect(cursor)
            top = rect.top()
            next_block = block.next()
            if next_block.isValid():
                next_rect = self.cursorRect(QTextCursor(next_block))
                bottom = max(rect.bottom(), next_rect.top() - 1)
            else:
                bottom = rect.bottom()

            if bottom < event.rect().top():
                block = next_block
                block_number += 1
                continue

            if top > event.rect().bottom():
                break

            if block.isVisible():
                color = QColor('#C5C5C5') if block_number == current_block else QColor('#858585')
                painter.setPen(color)
                painter.drawText(
                    0,
                    top,
                    self._line_number_area.width() - 8,
                    max(self.fontMetrics().height(), bottom - top + 1),
                    Qt.AlignRight,
                    str(block_number + 1),
                )

            block = next_block
            block_number += 1

    def selectLineAt(self, y_pos):
        if self._bridge.isMachineFileRunning():
            return
        point = self.viewport().rect().topLeft()
        point.setX(8)
        point.setY(y_pos)
        cursor = self.cursorForPosition(point)
        self.setTextCursor(cursor)
        self.setFocus(Qt.MouseFocusReason)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton and self.isReadOnly():
            if self._bridge.isMachineFileRunning():
                return
            cursor = self.cursorForPosition(event.pos())
            self.setTextCursor(cursor)

    def setEditorText(self, text):
        if text == self.toPlainText():
            return
        self._applying_text = True
        try:
            self.setPlainText(text)
            self.clearLineHighlight()
            self._apply_line_spacing()
        finally:
            self._applying_text = False

    def isApplyingText(self):
        return self._applying_text

    def setCurrentLineNumber(self, line_number, center=True):
        self.setLineHighlight(
            line_number,
            border_color=CURRENT_LINE_BORDER_COLOR,
            border_width=CURRENT_LINE_BORDER_WIDTH,
            center=center,
            move_cursor=True,
        )

    def setLineHighlight(self, line_number, border_color, border_width=1, center=False, move_cursor=False):
        try:
            line_number = int(line_number)
        except (TypeError, ValueError):
            return

        if line_number <= 0:
            return

        block = self.document().findBlockByLineNumber(line_number - 1)
        if not block.isValid():
            return

        self._highlight_line_number = line_number
        self._highlight_border_color = border_color
        self._highlight_border_width = border_width

        cursor = QTextCursor(block)
        if move_cursor:
            self.setTextCursor(cursor)
        if center:
            self._center_on_cursor(cursor)
        self._refresh_gutter()
        self.viewport().update()

    def clearLineHighlight(self):
        self._highlight_line_number = 0
        self._highlight_border_color = CURRENT_LINE_BORDER_COLOR
        self._highlight_border_width = CURRENT_LINE_BORDER_WIDTH
        self._refresh_gutter()
        self.viewport().update()

    def _effective_highlight_line(self):
        return self._highlight_line_number if self._highlight_line_number > 0 else 0

    def _line_rect_for_number(self, line_number):
        if line_number <= 0:
            return None
        block = self.document().findBlockByLineNumber(line_number - 1)
        if not block.isValid():
            return None
        return self.cursorRect(QTextCursor(block))

    def _center_on_cursor(self, cursor):
        self.ensureCursorVisible()
        scrollbar = self.verticalScrollBar()
        rect = self.cursorRect(cursor)
        target_value = scrollbar.value() + rect.center().y() - (self.viewport().height() // 2)
        scrollbar.setValue(max(scrollbar.minimum(), min(scrollbar.maximum(), target_value)))

    def positionLineNearBottom(self, line_number, lines_below=1):
        try:
            line_number = int(line_number)
        except (TypeError, ValueError):
            return

        if line_number <= 0:
            return

        block = self.document().findBlockByLineNumber(line_number - 1)
        if not block.isValid():
            return

        cursor = QTextCursor(block)
        rect = self.cursorRect(cursor)
        line_height = max(1, rect.height())
        target_y = self.viewport().height() - ((lines_below + 1) * line_height)
        scrollbar = self.verticalScrollBar()
        target_value = scrollbar.value() + rect.top() - target_y
        scrollbar.setValue(max(scrollbar.minimum(), min(scrollbar.maximum(), target_value)))

    def _apply_line_spacing(self):
        if self._applying_spacing:
            return

        self._applying_spacing = True
        try:
            cursor = QTextCursor(self.document())
            cursor.select(QTextCursor.Document)
            block_format = QTextBlockFormat()
            block_format.setLineHeight(
                100 + (EDITOR_LINE_SPACING * 10),
                QTextBlockFormat.ProportionalHeight,
            )
            cursor.mergeBlockFormat(block_format)
            self._refresh_gutter()
            self.viewport().update()
        finally:
            self._applying_spacing = False


class CallStackFrameWidget(QFrame):
    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self._bridge = bridge

        self.setStyleSheet(
            'QFrame {'
            'background: #252526;'
            'border: 2px solid #555555;'
            'border-radius: 10px;'
            '}'
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self._title = QLabel(self)
        self._title.setStyleSheet('color: #d4d4d4; font: 12pt "Noto";')
        layout.addWidget(self._title)

        self._editor = GCodeTextEdit(self._bridge, self)
        self._editor.setReadOnly(True)
        self._editor.setMinimumHeight(120)
        self._editor.setMaximumHeight(120)
        layout.addWidget(self._editor)

    def setFrameContent(self, file_path, content, line_number):
        title = os.path.basename(file_path) if file_path else 'Unknown file'
        self._title.setText(title)
        self._title.setToolTip(file_path or '')
        self._editor.setEditorText(content)
        self._editor.clearLineHighlight()
        if line_number > 0:
            self._editor.setLineHighlight(
                line_number,
                border_color=SUBROUTINE_CALL_BORDER_COLOR,
                border_width=SUBROUTINE_CALL_BORDER_WIDTH,
                center=False,
                move_cursor=True,
            )
            self._editor.positionLineNearBottom(line_number, lines_below=1)


class GCodeEditorPane(QWidget):
    def __init__(self, bridge, mode, runtime_store, call_stack_resolver, parent=None):
        super().__init__(parent)
        self._bridge = bridge
        self._mode = mode
        self._runtime_store = runtime_store
        self._call_stack_resolver = call_stack_resolver
        self._subroutine_active = False
        self._call_stack_widgets = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QWidget(self)
        toolbar.setStyleSheet('background: #2d2d2d;')
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 7, 12, 7)
        toolbar_layout.setSpacing(8)

        if self._mode == 'gremlin':
            back_button = QToolButton(toolbar)
            back_button.setText('Files')
            back_button.clicked.connect(lambda: self._bridge.navigateTo(0))
            toolbar_layout.addWidget(back_button)

        self._path_label = QLabel('No file loaded', toolbar)
        self._path_label.setStyleSheet('color: #aaaaaa;')
        self._path_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar_layout.addWidget(self._path_label)

        self._edit_button = QPushButton('Edit', toolbar)
        self._edit_button.clicked.connect(self._toggle_edit_mode)
        toolbar_layout.addWidget(self._edit_button)

        self._save_button = QPushButton('Save', toolbar)
        self._save_button.clicked.connect(lambda: self._bridge.saveCurrentFile(self))
        toolbar_layout.addWidget(self._save_button)

        self._save_as_button = QPushButton('Save As', toolbar)
        self._save_as_button.clicked.connect(lambda: self._bridge.saveCurrentFileAs(self))
        toolbar_layout.addWidget(self._save_as_button)

        if self._mode == 'files':
            self._open_button = QPushButton('Open in Machine', toolbar)
            self._open_button.clicked.connect(self._open_in_machine)
            toolbar_layout.addWidget(self._open_button)

        layout.addWidget(toolbar)

        self._content_container = QWidget(self)
        self._content_layout = QVBoxLayout(self._content_container)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        layout.addWidget(self._content_container, 1)

        self._editor = GCodeTextEdit(self._bridge, self._content_container)
        self._content_layout.addWidget(self._editor, 1)

        self._call_stack_container = QWidget(self._content_container)
        self._call_stack_container.hide()
        self._call_stack_layout = QVBoxLayout(self._call_stack_container)
        self._call_stack_layout.setContentsMargins(0, 0, 0, 0)
        self._call_stack_layout.setSpacing(8)
        self._content_layout.addWidget(self._call_stack_container, 1)

        self._active_subroutine_editor = GCodeTextEdit(self._bridge, self._call_stack_container)
        self._active_subroutine_editor.setReadOnly(True)
        self._call_stack_layout.addWidget(self._active_subroutine_editor, 1)

        self._bridge.fileContentChanged.connect(self._on_file_content_changed)
        self._bridge.filePathChanged.connect(self._on_file_path_changed)
        self._bridge.editModeChanged.connect(self._on_edit_mode_changed)
        self._bridge.dirtyChanged.connect(self._on_dirty_changed)
        self._editor.textChanged.connect(self._push_editor_changes)
        self._runtime_store.machineFileChanged.connect(self._refresh_execution_view)
        self._runtime_store.callLevelChanged.connect(self._refresh_execution_view)
        self._runtime_store.callStackChanged.connect(self._refresh_execution_view)
        self._runtime_store.motionLineChanged.connect(self._on_motion_line_changed)
        self._runtime_store.snapshotChanged.connect(self._on_runtime_snapshot_changed)

        self._on_file_content_changed(self._bridge._current_content)
        self._on_file_path_changed(self._bridge.currentFilePath)
        self._on_edit_mode_changed(self._bridge.editMode)
        self._on_dirty_changed(self._bridge.dirty)
        self._refresh_execution_view()

    def _toggle_edit_mode(self):
        self._bridge.setEditMode(not self._bridge.editMode)

    def _open_in_machine(self):
        file_path = self._bridge.currentFilePath
        if not file_path:
            return
        folder_path = None
        file_name = None
        for _, candidate_path in self._bridge._folders:
            if file_path.startswith(candidate_path + os.sep) or file_path == candidate_path:
                folder_path = candidate_path
                file_name = file_path[len(candidate_path):].lstrip(os.sep)
                break
        if folder_path is None:
            self._bridge.saveCurrentFile(self)
            load_or_reload_program(file_path)
            self._bridge.navigateTo(1)
            return

        folder_name = next(name for name, path in self._bridge._folders if path == folder_path)
        self._bridge.openFile(folder_name, file_name)

    def _push_editor_changes(self):
        if self._editor.isApplyingText():
            return
        self._bridge.updateCurrentContent(self._editor.toPlainText())

    def _on_file_content_changed(self, content):
        self._editor.setEditorText(content)

    def _on_file_path_changed(self, path):
        self._path_label.setText(path or 'No file loaded')
        self._apply_runtime_snapshot(self._runtime_store.snapshot)

    def _on_edit_mode_changed(self, editing):
        self._editor.setReadOnly(not editing)
        self._edit_button.setText('Preview' if editing else 'Edit')

    def _on_dirty_changed(self, dirty):
        path = self._bridge.currentFilePath or 'No file loaded'
        self._path_label.setText(f'* {path}' if dirty and path else path)
        self._save_button.setEnabled(bool(self._bridge.currentFilePath) or bool(self._editor.toPlainText()))
        self._save_as_button.setEnabled(bool(self._editor.toPlainText()))

    def _on_runtime_snapshot_changed(self, snapshot):
        if not self._subroutine_active:
            return
        if int(snapshot.motion_line or 0) <= 0:
            self._active_subroutine_editor.clearLineHighlight()
            return
        self._active_subroutine_editor.setCurrentLineNumber(snapshot.motion_line, center=True)

    def _on_motion_line_changed(self, line_number):
        snapshot = self._runtime_store.snapshot
        if not self._is_showing_machine_file(snapshot.machine_file):
            return

        line_number = int(line_number or 0)
        if self._subroutine_active:
            if line_number <= 0:
                self._active_subroutine_editor.clearLineHighlight()
            else:
                self._active_subroutine_editor.setCurrentLineNumber(line_number, center=True)
        else:
            if line_number <= 0:
                self._editor.clearLineHighlight()
            else:
                self._editor.setCurrentLineNumber(line_number, center=False)

    def _refresh_execution_view(self, *_args):
        self._apply_runtime_snapshot(self._runtime_store.snapshot)

    def _apply_runtime_snapshot(self, snapshot):
        if not self._is_showing_machine_file(snapshot.machine_file):
            self._clear_subroutine_state(clear_main_highlight=True)
            return

        if snapshot.call_level > 0:
            stack_view = self._call_stack_resolver.build_view(snapshot)
            if stack_view is not None:
                self._show_call_stack_view(stack_view)
                return

        self._clear_subroutine_state(clear_main_highlight=False)
        if snapshot.motion_line > 0:
            self._editor.setCurrentLineNumber(snapshot.motion_line, center=False)
        else:
            self._editor.clearLineHighlight()

    def _is_showing_machine_file(self, machine_file=''):
        editor_path = os.path.abspath(self._bridge.currentFilePath) if self._bridge.currentFilePath else ''
        runtime_path = os.path.abspath(machine_file) if machine_file else ''
        return bool(editor_path and runtime_path and editor_path == runtime_path)

    def _clear_subroutine_state(self, clear_main_highlight=False):
        self._subroutine_active = False
        self._editor.show()
        self._call_stack_container.hide()
        if clear_main_highlight:
            self._editor.clearLineHighlight()

    def _ensure_call_stack_widget_count(self, count):
        while len(self._call_stack_widgets) < count:
            widget = CallStackFrameWidget(self._bridge, self._call_stack_container)
            self._call_stack_widgets.append(widget)
            insert_index = max(0, self._call_stack_layout.count() - 1)
            self._call_stack_layout.insertWidget(insert_index, widget)

        while len(self._call_stack_widgets) > count:
            widget = self._call_stack_widgets.pop()
            self._call_stack_layout.removeWidget(widget)
            widget.deleteLater()

    def _show_call_stack_view(self, stack_view):
        self._subroutine_active = True
        self._editor.hide()
        self._call_stack_container.show()

        self._ensure_call_stack_widget_count(len(stack_view.frames))
        for widget, frame in zip(self._call_stack_widgets, stack_view.frames):
            widget.setFrameContent(frame.file_path, frame.content, frame.line_number)
            widget.show()

        self._active_subroutine_editor.setEditorText(stack_view.active_content)
        self._active_subroutine_editor.setCurrentLineNumber(stack_view.motion_line, center=True)
