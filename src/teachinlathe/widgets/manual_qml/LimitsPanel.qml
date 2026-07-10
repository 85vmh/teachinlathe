// LimitsPanel.qml — scalable Machine Limits + Tool Limits panel.
//
// Layout (ColumnLayout, 2 rows separated by a divider line):
//   Row 1 — Machine Limits: Chuck Limit (left) | label (center) | Tailstock (right)
//            Content is vertically centered in the row.
//   Row 2 — Tool Limits cross: Limit X- (top) | Z-/label/Z+ (middle) | Limit X+ (bottom)
//            Cross guide lines (horizontal + vertical) run through the center.
//
// Context property required: teachInDroViewModel
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../touchable_input"   // NumpadField

Rectangle {
    id: root

    color: "#e6e6e6"
    border.color: "#0a0a0a"
    border.width: 1
    radius: 8

    property var viewModel: teachInDroViewModel
    signal openNumPadRequested(var field)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 1
        spacing: 0

        // ── Row 1: Machine Limits — Chuck (left) | label (center) | Tailstock (right)
        Item {
            Layout.fillWidth: true
            implicitHeight: tailstockLimit.height + 16
            Layout.preferredHeight: implicitHeight

            // Guide line behind the Machine Limits label
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                height: 1
                color: "#202020"
                z: -1
            }

            // "Machine Limits" label — centered, with border
            Rectangle {
                id: machineLimitsLabel
                anchors.centerIn: parent
                width: machineLimitsText.implicitWidth + 24
                height: machineLimitsText.implicitHeight + 12
                radius: 6
                color: "#e6e6e6"
                border.color: "#323232"
                border.width: 1

                Text {
                    id: machineLimitsText
                    anchors.centerIn: parent
                    text: "Machine Limits"
                    font.pixelSize: 21
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            // Chuck Limit (left, vertically centered)
            Rectangle {
                id: chuckBox
                anchors.left: parent.left
                anchors.leftMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                width: 126
                height: 56
                radius: 8
                color: "#e6e6e6"
                border.color: "#323232"

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.top
                    anchors.bottomMargin: 4
                    text: "Chuck Limit"
                    font.pixelSize: 14
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                }

                NumpadField {
                    anchors.centerIn: parent
                    width: 106
                    value: root.viewModel ? root.viewModel.chuckValue : "--none--"
                    settingName: "smart_numpad.chuck-limit"
                    description: "Chuck limit"
                    hAlign: Text.AlignRight
                    formatter: function(v) { return (v === null || v === undefined) ? "" : String(v) }
                    parser: function(s) { return String(s) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: if (root.viewModel) root.viewModel.commitLimit("chuck", value)
                }
            }

            // Tailstock Limit (right, vertically centered)
            TeachableLimit {
                id: tailstockLimit
                anchors.right: parent.right
                anchors.rightMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                title: "Tailstock Limit"
                value: root.viewModel ? root.viewModel.tailstockValue : "--none--"
                settingName: "smart_numpad.tailstock-limit"
                description: "Tailstock limit"
                status: root.viewModel ? root.viewModel.tailstockStatus : 1
                toggleText: root.viewModel ? root.viewModel.tailstockToggleText : "Enable Limit"
                toggleEnabled: root.viewModel ? root.viewModel.tailstockToggleEnabled : false
                onTeachClicked: if (root.viewModel) root.viewModel.teachLimit("tailstock")
                onToggleClicked: if (root.viewModel) root.viewModel.toggleLimit("tailstock")
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onCommitted: if (root.viewModel) root.viewModel.commitLimit("tailstock", value)
            }
        }

        // ── Horizontal divider between rows ───────────────────────────
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: "#202020"
        }

        // ── Row 2: Tool Limits cross ──────────────────────────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            readonly property int edgeMargin: 10

            // Cross center — "Tool Limits" label with border (sized to text)
            Rectangle {
                id: crossCenter
                anchors.centerIn: parent
                width: toolLimitsText.implicitWidth + 24
                height: toolLimitsText.implicitHeight + 12
                radius: 6
                color: "#e6e6e6"
                border.color: "#323232"
                border.width: 1

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

            // Cross guide lines — 4 segments, each starting outside the crossCenter border
            // Horizontal left
            Rectangle {
                anchors.left: parent.left
                anchors.leftMargin: parent.edgeMargin
                anchors.right: crossCenter.left
                anchors.verticalCenter: parent.verticalCenter
                height: 1
                color: "#202020"
                z: -1
            }
            // Horizontal right
            Rectangle {
                anchors.left: crossCenter.right
                anchors.right: parent.right
                anchors.rightMargin: parent.edgeMargin
                anchors.verticalCenter: parent.verticalCenter
                height: 1
                color: "#202020"
                z: -1
            }
            // Vertical top
            Rectangle {
                anchors.top: parent.top
                anchors.topMargin: parent.edgeMargin
                anchors.bottom: crossCenter.top
                anchors.horizontalCenter: parent.horizontalCenter
                width: 1
                color: "#202020"
                z: -1
            }
            // Vertical bottom
            Rectangle {
                anchors.top: crossCenter.bottom
                anchors.bottom: parent.bottom
                anchors.bottomMargin: parent.edgeMargin
                anchors.horizontalCenter: parent.horizontalCenter
                width: 1
                color: "#202020"
                z: -1
            }

            // Limit X- (top edge, horizontally centered)
            TeachableLimit {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                anchors.topMargin: parent.edgeMargin
                title: "Limit X-"
                value: root.viewModel ? root.viewModel.xMinusValue : "--none--"
                settingName: "smart_numpad.x-minus-limit"
                description: "Tool limit on X-"
                status: root.viewModel ? root.viewModel.xMinusStatus : 1
                toggleText: root.viewModel ? root.viewModel.xMinusToggleText : "Enable Limit"
                toggleEnabled: root.viewModel ? root.viewModel.xMinusToggleEnabled : false
                onTeachClicked: if (root.viewModel) root.viewModel.teachLimit("xMinus")
                onToggleClicked: if (root.viewModel) root.viewModel.toggleLimit("xMinus")
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onCommitted: if (root.viewModel) root.viewModel.commitLimit("xMinus", value)
            }

            // Limit X+ (bottom edge, horizontally centered)
            TeachableLimit {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: parent.edgeMargin
                title: "Limit X+"
                value: root.viewModel ? root.viewModel.xPlusValue : "--none--"
                settingName: "smart_numpad.x-plus-limit"
                description: "Tool limit on X+"
                status: root.viewModel ? root.viewModel.xPlusStatus : 1
                toggleText: root.viewModel ? root.viewModel.xPlusToggleText : "Enable Limit"
                toggleEnabled: root.viewModel ? root.viewModel.xPlusToggleEnabled : false
                onTeachClicked: if (root.viewModel) root.viewModel.teachLimit("xPlus")
                onToggleClicked: if (root.viewModel) root.viewModel.toggleLimit("xPlus")
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onCommitted: if (root.viewModel) root.viewModel.commitLimit("xPlus", value)
            }

            // Limit Z- (left edge, vertically centered)
            TeachableLimit {
                anchors.left: parent.left
                anchors.leftMargin: parent.edgeMargin
                anchors.verticalCenter: parent.verticalCenter
                title: "Limit Z-"
                value: root.viewModel ? root.viewModel.zMinusValue : "--none--"
                settingName: "smart_numpad.z-minus-limit"
                description: "Tool limit on Z-"
                status: root.viewModel ? root.viewModel.zMinusStatus : 1
                toggleText: root.viewModel ? root.viewModel.zMinusToggleText : "Enable Limit"
                toggleEnabled: root.viewModel ? root.viewModel.zMinusToggleEnabled : false
                onTeachClicked: if (root.viewModel) root.viewModel.teachLimit("zMinus")
                onToggleClicked: if (root.viewModel) root.viewModel.toggleLimit("zMinus")
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onCommitted: if (root.viewModel) root.viewModel.commitLimit("zMinus", value)
            }

            // Limit Z+ (right edge, vertically centered)
            TeachableLimit {
                anchors.right: parent.right
                anchors.rightMargin: parent.edgeMargin
                anchors.verticalCenter: parent.verticalCenter
                title: "Limit Z+"
                value: root.viewModel ? root.viewModel.zPlusValue : "--none--"
                settingName: "smart_numpad.z-plus-limit"
                description: "Tool limit on Z+"
                status: root.viewModel ? root.viewModel.zPlusStatus : 1
                toggleText: root.viewModel ? root.viewModel.zPlusToggleText : "Enable Limit"
                toggleEnabled: root.viewModel ? root.viewModel.zPlusToggleEnabled : false
                onTeachClicked: if (root.viewModel) root.viewModel.teachLimit("zPlus")
                onToggleClicked: if (root.viewModel) root.viewModel.toggleLimit("zPlus")
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onCommitted: if (root.viewModel) root.viewModel.commitLimit("zPlus", value)
            }
        }
    }
}
