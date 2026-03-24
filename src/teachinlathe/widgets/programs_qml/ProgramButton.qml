import QtQuick 2.15
import QtQuick.Controls 2.15

Button {
    id: root
    property bool active: false
    property color accentColor: active ? "#1E88E5" : "#e8e8e8"
    property color borderColor: active ? "#1565C0" : "#cccccc"

    implicitHeight: 42
    implicitWidth: Math.max(120, contentItem.implicitWidth + 32)

    background: Rectangle {
        radius: 8
        color: root.enabled ? root.accentColor : "#f0f0f0"
        border.color: root.borderColor
        border.width: 1
        opacity: root.enabled ? 1.0 : 0.55
    }

    contentItem: Text {
        text: root.text
        color: root.enabled ? (root.active ? "#ffffff" : "#202020") : "#9e9e9e"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: 15
        font.family: "Noto Sans"
        font.bold: root.active
    }
}
