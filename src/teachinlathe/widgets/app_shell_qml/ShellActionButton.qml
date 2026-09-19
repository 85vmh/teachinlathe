import QtQuick 2.15
import QtQuick.Controls 2.15
import theme 1.0

Rectangle {
    id: root

    property alias text: label.text
    property bool secondary: false
    property bool checkable: false
    property bool checked: false

    signal clicked()

    implicitWidth: Math.max(96, label.implicitWidth + 36)
    implicitHeight: Theme.buttonHeight
    radius: Theme.radius
    color: {
        if (!enabled) return secondary ? Theme.surfaceSunken : Theme.primaryDisabled
        if (checkable && checked) return actionArea.pressed ? "#684b0f" : "#7a5a12"
        if (secondary) return actionArea.pressed ? Theme.accentSoft : Theme.hover
        return actionArea.pressed ? Theme.primaryPressed : Theme.primary
    }
    border.width: Theme.hairline
    border.color: {
        if (!enabled) return secondary ? Theme.separator : Theme.primaryDisabled
        if (checkable && checked) return "#d7ba7d"
        return secondary ? "#c5d0df" : Theme.primaryBorder
    }
    opacity: enabled ? 1.0 : 0.75

    Text {
        id: label
        anchors.centerIn: parent
        color: root.secondary ? (root.enabled ? Theme.foreground : "#8c97a8") : "white"
        font.pixelSize: root.secondary ? 15 : 16
        font.bold: true
        elide: Text.ElideRight
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    MouseArea {
        id: actionArea
        anchors.fill: parent
        enabled: root.enabled
        onClicked: root.clicked()
    }
}
