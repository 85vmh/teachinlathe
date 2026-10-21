import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.programs
import theme

// The program options under the code: Break on M1 and Skip "/" Blocks.
// Cycle Start is in the app bar until the program is going; Feed Hold /
// Resume and Cycle Abort are under the backplot while it runs (RunControlBar).
Rectangle {
    id: root

    required property var viewModel

    readonly property var actions: viewModel.actions

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
        spacing: Theme.spacingLarge

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
