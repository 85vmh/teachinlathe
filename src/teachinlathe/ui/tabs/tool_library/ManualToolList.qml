import QtQuick
import QtQuick.Controls
import theme
import common

// The Manual Turning screen's tools: the tool holders as LinuxCNC numbers
// them, one to a row - all, or with the title bar's recent toggle on only
// the recently used. The current loaded tool is selected, and kept in view;
// tapping another loads it. Each is a ToolHolderCard.
//
// Nothing is edited here: the offsets come from touching off.
Rectangle {
    id: root

    required property var viewModel        // ManualToolsViewModel

    readonly property int listSpacing: Theme.spacingSmall
    // How long scrolling the current loaded tool into view takes, in ms.
    readonly property int scrollDurationMs: 250

    // The current loaded tool into view, if it is not all in view already.
    function showCurrentLoadedTool() {
        var row = root.viewModel.currentLoadedToolRow
        if (row < 0 || row >= list.count || list.height <= 0)
            return
        scrollToCurrentLoadedTool.stop()
        var from = list.contentY
        list.positionViewAtIndex(row, ListView.Contain)
        var to = list.contentY
        if (Math.abs(to - from) < 1)
            return
        list.contentY = from
        scrollToCurrentLoadedTool.from = from
        scrollToCurrentLoadedTool.to = to
        scrollToCurrentLoadedTool.start()
    }

    Connections {
        target: root.viewModel
        function onCurrentLoadedToolRowChanged() { Qt.callLater(root.showCurrentLoadedTool) }
    }
    onVisibleChanged: if (visible) Qt.callLater(showCurrentLoadedTool)
    onHeightChanged: Qt.callLater(showCurrentLoadedTool)

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
        model: root.viewModel.toolsModel

        delegate: ToolHolderCard {
            width: ListView.view.width
            toolNo: model.toolNo
            toolId: model.toolId
            toolCard: model.toolCard
            toolView: model.toolView
            toolComment: model.toolComment
            xOffset: model.xOffset
            zOffset: model.zOffset
            selected: model.isCurrentLoadedTool
            // Feeding: only the current loaded tool stays live.
            enabled: model.selectable
            onClicked: root.viewModel.selectTool(model.toolNo)
        }
    }

    NumberAnimation {
        id: scrollToCurrentLoadedTool
        target: list
        property: "contentY"
        duration: root.scrollDurationMs
        easing.type: Easing.OutCubic
    }

    ScrollFades {
        anchors.fill: list
        flickable: list
        fadeHeight: 80
    }
}
