import QtQuick
import theme

OperationRowDelegate {
    id: root

    property int operationIndex: -1
    property var operationData: null
    property bool selected: false

    width: parent ? parent.width : 400
    height: Theme.rowHeight
    rowIndex: operationIndex
    op: operationData
    isCurrentItem: selected

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: Theme.hairline
        color: Theme.outlineDisabled
        z: 10
    }
}
