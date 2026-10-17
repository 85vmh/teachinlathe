// OperationHeader.qml — the row at the top of an operation's details: Speeds
// and Feeds in the width left, then Pause to Inspect, pauseWidth wide.
// Operations without an M1 (hasM1: false) leave that width empty, so every
// header lines up.
// The feed rate is passed in and reported out as a number: each operation
// keeps it in its own place (cutting_parameters, drilling_parameters, ...).
import QtQuick 2.15
import QtQuick.Layouts 1.15
import "."
import theme 1.0

RowLayout {
    id: root
    Layout.fillWidth: true
    spacing: Theme.innerSpacings

    property alias rpmOnly: speedsAndFeeds.rpmOnly
    property alias feedEnabled: speedsAndFeeds.feedEnabled
    // the only spindle direction the tool allows: true M3, false M4, null either
    property alias onlyClockwise: speedsAndFeeds.onlyClockwise
    // what Speeds and Feeds' feeds column holds: SpeedsAndFeeds.FeedKind -
    // Standard (Fz), Parting (Fz1 and Fz2), Threading (Pitch and Starts)
    property alias feedKind: speedsAndFeeds.feedKind
    // Parting's second feed rate, Threading's pitch and starts
    property alias feedRate2: speedsAndFeeds.feed_rate2
    property alias pitch: speedsAndFeeds.pitch
    property alias starts: speedsAndFeeds.starts
    property bool hasM1: true
    // Pause to Inspect's width - or the empty place it keeps without an M1
    readonly property real pauseWidth: 360
    // the width each Pause to Inspect button gets
    readonly property real pauseOptionWidth: m1Panel.optionWidth

    signal spindleEdited(var spindle)    // a whole spindle_parameters
    signal feedRateEdited(real value)
    signal feedRate2Edited(real value)
    signal pitchEdited(real value)
    signal startsEdited(int value)
    signal m1Edited(var m1)              // a whole m1_parameters
    signal openNumPadRequested(var field)

    function applyData(op, feedRate) {
        op = op || {}
        speedsAndFeeds.applyData(op.spindle_parameters, feedRate)
        if (hasM1)
            m1Panel.applyData(op.m1_parameters || {})
    }

    SpeedsAndFeeds {
        id: speedsAndFeeds
        // whatever width Pause to Inspect leaves, never less than it needs
        Layout.fillWidth: true
        Layout.minimumWidth: implicitWidth
        onSpindleEdited: function(spindle) { root.spindleEdited(spindle) }
        onFeedRateEdited: function(value) { root.feedRateEdited(value) }
        onFeedRate2Edited: function(value) { root.feedRate2Edited(value) }
        onPitchEdited: function(value) { root.pitchEdited(value) }
        onStartsEdited: function(value) { root.startsEdited(value) }
        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
    }

    M1Parameters {
        id: m1Panel
        visible: root.hasM1
        Layout.minimumWidth: root.pauseWidth
        Layout.preferredWidth: root.pauseWidth
        Layout.maximumWidth: root.pauseWidth
        Layout.preferredHeight: speedsAndFeeds.implicitHeight
        onSaveRequested: function(payload) { root.m1Edited(payload.m1_parameters) }
    }

    Item {
        visible: !root.hasM1
        Layout.preferredWidth: root.pauseWidth
    }
}
