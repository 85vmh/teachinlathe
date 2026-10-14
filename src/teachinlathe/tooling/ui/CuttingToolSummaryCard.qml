import QtQuick 2.15
import theme 1.0

// A cutting tool of a kind that has no card of its own yet: one line.
Rectangle {
    id: root

    property var view: null            // CuttingToolSummary
    signal tapped()

    radius: Theme.radius
    color: area.pressed ? Theme.hover : Theme.surface
    border.width: Theme.hairline
    border.color: Theme.outline

    MouseArea {
        id: area
        anchors.fill: parent
        onClicked: root.tapped()
    }

    Text {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: Theme.spacing
        anchors.verticalCenter: parent.verticalCenter
        text: root.view ? root.view.text : ""
        elide: Text.ElideRight
        color: Theme.foreground
        font.pixelSize: Theme.fontBody
    }
}
