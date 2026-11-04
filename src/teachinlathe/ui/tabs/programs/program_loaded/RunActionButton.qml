import QtQuick
import theme

// Cycle Abort and Feed Hold / Resume in the run bar: the app bar's Cycle
// Start button, in the colour each is given.
Rectangle {
    id: root

    property alias text: label.text
    property color fill: Theme.primary
    property color pressedFill: Theme.primaryPressed
    property color edge: Theme.primaryBorder
    // Lit, as Cycle Start is while the machine's cycle-start LED is.
    property bool active: false

    signal clicked()

    implicitHeight: Theme.buttonHeight
    implicitWidth: Math.max(140, label.implicitWidth + 36)
    radius: Theme.radius
    color: !enabled ? Theme.primaryDisabled
         : area.pressed ? root.pressedFill
         : root.active ? root.edge
         : root.fill
    border.width: Theme.hairline
    border.color: enabled ? root.edge : Theme.primaryDisabled
    opacity: enabled ? 1.0 : 0.75

    Text {
        id: label
        anchors.centerIn: parent
        color: "white"
        font.pixelSize: 16
        font.bold: true
    }

    MouseArea {
        id: area
        anchors.fill: parent
        enabled: root.enabled
        onClicked: root.clicked()
    }
}
