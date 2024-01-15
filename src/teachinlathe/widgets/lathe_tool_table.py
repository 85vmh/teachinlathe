from qtpy.QtCore import Qt, Slot, Signal, Property, QModelIndex, QSortFilterProxyModel
from qtpy.QtGui import QStandardItemModel, QColor, QBrush, QPen
from qtpy.QtWidgets import QTableView, QStyledItemDelegate, QMessageBox
from qtpyvcp.actions.machine_actions import issue_mdi
from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities.logger import getLogger

LOG = getLogger(__name__)


def get_orient_arrow_angle(value):
    # Define the mapping of value to angle here
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


_LATHE_COLUMNS = ['T', 'XZ', 'D', 'Q', 'IJ', 'R']
_PREFERRED_WIDTHS = [30, 100, 70, 70, 110]  # Define your custom widths here


class ItemDelegate(QStyledItemDelegate):

    def __init__(self, columns):
        super(ItemDelegate, self).__init__()

        self._columns = _LATHE_COLUMNS
        self._padding = ' ' * 2

    def displayText(self, value, locale):
        return f"{self._padding}{value}"

    def paint(self, painter, option, index):
        painter.save()

        # Get the data for the current cell
        data = index.model().data(index, Qt.DisplayRole)
        col = self._columns[index.column()]

        bg_color = index.model().data(index, Qt.BackgroundRole)
        if bg_color is not None:
            painter.fillRect(option.rect, bg_color)  # Fill the cell with the background color

        text_color = index.model().data(index, Qt.TextColorRole)
        if text_color is not None:
            painter.setPen(QPen(text_color.color()))

        if col in ['XZ', 'IJ']:  # Combined Offsets column
            x_val, z_val = data.split('\n')
            x_label, x_value = x_val.split(': ')
            z_label, z_value = z_val.split(': ')

            # Calculate positions
            rect = option.rect
            left_margin = 5
            right_margin = 5

            # QFontMetrics for text width calculation
            font_metrics = painter.fontMetrics()
            label_width = max(font_metrics.width(x_label + ': '), font_metrics.width(z_label + ': '))

            # Adjust middle position based on label width
            middle_margin = 10  # Adjust this margin as needed
            middle = left_margin + label_width + middle_margin

            # Draw labels (X and Z) aligned to the left
            painter.drawText(rect.adjusted(left_margin, 0, -rect.width() + middle, 0), Qt.AlignVCenter | Qt.AlignLeft, f"{x_label}:\n{z_label}:")

            # Draw values aligned to the right
            painter.drawText(rect.adjusted(middle, 0, -right_margin, 0), Qt.AlignVCenter | Qt.AlignRight, f"{x_value}\n{z_value}")

        elif col == 'Q':  # Assuming 'Q' is the Orient column
            arrow_length = 15
            space_between = 5  # Adjust this value for more or less space

            # Draw the arrow
            self.draw_arrow(painter, option, data, arrow_length)

            # Draw the text (value) next to the arrow
            painter.save()
            text = str(data)

            # Calculate the position to start the text
            # Add some additional space between the arrow and the text
            arrow_end_x = option.rect.center().x() + min(option.rect.width(), option.rect.height()) // 4 + space_between
            painter.drawText(arrow_end_x, option.rect.y(), option.rect.width(), option.rect.height(), Qt.AlignVCenter | Qt.AlignLeft, text)

            painter.restore()

        else:
            # Default rendering for other columns
            super().paint(painter, option, index)

        painter.restore()

    @staticmethod
    def draw_arrow(painter, option, value, arrow_length):
        # This method will draw a rotated arrow with the specified color
        painter.save()
        rect = option.rect

        # Translate and rotate the painter
        painter.translate(rect.center())
        painter.rotate(get_orient_arrow_angle(value))
        painter.translate(-rect.center())

        # Calculate the start and end points for the line
        # Use the specified arrowLength instead of calculating from the cell size
        start_x = rect.center().x() - arrow_length // 2
        end_x = rect.center().x() + arrow_length // 2
        center_y = rect.center().y()

        # Create a pen with the specified color and set it for the painter
        pen = QPen()
        pen.setWidth(2)
        painter.setPen(pen)

        # Draw the line part of the arrow
        painter.drawLine(start_x, center_y, end_x, center_y)

        # Draw the 'V' part of the arrow at the end
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
            tool_no = sorted(self._tool_table)[index.row() + 1]
            if self.stat.tool_in_spindle == tool_no:
                return QBrush(self.current_tool_color)
            else:
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

    def saveToolTable(self):
        self.tt.saveToolTable(self._tool_table, self._columns)
        return True

    def clearToolTable(self):
        self.beginRemoveRows(QModelIndex(), 0, 100)
        # delete all but the spindle, which can't be deleted
        self._tool_table = {0: self._tool_table[0]}
        self.endRemoveRows()
        return True

    def loadToolTable(self):
        # the tooltable plugin will emit the tool_table_changed signal
        # so we don't need to do any more here
        self.tt.loadToolTable()
        return True


class LatheToolTable(QTableView):
    toolSelected = Signal(int)
    anythingSelected = Signal(bool)

    def __init__(self, parent=None):
        super(LatheToolTable, self).__init__(parent)

        # Set a fixed row height that is sufficient for two lines
        self.verticalHeader().setDefaultSectionSize(60)  # Adjust this value as needed

        self.tool_model = ToolModel(self)

        self.item_delegate = ItemDelegate(columns=self.tool_model._columns)
        self.setItemDelegate(self.item_delegate)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setFilterKeyColumn(0)
        self.proxy_model.setSourceModel(self.tool_model)

        self.setModel(self.proxy_model)

        # Properties
        self._columns = self.tool_model._columns
        self._confirm_actions = False
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

        self.clicked.connect(self.onClick)
        self.selectionModel().currentRowChanged.connect(self.onSelectionChanged)
        self.anythingSelected.emit(False)

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
        if selected_tool is not None:
            issue_mdi("M61 Q%s G43" % selected_tool)
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

    def onClick(self, index):
        tool_no = self.tool_model.toolDataFromRow(index.row())['T']
        self.toolSelected.emit(tool_no)

    def onSelectionChanged(self, current: QModelIndex, previous: QModelIndex):
        """Slot that gets called when the selection changes."""
        if current.isValid():
            row = current.row()
            tool_number = self.tool_model.toolDataFromRow(row)['T']
            print("selection changed to: ", tool_number)
            self.anythingSelected.emit(True)
        else:
            print("selection cleared")
            self.anythingSelected.emit(False)

    def confirmAction(self, message):
        if not self._confirm_actions:
            return True

        box = QMessageBox.question(self,
                                   'Confirm Action',
                                   message,
                                   QMessageBox.Yes,
                                   QMessageBox.No)

        if box == QMessageBox.Yes:
            return True
        else:
            return False

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
