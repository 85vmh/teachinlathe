// OperationHeader.qml — the row at the top of an operation's details: Speeds
// and Feeds as wide as it needs, then Pause to Inspect in the width left.
// Operations without an M1 (hasM1: false) leave that width empty.
// Speeds and Feeds edits the operation's speeds_and_feeds - its feeds too -
// reported out whole.
import QtQuick
import QtQuick.Layouts
import theme

RowLayout {
    id: root
    Layout.fillWidth: true
    spacing: Theme.innerSpacings

    property alias rpmOnly: speedsAndFeeds.rpmOnly
    property alias feedEnabled: speedsAndFeeds.feedEnabled
    // the only spindle direction the tool allows: true M3, false M4, null
    // either. Unless set, the tool's the op's details carry
    // (_tool_spindle_direction, 3 or 4, from the last Change Tool above)
    property var onlyClockwise: null
    property var _toolClockwise: null
    // what Speeds and Feeds' feeds column holds: SpeedsAndFeeds.FeedKind -
    // Standard (Fz), Parting (Fz1 and Fz2), Threading (Pitch and Starts)
    property alias feedKind: speedsAndFeeds.feedKind
    // Threading's pitch and starts
    property alias pitch: speedsAndFeeds.pitch
    property alias starts: speedsAndFeeds.starts
    property bool hasM1: true
    // Pause to Inspect's third choice, stay where the tool is
    property alias allowStayInPlace: m1Panel.allowStayInPlace
    // the width each Pause to Inspect button gets
    readonly property real pauseOptionWidth: m1Panel.optionWidth

    signal speedsAndFeedsEdited(var speedsAndFeeds)   // a whole speeds_and_feeds
    signal pitchEdited(real value)
    signal startsEdited(int value)
    signal m1Edited(var m1)              // a whole m1_parameters
    signal openNumPadRequested(var field)

    function applyData(op) {
        op = op || {}
        var d = op._tool_spindle_direction
        _toolClockwise = d === 3 ? true : d === 4 ? false : null
        speedsAndFeeds.applyData(op.speeds_and_feeds)
        if (hasM1)
            m1Panel.applyData(op.m1_parameters || {})
    }

    SpeedsAndFeeds {
        id: speedsAndFeeds
        onlyClockwise: (root.onlyClockwise === true || root.onlyClockwise === false)
                       ? root.onlyClockwise : root._toolClockwise
        // as wide as its contents need
        Layout.minimumWidth: implicitWidth
        onSpeedsAndFeedsEdited: function(speeds) { root.speedsAndFeedsEdited(speeds) }
        onPitchEdited: function(value) { root.pitchEdited(value) }
        onStartsEdited: function(value) { root.startsEdited(value) }
        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
    }

    M1Parameters {
        id: m1Panel
        visible: root.hasM1
        // whatever width Speeds and Feeds leaves
        Layout.fillWidth: true
        Layout.minimumWidth: 0
        Layout.preferredWidth: 0
        Layout.preferredHeight: speedsAndFeeds.implicitHeight
        onSaveRequested: function(payload) { root.m1Edited(payload.m1_parameters) }
    }

    Item {
        visible: !root.hasM1
        Layout.fillWidth: true
    }
}
