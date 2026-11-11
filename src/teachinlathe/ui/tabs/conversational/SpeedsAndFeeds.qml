// SpeedsAndFeeds.qml — speed mode, speed and feeds in one row: CSS/RPM |
// the speed for the mode | the feeds. The spindle direction is the tool's
// (onlyClockwise): shown as the M3 / M4 icon before the speed, not picked.
// Shows an operation's speeds_and_feeds (``speeds``) and keeps nothing of its
// own: each edit reports the whole of it, with the change, its feeds as the
// feeds column holds them, and is shown once ``speeds`` has it.
//
// What the feeds column holds is ``feedKind``'s:
//   Standard   Feed rate (Fz)
//   Parting    Feed rate (Fz1) over Feed rate (Fz2)
//   Threading  Pitch over Starts
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import tabs.tool_library
import theme
import common
import "speeds.js" as Speeds

TitledCard {
    id: root
    title: "Speeds and Feeds"
    font.pixelSize: Theme.fontBody

    enum FeedKind { Standard, Parting, Threading }
    // what the feeds column holds; see above
    property int feedKind: SpeedsAndFeeds.FeedKind.Standard

    // for operations that cannot run in CSS: its button disabled, RPM only
    property bool rpmOnly: false
    // false for operations without a feed rate: the field disabled and empty
    property bool feedEnabled: true
    // the only spindle direction the tool allows - a drill's or a tap's:
    // true M3, false M4, null either: the one shown, and the one an edit
    // reports (the editor turns an operation set the other way round to it)
    property var onlyClockwise: null

    signal speedsAndFeedsEdited(var speedsAndFeeds)   // a whole speeds_and_feeds
    signal pitchEdited(real value)         // Threading's
    signal startsEdited(int value)         // Threading's
    signal openNumPadRequested(var field)

    // the operation's speeds_and_feeds, as its editor has it
    property var    speeds: ({})
    // Threading's pitch and starts, as its editor has them
    property real   pitch: 0.0
    property int    starts: 1

    readonly property var _read: Speeds.read(speeds, rpmOnly, onlyClockwise)
    readonly property string spindleMode: _read.mode
    readonly property int    rpm_value: _read.rpm_value
    readonly property int    css_value: _read.css_value
    readonly property int    css_max_rpm: _read.css_max_speed
    // "M3" forward, "M4" reverse: the tool's, when it allows only one
    readonly property string direction: _read.direction
    // Standard's Fz, Parting's Fz1; Parting's Fz2
    readonly property real   feed_rate: _read.feed_rate
    readonly property real   feed_rate_2: _read.feed_rate_2

    // the whole speeds_and_feeds with ``changes`` made - the feeds the feeds
    // column holds, none for Threading, which goes by the pitch - reported
    function _edit(changes) {
        root.speedsAndFeedsEdited(Speeds.edited(_read, changes,
            feedEnabled && feedKind !== SpeedsAndFeeds.FeedKind.Threading,
            feedEnabled && feedKind === SpeedsAndFeeds.FeedKind.Parting))
    }

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    // between the columns of the row, either side of each separator
    readonly property int columnGap: 12

    // one row of the speed area, and the width its label column keeps in either mode
    readonly property real speedRowHeight: maxSpeedField.implicitHeight
    readonly property real speedLabelWidth: Math.ceil(Math.max(cssLabelMetrics.advanceWidth,
                                                               directionIconSize + 6 + maxLabelMetrics.advanceWidth,
                                                               directionIconSize + 6 + rpmLabelMetrics.advanceWidth))
    // the M3 / M4 icon before the speed
    readonly property real directionIconSize: 36

    component Separator: Rectangle {
        implicitWidth: Theme.hairline
        color: Theme.outline
        Layout.fillHeight: true
        Layout.leftMargin: root.columnGap
        Layout.rightMargin: root.columnGap
    }


    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Each button level with the middle of a speed row: CSS with the
        // CSS value, RPM with the bottom row
        ColumnLayout {
            Layout.alignment: Qt.AlignVCenter
            spacing: speedRowHeight + speedGrid.rowSpacing - cssRadio.implicitHeight

            // no side padding: the separators' gaps alone set them apart,
            // as they do the M3/M4 buttons
            ModelRadioButton {
                id: cssRadio
                leftPadding: 0
                rightPadding: 0
                text: "<b>(G96)</b> CSS"
                enabled: !root.rpmOnly
                font.pixelSize: Theme.fontBody
                checked: root.spindleMode === "css"
                onChosen: root._edit({mode: "css"})
            }
            ModelRadioButton {
                leftPadding: 0
                rightPadding: 0
                text: "<b>(G97)</b> RPM"
                font.pixelSize: Theme.fontBody
                checked: root.spindleMode === "rpm"
                onChosen: root._edit({mode: "rpm"})
            }
        }

        Separator {}

        // The speed for the mode. Both rows always take their place, so the
        // area is as wide and as tall in either mode: the CSS value is only
        // hidden in RPM mode, and the bottom row holds Max speed or Spindle speed.
        TextMetrics { id: cssLabelMetrics; font.pixelSize: Theme.fontBody; text: "CSS (Vc)" }
        TextMetrics { id: maxLabelMetrics; font.pixelSize: Theme.fontBody; text: "max" }
        TextMetrics { id: rpmLabelMetrics; font.pixelSize: Theme.fontBody; text: "at" }

        GridLayout {
            id: speedGrid
            Layout.alignment: Qt.AlignVCenter
            columns: 3
            columnSpacing: 20
            rowSpacing: 20

            Label {
                Layout.row: 0; Layout.column: 0
                Layout.preferredWidth: root.speedLabelWidth
                opacity: root.spindleMode === "css" ? 1 : 0
                text: "CSS (Vc)"
                font.pixelSize: Theme.fontBody
            }
            NumpadField {
                Layout.row: 0; Layout.column: 1
                Layout.preferredWidth: 80
                opacity: root.spindleMode === "css" ? 1 : 0
                enabled: root.spindleMode === "css"
                settingName: "spindle.css"
                value: root.css_value
                validatorObject: IntValidator {}
                hAlign: Text.AlignRight
                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                onValueCommitted: function(value) { root._edit({css_value: Math.round(value)}) }
            }
            Label {
                Layout.row: 0; Layout.column: 2
                opacity: root.spindleMode === "css" ? 1 : 0
                text: "(m/min)"
                font.pixelSize: Theme.fontBody
            }

            // the way the spindle turns, M3 or M4, then "at" the speed - or
            // CSS's "max"
            Row {
                Layout.row: 1; Layout.column: 0
                Layout.preferredWidth: root.speedLabelWidth
                Layout.alignment: Qt.AlignVCenter
                spacing: 6
                Image {
                    anchors.verticalCenter: parent.verticalCenter
                    width: root.directionIconSize
                    height: width
                    source: Qt.resolvedUrl(Images.url(root.direction === "M3" ? "spindle_m3.svg" : "spindle_m4.svg"))
                    sourceSize.width: width
                    sourceSize.height: height
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                }
                Label {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.spindleMode === "css" ? "max" : "at"
                    font.pixelSize: Theme.fontBody
                }
            }
            NumpadField {
                id: maxSpeedField
                Layout.row: 1; Layout.column: 1
                visible: root.spindleMode === "css"
                Layout.preferredWidth: 80
                settingName: "spindle.max_rpm"
                value: root.css_max_rpm
                validatorObject: IntValidator {}
                hAlign: Text.AlignRight
                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                onValueCommitted: function(value) { root._edit({css_max_speed: Math.round(value)}) }
            }
            NumpadField {
                Layout.row: 1; Layout.column: 1
                visible: root.spindleMode === "rpm"
                Layout.preferredWidth: 80
                settingName: "spindle.rpm"
                value: root.rpm_value
                validatorObject: IntValidator {}
                hAlign: Text.AlignRight
                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                onValueCommitted: function(value) { root._edit({rpm_value: Math.round(value)}) }
            }
            Label {
                Layout.row: 1; Layout.column: 2
                text: "(rpm)"
                font.pixelSize: Theme.fontBody
            }
        }

        Separator {}

        // the feeds, unframed, each row level with a speed row: the first
        // with the CSS value's, the second with the bottom one
        GridLayout {
            Layout.alignment: Qt.AlignTop
            Layout.topMargin: speedGrid.y
            enabled: root.feedEnabled
            opacity: root.feedEnabled ? 1.0 : 0.5
            columns: 3
            columnSpacing: Theme.spacing
            rowSpacing: speedGrid.rowSpacing

            readonly property bool parting: root.feedKind === SpeedsAndFeeds.FeedKind.Parting
            readonly property bool threading: root.feedKind === SpeedsAndFeeds.FeedKind.Threading

            // first row: Fz, Fz1, or Pitch
            Label {
                Layout.preferredHeight: root.speedRowHeight
                verticalAlignment: Text.AlignVCenter
                text: parent.threading ? "Pitch" : parent.parting ? "Feed rate (Fz1)" : "Feed rate (Fz)"
                font.pixelSize: Theme.fontBody
            }
            NumpadField {
                visible: !parent.threading
                Layout.preferredWidth: 80
                settingName: "turning.feed_rate"
                value: root.feed_rate
                validatorObject: dblVal
                // up to three decimals, without trailing zeros
                formatter: function (v) { return (v == null || !root.feedEnabled) ? "" : String(Number(Number(v).toFixed(3))) }
                hAlign: Text.AlignRight
                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                onValueCommitted: function(value) { root._edit({feed_rate: Number(value)}) }
            }
            NumpadField {
                visible: parent.threading
                Layout.preferredWidth: 80
                settingName: "threading.metric_pitch"
                value: root.pitch
                validatorObject: dblVal
                formatter: function (v) { return (v == null) ? "" : String(Number(Number(v).toFixed(3))) }
                hAlign: Text.AlignRight
                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                onValueCommitted: function(value) { root.pitchEdited(Number(value)) }
            }
            Label {
                text: parent.threading ? "(mm)" : "(mm/rev)"
                font.pixelSize: Theme.fontBody
            }

            // second row: Fz2, or Starts; none for Standard
            Label {
                visible: parent.parting || parent.threading
                Layout.preferredHeight: root.speedRowHeight
                verticalAlignment: Text.AlignVCenter
                text: parent.threading ? "Starts" : "Feed rate (Fz2)"
                font.pixelSize: Theme.fontBody
            }
            NumpadField {
                visible: parent.parting
                Layout.preferredWidth: 80
                settingName: "turning.feed_rate"
                value: root.feed_rate_2
                validatorObject: dblVal
                formatter: function (v) { return (v == null || !root.feedEnabled) ? "" : String(Number(Number(v).toFixed(3))) }
                hAlign: Text.AlignRight
                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                onValueCommitted: function(value) { root._edit({feed_rate_2: Number(value)}) }
            }
            NumpadField {
                visible: parent.threading
                Layout.preferredWidth: 80
                settingName: "threading.starts_count"
                value: root.starts
                validatorObject: IntValidator { bottom: 1 }
                formatter: function (v) { return (v == null) ? "" : String(Math.round(Number(v))) }
                hAlign: Text.AlignRight
                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                onValueCommitted: function(value) { root.startsEdited(Math.max(1, Math.round(value))) }
            }
            Label {
                visible: parent.parting || parent.threading
                text: parent.parting ? "(mm/rev)" : ""
                font.pixelSize: Theme.fontBody
            }
        }

        Item { Layout.fillWidth: true }
    }
}
