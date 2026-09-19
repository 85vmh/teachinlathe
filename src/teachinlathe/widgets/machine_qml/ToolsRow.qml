import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../app_shell_qml" as Shell
import theme 1.0

// The row of LinuxCNC diagnostic utilities, shown on both machine screens.
Flow {
    id: root

    property var viewModel: null

    spacing: Theme.spacingSmall

    Repeater {
        model: root.viewModel ? root.viewModel.tools : []

        delegate: Shell.ShellActionButton {
            text: modelData.label
            secondary: true
            enabled: root.viewModel ? root.viewModel.canLaunchTool(modelData.key) : false
            onClicked: root.viewModel.launchTool(modelData.key)
        }
    }
}
