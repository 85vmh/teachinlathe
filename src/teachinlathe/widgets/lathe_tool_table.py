from PyQt5.QtCore import QRectF, QTimer
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QStyle, QStyledItemDelegate, QWidget, QHBoxLayout, QPushButton, QStyleOptionViewItem
from qtpy.QtCore import Qt, Slot, Signal, Property, QModelIndex, QSortFilterProxyModel
from qtpy.QtGui import QStandardItemModel, QColor, QBrush, QPen
from qtpy.QtWidgets import QTableView, QMessageBox
from qtpyvcp.actions.machine_actions import issue_mdi
from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities.logger import getLogger

LOG = getLogger(__name__)


def get_orient_arrow_angle(value):
    mapping = {
        1: 315,
        2: 225,
        3: 135,
        4: 45,
        5: 0,
        6: -90,
        7: 180,
        8: 90
    }
    return mapping.get(value, 0)


_LATHE_COLUMNS = ['T', 'XZ', 'D', 'Q', 'IJ', 'R', 'ACTIONS']
_PREFERRED_WIDTHS = [40, 120, 100, 80, 130, 350]


class ActionButtonsEditor(QWidget):
    editClicked = Signal(int)
    deleteClicked = Signal(int)
    loadClicked = Signal(int)
    unloadClicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)  # left and right margins for spacing before/after buttons
        layout.setSpacing(20)  # more spacing between buttons

        self.edit_btn = QPushButton("Edit")
        self.delete_btn = QPushButton("Delete")
        self.load_btn = QPushButton("Load")

        for btn in (self.edit_btn, self.delete_btn, self.load_btn):
            btn.setFixedHeight(40)
            layout.addWidget(btn)

        self.edit_btn.clicked.connect(self.on_edit)
        self.delete_btn.clicked.connect(self.on_delete)
        self.load_btn.clicked.connect(self.on_load_unload)

        self._tool_no = None

    def setToolNumber(self, tool_no, current_tool, edited_tool=None):
        self._tool_no = tool_no
        is_current_tool = (tool_no == current_tool)
        is_edited_tool = (tool_no == edited_tool)

        self.edit_btn.setEnabled(not is_current_tool and not is_edited_tool)
        self.delete_btn.setEnabled(not is_current_tool and not is_edited_tool)
        self.load_btn.setEnabled(not is_edited_tool)
        self.load_btn.setText("Unload" if is_current_tool else "Load")

    def on_edit(self):
        if self._tool_no is not None:
            self.editClicked.emit(self._tool_no)

    def on_delete(self):
        if self._tool_no is not None:
            self.deleteClicked.emit(self._tool_no)

    def on_load_unload(self):
        if self._tool_no is not None:
            if self.load_btn.text() == "Unload":
                # If the button says "Unload", emit unload signal
                self.unloadClicked.emit(self._tool_no)
            else:
                self.loadClicked.emit(self._tool_no)


