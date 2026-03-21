import QtQuick 2.15
import QtQuick.Controls 2.15

Button {
    id: root
    property bool active: false
    property color accentColor: active ? "#0e639c" : "#353535"
    property color borderColor: active ? "#3794ff" : "#575757"

    implicitHeight: 42
    implicitWidth: Math.max(120, contentItem.implicitWidth + 32)

    background: Rectangle {
        radius: 8
        color: root.enabled ? root.accentColor : "#2a2a2a"
        border.color: root.borderColor
        border.width: 1
        opacity: root.enabled ? 1.0 : 0.55
    }

    contentItem: Text {
        text: root.text
        color: root.enabled ? "#f0f0f0" : "#707070"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: 15
        font.family: "Noto Sans"
        font.bold: root.active
    }
}
