// The simulation timeline. Operations sit below the track; an operation that
// loads a tool is circled in yellow. Define Profile is a prerequisite, not a
// machining operation, and is deliberately absent.
import QtQuick
import theme

Item {
    id: root

    property real duration: 0
    property real time: 0
    property var marks: []
    property var collisions: []
    property bool seekable: true

    signal seekRequested(real time)

    readonly property color operationColor: "#1565c0"
    readonly property color toolChangeColor: "#fbc02d"
    readonly property color stopColor: Theme.warning
    readonly property color collisionColor: Theme.danger
    readonly property real snap: 14
    readonly property real trackHeight: 10
    readonly property real trackMargin: 10
    readonly property real endpointPadding: 8
    readonly property real operationY: 78
    readonly property var operationMarks: _operations()
    readonly property var stopMarks: _stops()

    implicitHeight: 108

    function clock(seconds) {
        var total = Math.max(0, Math.round(seconds || 0))
        var hours = Math.floor(total / 3600)
        var minutes = Math.floor(total / 60) % 60
        var secs = total % 60
        var mm = (hours > 0 && minutes < 10 ? "0" : "") + minutes
        var ss = (secs < 10 ? "0" : "") + secs
        return (hours > 0 ? hours + ":" : "") + mm + ":" + ss
    }

    function _x(t) {
        return root.duration > 0
                ? track.x + track.width * Math.min(Math.max(t, 0), root.duration) / root.duration
                : track.x
    }

    function _time(px) {
        var value = (px - track.x) / Math.max(track.width, 1) * root.duration
        return Math.min(Math.max(value, 0), root.duration)
    }

    function _isDefineProfile(mark) {
        var label = String(mark.label || "").toLowerCase()
        return label.indexOf("define") !== -1 && label.indexOf("profile") !== -1
    }

    function _operations() {
        var result = []
        for (var i = 0; i < root.marks.length; ++i) {
            var mark = root.marks[i]
            if (mark.kind !== "operation" || root._isDefineProfile(mark))
                continue

            result.push({
                "time": mark.time,
                "number": mark.number,
                "label": mark.label,
                "toolChange": !!mark.toolChange
            })
        }
        return result
    }

    function _stops() {
        var result = []
        for (var i = 0; i < root.marks.length; ++i) {
            if (root.marks[i].kind === "stop")
                result.push(root.marks[i])
        }
        return result
    }

    function _snapped(px) {
        for (var i = 0; i < root.operationMarks.length; ++i) {
            var operation = root.operationMarks[i]
            if (Math.abs(root._x(operation.time) - px) <= root.snap)
                return operation.time
        }
        return root._time(px)
    }

    Rectangle {
        id: track
        x: startTime.implicitWidth + root.endpointPadding
        y: 50
        width: Math.max(0, root.width - x - endTime.implicitWidth - root.endpointPadding)
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

    // Only M0/M1 are a model drawn on the track. Tool-change marks are used
    // solely by _operations() to fill the owning operation's circle.
    Repeater {
        model: root.stopMarks
        delegate: Rectangle {
            readonly property var mark: modelData
            x: root._x(mark.time) - width / 2
            y: track.y - 4
            width: 4
            height: track.height + 8
            radius: 1
            color: root.stopColor
        }
    }

    Text {
        id: startTime
        anchors.left: parent.left
        anchors.verticalCenter: track.verticalCenter
        text: "0:00"
        color: Theme.foregroundMuted
        font.pixelSize: Theme.fontSmall
    }

    Text {
        id: endTime
        anchors.right: parent.right
        anchors.verticalCenter: track.verticalCenter
        text: root.clock(root.duration)
        color: Theme.foregroundMuted
        font.pixelSize: Theme.fontSmall
    }

    // Operation numbers below the bar; yellow means that operation loads a tool.
    Repeater {
        model: root.operationMarks
        delegate: Item {
            readonly property var operation: modelData
            x: root._x(operation.time) - width / 2
            y: root.operationY
            width: 26
            height: 26

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                y: -root.operationY + track.y + track.height
                width: 2
                height: root.operationY - track.y - track.height
                color: root.operationColor
            }

            Rectangle {
                anchors.fill: parent
                radius: width / 2
                color: operation.toolChange ? root.toolChangeColor : "transparent"
                border.width: 2
                border.color: operation.toolChange ? "#b28704" : root.operationColor
            }

            Text {
                anchors.centerIn: parent
                text: String(operation.number)
                color: operation.toolChange ? "#3d3000" : root.operationColor
                font.pixelSize: Theme.fontSmall
                font.bold: true
            }
        }
    }

    // A rapid through the material, immediately below the track.
    Repeater {
        model: root.collisions
        delegate: Rectangle {
            x: root._x(modelData.time) - width / 2
            y: track.y + track.height + 3
            width: 4
            height: 10
            color: root.collisionColor
        }
    }

    // Progress is a vertical cursor with the current time in a box at its top.
    Item {
        id: cursor
        readonly property real at: root._x(root.time)
        x: at
        y: 0
        width: 1
        height: track.y + track.height + 5
        z: 5

        Rectangle {
            x: -1
            y: 43
            width: 3
            height: cursor.height - 43
            color: Theme.accentStrong
        }

        Rectangle {
            x: Math.max(-cursor.at + root.trackMargin,
                        Math.min(-width / 2, root.width - cursor.at - width - root.trackMargin))
            width: Math.max(52, currentTime.implicitWidth + 14)
            y: 20
            height: 26
            radius: Theme.radius
            color: Theme.surface
            border.color: Theme.accentStrong
            border.width: 2

            Text {
                id: currentTime
                anchors.centerIn: parent
                text: root.clock(root.time)
                color: Theme.foreground
                font.pixelSize: Theme.fontSmall
                font.bold: true
            }
        }
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
            if (!dragged)
                root.seekRequested(root._snapped(mouse.x))
        }
    }
}
