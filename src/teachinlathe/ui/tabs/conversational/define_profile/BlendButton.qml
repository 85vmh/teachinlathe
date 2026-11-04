// BlendButton.qml — the button at the end of a primitive card, for the screen to
// ask which blend (BlendTypePopup) and put it on the primitive. Off while the
// primitive has a blend, or where its corner can have none.
import QtQuick
import QtQuick.Layouts
import tabs.conversational
import theme

Rectangle {
    id: root

    property var primData: ({})
    // the corner it is for (Geometry.cornersOf)
    property var corner: null
    // the card's number: what it shows, in a blend's colour while it can be
    // pressed, grey when off
    property int number: 0

    readonly property bool _hasBlend: !!primData && !!primData.blend && !!primData.blend.type
                                      && primData.blend.type !== "none"

    signal pressedToChoose()

    implicitWidth: CardMetrics.blendButtonSize
    implicitHeight: CardMetrics.blendButtonSize
    radius: Theme.radiusLarge
    enabled: !!corner && corner.blendable && !_hasBlend
    opacity: enabled ? 1.0 : Theme.disabledOpacity
    color: mouse.pressed ? Theme.accentSoft : "transparent"
    border.width: enabled ? Theme.hairline : 0
    border.color: mouse.pressed ? Theme.accentBorder : Theme.outlineStrong
    Layout.alignment: Qt.AlignVCenter

    CardNumber {
        anchors.centerIn: parent
        number: root.number
        fill: root.enabled ? Theme.blendTint : Theme.outlineStrong
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        enabled: parent.enabled
        onClicked: root.pressedToChoose()
    }
}
