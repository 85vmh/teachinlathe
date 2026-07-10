import QtQuick 2.15
import "."

OperationRowDelegate {
    id: root

    property int operationIndex: -1
    property var operationData: null
    property bool selected: false
    property int operationsCount: 0

    width: parent ? parent.width : 400
    height: 72
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
        height: 1
        color: "#dddddd"
        z: 10
    }
}
