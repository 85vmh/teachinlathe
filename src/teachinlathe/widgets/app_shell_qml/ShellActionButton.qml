import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: root

    property alias text: label.text
    property bool secondary: false
    property bool checkable: false
    property bool checked: false

    signal clicked()

    implicitWidth: Math.max(96, label.implicitWidth + 36)
    implicitHeight: 44
    radius: 6
    color: {
        if (!enabled) return secondary ? "#f3f5f8" : "#8ea99a"
        if (checkable && checked) return actionArea.pressed ? "#684b0f" : "#7a5a12"
        if (secondary) return actionArea.pressed ? "#e5edf9" : "#eef3fb"
        return actionArea.pressed ? "#25673a" : "#2d7d46"
    }
    border.width: 1
    border.color: {
        if (!enabled) return secondary ? "#d5dbe4" : "#8ea99a"
        if (checkable && checked) return "#d7ba7d"
        return secondary ? "#c5d0df" : "#3fb950"
    }
    opacity: enabled ? 1.0 : 0.75

    Text {
        id: label
        anchors.centerIn: parent
        color: root.secondary ? (root.enabled ? "#1e2430" : "#8c97a8") : "white"
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
