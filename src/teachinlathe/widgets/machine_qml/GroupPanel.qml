import QtQuick 2.15

// A titled box, the QML counterpart of the .ui's QGroupBox.
Rectangle {
    id: root

    property string title: ""
    property Item content: null

    implicitHeight: column.implicitHeight + 28
    radius: 8
    color: "white"
    border.width: 1
    border.color: "#d5dbe4"

    Column {
        id: column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 14
        spacing: 12

        Text {
            text: root.title
            font.pixelSize: 16
            font.bold: true
            color: "#1e2430"
        }

        Item {
            width: parent.width
            implicitHeight: root.content ? root.content.implicitHeight : 0
            children: root.content ? [root.content] : []
        }
    }
}
