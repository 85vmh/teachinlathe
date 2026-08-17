import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "gcode_viewer"
import "program_loaded"

Item {
    id: root
    objectName: "programLoadedScreen"
    property var viewModel
    property bool toolChangedToastVisible: false
    property string toolChangedToastMessage: ""

    function toolChangeViewModel() {
        return root.viewModel ? root.viewModel.toolChange : null
    }

    function escapeHtml(value) {
        return String(value === undefined || value === null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;")
    }

    function refreshToolChangeFromHal() {
        var toolChange = root.toolChangeViewModel()
        if (toolChange)
            toolChange.refreshFromHal()
    }

    function toolChangedMessage(toolNo) {
        var displayToolNo = toolNo > 0 ? toolNo : "?"
        return "<div align=\"center\"><b>Tool " + displayToolNo + " loaded</b><br/><br/>"
            + "Press <font color=\"#22c55e\"><b>Cycle Start</b></font> to resume the program</div>"
    }

    function showToolChangedToast(toolNo) {
        root.toolChangedToastMessage = root.toolChangedMessage(toolNo)
        root.toolChangedToastVisible = true
        toolChangedToastTimer.restart()
    }

    Component.onCompleted: root.refreshToolChangeFromHal()
    onVisibleChanged: if (visible) root.refreshToolChangeFromHal()
    onViewModelChanged: root.refreshToolChangeFromHal()

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
        function onToolChangedPulsed(toolNo) { root.showToolChangedToast(toolNo) }
    }

    Timer {
        id: toolChangedToastTimer
        interval: 5000
        repeat: false
        onTriggered: root.toolChangedToastVisible = false
    }

    Rectangle {
        id: toolChangedToast
        visible: root.toolChangedToastVisible
        z: 1200
        x: gcodePane.x + Math.max(0, (gcodePane.width - width) / 2)
        y: Math.max(0, root.height - 200 - height)
        width: Math.min(gcodePane.width, toolChangedToastText.implicitWidth + 100)
        height: toolChangedToastText.implicitHeight + 50
        radius: 8
        color: "#cc303030"

        Text {
            id: toolChangedToastText
            anchors.centerIn: parent
            width: parent.width - 32
            text: root.toolChangedToastMessage
            textFormat: Text.RichText
            color: "#ffffff"
            font.pixelSize: 18
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
        }
    }

    Rectangle {
        id: programCompletedToast
        visible: root.viewModel ? root.viewModel.programCompletedVisible : false
        z: 1300
        x: gcodePane.x + Math.max(0, (gcodePane.width - width) / 2)
        y: Math.max(0, root.height - 220 - height)
        width: Math.min(gcodePane.width, programCompletedToastText.implicitWidth + 100)
        height: programCompletedToastText.implicitHeight + 50
        radius: 8
        color: "#ff303030"

        Text {
            id: programCompletedToastText
            anchors.centerIn: parent
            width: parent.width - 32
            textFormat: Text.RichText
            text: "<div align=\"center\"><b>Program Completed</b><br/>"
                + "[" + root.escapeHtml(root.viewModel ? root.viewModel.programCompletedName : "") + "]<br/><br/><br/><br/>"
                + "Press <font color=\"#22c55e\"><b>Cycle Start</b></font> to run again the same program.<br/><br/>"
                + "Press <font color=\"#ef4444\"><b>Cycle Abort</b></font> to close this screen.</div>"
            color: "#ffffff"
            font.pixelSize: 18
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
        }
    }
}
