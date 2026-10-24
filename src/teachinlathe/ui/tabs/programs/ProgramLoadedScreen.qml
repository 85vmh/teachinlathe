import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import tabs.programs.program_loaded
import TeachInLathe.Backplot
import theme
import common

// The loaded-program screen's own pane - the backplot, and under it the run
// controls while the program runs - on the right of the strip
// ProgramsTabRoot slides; the code beside it, with the DRO over it, is the
// strip's shared code pane.
Item {
    id: root
    objectName: "programLoadedScreen"
    required property var viewModel
    // Whether the loaded-program screen is the one on show (it stays visible
    // while the strip slides away from it).
    property bool shown: true
    // How far the bar under the code has reached across under the backplot, 0..1.
    property real runBarReveal: 0
    // How far three fingers have to travel together, in px, for the swipe
    // that clears the plot.
    readonly property int clearSwipeDistance: 80
    property bool toolChangedToastVisible: false
    property string toolChangedToastMessage: ""

    function toolChangeViewModel() {
        return root.viewModel.toolChange
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
            + "Press <font color=\"#22c55e\"><b>Cycle Start</b></font> to resume the motion</div>"
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
                    Component.onCompleted: if (root.viewModel) setProgramFile(root.viewModel.previewFile)

                    // What to preview, and what to do to the view, as the
                    // view model says.
                    Connections {
                        target: root.viewModel
                        function onPreviewFileChanged() { backplot.setProgramFile(root.viewModel.previewFile) }
                        function onPreviewInvalidated(path) { backplot.invalidatePreview(path) }
                        function onPreviewPollRequested() { backplot.poll() }
                        function onGremlinZoomInRequested() { backplot.zoomIn() }
                        function onGremlinZoomOutRequested() { backplot.zoomOut() }
                        function onGremlinClearRequested() { backplot.clearPlot() }
                        function onGremlinFitRequested() { backplot.fitToWindow() }
                    }
                    // three fingers swiped this far clear the plot
                    clearSwipeDistance: root.clearSwipeDistance
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

                    // As the profile canvases have them (Theme), over the
                    // scale the plot draws round its own edge.
                    Row {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.leftMargin: Theme.zoomInOutFitMirrorButtonMarginLeft
                        anchors.topMargin: Theme.zoomInOutFitMirrorButtonMarginTop
                        spacing: Theme.zoomInOutFitMirrorButtonSpacing

                        BackplotIconButton {
                            implicitWidth: Theme.zoomInOutFitMirrorButtonSize
                            implicitHeight: Theme.zoomInOutFitMirrorButtonSize
                            iconSource: Images.url("zoom-in.svg")
                            autoRepeat: true
                            autoRepeatDelay: 300
                            autoRepeatInterval: 100
                            onClicked: backplot.zoomIn()
                        }
                        BackplotIconButton {
                            implicitWidth: Theme.zoomInOutFitMirrorButtonSize
                            implicitHeight: Theme.zoomInOutFitMirrorButtonSize
                            iconSource: Images.url("zoom-out.svg")
                            autoRepeat: true
                            autoRepeatDelay: 300
                            autoRepeatInterval: 100
                            onClicked: backplot.zoomOut()
                        }
                        BackplotIconButton {
                            implicitWidth: Theme.zoomInOutFitMirrorButtonSize
                            implicitHeight: Theme.zoomInOutFitMirrorButtonSize
                            iconSource: Images.url("zoom-fit.svg")
                            onClicked: backplot.fitToWindow()
                        }
                        // the material left so far, drawn above the centre
                        // line; off when the app starts, then as left
                        BackplotIconButton {
                            implicitWidth: Theme.zoomInOutFitMirrorButtonSize
                            implicitHeight: Theme.zoomInOutFitMirrorButtonSize
                            iconSource: Images.url("mirror.svg")
                            active: backplot.mirror
                            onClicked: backplot.mirror = !backplot.mirror
                        }
                    }

                    // Same button as the zoom row, so the two line up
                    // across the top of the plot - as far in from the right
                    // as the row is from the left; the tint is what says
                    // it throws something away.
                    BackplotIconButton {
                        implicitWidth: Theme.zoomInOutFitMirrorButtonSize
                        implicitHeight: Theme.zoomInOutFitMirrorButtonSize
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.rightMargin: Theme.zoomInOutFitMirrorButtonMarginLeft
                        anchors.topMargin: Theme.zoomInOutFitMirrorButtonMarginTop
                        iconSource: Images.url("brush_out.svg")
                        tint: Theme.danger
                        borderTint: Theme.danger
                        onClicked: backplot.clearPlot()
                    }
                }
            }

            // Room for the bar under the code, which reaches across under
            // the backplot while the program runs (ProgramsTabRoot draws it).
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(0, (Theme.barHeight + parent.spacing) * root.runBarReveal - parent.spacing)
                visible: root.runBarReveal > 0
            }
        }
    }

    // No geometry here any more: it is a Popup in the window's overlay, so it
    // centres on the screen and dims all of it.
    ToolChangeDialog {
        viewModel: root.viewModel.toolChange
    }

    Connections {
        target: root.toolChangeViewModel()
        function onToolChangedPulsed(toolNo) { root.showToolChangedToast(toolNo) }
    }

    // The program waits, paused, for Cycle Start after a tool change: the
    // toast that says so stays until the motion resumes - or the program is
    // stopped - not for a fixed time. Only when no pause comes does it go
    // after a few seconds.
    readonly property var pauseResume: root.viewModel.actions ? root.viewModel.actions.pauseResumeAction : null
    Connections {
        target: root.pauseResume
        function onActiveChanged(active) { if (!active) root.toolChangedToastVisible = false }
    }

    Timer {
        id: toolChangedToastTimer
        interval: 5000
        repeat: false
        onTriggered: if (!(root.pauseResume && root.pauseResume.active)) root.toolChangedToastVisible = false
    }

    Rectangle {
        id: toolChangedToast
        // Over the whole window, in its middle - wherever the strip has slid
        // this screen to: a position worked out from this screen's own went
        // stale as it moved.
        parent: Overlay.overlay
        anchors.centerIn: parent
        visible: root.toolChangedToastVisible && root.shown
        z: 1200
        width: Math.min(parent ? parent.width - 32 : root.width,
                        toolChangedToastText.implicitWidth + 100)
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
        // in the middle of the window, as the tool-changed toast
        parent: Overlay.overlay
        anchors.centerIn: parent
        visible: root.shown && (root.viewModel.programCompletedVisible)
        z: 1300
        width: Math.min(parent ? parent.width - 32 : root.width,
                        programCompletedToastText.implicitWidth + 100)
        height: programCompletedToastText.implicitHeight + 50
        radius: Theme.radiusLarge
        color: "#ff303030"

        Text {
            id: programCompletedToastText
            anchors.centerIn: parent
            width: parent.width - 32
            textFormat: Text.RichText
            text: "<div align=\"center\"><b>Program Completed</b><br/>"
                + "[" + root.escapeHtml(root.viewModel.programCompletedName) + "]<br/><br/><br/><br/>"
                + "Press <font color=\"#22c55e\"><b>Cycle Start</b></font> to run again the same program.<br/><br/>"
                + "Press <font color=\"#ef4444\"><b>Cycle Abort</b></font> to close this screen.</div>"
            color: Theme.surface
            font.pixelSize: Theme.fontLarge
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
        }
    }
}
