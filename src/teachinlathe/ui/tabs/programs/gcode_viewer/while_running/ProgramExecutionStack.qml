import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.programs.gcode_viewer
import tabs.programs
import theme

// The calling frames, one card each, and the running file's under them. No
// fill of its own: the window's background shows between the cards, and they
// reach from edge to edge of the pane - as the code's single frame does with
// no stack, and the DRO over it - Theme.paneGap apart, as the DRO is from them.
Item {
    id: root
    required property var viewModel
    // Space under the last frame. The pane sets it so the frame ends as far
    // above the action bar as the backplot does.
    property real bottomPadding: 10
    // The running file is never squeezed below this; past it, the stack scrolls.
    readonly property real minimumCodeHeight: 260

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
                width: root.width
                spacing: Theme.paneGap

                Repeater {
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
