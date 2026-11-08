import QtQuick
import theme

// An on / off switch: a pill, green with the knob at the right when on, grey
// with it at the left when off; the knob slides between the two. Drawn only -
// what it sits in takes the tap (ToggleBox), unless interactive.
Item {
    id: root

    property bool checked: false
    //: takes its own taps (toggled()); off where the box round it takes them
    property bool interactive: false

    signal toggled()

    readonly property int knobMargin: 3

    implicitWidth: 52
    implicitHeight: 30
    // faded when off on its own; in a box, the box fades
    opacity: interactive && !enabled ? Theme.disabledOpacity : 1.0

    Rectangle {
        id: track
        anchors.fill: parent
        radius: height / 2
        color: root.checked ? Theme.switchOn : Theme.switchOff
        Behavior on color { ColorAnimation { duration: Theme.animationFast } }
    }

    // the knob's shadow, a little under it
    Rectangle {
        width: knob.width
        height: knob.height
        radius: width / 2
        x: knob.x
        y: knob.y + 1.5
        color: Theme.shadow
    }

    Rectangle {
        id: knob
        width: root.height - 2 * root.knobMargin
        height: width
        radius: width / 2
        y: root.knobMargin
        x: root.checked ? root.width - width - root.knobMargin : root.knobMargin
        color: Theme.surface
        Behavior on x { NumberAnimation { duration: Theme.animationFast; easing.type: Easing.OutCubic } }
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.interactive
        onClicked: root.toggled()
    }
}