class ItemDelegate(QStyledItemDelegate):
    def __init__(self, columns):
        super(ItemDelegate, self).__init__()
        self._columns = _LATHE_COLUMNS
        self._padding = ' ' * 2

    def createEditor(self, parent, option, index):
        col = self._columns[index.column()]
        if col == 'ACTIONS':
            editor = ActionButtonsEditor(parent)
            view = parent.parent()  # QTableView
            model_index = index.model().mapToSource(index)
            row = model_index.row()
            tool_no = view.tool_model.toolDataFromRow(row)['T']
            current_tool = view.tool_model.stat.tool_in_spindle
            editor.setToolNumber(tool_no, current_tool, view.tool_model.edited_tool_no)

            editor.editClicked.connect(view._onEditTool)
            editor.deleteClicked.connect(view._onDeleteTool)
            editor.loadClicked.connect(view._onLoadTool)
            editor.unloadClicked.connect(view._onUnloadTool)

            return editor
        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        pass

    def setModelData(self, editor, model, index):
        pass

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def displayText(self, value, locale):
        return f"{self._padding}{value}"

    def paint(self, painter, option, index):
        model_index = index.model().mapToSource(index)
        tool_no = index.model().sourceModel().toolDataFromRow(model_index.row())['T']

        if hasattr(index.model().sourceModel(), 'edited_tool_no') and tool_no == index.model().sourceModel().edited_tool_no:
            painter.save()
            pen = QPen(QColor("#C9A635"), 2)
            painter.setPen(pen)
            painter.drawRect(option.rect.adjusted(1, 1, -1, -1))
            painter.restore()

        painter.save()

        data = index.model().data(index, Qt.DisplayRole)
        col = self._columns[index.column()]

        if col == 'ACTIONS':
            painter.restore()
            return

        bg_color = index.model().data(index, Qt.BackgroundRole)
        if bg_color is not None:
            painter.fillRect(option.rect, bg_color)

        if option.state & QStyle.State_Selected:
            color = option.palette.color(QPalette.Active, QPalette.HighlightedText)
        else:
            brush = index.model().data(index, Qt.TextColorRole)
            if isinstance(brush, QBrush):
                color = brush.color()
            elif isinstance(brush, QColor):
                color = brush
            else:
                color = Qt.black

        if col in ['XZ', 'IJ']:
            x_val, z_val = data.split('\n')
            x_label, x_value = x_val.split(': ')
            z_label, z_value = z_val.split(': ')

            rect = option.rect
            left_margin = 5
            right_margin = 5

            font_metrics = painter.fontMetrics()
            label_width = max(font_metrics.width(x_label + ': '), font_metrics.width(z_label + ': '))
            middle_margin = 10
            middle = left_margin + label_width + middle_margin

            painter.drawText(rect.adjusted(left_margin, 0, -rect.width() + middle, 0), Qt.AlignVCenter | Qt.AlignLeft, f"{x_label}:\n{z_label}:")
            painter.drawText(rect.adjusted(middle, 0, -right_margin, 0), Qt.AlignVCenter | Qt.AlignRight, f"{x_value}\n{z_value}")

        elif col == 'Q':
            arrow_length = 15
            space_between = 5
            self.draw_arrow(painter, option, data, arrow_length, color)

            painter.save()
            text = str(data)
            arrow_end_x = option.rect.center().x() + min(option.rect.width(), option.rect.height()) // 4 + space_between
            painter.drawText(arrow_end_x, option.rect.y(), option.rect.width(), option.rect.height(), Qt.AlignVCenter | Qt.AlignLeft, text)
            painter.restore()

        else:
            super().paint(painter, option, index)

        painter.restore()

    @staticmethod
    def draw_arrow(painter, option, value, arrow_length, color):
        painter.save()
        rect = option.rect

        if value == 9:
            radius = arrow_length // 2
            center = rect.center()
            circle_rect = QRectF(
                center.x() - radius,
                center.y() - radius,
                radius * 2,
                radius * 2
            )

            brush = QBrush(color)
            painter.setBrush(brush)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(circle_rect)
        else:
            painter.translate(rect.center())
            painter.rotate(get_orient_arrow_angle(value))
            painter.translate(-rect.center())

            start_x = rect.center().x() - arrow_length // 2
            end_x = rect.center().x() + arrow_length // 2
            center_y = rect.center().y()

            pen = QPen(color)
            pen.setWidth(2)
            painter.setPen(pen)

            painter.drawLine(start_x, center_y, end_x, center_y)
            arrow_head_size = arrow_length // 4
            painter.drawLine(end_x, center_y, end_x - arrow_head_size, center_y - arrow_head_size)
            painter.drawLine(end_x, center_y, end_x - arrow_head_size, center_y + arrow_head_size)

        painter.restore()

