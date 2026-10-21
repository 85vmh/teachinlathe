import QtQuick
import theme

// A program option that stays on: the app bar's Back button, with a lamp at
// its start that is green while the option is on. One line of text.
Rectangle {
    id: root

    property alias text: label.text
    property bool checked: false

    signal clicked()

    implicitHeight: Theme.buttonHeight
    implicitWidth: row.implicitWidth + 36
    radius: Theme.radius
    color: !enabled ? Theme.surfaceSunken : (mouse.pressed ? Theme.accentSoft : Theme.hover)
    border.width: Theme.hairline
    border.color: enabled ? "#c5d0df" : Theme.separator
    opacity: enabled ? 1.0 : 0.75

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 12

        Rectangle {
            id: led
            anchors.verticalCenter: parent.verticalCenter
            width: 20
            height: 20
            radius: 10
            color: root.checked ? Theme.primaryBorder : "#b9c3d1"
            border.width: Theme.hairline
            border.color: root.checked ? Theme.primary : "#8c97a8"

            // the glow of a lit lamp
            Rectangle {
                anchors.centerIn: parent
                width: 30
                height: 30
                radius: 15
                visible: root.checked
                color: "transparent"
                border.width: 3
                border.color: Qt.rgba(63 / 255, 185 / 255, 80 / 255, 0.3)
            }
        }

        Text {
            id: label
            anchors.verticalCenter: parent.verticalCenter
            color: root.enabled ? Theme.foreground : "#8c97a8"
            font.pixelSize: 15
            font.bold: true
            maximumLineCount: 1
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        enabled: root.enabled
        onClicked: root.clicked()
    }
}
