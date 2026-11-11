// OperationHeader.qml — the row at the top of an operation's details: Speeds
// and Feeds as wide as it needs, then Pause to Inspect in the width left.
// Operations without an M1 (hasM1: false) leave that width empty.
// It shows its editor's operation and keeps nothing of its own: an edit -
// the whole speeds_and_feeds (its feeds too), m1_parameters, a thread's pitch
// or starts - goes to the editor, and is shown once the operation has it.
import QtQuick
import QtQuick.Layouts
import theme

RowLayout {
    id: root
    Layout.fillWidth: true
    spacing: Theme.innerSpacings

    // Plain properties handed down, not aliases: an alias into a child is
    // compiled as the index of the property it points at, and stays at that
    // index from a cached compile after the child's type changes - adding a
    // property to TitledCard once shifted every one of these by one.
    property bool rpmOnly: false
    property bool feedEnabled: true
    // the only spindle direction the tool allows: true M3, false M4, null
    // either. Unless set, the tool's the op's details carry
    // (_tool_spindle_direction, 3 or 4, from the tool it cuts with)
    property var onlyClockwise: null
    // the operation's editor (OperationEditorViewModel.py): all the header
    // shows, and where its edits go
    required property var editor
    readonly property var _op: editor.operation || {}
    // the way the operation's tool turns: 3 (M3), 4 (M4), 0 with none
    readonly property var _toolClockwise: _op._tool_spindle_direction === 3 ? true
                                        : _op._tool_spindle_direction === 4 ? false : null
    // what Speeds and Feeds' feeds column holds: SpeedsAndFeeds.FeedKind -
    // Standard (Fz), Parting (Fz1 and Fz2), Threading (Pitch and Starts)
    property int feedKind: SpeedsAndFeeds.FeedKind.Standard
    property bool hasM1: true
    // Pause to Inspect's third choice, stay where the tool is
    property bool allowStayInPlace: false
    // the width each Pause to Inspect button gets
    readonly property real pauseOptionWidth: m1Panel.optionWidth

    signal openNumPadRequested(var field)

    SpeedsAndFeeds {
        id: speedsAndFeeds
        rpmOnly: root.rpmOnly
        feedEnabled: root.feedEnabled
        feedKind: root.feedKind
        onlyClockwise: (root.onlyClockwise === true || root.onlyClockwise === false)
                       ? root.onlyClockwise : root._toolClockwise
        // as wide as its contents need
        Layout.minimumWidth: implicitWidth
        speeds: root._op.speeds_and_feeds || ({})
        // Threading's: the calculated diameter follows the pitch (editPitch)
        pitch: Number(root._op.pitch || 0)
        starts: root._op.starts !== undefined ? Math.max(1, Math.round(Number(root._op.starts))) : 1
        onSpeedsAndFeedsEdited: function(speeds) { root.editor.edit({ speeds_and_feeds: speeds }) }
        onPitchEdited: function(value) { root.editor.editPitch(value) }
        onStartsEdited: function(value) { root.editor.edit({ starts: value }) }
        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
    }

    M1Parameters {
        id: m1Panel
        visible: root.hasM1
        allowStayInPlace: root.allowStayInPlace
        // whatever width Speeds and Feeds leaves
        Layout.fillWidth: true
        Layout.minimumWidth: 0
        Layout.preferredWidth: 0
        Layout.preferredHeight: speedsAndFeeds.implicitHeight
        m1: root._op.m1_parameters || ({})
        onM1Edited: function(m1) { root.editor.edit({ m1_parameters: m1 }) }
    }

    Item {
        visible: !root.hasM1
        Layout.fillWidth: true
    }
}
