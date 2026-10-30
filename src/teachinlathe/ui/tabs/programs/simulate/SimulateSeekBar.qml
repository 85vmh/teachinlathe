// SimulateSeekBar.qml — the simulation's timeline: as long as the program runs,
// what is done of it filled in, and its marks along it - each operation's
// start, numbered over the bar, a tool change, an M0/M1 the run may wait at,
// and under the bar, in red, a rapid through the material. Dragged or tapped,
// it asks for that moment (seekRequested); a tap near an operation's mark
// goes to the operation's start.
import QtQuick
import theme

Item {
    id: root

    property real duration: 0
    property real time: 0
    // [{time, kind, number, label}] - kind "operation", "tool_change", "stop", "end"
    property var marks: []
    // [{time}]
    property var collisions: []
    // false while the run is running: it cannot be moved then
    property bool seekable: true

    signal seekRequested(real time)

    readonly property color operationColor: "#1565c0"
    readonly property color toolChangeColor: "#6d4c41"
    readonly property color stopColor: Theme.warning
    readonly property color collisionColor: Theme.danger
    // px either side of an operation's mark a tap snaps to it
    readonly property real snap: 14
    readonly property real trackHeight: 10
    readonly property real labelBand: 22

    implicitHeight: labelBand + trackHeight + 26

    function _x(t) { return root.duration > 0 ? track.x + track.width * t / root.duration : track.x }
    function _time(px) {
        var t = (px - track.x) / Math.max(track.width, 1) * root.duration
        return Math.min(Math.max(t, 0), root.duration)
    }
    // the time a tap at ``px`` asks for: an operation's start when near one
    function _snapped(px) {
        for (var i = 0; i < root.marks.length; i++)
            if (root.marks[i].kind === "operation" && Math.abs(_x(root.marks[i].time) - px) <= root.snap)
                return root.marks[i].time
        return _time(px)
    }

    Rectangle {
        id: track
        x: Theme.spacingLarge
        y: root.labelBand
        width: root.width - 2 * Theme.spacingLarge
        height: root.trackHeight
        radius: height / 2
        color: Theme.surfaceSunken
        border.color: Theme.outline
        border.width: Theme.hairline

        Rectangle {
            width: root.duration > 0 ? parent.width * root.time / root.duration : 0
            height: parent.height
            radius: parent.radius
            color: Theme.accent
        }
    }

    // the marks: an operation's numbered over the bar, the others on it
    Repeater {
        model: root.marks
        delegate: Item {
            readonly property var mark: modelData
            readonly property bool isOperation: mark.kind === "operation"
            x: root._x(mark.time) - width / 2
            y: isOperation ? 0 : track.y - 4
            width: isOperation ? Math.max(18, numberText.implicitWidth + 6) : 4
            height: isOperation ? root.labelBand + track.height : track.height + 8
            visible: mark.kind !== "end"

            Rectangle {
                visible: isOperation
                anchors.horizontalCenter: parent.horizontalCenter
                y: root.labelBand - 4
                width: 2
                height: track.height + 8
                color: root.operationColor
            }
            Text {
                id: numberText
                visible: isOperation
                anchors.horizontalCenter: parent.horizontalCenter
                text: isOperation ? String(mark.number) : ""
                color: root.operationColor
                font.pixelSize: Theme.fontSmall
                font.bold: true
            }
            Rectangle {
                visible: !isOperation
                anchors.fill: parent
                radius: 1
                color: mark.kind === "stop" ? root.stopColor : root.toolChangeColor
            }
        }
    }

    // a rapid through the material, under the bar
    Repeater {
        model: root.collisions
        delegate: Rectangle {
            x: root._x(modelData.time) - width / 2
            y: track.y + track.height + 3
            width: 4
            height: 8
            color: root.collisionColor
        }
    }

    // where the run is
    Rectangle {
        x: root._x(root.time) - width / 2
        y: track.y + track.height / 2 - height / 2
        width: 22
        height: 22
        radius: 11
        color: root.seekable ? Theme.surface : Theme.surfaceSunken
        border.color: Theme.accentStrong
        border.width: 3
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.seekable && root.duration > 0
        property bool dragged: false
        onPressed: function(mouse) { dragged = false }
        onPositionChanged: function(mouse) {
            dragged = true
            root.seekRequested(root._time(mouse.x))
        }
        onReleased: function(mouse) {
            if (!dragged) root.seekRequested(root._snapped(mouse.x))
        }
    }
}
