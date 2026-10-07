import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "program_loaded"
import TeachInLathe.Backplot 1.0
import theme 1.0

// The loaded-program screen's own pane - the backplot, and under it the run
// controls while the program runs - on the right of the strip
// ProgramsTabRoot slides; the code beside it, with the DRO over it, is the
// strip's shared code pane.
Item {
    id: root
    objectName: "programLoadedScreen"
    property var viewModel
    // Whether the loaded-program screen is the one on show (it stays visible
    // while the strip slides away from it).
    property bool shown: true
    // Where the code pane is, relative to this pane: the toasts centre over it.
    property real codePaneX: 0
    property real codePaneWidth: width
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
    onShownChanged: if (shown) root.refreshToolChangeFromHal()
    onViewModelChanged: root.refreshToolChangeFromHal()

    Rectangle {
        anchors.fill: parent
        color: Theme.surfaceSunken

        ColumnLayout {
            anchors.fill: parent
            spacing: Theme.spacingSmall

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                // The same panel an operation detail sits on: white with
                // a light border. The preview's own palette is tuned to
                // match - see _configure_for_lathe.
                color: Theme.surface
                border.color: Theme.outline
                border.width: Theme.hairline

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

                    // Two fingers pinch-zoom, and pan as they move. One
                    // finger still reaches the MouseArea inside; a second
                    // one hands the gesture over here, cancelling that pan.
                    PinchArea {
                        anchors.fill: parent
                        onPinchStarted: function (pinch) {
                            backplot.pinchStarted(pinch.startCenter.x, pinch.startCenter.y)
                        }
                        onPinchUpdated: function (pinch) {
                            backplot.pinchUpdated(pinch.scale, pinch.center.x, pinch.center.y)
                        }
                        onPinchFinished: backplot.pinchFinished()

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
                            onDoubleClicked: backplot.fitToWindow()
                            onWheel: function (wheel) {
                                backplot.wheelZoom(wheel.angleDelta.y)
                            }
                        }
                    }

                    // Clear of the scale the plot draws round its own
                    // edge. The ticks reach 7px in, their labels another
                    // 2px past that, and a label as wide as "-100" adds
                    // about 36 more - so anything inside 48px sits on top
                    // of the numbers. See actors/ticks.py for those three.
                    readonly property int plotMargin: 48

                    Row {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.margins: backplot.plotMargin
                        // The profile editor's spacing over its canvas.
                        spacing: 32

                        BackplotIconButton {
                            iconSource: "../conversational_qml/icons/zoom-in.svg"
                            autoRepeat: true
                            autoRepeatDelay: 300
                            autoRepeatInterval: 100
                            onClicked: backplot.zoomIn()
                        }
                        BackplotIconButton {
                            iconSource: "../conversational_qml/icons/zoom-out.svg"
                            autoRepeat: true
                            autoRepeatDelay: 300
                            autoRepeatInterval: 100
                            onClicked: backplot.zoomOut()
                        }
                        BackplotIconButton {
                            iconSource: "../conversational_qml/icons/zoom-fit.svg"
                            onClicked: backplot.fitToWindow()
                        }
                    }

                    // Same button as the zoom row, so the two line up
                    // across the top of the plot; the tint is what says
                    // it throws something away.
                    BackplotIconButton {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: backplot.plotMargin
                        iconSource: "../conversational_qml/icons/brush_out.svg"
                        tint: Theme.danger
                        borderTint: Theme.danger
                        onClicked: backplot.clearPlot()
                    }
                }
            }

            // Cycle Abort and Feed Hold / Resume, while the program runs - the
            // same height as the options bar under the code, so the two line up.
            RunControlBar {
                Layout.fillWidth: true
                Layout.preferredHeight: 90
                visible: root.viewModel ? root.viewModel.screenIndex === ProgramsScreen.Running : false
                viewModel: root.viewModel
            }
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
        visible: root.toolChangedToastVisible && root.shown
        z: 1200
        x: root.codePaneX + Math.max(0, (root.codePaneWidth - width) / 2)
        y: Math.max(0, root.height - 200 - height)
        width: Math.min(root.codePaneWidth, toolChangedToastText.implicitWidth + 100)
        height: toolChangedToastText.implicitHeight + 50
        radius: Theme.radiusLarge
        color: "#cc303030"

        Text {
            id: toolChangedToastText
            anchors.centerIn: parent
            width: parent.width - 32
            text: root.toolChangedToastMessage
            textFormat: Text.RichText
            color: Theme.surface
            font.pixelSize: Theme.fontLarge
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
        }
    }

    Rectangle {
        id: programCompletedToast
        visible: root.shown && (root.viewModel ? root.viewModel.programCompletedVisible : false)
        z: 1300
        x: root.codePaneX + Math.max(0, (root.codePaneWidth - width) / 2)
        y: Math.max(0, root.height - 220 - height)
        width: Math.min(root.codePaneWidth, programCompletedToastText.implicitWidth + 100)
        height: programCompletedToastText.implicitHeight + 50
        radius: Theme.radiusLarge
        color: "#ff303030"

        Text {
            id: programCompletedToastText
            anchors.centerIn: parent
            width: parent.width - 32
            textFormat: Text.RichText
            // The two actions are links: tapping either does what the
            // machine's button would.
            text: "<div align=\"center\"><b>Program Completed</b><br/>"
                + "[" + root.escapeHtml(root.viewModel ? root.viewModel.programCompletedName : "") + "]<br/><br/><br/><br/>"
                + "Press <a href=\"cycle_start\"><font color=\"#22c55e\"><b>Cycle Start</b></font></a> to run again the same program.<br/><br/>"
                + "Press <a href=\"cycle_abort\"><font color=\"#ef4444\"><b>Cycle Abort</b></font></a> to close this screen.</div>"
            onLinkActivated: function(link) {
                if (!root.viewModel) return
                if (link === "cycle_start") root.viewModel.triggerCycleStart()
                else if (link === "cycle_abort") root.viewModel.closeCompletedProgram()
            }
            color: Theme.surface
            font.pixelSize: Theme.fontLarge
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
        }
    }
}
