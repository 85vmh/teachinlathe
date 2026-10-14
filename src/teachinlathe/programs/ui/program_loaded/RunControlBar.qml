import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import theme 1.0

// Under the backplot while the program runs (the full-screen view): Cycle
// Abort, and Feed Hold / Feed Resume. Cycle Start is not here - before the
// program starts it is in the app bar, and once it has completed the
// "Program Completed" dialog offers it.
Rectangle {
    id: root

    property var viewModel

    readonly property var actions: viewModel ? viewModel.actions : null
    // The pause action is "active" while the program is paused.
    readonly property bool paused: actions ? actions.pauseResumeAction.active : false

    color: Theme.surfaceSunken
    radius: Theme.radius
    border.color: Theme.outline
    border.width: Theme.hairline

    RowLayout {
        anchors {
            right: parent.right
            rightMargin: 16
            verticalCenter: parent.verticalCenter
        }
        spacing: Theme.spacingLarge

        MachineRoundButton {
            text: "Cycle\nAbort"
            enabled: root.actions ? root.actions.stopAction.enabled : false
            active: false
            normalFillCenterColor: "#6a0000"
            normalFillMidColor:    Theme.danger
            normalFillRimColor:    "#ef9a9a"
            activeFillCenterColor: Theme.danger
            activeFillRimColor:    "#ef9a9a"
            onClicked: if (root.viewModel) root.viewModel.triggerCycleAbort()
        }

        MachineRoundButton {
            text: root.paused ? "Feed\nResume" : "Feed\nHold"
            enabled: root.actions ? root.actions.pauseResumeAction.enabled : false
            active: root.actions ? root.actions.cycleStartLedActive : false
            normalFillCenterColor: "#0b3d12"
            normalFillMidColor:    "#1b5e20"
            normalFillRimColor:    Theme.success
            activeFillCenterColor: Theme.success
            activeFillRimColor:    "#a5d6a7"
            onClicked: if (root.actions) root.actions.triggerPauseResume()
        }
    }
}
