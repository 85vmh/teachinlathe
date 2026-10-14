import QtQuick 2.15
import Qt5Compat.GraphicalEffects
import theme 1.0

// The square icon button of the operation list's rows - delete, and the
// reorder arrows - and of the Programs file list's delete column.
Rectangle {
    id: iconBtn
    width: 40
    height: Theme.buttonHeight
    radius: Theme.radius

    // Background stays transparent, flashes light blue when pressed
    color: (!enabled ? "transparent"
                     : (pressedArea.pressed ? Theme.accentSoft : "transparent"))

    // Always show a border when enabled: gray by default, blue when pressed
    border.width: enabled ? 1 : 0
    border.color: !enabled ? "transparent"
                           : (pressedArea.pressed ? Theme.accentBorder : iconBtn.borderTint)

    opacity: enabled ? 1.0 : 0.35

    property alias source: baseImg.source
    property color tint: Theme.foregroundMuted
    // Named apart from the tint: the reorder arrows share this
    // component and are tinted too, and only the destructive one is
    // outlined in its own colour.
    property color borderTint: Theme.outlineStrong
    property bool  enabled: true
    signal clicked()

    Image {
        id: baseImg
        anchors.centerIn: parent
        sourceSize.width: 30
        sourceSize.height: 30
        visible: false
        fillMode: Image.PreserveAspectFit
        smooth: true
    }
    ColorOverlay {
        anchors.centerIn: baseImg
        width: baseImg.width
        height: baseImg.height
        source: baseImg
        color: iconBtn.tint
    }

    MouseArea {
        id: pressedArea
        anchors.fill: parent
        enabled: iconBtn.enabled
        onClicked: iconBtn.clicked()
    }
}
