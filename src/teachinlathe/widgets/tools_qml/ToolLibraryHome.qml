import QtQuick 2.15
import theme 1.0

// The Tool Library's first screen: the tool holders on the left, the
// cutting tools that can be clamped in them on the right.
Item {
    id: root

    property var viewModel: null

    // The gap the Programs tab leaves between its panes.
    readonly property real gap: 6
    readonly property real paneWidth: Math.max(0, (width - gap) / 2)

    ToolHoldersPane {
        x: 0
        width: root.paneWidth
        height: root.height
        model: root.viewModel ? root.viewModel.holdersModel : null
    }

    CuttingToolsPane {
        x: root.paneWidth + root.gap
        width: root.paneWidth
        height: root.height
        model: root.viewModel ? root.viewModel.cuttingToolsModel : null
        onAddRequested: function(toolType) {
            if (root.viewModel) root.viewModel.addCuttingTool(toolType)
        }
        onToolTapped: function(toolId) {
            if (root.viewModel) root.viewModel.editCuttingTool(toolId)
        }
    }
}
