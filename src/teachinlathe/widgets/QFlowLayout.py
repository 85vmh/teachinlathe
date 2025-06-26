from PyQt5.QtWidgets import QLayout, QPushButton, QApplication, QWidget, QSizePolicy
from PyQt5.QtCore import QRect, QSize, QPoint, Qt


class QFlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super(QFlowLayout, self).__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def count(self):
        # Return the number of items in the layout
        return len(self.itemList)

    def itemAt(self, index):
        # Return the layout item at the given index
        if index < 0 or index >= len(self.itemList):
            return None
        return self.itemList[index]

    def takeAt(self, index):
        # Remove and return the layout item at the given index
        if index < 0 or index >= len(self.itemList):
            return None
        return self.itemList.pop(index)

    def addItem(self, item):
        self.itemList.append(item)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
        return size

    def setGeometry(self, rect):
        super(QFlowLayout, self).setGeometry(rect)
        if not self.itemList:
            return

        left, top, right, bottom = self.getContentsMargins()
        effectiveRect = rect.adjusted(+left, +top, -right, -bottom)

        max_per_row = 4
        vSpacing = 20
        y = effectiveRect.y() + 5  # top padding

        item_width = 80
        item_height = 50

        total_spacing = effectiveRect.width() - (max_per_row * item_width)
        if total_spacing < 0:
            total_spacing = 0
        space_between = total_spacing // (max_per_row + 1)

        i = 0
        while i < len(self.itemList):
            row_items = self.itemList[i:i + max_per_row]

            x = effectiveRect.x() + space_between

            for col in range(max_per_row):
                if col < len(row_items):
                    item = row_items[col]
                    item.setGeometry(QRect(QPoint(x, y), QSize(item_width, item_height)))
                x += item_width + space_between

            y += item_height + vSpacing
            i += max_per_row