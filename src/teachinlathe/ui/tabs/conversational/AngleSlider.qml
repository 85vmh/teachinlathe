// AngleSlider.qml — an angle picked on a horizontal slider: the track from
// `from` to `to`, its snap points ticked on it and their angles under it,
// the knob on the angle, and over the knob a box with the angle in it.
// A press or a drag on it moves the knob to the angle under the finger: in
// whole `step`s, or a snap point's when within `snapDistance` of one.
// It shows value, as it is given, but for the drag's angle while one is on;
// the angle picked is reported once the finger is lifted (valueEdited).
import QtQuick
import QtQuick.Controls
import theme

Item {
    id: root

    property real value: 45
    property real from: 30
    property real to: 60
    // the angles it snaps to, ticked and named under the track
    property var snaps: [30, 45, 60]
    // how near a snap point a finger takes the angle to it
    property real snapDistance: 2
    property real step: 1

    signal valueEdited(real value)

    // view state: a drag on
    property bool _dragging: false
    // view state: the angle under the drag's finger
    property real _dragValue: value
    // the angle the knob and the box show: the drag's while it is on
    readonly property real shownValue: _dragging ? _dragValue : value

    readonly property real knobRadius: 13
    readonly property real trackHeight: 6
    // the box over the knob, as wide as the widest angle
    readonly property real valueBoxWidth: 56
    readonly property real valueBoxHeight: 30
    // the knob's centre this far in at either end: the box over it inside
    // the slider
    readonly property real trackLeft: Math.max(knobRadius, valueBoxWidth / 2)
    readonly property real trackWidth: Math.max(1, width - 2 * trackLeft)
    readonly property real trackY: valueBoxHeight + 10 + knobRadius

    implicitWidth: 260
    implicitHeight: trackY + knobRadius + 8 + snapLabelMetrics.height

    function _xOf(angle) {
        return trackLeft + (Math.min(Math.max(angle, from), to) - from) / (to - from) * trackWidth
    }

    // the angle under a finger at x: a snap point's near one, else in whole steps
    function _angleAt(x) {
        var raw = from + (x - trackLeft) / trackWidth * (to - from)
        raw = Math.min(Math.max(raw, from), to)
        for (var i = 0; i < snaps.length; i++)
            if (Math.abs(raw - snaps[i]) <= snapDistance)
                return snaps[i]
        return Math.min(Math.max(Math.round(raw / step) * step, from), to)
    }

    function _text(angle) { return Math.round(angle) + "°" }

    TextMetrics { id: snapLabelMetrics; font.pixelSize: Theme.fontSmall; text: "60°" }

    component Track: Rectangle {
        x: root.trackLeft
        y: root.trackY - height / 2
        height: root.trackHeight
        radius: height / 2
    }

    // the track, filled from its start to the knob
    Track {
        width: root.trackWidth
        color: Theme.surfaceSunken
        border.color: Theme.outline
        border.width: Theme.hairline
    }
    Track {
        width: root._xOf(root.shownValue) - root.trackLeft
        color: Theme.accentStrong
    }

    // the snap points: a tick across the track, the angle under it
    Repeater {
        model: root.snaps
        Item {
            required property var modelData
            x: root._xOf(modelData)
            Rectangle {
                x: -width / 2
                y: root.trackY - 9
                width: 2
                height: 18
                radius: 1
                color: Theme.foregroundMuted
            }
            Label {
                x: -width / 2
                y: root.trackY + root.knobRadius + 8
                text: root._text(modelData)
                font.pixelSize: Theme.fontSmall
                font.bold: modelData === root.shownValue
                color: modelData === root.shownValue ? Theme.foregroundStrong : Theme.foregroundMuted
            }
        }
    }

    // the knob, on the angle
    Rectangle {
        id: knob
        x: root._xOf(root.shownValue) - width / 2
        y: root.trackY - height / 2
        width: 2 * root.knobRadius
        height: width
        radius: width / 2
        color: Theme.surface
        border.color: Theme.accentStrong
        border.width: 3
    }

    // over the knob, the angle in a box
    Rectangle {
        x: knob.x + knob.width / 2 - width / 2
        y: 0
        width: root.valueBoxWidth
        height: root.valueBoxHeight
        radius: Theme.radius
        color: Theme.accentStrong
        Label {
            anchors.centerIn: parent
            text: root._text(root.shownValue)
            font.pixelSize: Theme.fontBody
            font.bold: true
            color: Theme.surface
        }
        // its point, down to the knob
        Rectangle {
            x: parent.width / 2 - width / 2
            y: parent.height - height / 2
            width: 10
            height: 10
            rotation: 45
            color: Theme.accentStrong
            z: -1
        }
    }

    // a press or a drag along it takes the knob to the angle under the
    // finger; lifted, that angle is the one picked. Kept from the canvas
    // under the box, which would pan.
    MouseArea {
        anchors.fill: parent
        preventStealing: true
        onPressed: function(mouse) {
            root._dragValue = root._angleAt(mouse.x)
            root._dragging = true
        }
        onPositionChanged: function(mouse) {
            if (root._dragging)
                root._dragValue = root._angleAt(mouse.x)
        }
        onReleased: {
            if (!root._dragging)
                return
            var angle = root._dragValue
            root._dragging = false
            if (angle !== root.value)
                root.valueEdited(angle)
        }
        onCanceled: root._dragging = false
    }
}
