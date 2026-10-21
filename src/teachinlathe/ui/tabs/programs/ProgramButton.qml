import QtQuick 2.15
import QtQuick.Controls 2.15
import theme 1.0

Button {
    id: root
    property bool active: false
    property color accentColor: active ? "#1E88E5" : Theme.outlineDisabled
    property color borderColor: active ? Theme.accentStrong : Theme.outline

    implicitHeight: Theme.buttonHeight
    implicitWidth: Math.max(120, contentItem.implicitWidth + 32)

    background: Rectangle {
        radius: Theme.radiusLarge
        color: root.enabled ? root.accentColor : Theme.surfaceSunken
        border.color: root.borderColor
        border.width: Theme.hairline
        opacity: root.enabled ? 1.0 : 0.55
    }

    contentItem: Text {
        text: root.text
        color: root.enabled ? (root.active ? Theme.surface : Theme.surfaceInverse) : Theme.outlineEmphasis
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: Theme.fontSmall
        font.family: "Noto Sans"
        font.bold: root.active
    }
}
