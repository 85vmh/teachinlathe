import QtQuick
import QtQuick.Layouts
import app_shell_qml as Shell
import theme

// The row of LinuxCNC diagnostic utilities, shown on both machine screens.
Flow {
    id: root

    required property var viewModel

    spacing: Theme.spacingSmall

    Repeater {
        model: root.viewModel.tools

        delegate: Shell.ShellActionButton {
            text: modelData.label
            secondary: true
            enabled: root.viewModel.canLaunchTool(modelData.key)
            onClicked: root.viewModel.launchTool(modelData.key)
        }
    }
}
