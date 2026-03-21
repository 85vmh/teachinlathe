import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ProgramContentFrame {
    id: root
    property string title: ""
    property int lineNumber: 0
    property string lineText: ""
    property real lineBoxConnectorX: lineBox.x + 18
    property real lineBoxMidY: lineBox.y + (lineBox.height / 2)

    Rectangle {
        id: lineBox
        Layout.fillWidth: true
        color: "#1e1e1e"
        radius: 3
        border.color: "#E51400"
        border.width: 2
        implicitHeight: lineLabel.implicitHeight + 18

        Text {
            id: lineLabel
            anchors.fill: parent
            anchors.margins: 9
            text: (root.lineNumber > 0 ? root.lineNumber : "?") + ": " + (root.lineText || "")
            color: "#f0f0f0"
            font.family: "DejaVu Sans Mono"
            font.pixelSize: 14
            elide: Text.ElideRight
        }
    }
}
