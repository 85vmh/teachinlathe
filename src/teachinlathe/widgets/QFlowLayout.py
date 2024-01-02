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

        # Initial vertical space before the first row
        initialVSpacing = 5  # Adjust the value as needed for your layout

        x = effectiveRect.x()
        y = effectiveRect.y() + initialVSpacing  # Start with the initial vertical spacing
        lineHeight = 0

        # Horizontal and vertical spacing between buttons and rows
        hSpacing = 15  # Horizontal spacing between buttons
        vSpacing = 12  # Vertical spacing between rows of buttons

        # Calculate the width of all buttons and the spacing in one row
        totalButtonWidth = sum(item.sizeHint().width() for item in self.itemList[:4])
        totalSpacingWidth = (3 * hSpacing)  # There are always 3 gaps between 4 buttons

        # Start position for the first button
        x += (effectiveRect.width() - (totalButtonWidth + totalSpacingWidth)) // 2

        for i, item in enumerate(self.itemList):
            wid = item.widget()
            itemWidthWithSpacing = item.sizeHint().width()

            # Place the item
            item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            # Update x to the next item's position, with horizontal spacing
            x += itemWidthWithSpacing + hSpacing

            # Update lineHeight for the tallest item in the row
            lineHeight = max(lineHeight, item.sizeHint().height())

            # If we have placed 4 items or this is the last item, reset x and increment y
            if (i + 1) % 4 == 0 or (i + 1) == len(self.itemList):
                x = effectiveRect.x() + (effectiveRect.width() - (totalButtonWidth + totalSpacingWidth)) // 2
                y += lineHeight + vSpacing
                lineHeight = 0
