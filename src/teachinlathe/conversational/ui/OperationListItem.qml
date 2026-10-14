import QtQuick 2.15
import "."
import theme 1.0

OperationRowDelegate {
    id: root

    property int operationIndex: -1
    property var operationData: null
    property bool selected: false
    property int operationsCount: 0

    width: parent ? parent.width : 400
    height: Theme.rowHeight
    rowIndex: operationIndex
    op: operationData
    isCurrentItem: selected
    totalCount: operationsCount
    isFirstItem: operationIndex === 0
    isLastItem: operationIndex === (operationsCount - 1)

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: Theme.hairline
        color: Theme.outlineDisabled
        z: 10
    }
}
