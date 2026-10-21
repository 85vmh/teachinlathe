import QtQuick 2.15
import theme 1.0

// A titled box, the QML counterpart of the .ui's QGroupBox.
Rectangle {
    id: root

    property string title: ""
    property Item content: null

    implicitHeight: column.implicitHeight + 28
    radius: Theme.radiusLarge
    color: "white"
    border.width: Theme.hairline
    border.color: Theme.separator

    Column {
        id: column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 14
        spacing: Theme.spacing

        Text {
            text: root.title
            font.pixelSize: Theme.fontBody
            font.bold: true
            color: Theme.foreground
        }

        Item {
            width: parent.width
            implicitHeight: root.content ? root.content.implicitHeight : 0
            children: root.content ? [root.content] : []
        }
    }
}
