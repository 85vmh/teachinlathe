import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.programs.gcode_viewer
import tabs.programs
import theme

Rectangle {
    id: root
    required property var viewModel
    // Space under the last frame. The pane sets it so the frame ends as far
    // above the action bar as the backplot does.
    property real bottomPadding: 10
    readonly property real padding: 10
    // The running file is never squeezed below this; past it, the stack scrolls.
    readonly property real minimumCodeHeight: 260
    color: Theme.surface

    function startFrameAt(index) {
        return frameRepeater.itemAt(index)
    }

    function endFrameAt(index) {
        if (index + 1 < frameRepeater.count) {
            return frameRepeater.itemAt(index + 1)
        }
        return activeFrame.visible ? activeFrame : null
    }

    Flickable {
        anchors.fill: parent
        clip: true
        contentWidth: scene.width
        contentHeight: scene.height

        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        Item {
            id: scene
            width: root.width
            height: contentColumn.y + contentColumn.height + root.bottomPadding

            Column {
                id: contentColumn
                x: root.padding
                y: root.padding
                width: root.width - 2 * root.padding
                spacing: 10

                Repeater {
                    id: frameRepeater
                    model: viewModel.executionFrames

                    delegate: ProgramCallFrameCard {
                        width: contentColumn.width
                        title: modelData.title
                        filePath: modelData.filePath
                        lineNumber: modelData.lineNumber
                        lineText: modelData.lineText
                    }
                }

                // Runs down to the bottom of the view, below the calling frames.
                ProgramContentFrame {
                    id: activeFrame
                    width: contentColumn.width
                    height: Math.max(implicitHeight + root.minimumCodeHeight,
                                     root.height - contentColumn.y - y - root.bottomPadding)
                    visible: viewModel.activeExecutionContent !== ""
                    filePath: viewModel.activeExecutionFilePath

                    GCodeTextArea {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        viewModel: root.viewModel
                        content: viewModel.activeExecutionContent
                        highlightLine: viewModel.executionHighlightVisible ? viewModel.activeExecutionMotionLine : 0
                        highlightColor: "#3A86FF"
                        highlightWidth: 1
                        centerOnHighlight: viewModel.executionHighlightVisible
                        emptyText: ""
                    }
                }
            }
        }
    }
}
