// SpeedsAndFeeds.qml — speed mode, speed and feeds in one row: CSS/RPM |
// the speed for the mode | the feeds. The spindle direction is the tool's
// (onlyClockwise): shown as the M3 / M4 icon before the speed, not picked.
// Edits an operation's spindle_parameters, and feeds the operation keeps
// wherever it keeps them: each edit reports only what changed.
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

GroupBox {
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
    // true M3, false M4, null either. The other button is disabled, and an
    // op set the other way is turned round to it when its data comes in
    // (applyData), and saved; set it before then
    property var onlyClockwise: null

    signal spindleEdited(var spindle)    // a whole spindle_parameters
    signal feedRateEdited(real value)      // Standard's Fz, Parting's Fz1
    signal feedRate2Edited(real value)     // Parting's Fz2
    signal pitchEdited(real value)         // Threading's
    signal startsEdited(int value)         // Threading's
    signal openNumPadRequested(var field)

    property string spindleMode: "rpm"   // "rpm" | "css"
    property int    rpm_value: 0
    property int    css_value: 0
    property int    css_max_rpm: 0
    property int    direction: -1        // +1 = Forward (M3), -1 = Reverse (M4)
    property real   feed_rate: 0.0
    // Parting's second feed rate, and Threading's pitch and starts: set them
    // as feed_rate is, from the operation's data
    property real   feed_rate2: 0.0
    property real   pitch: 0.0
    property int    starts: 1

    function applyData(spindleParams, feedRate) {
        var sp = spindleParams || {}
        direction = (sp.direction !== undefined) ? sp.direction : -1
        var hasRPM = (sp.rpm_value !== undefined && sp.rpm_value !== null)
        var hasCSS = (sp.css_value !== undefined && sp.css_max_speed !== undefined)
        spindleMode = rpmOnly ? "rpm"
                    : (sp.mode === "css" || sp.mode === "rpm") ? sp.mode : (hasRPM ? "rpm" : "css")
        rpm_value = hasRPM ? +sp.rpm_value : 0
        css_value = hasCSS ? +sp.css_value : 0
        css_max_rpm = hasCSS ? +sp.css_max_speed : 0
        feed_rate = (feedRate !== undefined && feedRate !== null) ? +feedRate : 0
        _keepToAllowedDirection()
    }

    function _keepToAllowedDirection() {
        if (onlyClockwise !== true && onlyClockwise !== false) return
        if ((direction === 1) === onlyClockwise) return
        direction = onlyClockwise ? 1 : -1
        emitSpindle()
    }

    function emitSpindle() {
        var spindle = {direction: direction, mode: spindleMode}
        if (spindleMode === "rpm") {
            spindle.rpm_value = rpm_value
        } else {
            spindle.css_value = css_value
            spindle.css_max_speed = css_max_rpm
        }
        root.spindleEdited(spindle)
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

            ButtonGroup { id: modeGroup }
            // no side padding: the separators' gaps alone set them apart,
            // as they do the M3/M4 buttons
            RadioButton {
                id: cssRadio
                leftPadding: 0
                rightPadding: 0
                text: "<b>(G96)</b> CSS"
                enabled: !root.rpmOnly
                font.pixelSize: Theme.fontBody
                checked: root.spindleMode === "css"
                ButtonGroup.group: modeGroup
                onToggled: if (checked) { root.spindleMode = "css"; root.emitSpindle() }
            }
            RadioButton {
                leftPadding: 0
                rightPadding: 0
                text: "<b>(G97)</b> RPM"
                font.pixelSize: Theme.fontBody
                checked: root.spindleMode === "rpm"
                ButtonGroup.group: modeGroup
                onToggled: if (checked) { root.spindleMode = "rpm"; root.emitSpindle() }
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
                onValueCommitted: function(value) { root.css_value = value; root.emitSpindle() }
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
                    source: Qt.resolvedUrl(Images.url(root.direction === 1 ? "spindle_m3.svg" : "spindle_m4.svg"))
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
                onValueCommitted: function(value) { root.css_max_rpm = value; root.emitSpindle() }
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
                onValueCommitted: function(value) { root.rpm_value = value; root.emitSpindle() }
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
            columnSpacing: 20
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
                onValueCommitted: function(value) { root.feed_rate = value; root.feedRateEdited(value) }
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
                onValueCommitted: function(value) { root.pitch = value; root.pitchEdited(value) }
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
                value: root.feed_rate2
                validatorObject: dblVal
                formatter: function (v) { return (v == null || !root.feedEnabled) ? "" : String(Number(Number(v).toFixed(3))) }
                hAlign: Text.AlignRight
                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                onValueCommitted: function(value) { root.feed_rate2 = value; root.feedRate2Edited(value) }
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
                onValueCommitted: function(value) { root.starts = Math.max(1, Math.round(value)); root.startsEdited(root.starts) }
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
