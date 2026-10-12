import QtQuick 2.15
import QtQuick.Controls 2.15
import theme 1.0

// The tool holders, one row each, showing what is stored for the holder.
// A holder that cannot be used yet - no cutting tool, or one that has not
// been touched off - is marked with a stripe down its left edge.
ToolLibraryPane {
    id: root

    property var model: null

    title: "Tool Holders"

    ListView {
        anchors.fill: parent
        anchors.margins: Theme.spacingSmall
        spacing: Theme.spacingSmall
        clip: true
        model: root.model
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {}

        delegate: Rectangle {
            width: ListView.view.width
            height: Math.max(Theme.rowHeight, column.implicitHeight + 2 * Theme.spacing)
            radius: Theme.radius
            color: Theme.surface
            border.color: Theme.outline
            border.width: Theme.hairline

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.margins: Theme.hairline
                width: 5
                radius: Theme.radiusSmall
                color: model.ready ? Theme.primary : Theme.warning
            }

            Column {
                id: column
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: Theme.spacingLarge
                anchors.rightMargin: Theme.spacing
                spacing: 4

                Text {
                    width: parent.width
                    text: model.text
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    color: Theme.foreground
                    font.pixelSize: Theme.fontSmall
                    font.family: "monospace"
                }

                Text {
                    width: parent.width
                    visible: text !== ""
                    text: model.toolText
                    elide: Text.ElideRight
                    color: Theme.foregroundSubtle
                    font.pixelSize: Theme.fontSmall
                }
            }
        }
    }
}
