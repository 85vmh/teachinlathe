import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../app_shell_qml" as Shell

// The row of LinuxCNC diagnostic utilities, shown on both machine screens.
Flow {
    id: root

    property var viewModel: null

    spacing: 8

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
