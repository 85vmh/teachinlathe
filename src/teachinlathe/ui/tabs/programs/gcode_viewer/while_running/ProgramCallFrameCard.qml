import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.programs
import theme

// One line of a calling file, drawn as a slice of the GCodeTextArea under it:
// the same gutter, font and offsets, so its number and code line up with the
// code below. The calling line is marked like the viewer marks the current
// one - a box round the code only, the number just in red.
ProgramContentFrame {
    id: root
    property string title: ""
    property int lineNumber: 0
    property string lineText: ""
    property real lineBoxConnectorX: lineRow.x + lineBox.x + 18
    property real lineBoxMidY: lineRow.y + lineBox.y + (lineBox.height / 2)

    // GCodeTextArea's metrics.
    readonly property int gutterWidth: 56
    readonly property int codeIndent: 12
    readonly property string codeFont: "DejaVu Sans Mono"
    readonly property int codePixelSize: 18
    readonly property color callColor: "#E51400"

    Rectangle {
        id: lineRow
        Layout.fillWidth: true
        implicitHeight: lineLabel.implicitHeight + 12
        color: "#ffffff"

        Rectangle {
            id: gutter
            width: root.gutterWidth
            height: parent.height
            color: "#f5f5f5"

            Text {
                width: parent.width - 10
                anchors.verticalCenter: parent.verticalCenter
                horizontalAlignment: Text.AlignRight
                text: root.lineNumber > 0 ? root.lineNumber : "?"
                color: root.callColor
                font.family: root.codeFont
                font.pixelSize: root.codePixelSize
            }

            Rectangle {
                anchors.right: parent.right
                width: Theme.hairline
                height: parent.height
                color: "#e0e0e0"
            }
        }

        Rectangle {
            id: lineBox
            anchors.left: gutter.right
            anchors.right: parent.right
            height: parent.height
            color: Theme.dangerSoft
            border.color: root.callColor
            border.width: 2

            Text {
                id: lineLabel
                x: root.codeIndent
                width: parent.width - root.codeIndent - 6
                anchors.verticalCenter: parent.verticalCenter
                text: root.lineText || ""
                color: "#2e2e2e"
                font.family: root.codeFont
                font.pixelSize: root.codePixelSize
                elide: Text.ElideRight
            }
        }
    }
}
