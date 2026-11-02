import QtQuick
import theme

// The spindle's lever, as on the machine, seen from the front, beside the
// spindle panel: a slot from M4 at the top through OFF in the middle to M3 at
// the bottom, its knob where the spindle is (``position``), sliding there
// when it changes. The slot runs between ``topY`` and ``bottomY`` - the
// panel's M4 and M3 icons' middles - a mark at OFF halfway.
Item {
    id: root

    //: -1 M4 (top), 0 OFF (middle), 1 M3 (bottom)
    property int position: 0
    property real topY: 0
    property real bottomY: height
    //: the knob's colour: green while the spindle turns, red just stopped;
    //: it changes over ``travelMs``
    property color knobColor: "#9aa3b0"
    Behavior on knobColor { ColorAnimation { duration: root.travelMs } }
    //: how long the knob takes from OFF to M3 or M4, ms
    property int travelMs: 350

    readonly property real knobSize: 30
    readonly property real slotWidth: 10

    function yAt(position) {
        return (topY + bottomY) / 2 + position * (bottomY - topY) / 2
    }

    // the slot, a little past the end stops
    Rectangle {
        x: (root.width - root.slotWidth) / 2
        y: root.topY - root.slotWidth
        width: root.slotWidth
        height: root.bottomY - root.topY + 2 * root.slotWidth
        radius: root.slotWidth / 2
        color: Theme.outlineDisabled
        border.color: Theme.outlineStrong
        border.width: Theme.hairline
    }

    // OFF's mark
    Rectangle {
        x: (root.width - width) / 2
        y: root.yAt(0) - height / 2
        width: root.slotWidth + 12
        height: 2
        radius: 1
        color: Theme.outlineStrong
    }

    // the knob, a ball on the lever's end
    Rectangle {
        id: knob
        x: (root.width - width) / 2
        y: root.yAt(root.position) - height / 2
        width: root.knobSize
        height: root.knobSize
        radius: width / 2
        border.color: Qt.darker(root.knobColor, 1.4)
        border.width: 1.5
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.lighter(root.knobColor, 1.45) }
            GradientStop { position: 1.0; color: root.knobColor }
        }
        Behavior on y { NumberAnimation { duration: root.travelMs; easing.type: Easing.InOutCubic } }
    }
}
