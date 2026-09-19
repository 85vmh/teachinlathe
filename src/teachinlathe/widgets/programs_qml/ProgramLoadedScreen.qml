import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "gcode_viewer"
import "program_loaded"
import TeachInLathe.Backplot 1.0

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
                    // The same panel an operation detail sits on: white with
                    // a light border. The preview's own palette is tuned to
                    // match - see _configure_for_lathe.
                    color: "#ffffff"
                    border.color: "#cccccc"
                    border.width: 1

                    // Was an empty Item that Python mapped a QOpenGLWidget
                    // onto, resyncing its geometry on every move and resize.
                    // The preview renders into the scene graph now, so it is
                    // just an item, and the controls over it are ordinary
                    // buttons rather than QPushButtons positioned by hand.
                    LatheBackplot {
                        id: backplot
                        objectName: "latheBackplot"
                        anchors.fill: parent
                        anchors.margins: 1

                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                            onPressed: function (mouse) {
                                backplot.pressed(mouse.x, mouse.y)
                            }
                            onPositionChanged: function (mouse) {
                                if (mouse.buttons & Qt.MiddleButton)
                                    backplot.zoomDragged(mouse.y)
                                else if (mouse.buttons & Qt.LeftButton)
                                    backplot.panned(mouse.x, mouse.y)
                            }
                            onWheel: function (wheel) {
                                backplot.wheelZoom(wheel.angleDelta.y)
                            }
                        }

                        Row {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.margins: 16
                            spacing: 12

                            BackplotButton {
                                text: "Zoom In"
                                autoRepeat: true
                                autoRepeatDelay: 300
                                autoRepeatInterval: 100
                                onClicked: backplot.zoomIn()
                            }
                            BackplotButton {
                                text: "Zoom Out"
                                autoRepeat: true
                                autoRepeatDelay: 300
                                autoRepeatInterval: 100
                                onClicked: backplot.zoomOut()
                            }
                            BackplotButton {
                                text: "Fit To Screen"
                                onClicked: backplot.fitToWindow()
                            }
                        }

                        BackplotButton {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 16
                            text: "Clear Plot"
                            baseColor: "#7a2d2d"
                            hoverColor: "#652424"
                            borderColor: "#d16969"
                            onClicked: backplot.clearPlot()
                        }
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

    // No geometry here any more: it is a Popup in the window's overlay, so it
    // centres on the screen and dims all of it.
    ToolChangeDialog {
        viewModel: root.viewModel ? root.viewModel.toolChange : null
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
