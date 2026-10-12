import QtQuick 2.15
import theme 1.0
import "../conversational_qml"

// The Tool Library's first screen: the tool holders on the left, the
// cutting tools that can be clamped in them on the right.
//
// Tapping an empty holder's box waits for a cutting tool: the next one
// tapped in the list is mounted in it. A tap anywhere but the list gives up.
Item {
    id: root

    property var viewModel: null

    // The gap the Programs tab leaves between its panes.
    readonly property real gap: 6
    readonly property real paneWidth: Math.max(0, (width - gap) / 2)
    readonly property int selectingHolderId: viewModel ? viewModel.selectingHolderId : 0

    ToolHoldersPane {
        x: 0
        width: root.paneWidth
        height: root.height
        model: root.viewModel ? root.viewModel.holdersModel : null
        selectingHolderId: root.selectingHolderId
        onMountRequested: function(holderId) { root.viewModel.beginMount(holderId) }
        onUnmountRequested: function(holderId) { root.viewModel.unmountTool(holderId) }
        onToolRevealRequested: function(toolId) { cuttingTools.revealTool(toolId) }
        onAddRequested: if (root.viewModel) root.viewModel.addToolHolder()
    }

    // While a holder waits for a tool: a tap anywhere but the cutting-tool
    // list, which is above this, gives up waiting.
    MouseArea {
        anchors.fill: parent
        z: 1
        enabled: root.selectingHolderId !== 0
        onClicked: root.viewModel.cancelMount()
    }

    CuttingToolsPane {
        id: cuttingTools
        z: 2
        x: root.paneWidth + root.gap
        width: root.paneWidth
        height: root.height
        model: root.viewModel ? root.viewModel.cuttingToolsModel : null
        onAddRequested: function(toolType) {
            if (root.viewModel) root.viewModel.addCuttingTool(toolType)
        }
        onToolTapped: function(toolId) {
            if (root.viewModel) root.viewModel.cuttingToolTapped(toolId)
        }
    }

    // The tool picked is in another holder: move it?
    ConfirmDialog {
        id: moveDialog

        property int toolId: 0
        property int toHolderId: 0

        titleText: "Move cutting tool"
        confirmText: "Yes"
        confirmColor: Theme.accent
        confirmPressedColor: Theme.accentStrong
        onConfirmed: root.viewModel.mountTool(toolId, toHolderId)
        onCancelled: root.viewModel.cancelMount()
    }

    Connections {
        target: root.viewModel
        function onMountMoveRequested(toolId, fromHolderId, toHolderId) {
            moveDialog.toolId = toolId
            moveDialog.toHolderId = toHolderId
            moveDialog.messageText = "Cutting Tool #" + toolId
                    + " is already mounted on Tool Holder #" + fromHolderId
                    + ". Mount this cutting tool to Tool Holder #" + toHolderId + "?"
            moveDialog.open()
        }
    }
}
