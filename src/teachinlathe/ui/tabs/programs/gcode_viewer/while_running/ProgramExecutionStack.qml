import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.programs.gcode_viewer
import tabs.programs
import theme

Rectangle {
    id: root
    required property var viewModel
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
            height: contentColumn.height + 20

            Column {
                id: contentColumn
                x: 10
                y: 10
                width: root.width - 20
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

                ProgramContentFrame {
                    id: activeFrame
                    width: contentColumn.width
                    visible: viewModel.activeExecutionContent !== ""
                    filePath: viewModel.activeExecutionFilePath

                    GCodeTextArea {
                        Layout.fillWidth: true
                        width: contentColumn.width - 20
                        height: Math.max(root.height - 40, 260)
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
