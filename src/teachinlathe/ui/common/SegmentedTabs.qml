import QtQuick
import theme

// A row of tabs inside one rounded outline, one of them chosen: the chosen one
// filled and its text bold, the others white, a line between two. The Line
// card's XZ End / Angle + X End / Angle + Z End and the Manual Turning
// spindle's RPM / CSS.
Rectangle {
    id: root

    //: the tabs' texts, left to right
    property var labels: []
    property int currentIndex: 0
    property int fontPixelSize: Theme.fontBody

    //: a tab was tapped; currentIndex follows only through its binding
    signal activated(int index)

    implicitHeight: 46
    radius: Theme.radiusLarge
    color: "transparent"

    Row {
        anchors.fill: parent

        Repeater {
            model: root.labels

            delegate: Item {
                id: tab
                required property int index
                required property string modelData
                readonly property bool selected: index === root.currentIndex
                readonly property bool isFirst: index === 0
                readonly property bool isLast: index === root.labels.length - 1
                width: root.width / Math.max(1, root.labels.length)
                height: root.height

                // rounded only on the outline's own corners: a square strip
                // covers the inner side of the first and the last tab
                Rectangle {
                    anchors.fill: parent
                    radius: (tab.isFirst || tab.isLast) ? root.radius : 0
                    color: tab.selected ? Theme.outlineDisabled : Theme.surface

                    Rectangle {
                        anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
                        width: root.radius
                        visible: tab.isFirst && !tab.isLast
                        color: parent.color
                    }
                    Rectangle {
                        anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
                        width: root.radius
                        visible: tab.isLast && !tab.isFirst
                        color: parent.color
                    }
                }

                Rectangle {
                    visible: !tab.isLast
                    anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
                    width: Theme.hairline
                    color: Theme.separator
                    z: 1
                }

                Text {
                    anchors.centerIn: parent
                    text: tab.modelData
                    color: tab.selected ? Theme.surfaceInverse : Theme.foreground
                    font.pixelSize: root.fontPixelSize
                    font.bold: tab.selected
                    z: 2
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: root.activated(tab.index)
                }
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: "transparent"
        border.color: Theme.separator
        border.width: Theme.hairline
        z: 3
    }
}
