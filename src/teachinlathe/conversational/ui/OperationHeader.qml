// OperationHeader.qml — the row at the top of an operation's details: Speeds
// and Feeds, then Pause to Inspect in the width left. Operations without an
// M1 (hasM1: false) leave that width empty, so every header lines up.
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
    property bool hasM1: true
    // the width each Pause to Inspect button gets
    readonly property real pauseOptionWidth: m1Panel.optionWidth

    signal spindleEdited(var spindle)    // a whole spindle_parameters
    signal feedRateEdited(real value)
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
        Layout.minimumWidth: implicitWidth
        onSpindleEdited: function(spindle) { root.spindleEdited(spindle) }
        onFeedRateEdited: function(value) { root.feedRateEdited(value) }
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
