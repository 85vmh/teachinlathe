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
