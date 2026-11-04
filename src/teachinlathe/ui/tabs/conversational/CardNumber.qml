// CardNumber.qml — a card's number in a circle, over whatever is under it: the
// card's own colour behind it, or Theme.blendTint on what stands for a blend.
import QtQuick
import theme

Rectangle {
    property int number: 0
    property real diameter: 20
    property color fill: Theme.surface
    readonly property real fontRatio: 0.65

    width: diameter
    height: diameter
    radius: diameter / 2
    z: 1
    color: fill
    border.color: Theme.ink
    border.width: Theme.hairline

    Text {
        anchors.centerIn: parent
        text: parent.number
        color: Theme.ink
        font.pixelSize: Math.round(parent.diameter * parent.fontRatio)
    }
}
