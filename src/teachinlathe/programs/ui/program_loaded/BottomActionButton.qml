import QtQuick 2.15
import theme 1.0

// Rectangular checkable action button — QML port of the app-shell header
// button (#appShellActionButton QSS), so Break-on-M1 / Skip-Blocks keep the
// same look now that they live in the bottom action bar.
Item {
    id: root

    property string text: ""
    property bool enabled: true
    property bool checked: false

    signal clicked()

    implicitHeight: Theme.buttonHeightTouch
    implicitWidth: 90

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: Theme.radius
        border.width: Theme.hairline
        color: !root.enabled ? Theme.primaryDisabled
             : root.checked  ? (mouse.containsMouse ? Theme.primaryPressed : Theme.primary)
             :                  (mouse.containsMouse ? "#684b0f" : "#7a5a12")
        border.color: !root.enabled ? Theme.primaryDisabled
                    : root.checked  ? Theme.primaryBorder
                    :                  "#d7ba7d"

        Text {
            id: label
            anchors.centerIn: parent
            text: root.text
            color: root.enabled ? "white" : Theme.outlineDisabled
            font.pixelSize: Theme.fontBody
            font.family: "Noto Sans"
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        enabled: root.enabled
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }
}
