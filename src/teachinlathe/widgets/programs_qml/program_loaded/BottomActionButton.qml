import QtQuick 2.15

// Rectangular checkable action button — QML port of the app-shell header
// button (#appShellActionButton QSS), so Break-on-M1 / Skip-Blocks keep the
// same look now that they live in the bottom action bar.
Item {
    id: root

    property string text: ""
    property bool enabled: true
    property bool checked: false

    signal clicked()

    implicitHeight: 70
    implicitWidth: 90

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: 6
        border.width: 1
        color: !root.enabled ? "#8ea99a"
             : root.checked  ? (mouse.containsMouse ? "#684b0f" : "#7a5a12")
             :                  (mouse.containsMouse ? "#25673a" : "#2d7d46")
        border.color: !root.enabled ? "#8ea99a"
                    : root.checked  ? "#d7ba7d"
                    :                  "#3fb950"

        Text {
            id: label
            anchors.centerIn: parent
            text: root.text
            color: root.enabled ? "white" : "#d9e7de"
            font.pixelSize: 16
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
