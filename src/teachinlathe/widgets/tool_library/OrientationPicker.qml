import QtQuick 2.15
import QtQuick.Layouts 1.15
import theme 1.0

// LinuxCNC's nine lathe tool orientations, laid out as the tool sits
// around the tip: each picture shows the control point of one.
//
// `allowed` limits which can be picked; the rest stay on screen, dimmed,
// so the grid keeps its shape. Picking emits `picked` - the owner decides
// what that means and sets `orientation` back.
ColumnLayout {
    id: root

    property int orientation: 1
    property var allowed: [1, 2, 3, 4, 5, 6, 7, 8, 9]
    property int cellSize: 80
    property string title: "Orientation"

    signal picked(int orientation)

    spacing: 10

    Text {
        text: root.title; font.pixelSize: Theme.fontSmall; font.bold: true
        color: Theme.foreground
        horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true
        visible: root.title !== ""
    }

    GridLayout {
        columns: 3; rowSpacing: 6; columnSpacing: 6

        Repeater {
            model: [4, 8, 3, 5, 9, 7, 1, 6, 2]
            delegate: Rectangle {
                readonly property bool selectable: root.allowed.indexOf(modelData) >= 0
                width: root.cellSize; height: root.cellSize; radius: Theme.radius
                color:        (root.orientation === modelData) ? Theme.selection : Theme.surface
                border.color: (root.orientation === modelData) ? Theme.accent : "#aaaaaa"
                border.width: (root.orientation === modelData) ? 2 : 1
                opacity: selectable ? 1.0 : 0.3

                Image {
                    anchors.centerIn: parent
                    width: root.cellSize * 0.75; height: width
                    source: "../../images/lathe_control_point_" + modelData + ".png"
                    fillMode: Image.PreserveAspectFit
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: parent.selectable
                    onClicked: root.picked(modelData)
                }
            }
        }
    }
}
