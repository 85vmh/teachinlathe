import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var viewModel
    readonly property var actions: viewModel ? viewModel.actions : null
    readonly property bool running: actions ? actions.isRunning : false
    // Full-screen (running) program view — Cycle Abort is shown the whole time here.
    readonly property bool fullScreen: viewModel ? viewModel.screenIndex === ProgramsScreen.Running : false
    // Side cells size to their content (max of both), so the left buttons always
    // fit; the middle cell fills the rest, keeping the override centered.
    readonly property real sideWidth: Math.max(leftRow.implicitWidth, rightRow.implicitWidth)
    color: "#f5f5f5"
    border.color: "#cccccc"
    border.width: 1

    RowLayout {
        anchors {
            fill: parent
            leftMargin: 16
            rightMargin: 16
        }
        spacing: 16

        // ── Left cell: Break on M1 / Skip "/" Blocks ──────────────────
        Item {
            Layout.preferredWidth: root.sideWidth
            Layout.fillHeight: true

            RowLayout {
                id: leftRow
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 16

                BottomActionButton {
                    text: "Break\non M1"
                    enabled: actions ? actions.optionalStopAction.enabled : false
                    checked: actions ? actions.optionalStopAction.checked : false
                    onClicked: if (actions) actions.setOptionalStopEnabled(!actions.optionalStopAction.checked)
                }

                BottomActionButton {
                    text: "Skip \/\nBlocks"
                    enabled: actions ? actions.blockDeleteAction.enabled : false
                    checked: actions ? actions.blockDeleteAction.checked : false
                    onClicked: if (actions) actions.setBlockDeleteEnabled(!actions.blockDeleteAction.checked)
                }
            }
        }

        // ── Middle cell: Rapid Override (centered) ────────────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            OverrideSelector {
                anchors.centerIn: parent
                label: "Rapid Override"
                maxSpeed: 6000
                value: 100
                onSelected: function(v) { /* TODO: wire to HAL feed override pin */ }
            }
        }

        // ── Right cell: Cycle Start (+ Cycle Abort while running) ─────
        Item {
            Layout.preferredWidth: root.sideWidth
            Layout.fillHeight: true

            RowLayout {
                id: rightRow
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 16

                // Cycle Abort — always visible in the full-screen running view
                MachineButton {
                    visible: root.fullScreen
                    text: "Cycle\nAbort"
                    enabled: actions ? actions.stopAction.enabled : false
                    active: false
                    normalFillCenterColor: "#6a0000"
                    normalFillMidColor:    "#c62828"
                    normalFillRimColor:    "#ef9a9a"
                    activeFillCenterColor: "#c62828"
                    activeFillRimColor:    "#ef9a9a"
                    onClicked: if (actions) actions.triggerStop()
                }

                // Cycle Start / Pause / Resume
                MachineButton {
                    text:    actions ? actions.cycleStartAction.text    : "Cycle\nStart"
                    enabled: actions ? actions.cycleStartAction.enabled : false
                    active:  actions ? actions.cycleStartAction.active  : false
                    normalFillCenterColor: "#1a5e20"
                    normalFillMidColor:    "#2e7d32"
                    normalFillRimColor:    "#a5d6a7"
                    activeFillCenterColor: "#2e7d32"
                    activeFillRimColor:    "#81c784"
                    onClicked: if (actions) actions.triggerCycleStart()
                }
            }
        }
    }
}