class ToolModel(QStandardItemModel):
    def __init__(self, parent=None):
        super(ToolModel, self).__init__(parent)

        self.status = getPlugin('status')
        self.stat = self.status.stat
        self.tt = getPlugin('tooltable')
        self.edited_tool_no = None

        self.current_tool_color = QColor(Qt.darkGreen)
        self.current_tool_bg = None

        # self._columns = self.tt.columns
        self._columns = _LATHE_COLUMNS

        self._column_labels = self.tt.COLUMN_LABELS

        self._tool_table = self.tt.getToolTable()

        self.setColumnCount(self.columnCount())
        self.setRowCount(1000)  # (self.rowCount())

        self.status.tool_in_spindle.notify(self.refreshModel)
        self.tt.tool_table_changed.connect(self.updateModel)

    def refreshModel(self):
        # refresh model so current tool gets highlighted
        self.beginResetModel()
        self.endResetModel()

    def updateModel(self, tool_table):
        # update model with new data
        self.beginResetModel()
        self._tool_table = tool_table
        self.endResetModel()

    def setColumns(self, columns):
        self._columns = columns
        self.setColumnCount(len(columns))

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            col = self._columns[section]
            if col == 'T':  # Tool Number column
                return 'T#'
            elif col == 'XZ':  # Combined Offsets column
                return 'Offsets'
            elif col == 'D':  # Tip Radius
                return 'Radius'
            elif col == 'IJ':  # Combined Tip Angle column
                return 'Tip Angle'
            elif col == 'R': # Remark column
                return 'Description'
            elif col == 'ACTIONS':
                return 'Actions'
            return self._column_labels.get(col, col)
        return super().headerData(section, orientation, role)

    def columnCount(self, parent=None):
        return len(self._columns)

    def rowCount(self, parent=None):
        return len(self._tool_table) - 1

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            key = self._columns[index.column()]
            tool_no = sorted(self._tool_table)[index.row() + 1]

            if key == 'XZ':  # Combined Offsets column
                x_val = self._tool_table[tool_no].get('X', '')
                z_val = self._tool_table[tool_no].get('Z', '')
                return f"X: {x_val:.3f}\nZ: {z_val:.3f}"

            elif key == 'IJ':  # Combined Tip Angle column
                i_val = self._tool_table[tool_no].get('I', '')
                j_val = self._tool_table[tool_no].get('J', '')
                return f"Front: {i_val}°\nBack: {j_val}°"

            elif key == 'D':
                return f"{self._tool_table[tool_no].get(key, ''):.1f}"

            return self._tool_table[tool_no].get(key, '')

        elif role == Qt.TextAlignmentRole:
            col = self._columns[index.column()]
            if col == 'R':  # Remark
                return Qt.AlignVCenter | Qt.AlignLeft
            elif col in 'TPQD':  # Integers (Tool, Pocket, Orient, Diameter)
                return Qt.AlignVCenter | Qt.AlignCenter
            else:  # All the other floats
                return Qt.AlignVCenter | Qt.AlignRight

        elif role == Qt.TextColorRole:
            return QStandardItemModel.data(self, index, role)

        elif role == Qt.BackgroundRole and self.current_tool_bg is not None:
            tool_no = sorted(self._tool_table)[index.row() + 1]
            if self.stat.tool_in_spindle == tool_no:
                return QBrush(self.current_tool_bg)
            else:
                return QStandardItemModel.data(self, index, role)

        return super().data(index, role)

    def setData(self, index, value, role):
        key = self._columns[index.column()]
        tnum = sorted(self._tool_table)[index.row() + 1]
        self._tool_table[tnum][key] = value
        return True

    def removeTool(self, row):
        self.beginRemoveRows(QModelIndex(), row, row)
        tnum = sorted(self._tool_table)[row + 1]
        del self._tool_table[tnum]
        self.endRemoveRows()
        return True

    def addTool(self):
        try:
            tnum = sorted(self._tool_table)[-1] + 1
        except IndexError:
            tnum = 1

        row = len(self._tool_table) - 1

        if row == 1000:
            # max 1000 tools
            return False

        self.beginInsertRows(QModelIndex(), row, row)
        self._tool_table[tnum] = self.tt.newTool(tnum=tnum)
        self.endInsertRows()
        return True

    def toolDataFromRow(self, row):
        """Returns dictionary of tool data"""
        tnum = sorted(self._tool_table)[row + 1]
        return self._tool_table[tnum]

    def toolDataFromTool(self, tnum):
        """Returns dictionary of tool data"""
        return self._tool_table[tnum]

    def saveToolTable(self):
        self.tt.saveToolTable(self._tool_table, self._column_labels)
        return True

    def clearToolTable(self):
        self.beginRemoveRows(QModelIndex(), 0, 100)
        # delete all but the spindle, which can't be deleted
        self._tool_table = {0: self._tool_table[0]}
        self.endRemoveRows()
        return True

    def loadToolTable(self):
        # the tooltable plugin will emit the tool_table_changed signal
        # so we don't need to do anymore here
        self.tt.loadToolTable()
        return True


