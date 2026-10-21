import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.programs
import theme

// The bar under the code: the program options, Break on M1 and Skip "/"
// Blocks. While the program runs the bar reaches across under the backplot
// too (ProgramsTabRoot widens it) and Cycle Abort and Feed Hold / Resume come
// in at its right end; Cycle Start is in the app bar until then.
Rectangle {
    id: root

    required property var viewModel
    // How far the run controls are in, 0..1: they fade in as the bar widens.
    property real runControlsReveal: 0

    readonly property var actions: viewModel.actions
    // The pause action is "active" while the program is paused.
    readonly property bool paused: actions ? actions.pauseResumeAction.active : false

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

        LedToggleButton {
            text: "Break on M1"
            enabled: root.actions ? root.actions.optionalStopAction.enabled : false
            checked: root.actions ? root.actions.optionalStopAction.checked : false
            onClicked: root.actions.setOptionalStopEnabled(!checked)
        }

        LedToggleButton {
            text: "Skip / Blocks"
            enabled: root.actions ? root.actions.blockDeleteAction.enabled : false
            checked: root.actions ? root.actions.blockDeleteAction.checked : false
            onClicked: root.actions.setBlockDeleteEnabled(!checked)
        }
    }

    RowLayout {
        anchors {
            right: parent.right
            rightMargin: 16
            verticalCenter: parent.verticalCenter
        }
        spacing: 2 * Theme.spacingLarge
        // in over the second half of the bar's widening, once there is room
        opacity: Math.max(0, root.runControlsReveal * 2 - 1)
        visible: opacity > 0

        RunActionButton {
            text: "Cycle Abort"
            fill: Theme.danger
            pressedFill: Theme.dangerPressed
            edge: "#ef5350"
            enabled: root.actions ? root.actions.stopAction.enabled : false
            onClicked: root.viewModel.triggerCycleAbort()
        }

        RunActionButton {
            text: root.paused ? "Feed Resume" : "Feed Hold"
            enabled: root.actions ? root.actions.pauseResumeAction.enabled : false
            active: root.actions ? root.actions.cycleStartLedActive : false
            onClicked: root.actions.triggerPauseResume()
        }
    }
}
