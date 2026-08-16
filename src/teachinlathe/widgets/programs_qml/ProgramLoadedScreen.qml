import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "gcode_viewer"
import "program_loaded"
import "program_loaded/running"

Item {
    id: root
    objectName: "programLoadedScreen"
    property var viewModel
    property bool toolChangeToastVisible: false

    function toolChangeViewModel() {
        return root.viewModel ? root.viewModel.toolChange : null
    }

    function toolChangeMessage() {
        var toolChange = root.toolChangeViewModel()
        var toolNo = toolChange && toolChange.toolNo > 0 ? toolChange.toolNo : "?"
        return "Tool " + toolNo + " loaded, press <font color=\"#22c55e\"><b>CycleStart</b></font> to resume the program"
    }

    function showToolChangeToast() {
        root.toolChangeToastVisible = true
        toolChangeToastTimer.restart()
    }

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        handle: Rectangle {
            implicitWidth: 6
            implicitHeight: 6
            color: "#ffffff"
        }

        Rectangle {
            color: "#f5f5f5"
            SplitView.preferredWidth: root.width / 2
            SplitView.minimumWidth: 420

            ColumnLayout {
                anchors.fill: parent
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: false
                    Layout.preferredHeight: 220
                    spacing: 8

                    ProgramsDro {
                        Layout.fillHeight: true
                        Layout.preferredWidth: 600
                        viewModel: root.viewModel
                    }

                    ProgramsToolFeedSpeed {
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        viewModel: programsToolFeedSpeedViewModel
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#0f0f0f"
                    border.color: "#252525"
                    border.width: 1

                    Item {
                        id: viewport
                        objectName: "gremlinViewport"
                        anchors.fill: parent
                    }
                }
            }
        }

        GCodeViewerPane {
            id: gcodePane
            viewModel: root.viewModel
            SplitView.preferredWidth: root.width / 2
            SplitView.minimumWidth: 420
        }
    }

    ProgramCompleteDialog {
        id: completeDialog
        objectName: "programCompleteDialog"
        dialogCenterX: gcodePane.width > 0
            ? root.width - (gcodePane.width / 2)
            : root.width * 0.75
        dialogCenterY: root.height / 2
    }

    ToolChangeDialog {
        anchors.fill: parent
        viewModel: root.viewModel ? root.viewModel.toolChange : null
        dialogCenterX: gcodePane.width > 0
            ? root.width - (gcodePane.width / 2)
            : root.width * 0.75
        dialogCenterY: root.height / 2
    }

    Connections {
        target: root.toolChangeViewModel()
        function onToolChangedPulsed() { root.showToolChangeToast() }
    }

    Timer {
        id: toolChangeToastTimer
        interval: 5000
        repeat: false
        onTriggered: root.toolChangeToastVisible = false
    }

    Rectangle {
        id: toolChangeToast
        visible: root.toolChangeToastVisible
        z: 1200
        x: gcodePane.x + Math.max(0, (gcodePane.width - width) / 2)
        y: Math.max(0, root.height - 200 - height)
        width: Math.min(gcodePane.width, toolChangeToastText.implicitWidth + 100)
        height: toolChangeToastText.implicitHeight + 50
        radius: 8
        color: "#cc303030"

        Text {
            id: toolChangeToastText
            anchors.centerIn: parent
            width: parent.width - 32
            text: root.toolChangeMessage()
            textFormat: Text.RichText
            color: "#ffffff"
            font.pixelSize: 18
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
        }
    }
}