class LatheToolTable(QTableView):
    toolEditClicked = Signal(dict, object, int)  # toolData, toolModel, toolNo
    toolAddClicked = Signal(dict, object)  # toolData, toolModel

    def __init__(self, parent=None):
        super(LatheToolTable, self).__init__(parent)

        # Set a fixed row height that is sufficient for two lines
        self.verticalHeader().setDefaultSectionSize(60)  # Adjust this value as needed

        self.tool_model = ToolModel(self)

        self.item_delegate = ItemDelegate(columns=self.tool_model._columns)
        self.setItemDelegate(self.item_delegate)
        self.item_delegate.commitData.connect(self.commitData)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setFilterKeyColumn(0)
        self.proxy_model.setSourceModel(self.tool_model)

        self.setModel(self.proxy_model)

        QTimer.singleShot(0, self.openEditorsForActionColumn)
        self.model().modelReset.connect(lambda: QTimer.singleShot(0, self.openEditorsForActionColumn))
        self.model().layoutChanged.connect(lambda: QTimer.singleShot(0, self.openEditorsForActionColumn))

        # Properties
        self._columns = self.tool_model._columns
        self._confirm_actions = True
        self._current_tool_color = QColor('sage')
        self._current_tool_bg = None

        # Appearance/Behaviour settings
        self.setSortingEnabled(True)
        self.verticalHeader().hide()
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.SingleSelection)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSortIndicator(0, Qt.AscendingOrder)

        if _PREFERRED_WIDTHS:
            for i, width in enumerate(_PREFERRED_WIDTHS):
                self.setColumnWidth(i, width)


    def _onEditTool(self, tool_no):
        print(f"[Edit Tool] {tool_no}")
        self.tool_model.edited_tool_no = tool_no
        for row in range(self.tool_model.rowCount()):
            index = self.model().index(row, _LATHE_COLUMNS.index('ACTIONS'))
            self.closePersistentEditor(index)
            self.openPersistentEditor(index)

        self.tool_model.refreshModel()
        self.toolEditClicked.emit(self.tool_model.toolDataFromTool(tool_no), self.tool_model, tool_no)

    def finishEditingTool(self):
        """Called when editing a tool is finished."""
        self.tool_model.edited_tool_no = None
        self.tool_model.refreshModel()
        self.openEditorsForActionColumn()

    def _onDeleteTool(self, tool_no):
        self.deleteToolByNumber(tool_no)

    def _onLoadTool(self, tool_no):
        print(f"[Load Tool] {tool_no}")
        self.loadToolWIthM61(tool_no)

    def _onUnloadTool(self, tool_no):
        print(f"[Unload Tool] {tool_no}")
        self.loadToolWIthM61(0)

    def openEditorsForActionColumn(self):
        for row in range(self.model().rowCount()):
            index = self.model().index(row, _LATHE_COLUMNS.index('ACTIONS'))
            self.openPersistentEditor(index)

    @Slot()
    def saveToolTable(self):
        if not self.confirmAction("Do you want to save changes and\n"
                                  "load tool table into LinuxCNC?"):
            return
        self.tool_model.saveToolTable()

    @Slot()
    def loadToolTable(self):
        if not self.confirmAction("Do you want to re-load the tool table?\n"
                                  "All unsaved changes will be lost."):
            return
        self.tool_model.loadToolTable()

    @Slot()
    def deleteSelectedTool(self):
        """Delete the currently selected item"""
        current_row = self.selectedRowIndex()
        if current_row == -1:
            # no row selected
            return

        tdata = self.tool_model.toolDataFromRow(current_row)
        tnum = tdata['T']

        # should not delete tool if currently loaded in spindle. Warn user
        if tnum == self.tool_model.stat.tool_in_spindle:
            box = QMessageBox(QMessageBox.Warning,
                              "Can't delete current tool!",
                              "Tool #{} is currently loaded in the spindle.\n"
                              "Please remove tool from spindle and try again.".format(tnum),
                              QMessageBox.Ok,
                              parent=self)
            box.show()
            return False

        if not self.confirmAction('Are you sure you want to delete T{tdata[T]}?\n'
                                  '"{tdata[R]}"'.format(tdata=tdata)):
            return

        self.tool_model.removeTool(current_row)

    def deleteToolByNumber(self, tool_no):
        """Delete tool by its number (not by selection)."""
        tool_table = self.tool_model._tool_table
        sorted_tools = sorted(tool_table)

        for row, tnum in enumerate(sorted_tools[1:]):  # Ignorăm tool 0
            if tnum == tool_no:
                if not self.confirmAction(f'Are you sure you want to delete T{tool_no} ?'
                                          f'\n"{tool_table[tool_no].get("R", "")}"'):
                    return False

                print("found row to delete: ", row)
                self.tool_model.removeTool(row)
                self.tool_model.saveToolTable()
                self.tool_model.loadToolTable()
                return True
            print("tool not found: ", tool_no)
        return False

    @Slot()
    def selectPrevious(self):
        """Select the previous item in the view."""
        self.selectRow(self.selectedRowIndex() - 1)
        return True

    @Slot()
    def selectNext(self):
        """Select the next item in the view."""
        self.selectRow(self.selectedRowIndex() + 1)
        return True

    @Slot()
    def clearToolTable(self, confirm=True):
        """Remove all items from the model"""
        if confirm:
            if not self.confirmAction("Do you want to delete the whole tool table?"):
                return

        self.tool_model.clearToolTable()

    @Slot()
    def addTool(self):
        """Appends a new item to the model"""
        self.tool_model.addTool()
        self.selectRow(self.tool_model.rowCount() - 1)
        self.toolAddClicked.emit(self.tool_model.toolDataFromRow(self.selectedRowIndex()), self.tool_model)

    @Slot()
    def loadSelectedToolWithM6(self):
        selected_tool = self._get_selected_tool()
        if selected_tool is not None:
            issue_mdi("M6 T%s G43" % selected_tool)
        else:
            LOG.warning("No tool selected to load with M6.")

    @Slot()
    def loadSelectedToolWithM61(self):
        selected_tool = self._get_selected_tool()
        self.loadToolWIthM61(selected_tool)

    @staticmethod
    def loadToolWIthM61(tool_no):
        if tool_no is not None:
            issue_mdi("M61 Q%s G43" % tool_no)
        else:
            LOG.warning("No tool selected to load with M61.")

    def _get_selected_tool(self):
        """Loads the currently selected tool"""
        # see: https://forum.linuxcnc.org/41-guis/36042?start=50#151820
        selected_index = self.selectedRowIndex()
        if selected_index == -1:
            # no row selected
            return None

        return self.tool_model.toolDataFromRow(selected_index)['T']

    def selectedRowIndex(self):
        return self.selectionModel().currentIndex().row()

    def confirmAction(self, message):
        if not self._confirm_actions:
            return True

        parent = self if isinstance(self, QWidget) else None

        box = QMessageBox.question(
            parent,
            'Confirm Action',
            message,
            QMessageBox.Yes,
            QMessageBox.No
        )

        return box == QMessageBox.Yes

    @Property(bool)
    def confirmActions(self):
        return self._confirm_actions

    @confirmActions.setter
    def confirmActions(self, confirm):
        self._confirm_actions = confirm

    @Property(QColor)
    def currentToolColor(self):
        return self.tool_model.current_tool_color

    @currentToolColor.setter
    def currentToolColor(self, color):
        self.tool_model.current_tool_color = color

    @Property(QColor)
    def currentToolBackground(self):
        return self.tool_model.current_tool_bg or QColor()

    @currentToolBackground.setter
    def currentToolBackground(self, color):
        self.tool_model.current_tool_bg = color
