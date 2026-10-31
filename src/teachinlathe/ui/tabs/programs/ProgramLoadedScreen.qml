import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import tabs.programs.program_loaded
import TeachInLathe.Backplot
import theme
import common

// The loaded-program screen's own pane - the spindle / feed / tool boxes,
// the backplot under them, and under it the run controls while the
// program runs - on the right of the strip ProgramsTabRoot slides; the code
// beside it, with the DRO over it, is the strip's shared code pane.
Item {
    id: root
    objectName: "programLoadedScreen"
    required property var viewModel
    required property var run
    required property var simulationViewModel
    property bool simulation: false
    property string programFile: ""
    // Whether the loaded-program screen is the one on show (it stays visible
    // while the strip slides away from it).
    property bool shown: true
    // How far the bar under the code has reached across under the backplot, 0..1.
    property real runBarReveal: 0
    property int runBarHeight: Theme.barHeight
    // How far three fingers have to travel together, in px, for the swipe
    // that clears the plot.
    readonly property int clearSwipeDistance: 80
    property bool toolChangedToastVisible: false
    property string toolChangedToastMessage: ""

    function withPlot(callback) {
        var view = root.simulation ? simulationBackplot : machineBackplot
        if (view)
            callback(view.plot)
    }

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
    onProgramFileChanged: root.withPlot(function(plot) { plot.setProgramFile(root.programFile) })

    Rectangle {
        anchors.fill: parent
        color: Theme.surfaceSunken

        ColumnLayout {
            anchors.fill: parent
            spacing: Theme.spacingSmall

            // The spindle, the feed and the tool, between the top bar and
            // the backplot.
            ProgramsToolFeedSpeed {
                Layout.fillWidth: true
                Layout.preferredHeight: implicitHeight
                viewModel: root.run
                actions: root.viewModel.actions
                simulationViewModel: root.simulationViewModel
                simulation: root.simulation
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                // QQuickFramebufferObject cannot safely be destroyed and
                // recreated while the application runs. Keep one renderer
                // per immutable source and show only the active one.
                BackplotView {
                    id: machineBackplot
                    anchors.fill: parent
                    visible: !root.simulation
                    clearSwipeDistance: root.clearSwipeDistance
                    run: root.viewModel.run
                    Component.onCompleted: plot.setProgramFile(root.viewModel.previewFile)
                }

                BackplotView {
                    id: simulationBackplot
                    anchors.fill: parent
                    visible: root.simulation
                    clearSwipeDistance: root.clearSwipeDistance
                    run: root.simulationViewModel.run
                    Component.onCompleted: plot.setProgramFile(root.simulationViewModel.programFile)
                }

                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: Theme.spacingLarge
                    visible: root.simulation && root.run.state === "waiting"
                    width: waitText.implicitWidth + 2 * Theme.spacingLarge
                    height: waitText.implicitHeight + 2 * Theme.spacing
                    radius: Theme.radius
                    color: "#fff3e0"
                    border.color: Theme.warning
                    border.width: Theme.hairline

                    Text {
                        id: waitText
                        anchors.centerIn: parent
                        text: root.run.waitingFor + ": press Cycle Start to go on"
                        color: Theme.foreground
                        font.pixelSize: Theme.fontBody
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: root.simulation && root.simulationViewModel
                             && root.simulationViewModel.loading
                    text: "Reading the program as the machine would run it…"
                    color: Theme.foregroundMuted
                    font.pixelSize: Theme.fontBody
                }

                Column {
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.topMargin: Theme.zoomInOutFitMirrorButtonMarginTop
                                       + Theme.zoomInOutFitMirrorButtonSize + Theme.spacing
                    anchors.rightMargin: Theme.spacingLarge + 32
                    spacing: 2
                    visible: root.simulation && root.simulationViewModel
                             && root.simulationViewModel.ready

                    Text {
                        anchors.right: parent.right
                        text: root.simulationViewModel ? root.simulationViewModel.operation : ""
                        color: Theme.foreground
                        font.pixelSize: Theme.fontBody
                        font.bold: true
                    }

                    Text {
                        anchors.right: parent.right
                        visible: root.simulationViewModel
                                 && root.simulationViewModel.collisions.length > 0
                        text: root.simulationViewModel
                              && root.simulationViewModel.collisions.length === 1
                              ? "1 rapid through the material"
                              : (root.simulationViewModel
                                 ? root.simulationViewModel.collisions.length : 0)
                                + " rapids through the material"
                        color: Theme.danger
                        font.pixelSize: Theme.fontSmall
                        font.bold: true
                    }
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    anchors.margins: Theme.spacingLarge
                    visible: root.simulation && root.simulationViewModel
                             && root.simulationViewModel.error !== ""
                    width: Math.min(errorText.implicitWidth + 2 * Theme.spacing,
                                    parent.width - 2 * Theme.spacingLarge)
                    height: errorText.implicitHeight + 2 * Theme.spacingSmall
                    radius: Theme.radius
                    color: Theme.dangerSoft
                    border.color: Theme.danger
                    border.width: Theme.hairline

                    Text {
                        id: errorText
                        x: Theme.spacing
                        y: Theme.spacingSmall
                        width: parent.width - 2 * Theme.spacing
                        text: root.simulationViewModel ? root.simulationViewModel.error : ""
                        color: Theme.foreground
                        font.pixelSize: Theme.fontSmall
                        wrapMode: Text.Wrap
                    }
                }
            }

            // Room for the bar under the code, which reaches across under
            // the backplot while the program runs (ProgramsTabRoot draws it).
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(0, (root.runBarHeight + parent.spacing)
                                                 * root.runBarReveal - parent.spacing)
                visible: root.runBarReveal > 0
            }
        }
    }

    // Machine preview requests always address the machine renderer. They can
    // arrive while simulation is shown, but must not mutate its plot.
    Connections {
        target: root.viewModel
        function onPreviewFileChanged() {
            machineBackplot.plot.setProgramFile(root.viewModel.previewFile)
        }
        function onPreviewInvalidated(path) { machineBackplot.plot.invalidatePreview(path) }
        function onPreviewPollRequested() { machineBackplot.plot.poll() }
        function onGremlinZoomInRequested() { root.withPlot(function(plot) { plot.zoomIn() }) }
        function onGremlinZoomOutRequested() { root.withPlot(function(plot) { plot.zoomOut() }) }
        function onGremlinClearRequested() { root.withPlot(function(plot) { plot.clearPlot() }) }
        function onGremlinFitRequested() { root.withPlot(function(plot) { plot.fitToWindow() }) }
    }

    // No geometry here any more: it is a Popup in the window's overlay, so it
    // centres on the screen and dims all of it.
    ToolChangeDialog {
        viewModel: root.viewModel.toolChange
        enabledForMode: !root.simulation
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
        visible: !root.simulation && root.toolChangedToastVisible && root.shown
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
        visible: !root.simulation && root.shown && (root.viewModel.programCompletedVisible)
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
