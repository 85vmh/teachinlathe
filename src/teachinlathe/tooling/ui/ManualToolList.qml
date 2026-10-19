import QtQuick 2.15
import QtQuick.Controls 2.15
import theme 1.0
import common 1.0

// The Manual Turning screen's tools: the tool holders as LinuxCNC numbers
// them, one to a row - all, or with the title bar's recent toggle on only
// the recently used. The one in the spindle is selected; tapping another
// loads it. Each is a ToolHolderCard.
//
// Nothing is edited here: the offsets come from touching off.
Rectangle {
    id: root

    property var viewModel: null        // ManualToolsViewModel

    readonly property int listSpacing: Theme.spacingSmall

    // Outlined and rounded as the other panes are.
    color: Theme.surfaceSunken
    radius: Theme.radius
    border.color: Theme.outline
    border.width: Theme.hairline
    clip: true

    ListView {
        id: list
        anchors.fill: parent
        anchors.margins: root.listSpacing
        spacing: root.listSpacing
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {}
        model: root.viewModel ? root.viewModel.toolsModel : null

        delegate: ToolHolderCard {
            width: ListView.view.width
            toolNo: model.toolNo
            toolId: model.toolId
            toolCard: model.toolCard
            toolView: model.toolView
            toolComment: model.toolComment
            xOffset: model.xOffset
            zOffset: model.zOffset
            selected: model.current
            // Feeding: only the tool in the spindle stays live.
            enabled: model.selectable
            onClicked: root.viewModel.selectTool(model.toolNo)
        }
    }

    ScrollFades {
        anchors.fill: list
        flickable: list
        fadeHeight: 80
    }
}
