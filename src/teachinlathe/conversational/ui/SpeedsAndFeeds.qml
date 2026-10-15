// SpeedsAndFeeds.qml — spindle direction, speed mode, speed and feed rate in
// one row: M3/M4 | CSS/RPM | the speed for the mode | feed rate.
// Edits an operation's spindle_parameters, and a feed rate the operation
// keeps wherever it keeps it: each edit reports only what changed.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import touchable_input 1.0
import "../../tooling/ui"
import theme 1.0

GroupBox {
    id: root
    title: "Speeds and Feeds"
    font.pixelSize: Theme.fontBody

    // for operations that cannot run in CSS: its button disabled, RPM only
    property bool rpmOnly: false
    // false for operations without a feed rate: the field disabled and empty
    property bool feedEnabled: true

    signal spindleEdited(var spindle)    // a whole spindle_parameters
    signal feedRateEdited(real value)
    signal openNumPadRequested(var field)

    property string spindleMode: "rpm"   // "rpm" | "css"
    property int    rpm_value: 0
    property int    css_value: 0
    property int    css_max_rpm: 0
    property int    direction: -1        // +1 = Forward (M3), -1 = Reverse (M4)
    property real   feed_rate: 0.0

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
                                                               maxLabelMetrics.advanceWidth,
                                                               rpmLabelMetrics.advanceWidth))

    component Separator: Rectangle {
        implicitWidth: Theme.hairline
        color: Theme.outline
        Layout.fillHeight: true
        Layout.leftMargin: root.columnGap
        Layout.rightMargin: root.columnGap
    }

    component ValueFrame: Frame {
        Layout.alignment: Qt.AlignVCenter
        padding: 10
        background: Rectangle {
            radius: Theme.radius
            border.width: Theme.hairline
            border.color: Theme.outlineStrong
            color: "transparent"
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // M3 above M4
        SpindleDirectionPicker {
            vertical: true
            Layout.alignment: Qt.AlignVCenter
            clockwise: root.direction === 1
            onPicked: function(clockwise) {
                root.direction = clockwise ? 1 : -1
                root.emitSpindle()
            }
        }

        // as far from the buttons as the box's edge is on their other side
        Separator { Layout.leftMargin: root.leftPadding }

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
        TextMetrics { id: cssLabelMetrics; font.pixelSize: Theme.fontBody; text: "CSS value (Vc)" }
        TextMetrics { id: maxLabelMetrics; font.pixelSize: Theme.fontBody; text: "Max speed" }
        TextMetrics { id: rpmLabelMetrics; font.pixelSize: Theme.fontBody; text: "Spindle speed" }

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
                text: "CSS value (Vc)"
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
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.css_value = value; root.emitSpindle() }
            }
            Label {
                Layout.row: 0; Layout.column: 2
                opacity: root.spindleMode === "css" ? 1 : 0
                text: "(m/min)"
                font.pixelSize: Theme.fontBody
            }

            Label {
                Layout.row: 1; Layout.column: 0
                Layout.preferredWidth: root.speedLabelWidth
                text: root.spindleMode === "css" ? "Max speed" : "Spindle speed"
                font.pixelSize: Theme.fontBody
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
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.css_max_rpm = value; root.emitSpindle() }
            }
            NumpadField {
                Layout.row: 1; Layout.column: 1
                visible: root.spindleMode === "rpm"
                Layout.preferredWidth: 80
                settingName: "spindle.rpm"
                value: root.rpm_value
                validatorObject: IntValidator {}
                hAlign: Text.AlignRight
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.rpm_value = value; root.emitSpindle() }
            }
            Label {
                Layout.row: 1; Layout.column: 2
                text: "(rpm)"
                font.pixelSize: Theme.fontBody
            }
        }

        Separator {}

        ValueFrame {
            enabled: root.feedEnabled
            opacity: root.feedEnabled ? 1.0 : 0.5

            RowLayout {
                spacing: 20

                Label {
                    text: "Feed rate (Fz)"
                    font.pixelSize: Theme.fontBody
                }
                NumpadField {
                    Layout.preferredWidth: 80
                    settingName: "turning.feed_rate"
                    value: root.feed_rate
                    validatorObject: dblVal
                    // up to three decimals, without trailing zeros
                    formatter: function (v) { return (v == null || !root.feedEnabled) ? "" : String(Number(Number(v).toFixed(3))) }
                    hAlign: Text.AlignRight
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.feed_rate = value; root.feedRateEdited(value) }
                }
                Label {
                    text: "(mm/rev)"
                    font.pixelSize: Theme.fontBody
                }
            }
        }

        Item { Layout.fillWidth: true }
    }
}
