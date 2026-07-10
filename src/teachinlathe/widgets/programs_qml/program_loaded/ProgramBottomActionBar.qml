import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../../common"

Rectangle {
    id: root

    enum CycleStartState { CycleStart, Pause, Resume }

    property var viewModel

    readonly property var actions: viewModel ? viewModel.actions : null
    readonly property bool running: actions ? actions.isRunning : false
    // Full-screen (running) program view — Cycle Abort is shown the whole time here.
    readonly property bool fullScreen: viewModel ? viewModel.screenIndex === ProgramsScreen.Running : false

    property bool breakOnM1Active: actions ? actions.optionalStopAction.checked : false
    property bool breakOnM1Enabled: actions ? actions.optionalStopAction.enabled : false
    property var breakOnM1Clicked: function() {
        if (actions) {
            actions.setOptionalStopEnabled(!root.breakOnM1Active)
        }
    }

    property bool skipOptionalBlocksActive: actions ? actions.blockDeleteAction.checked : false
    property bool skipOptionalBlocksEnabled: actions ? actions.blockDeleteAction.enabled : false
    property var skipOptionalBlocksClicked: function() {
        if (actions) {
            actions.setBlockDeleteEnabled(!root.skipOptionalBlocksActive)
        }
    }

    property real maximumVelocity: actions ? actions.maximumRapidVelocity : 0
    property int currentPercentage: actions ? actions.rapidOverridePercent : 100
    property var rapidPercentageSelected: function(value) {
        if (actions) {
            actions.setRapidOverridePercent(value)
        }
    }

    property bool cycleAbortVisible: root.fullScreen
    property bool cycleAbortEnabled: actions ? actions.stopAction.enabled : false
    property var cycleAbortClicked: function() {
        if (actions) {
            actions.triggerStop()
        }
    }

    property int cycleStartState: defaultCycleStartState()
    property bool cycleStartEnabled: actions ? actions.cycleStartAction.enabled : false
    property bool cycleStartBlink: actions ? actions.cycleStartLedActive : false
    property var cycleStartClicked: function() {
        if (actions) {
            actions.triggerStart()
        }
    }
    property var pauseClicked: function() {
        if (actions) {
            actions.triggerPauseResume()
        }
    }
    property var resumeClicked: function() {
        if (actions) {
            actions.triggerPauseResume()
        }
    }

    readonly property string cycleStartButtonText:
        cycleStartState === ProgramBottomActionBar.Pause ? "Feed\nHold"
      : cycleStartState === ProgramBottomActionBar.Resume ? "Feed\nResume"
      : "Cycle\nStart"

    // Side cells size to their content (max of both), so the left buttons always
    // fit; the middle cell fills the rest, keeping the override centered.
    readonly property real sideWidth: Math.max(leftRow.implicitWidth, rightRow.implicitWidth)

    function defaultCycleStartState() {
        if (!actions) {
            return ProgramBottomActionBar.CycleStart
        }

        var actionText = actions.cycleStartAction.text
        if (actionText === "Pause" || actionText === "Feed\nHold") {
            return ProgramBottomActionBar.Pause
        }
        if (actionText === "Resume" || actionText === "Feed\nResume") {
            return ProgramBottomActionBar.Resume
        }
        return ProgramBottomActionBar.CycleStart
    }

    function triggerCycleStartButton() {
        if (cycleStartState === ProgramBottomActionBar.Pause) {
            pauseClicked()
        } else if (cycleStartState === ProgramBottomActionBar.Resume) {
            resumeClicked()
        } else {
            cycleStartClicked()
        }
    }

    color: "#f5f5f5"
    radius: 6
    border.color: "#ccc"
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
                    enabled: root.breakOnM1Enabled
                    checked: root.breakOnM1Active
                    onClicked: root.breakOnM1Clicked()
                }

                BottomActionButton {
                    text: "Skip \/\nBlocks"
                    enabled: root.skipOptionalBlocksEnabled
                    checked: root.skipOptionalBlocksActive
                    onClicked: root.skipOptionalBlocksClicked()
                }
            }
        }

        // ── Middle cell: Rapid Override (centered) ────────────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            RapidOverrideSelector {
                anchors.centerIn: parent
                label: "Rapid Override"
                maxSpeed: root.maximumVelocity
                value: root.currentPercentage
                updateValueOnClick: false
                onSelected: function(v) { root.rapidPercentageSelected(v) }
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
                MachineRoundButton {
                    visible: root.cycleAbortVisible
                    text: "Cycle\nAbort"
                    enabled: root.cycleAbortEnabled
                    active: false
                    normalFillCenterColor: "#6a0000"
                    normalFillMidColor:    "#c62828"
                    normalFillRimColor:    "#ef9a9a"
                    activeFillCenterColor: "#c62828"
                    activeFillRimColor:    "#ef9a9a"
                    onClicked: root.cycleAbortClicked()
                }

                // Cycle Start / Pause / Resume
                MachineRoundButton {
                    text: root.cycleStartButtonText
                    enabled: root.cycleStartEnabled
                    active: root.cycleStartBlink
                    normalFillCenterColor: "#0b3d12"
                    normalFillMidColor:    "#1b5e20"
                    normalFillRimColor:    "#2e7d32"
                    activeFillCenterColor: "#2e7d32"
                    activeFillRimColor:    "#a5d6a7"
                    onClicked: root.triggerCycleStartButton()
                }
            }
        }
    }
}
