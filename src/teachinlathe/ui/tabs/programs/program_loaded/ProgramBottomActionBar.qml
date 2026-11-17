import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.programs
import tabs.programs.simulate
import theme

// The common full-screen run bar. Abort and the context-sensitive Cycle Start
// / Feed Hold / Feed Resume are on the left. A simulation adds its seek bar
// on the right; the machine leaves that space empty.
Rectangle {
    id: root

    required property var viewModel
    required property var run
    property var simulationViewModel: null
    property bool simulation: false
    property real backplotLeftMargin: 0
    // How far the run controls are in, 0..1: they fade in as the bar widens.
    property real runControlsReveal: 0

    readonly property var actions: viewModel.actions
    // the current loaded tool corrected at an M1: the machine's run only
    readonly property var correction: viewModel.toolCorrection
    readonly property bool running: run.state === "running"
    readonly property bool held: run.state === "held"

    color: Theme.surfaceSunken
    radius: Theme.radius
    border.color: Theme.outline
    border.width: Theme.hairline

    RowLayout {
        anchors {
            left: parent.left
            leftMargin: 16
            verticalCenter: parent.verticalCenter
        }
        spacing: 2 * Theme.spacingLarge

        RunActionButton {
            text: "Cycle Abort"
            fill: Theme.danger
            pressedFill: Theme.dangerPressed
            edge: "#ef5350"
            enabled: root.simulation
                     ? root.run.state !== "idle"
                     : !!root.actions && root.actions.stopAction.enabled
            onClicked: {
                if (root.simulation)
                    root.viewModel.abortSimulationRun()
                else
                    root.viewModel.triggerCycleAbort()
            }
        }

        RunActionButton {
            text: root.held ? "Feed Resume" : (root.running ? "Feed Hold" : "Cycle Start")
            enabled: root.simulation
                     ? !!root.simulationViewModel && root.simulationViewModel.ready
                     : !!root.actions && (root.actions.pauseResumeAction.enabled
                                           || root.actions.startAction.enabled)
            active: root.held || (!!root.actions && root.actions.cycleStartLedActive)
            onClicked: {
                if (root.running || root.held)
                    root.run.feedHold()
                else
                    root.run.cycleStart()
            }
        }
    }

    // The middle of the bar, on the machine's run: "Correct T<n>" at an M1,
    // the correction armed, or the one just applied.
    Item {
        anchors.centerIn: parent
        width: Math.max(correctButton.width, armedBox.width, appliedText.width)
        height: parent.height
        visible: !root.simulation

        RunActionButton {
            id: correctButton
            anchors.centerIn: parent
            text: root.correction.buttonText
            visible: opacity > 0
            opacity: root.correction.available ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: 200 } }
            fill: Theme.warning
            pressedFill: Qt.darker(Theme.warning, 1.2)
            edge: Qt.darker(Theme.warning, 1.1)
            onClicked: {
                root.correction.clearEntries()
                correctionPanel.open()
            }
        }

        // armed: Cycle Start applies it; Edit it, or Undo - Cycle Start goes
        // on without
        Rectangle {
            id: armedBox
            anchors.centerIn: parent
            width: armedRow.implicitWidth + 2 * Theme.spacingLarge
            height: armedRow.implicitHeight + 2 * Theme.spacingLarge
            radius: Theme.radius
            color: "#fff3e0"
            border.color: Theme.warning
            border.width: Theme.hairline
            visible: opacity > 0
            opacity: root.correction.armed ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: 200 } }

            RowLayout {
                id: armedRow
                anchors.centerIn: parent
                spacing: Theme.spacingLarge

                Column {
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 4
                    Text {
                        text: root.correction.armedTitle
                        color: Theme.foreground
                        font.pixelSize: Theme.fontBody
                        font.bold: true
                    }
                    Repeater {
                        model: root.correction.armedEffects
                        Text {
                            required property string modelData
                            text: modelData
                            textFormat: Text.StyledText
                            color: Theme.foreground
                            font.pixelSize: Theme.fontBody
                        }
                    }
                }
                RunActionButton {
                    text: "Edit"
                    implicitWidth: 100
                    onClicked: {
                        root.correction.editArmed()
                        correctionPanel.open()
                    }
                }
                RunActionButton {
                    text: "Undo"
                    implicitWidth: 100
                    fill: Theme.foregroundMuted
                    pressedFill: Theme.foreground
                    edge: Theme.outline
                    onClicked: root.correction.disarm()
                }
            }
        }

        // applied: the tool's offsets before and after, for a moment
        Column {
            id: appliedText
            anchors.centerIn: parent
            // view state: the applied correction's passing message
            property bool shown: false
            visible: opacity > 0
            opacity: shown ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: 300 } }
            spacing: 4

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.correction.appliedTitle
                color: Theme.foreground
                font.pixelSize: Theme.fontBody
                font.bold: true
            }
            Repeater {
                model: root.correction.appliedRows
                delegate: Row {
                    required property var modelData
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: Theme.spacingLarge

                    Text {
                        width: 110
                        text: modelData.before
                        color: Theme.foreground
                        font.pixelSize: Theme.fontBody
                    }
                    Text {
                        text: "→"
                        color: Theme.foregroundMuted
                        font.pixelSize: Theme.fontBody
                    }
                    Text {
                        width: 110
                        text: modelData.after
                        color: Theme.foreground
                        font.pixelSize: Theme.fontBody
                        font.bold: modelData.changed
                    }
                }
            }

            Timer {
                id: appliedTimer
                interval: 8000
                onTriggered: appliedText.shown = false
            }
            Connections {
                target: root.correction
                function onAppliedShown() {
                    appliedText.shown = true
                    appliedTimer.restart()
                }
            }
        }
    }

    ToolCorrectionPanel {
        id: correctionPanel
        correction: root.correction
    }

    SimulationSeekControls {
        anchors {
            left: parent.left
            leftMargin: root.backplotLeftMargin + Theme.spacing
            right: parent.right
            rightMargin: 16
            verticalCenter: parent.verticalCenter
        }
        visible: root.simulation && !!root.simulationViewModel
        run: root.run
        simulationViewModel: root.simulationViewModel
    }
}
