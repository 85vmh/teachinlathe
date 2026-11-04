// LimitsPanel.qml — scalable Machine Limits + Tool Limits panel.
//
// Layout (ColumnLayout, 2 rows):
//   Row 1 — Machine Limits: Chuck Limit (left) | label (center) | Tailstock (right)
//            From the label a line runs out each way to above its card, then
//            turns down and ends in an arrow on the card's top. The cards
//            hang below the line, into the corners the cross leaves free.
//   Row 2 — Tool Limits cross: Limit X- (top) | Z-/label/Z+ (middle) | Limit X+ (bottom)
//            An arrow from the label to each limit's box. A tool limit is off
//            without the current loaded tool's offset on its axis.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input   // NumpadField
import theme

Rectangle {
    id: root

    color: Theme.surfaceSunken
    border.color: Theme.outline
    border.width: Theme.hairline
    radius: Theme.radius

    required property var viewModel
    signal openNumPadRequested(Item field)

    //: The arrow heads' length along the line, and their width.
    readonly property int arrowHeadLength: 12
    readonly property int arrowHeadWidth: 10

    // An arrow's head, its tip on the side it points to: "left", "right",
    // "up" or "down".
    component ArrowHead: Canvas {
        property string pointing: "left"
        readonly property bool vertical: pointing === "up" || pointing === "down"
        width: vertical ? root.arrowHeadWidth : root.arrowHeadLength
        height: vertical ? root.arrowHeadLength : root.arrowHeadWidth
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.fillStyle = Theme.surfaceInverse
            ctx.beginPath()
            if (pointing === "left") {
                ctx.moveTo(0, height / 2); ctx.lineTo(width, 0); ctx.lineTo(width, height)
            } else if (pointing === "right") {
                ctx.moveTo(width, height / 2); ctx.lineTo(0, 0); ctx.lineTo(0, height)
            } else if (pointing === "up") {
                ctx.moveTo(width / 2, 0); ctx.lineTo(0, height); ctx.lineTo(width, height)
            } else {
                ctx.moveTo(width / 2, height); ctx.lineTo(0, 0); ctx.lineTo(width, 0)
            }
            ctx.closePath()
            ctx.fill()
        }
    }

    // A line from the Machine Limits label out to above a card, then down
    // onto the card's top, ending in an arrow. `fromX` is where it leaves
    // the label, `toX` the card's middle, `lineY` its height, `toY` the
    // card's top - all in the parent's coordinates.
    component ElbowArrow: Item {
        id: elbow
        property real fromX: 0
        property real toX: 0
        property real lineY: 0
        property real toY: 0
        anchors.fill: parent
        z: -1

        Rectangle {
            x: Math.min(elbow.fromX, elbow.toX)
            y: elbow.lineY
            width: Math.abs(elbow.toX - elbow.fromX) + Theme.hairline
            height: Theme.hairline
            color: Theme.surfaceInverse
        }
        Rectangle {
            x: elbow.toX
            y: elbow.lineY
            width: Theme.hairline
            height: Math.max(0, elbow.toY - root.arrowHeadLength + 1 - elbow.lineY)
            color: Theme.surfaceInverse
        }
        ArrowHead {
            x: elbow.toX - width / 2 + Theme.hairline / 2
            y: elbow.toY - height
            pointing: "down"
        }
    }

    function formatLimitValue(v) {
        if (v === null || v === undefined || v === "" || v === "--none--") {
            return (v === null || v === undefined) ? "" : String(v)
        }
        var numberValue = Number(String(v).trim())
        return isNaN(numberValue) ? String(v) : numberValue.toFixed(3)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 1
        spacing: 0

        // ── Row 1: Machine Limits — Chuck (left) | label (center) | Tailstock (right)
        Item {
            id: machineRow
            Layout.fillWidth: true
            // Only as tall as the label: the cards hang down into the
            // cross's row, beside it, so the cross keeps the height.
            implicitHeight: machineLimitsLabel.height + 2 * 8
            Layout.preferredHeight: implicitHeight
            z: 1

            readonly property real lineY: height / 2
            // The cards' bottoms level with the middle of the Z limits'
            // boxes - which are centred in the cross's row, right under this.
            readonly property real cardTop: height + toolRow.height / 2 - tailstockLimit.height

            ElbowArrow {
                fromX: machineLimitsLabel.x
                toX: chuckBox.x + chuckBox.width / 2
                lineY: machineRow.lineY
                toY: machineRow.cardTop
            }
            ElbowArrow {
                fromX: machineLimitsLabel.x + machineLimitsLabel.width
                toX: tailstockLimit.x + tailstockLimit.width / 2
                lineY: machineRow.lineY
                toY: machineRow.cardTop
            }

            // "Machine Limits" label — centered
            Rectangle {
                id: machineLimitsLabel
                anchors.centerIn: parent
                width: machineLimitsText.implicitWidth + 24
                height: machineLimitsText.implicitHeight + 12
                radius: Theme.radius
                color: Theme.surfaceSunken
                border.color: Theme.outline
                border.width: Theme.hairline

                Text {
                    id: machineLimitsText
                    anchors.centerIn: parent
                    text: "Machine Limits"
                    font.pixelSize: 21
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            // Chuck Limit (left, under its arrow) — the tailstock card's
            // size: its name where that has its toggle, then the value.
            Rectangle {
                id: chuckBox
                anchors.left: parent.left
                anchors.leftMargin: 16
                y: machineRow.cardTop
                width: tailstockLimit.width
                height: tailstockLimit.height
                radius: Theme.radius
                color: Theme.surfaceSunken
                border.color: Theme.outline

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: tailstockLimit.contentMargin
                    spacing: 0

                    Text {
                        Layout.fillWidth: true
                        Layout.preferredHeight: tailstockLimit.buttonHeight
                        text: "Chuck Limit"
                        font.pixelSize: Theme.fontBody
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.topMargin: tailstockLimit.sectionSpacing
                        Layout.bottomMargin: tailstockLimit.sectionSpacing
                        height: Theme.hairline
                        color: Theme.outline
                    }

                    NumpadField {
                        Layout.fillWidth: true
                        value: root.viewModel.chuckValue
                        settingName: "smart_numpad.chuck-limit"
                        description: "Chuck limit"
                        hAlign: Text.AlignRight
                        formatter: root.formatLimitValue
                        parser: function(s) { return String(s) }
                        onOpenRequested: function(field) { root.openNumPadRequested(field) }
                        onValueCommitted: function(value) {
                            var formattedValue = root.formatLimitValue(value)
                            value = formattedValue
                            root.viewModel.commitLimit("chuck", formattedValue)
                        }
                    }
                }
            }

            // Tailstock Limit (right, under its arrow)
            TeachableLimit {
                id: tailstockLimit
                anchors.right: parent.right
                anchors.rightMargin: 16
                y: machineRow.cardTop
                title: "Tailstock Limit"
                value: root.viewModel.tailstockValue
                settingName: "smart_numpad.tailstock-limit"
                description: "Tailstock limit"
                status: root.viewModel.tailstockStatus
                toggleText: root.viewModel.tailstockToggleText
                toggleEnabled: root.viewModel.tailstockToggleEnabled
                onTeachClicked: root.viewModel.teachLimit("tailstock")
                onToggleClicked: root.viewModel.toggleLimit("tailstock")
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                onCommitted: function(value) { root.viewModel.commitLimit("tailstock", value) }
            }
        }

        // ── Row 2: Tool Limits cross ──────────────────────────────────
        Item {
            id: toolRow
            Layout.fillWidth: true
            Layout.fillHeight: true

            readonly property int edgeMargin: 10
            //: From "Tool Limits" to each Z limit's box: the arrow's length.
            readonly property int zArrowLength: 110
            //: The X limits' boxes' distance from the top and bottom of the
            //: cross's row.
            readonly property int xEdgeMargin: 14

            // Cross center — "Tool Limits" label with border (sized to text)
            Rectangle {
                id: crossCenter
                anchors.centerIn: parent
                width: toolLimitsText.implicitWidth + 24
                height: toolLimitsText.implicitHeight + 12
                radius: Theme.radius
                color: Theme.surfaceSunken
                border.color: Theme.outline
                border.width: Theme.hairline

                Text {
                    id: toolLimitsText
                    anchors.centerIn: parent
                    text: "Tool Limits"
                    font.pixelSize: 21
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            // Cross guide lines — 4 segments, each starting outside the crossCenter border.
            // Along Z, an arrow from "Tool Limits" to each limit's box, its
            // head stopping on the box.
            // Horizontal left, to Z-
            Rectangle {
                anchors.left: zMinusLimit.right
                anchors.leftMargin: root.arrowHeadLength - 1
                anchors.right: crossCenter.left
                anchors.verticalCenter: parent.verticalCenter
                height: Theme.hairline
                color: Theme.surfaceInverse
                z: -1
            }
            ArrowHead {
                anchors.left: zMinusLimit.right
                anchors.verticalCenter: parent.verticalCenter
                pointing: "left"
            }
            // Horizontal right, to Z+
            Rectangle {
                anchors.left: crossCenter.right
                anchors.right: zPlusLimit.left
                anchors.rightMargin: root.arrowHeadLength - 1
                anchors.verticalCenter: parent.verticalCenter
                height: Theme.hairline
                color: Theme.surfaceInverse
                z: -1
            }
            ArrowHead {
                anchors.right: zPlusLimit.left
                anchors.verticalCenter: parent.verticalCenter
                pointing: "right"
            }
            // Vertical top, to X-
            Rectangle {
                anchors.top: xMinusLimit.bottom
                anchors.topMargin: root.arrowHeadLength - 1
                anchors.bottom: crossCenter.top
                anchors.horizontalCenter: parent.horizontalCenter
                width: Theme.hairline
                color: Theme.surfaceInverse
                z: -1
            }
            ArrowHead {
                anchors.top: xMinusLimit.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                pointing: "up"
            }
            // Vertical bottom, to X+
            Rectangle {
                anchors.top: crossCenter.bottom
                anchors.bottom: xPlusLimit.top
                anchors.bottomMargin: root.arrowHeadLength - 1
                anchors.horizontalCenter: parent.horizontalCenter
                width: Theme.hairline
                color: Theme.surfaceInverse
                z: -1
            }
            ArrowHead {
                anchors.bottom: xPlusLimit.top
                anchors.horizontalCenter: parent.horizontalCenter
                pointing: "down"
            }

            // Limit X- (top edge, horizontally centered)
            TeachableLimit {
                id: xMinusLimit
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                anchors.topMargin: parent.xEdgeMargin
                title: "Limit X-"
                value: root.viewModel.xMinusValue
                settingName: "smart_numpad.x-minus-limit"
                description: "Tool limit on X-"
                status: root.viewModel.xMinusStatus
                available: root.viewModel.xToolSet
                toggleText: root.viewModel.xMinusToggleText
                toggleEnabled: root.viewModel.xMinusToggleEnabled
                onTeachClicked: root.viewModel.teachLimit("xMinus")
                onToggleClicked: root.viewModel.toggleLimit("xMinus")
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                onCommitted: function(value) { root.viewModel.commitLimit("xMinus", value) }
            }

            // Limit X+ (bottom edge, horizontally centered)
            TeachableLimit {
                id: xPlusLimit
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: parent.xEdgeMargin
                title: "Limit X+"
                value: root.viewModel.xPlusValue
                settingName: "smart_numpad.x-plus-limit"
                description: "Tool limit on X+"
                status: root.viewModel.xPlusStatus
                available: root.viewModel.xToolSet
                toggleText: root.viewModel.xPlusToggleText
                toggleEnabled: root.viewModel.xPlusToggleEnabled
                onTeachClicked: root.viewModel.teachLimit("xPlus")
                onToggleClicked: root.viewModel.toggleLimit("xPlus")
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                onCommitted: function(value) { root.viewModel.commitLimit("xPlus", value) }
            }

            // Limit Z- (zArrowLength left of "Tool Limits", vertically centered)
            TeachableLimit {
                id: zMinusLimit
                anchors.right: crossCenter.left
                anchors.rightMargin: parent.zArrowLength
                anchors.verticalCenter: parent.verticalCenter
                title: "Limit Z-"
                value: root.viewModel.zMinusValue
                settingName: "smart_numpad.z-minus-limit"
                description: "Tool limit on Z-"
                status: root.viewModel.zMinusStatus
                available: root.viewModel.zToolSet
                toggleText: root.viewModel.zMinusToggleText
                toggleEnabled: root.viewModel.zMinusToggleEnabled
                onTeachClicked: root.viewModel.teachLimit("zMinus")
                onToggleClicked: root.viewModel.toggleLimit("zMinus")
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                onCommitted: function(value) { root.viewModel.commitLimit("zMinus", value) }
            }

            // Limit Z+ (zArrowLength right of "Tool Limits", vertically centered)
            TeachableLimit {
                id: zPlusLimit
                anchors.left: crossCenter.right
                anchors.leftMargin: parent.zArrowLength
                anchors.verticalCenter: parent.verticalCenter
                title: "Limit Z+"
                value: root.viewModel.zPlusValue
                settingName: "smart_numpad.z-plus-limit"
                description: "Tool limit on Z+"
                status: root.viewModel.zPlusStatus
                available: root.viewModel.zToolSet
                toggleText: root.viewModel.zPlusToggleText
                toggleEnabled: root.viewModel.zPlusToggleEnabled
                onTeachClicked: root.viewModel.teachLimit("zPlus")
                onToggleClicked: root.viewModel.toggleLimit("zPlus")
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                onCommitted: function(value) { root.viewModel.commitLimit("zPlus", value) }
            }
        }
    }
}
