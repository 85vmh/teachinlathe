import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../.."

Rectangle {
    id: root
    property var viewModel
    color: "#ffffff"

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
                    model: viewModel ? viewModel.executionFrames : []

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
                    visible: !!viewModel && viewModel.activeExecutionContent !== ""
                    filePath: viewModel ? viewModel.activeExecutionFilePath : ""

                    GCodeTextArea {
                        Layout.fillWidth: true
                        width: contentColumn.width - 20
                        height: Math.max(root.height - 40, 260)
                        viewModel: root.viewModel
                        content: viewModel ? viewModel.activeExecutionContent : ""
                        highlightLine: viewModel && viewModel.executionHighlightVisible ? viewModel.activeExecutionMotionLine : 0
                        highlightColor: "#3A86FF"
                        highlightWidth: 1
                        centerOnHighlight: !!viewModel && viewModel.executionHighlightVisible
                        emptyText: ""
                    }
                }
            }
        }
    }
}
