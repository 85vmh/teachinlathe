// SimulateScreen.qml — a G-code file played as the machine would run it
// (SimulateViewModel), laid out as the loaded-program screen is, each part in a
// box of its own: on the left, as wide as that screen's code, the DRO - where
// the run is - over the code - the line being run kept in the middle;
// scrolled, the run goes to the line in the middle - and under it the
// machine's buttons; on the right the backplot, drawn as the machine running
// it would be - the toolpath, the stock and the material left, the trail, the
// tool - and under it the timeline (SimulateSeekBar), how long it runs and how
// fast it plays.
import QtQuick
import QtQuick.Layouts
import tabs.programs
import tabs.programs.gcode_viewer
import tabs.programs.program_loaded
import theme

Rectangle {
    id: root

    required property var viewModel

    readonly property bool running: viewModel.state === "running"
    readonly property bool held: viewModel.state === "held"
    readonly property bool moving: running || held

    readonly property color collisionColor: Theme.danger
    // between the boxes, as between the Conversational screen's panes and
    // over the Programs screen's bar
    readonly property int boxGap: 6

    color: Theme.surfaceSunken

    // mm:ss, or h:mm:ss for an hour and more
    function clock(seconds) {
        var s = Math.max(0, Math.round(seconds))
        var h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60, sec = s % 60
        var mm = (h > 0 && m < 10 ? "0" : "") + m, ss = (sec < 10 ? "0" : "") + sec
        return (h > 0 ? h + ":" : "") + mm + ":" + ss
    }

    // The view fitted to the program each time a run comes in
    Connections {
        target: root.viewModel
        function onFileChanged() { backplotView.plot.setProgramFile(root.viewModel.programFile) }
        function onRunChanged() { Qt.callLater(backplotView.plot.fitToWindow) }
    }

    RowLayout {
        anchors.fill: parent
        spacing: root.boxGap

        // ── the DRO, the code, and the machine's buttons under it ─────────
        ColumnLayout {
            // as wide as the loaded-program screen's code (ProgramsTabRoot),
            // and no wider: a layout in a layout fills by default
            readonly property real codeWidth: Math.max(0, root.width - 2 * root.boxGap) * 0.3
            Layout.fillWidth: false
            Layout.preferredWidth: codeWidth
            Layout.minimumWidth: codeWidth
            Layout.maximumWidth: codeWidth
            Layout.fillHeight: true
            spacing: root.boxGap

            // where the run is, as the machine's DRO shows where it is - in
            // the same place, over the code: scrolled through the code, it
            // follows
            ProgramsDro {
                Layout.fillWidth: true
                Layout.preferredHeight: implicitHeight
                // as far above the code as the loaded-program screen's
                Layout.bottomMargin: Theme.spacingSmall - root.boxGap
                viewModel: root.viewModel
            }

            // as the Programs screen frames its code
            ProgramContentFrame {
                Layout.fillWidth: true
                Layout.fillHeight: true
                filePath: root.viewModel.programFile

                GCodeTextArea {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    viewModel: root.viewModel
                    content: root.viewModel.content
                    highlightLine: root.viewModel.ready ? root.viewModel.programLine : 0
                    centerOnHighlight: true
                    // the code a seek bar too, while the run is not running
                    followUserScroll: root.viewModel.ready && !root.moving
                    onLineScrolledTo: function(line) { root.viewModel.seekToLine(line) }
                    emptyText: "No program"
                }
            }

            // the machine's buttons, in a bar as the Programs screen's
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Theme.barHeight
                color: Theme.surfaceSunken
                radius: Theme.radius
                border.color: Theme.outline
                border.width: Theme.hairline

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spacingLarge
                    anchors.rightMargin: Theme.spacingLarge
                    spacing: Theme.spacingSmall

                    RunActionButton {
                        Layout.fillWidth: true
                        implicitWidth: 100
                        text: "Cycle Start"
                        enabled: root.viewModel.ready && !root.moving
                        active: root.viewModel.state === "waiting"
                        onClicked: root.viewModel.cycleStart()
                    }

                    RunActionButton {
                        Layout.fillWidth: true
                        implicitWidth: 100
                        text: root.held ? "Feed Resume" : "Feed Hold"
                        enabled: root.moving
                        active: root.held
                        onClicked: root.viewModel.feedHold()
                    }

                    RunActionButton {
                        Layout.fillWidth: true
                        implicitWidth: 100
                        text: "Cycle Stop"
                        fill: Theme.danger
                        pressedFill: Theme.dangerPressed
                        edge: "#ef5350"
                        enabled: root.viewModel.ready && root.viewModel.state !== "idle"
                        onClicked: root.viewModel.cycleStop()
                    }
                }
            }
        }

        // ── the backplot, and the timeline under it ───────────────────────
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: root.boxGap

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                // the run as the machine running it would show it: the same
                // plot, fed by the run (backplot.feeds.SimulatedFeed)
                BackplotView {
                    id: backplotView
                    anchors.fill: parent
                    simulation: root.viewModel
                    Component.onCompleted: plot.setProgramFile(root.viewModel.programFile)
                }

                // what is going on: the operation, the line, the tool
                Column {
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.topMargin: Theme.zoomInOutFitMirrorButtonMarginTop + Theme.zoomInOutFitMirrorButtonSize + Theme.spacing
                    // in from the ruler the plot draws round its edge
                    anchors.rightMargin: Theme.spacingLarge + 32
                    spacing: 2
                    visible: root.viewModel.ready

                    Text {
                        anchors.right: parent.right
                        text: root.viewModel.operation
                        color: Theme.foreground
                        font.pixelSize: Theme.fontBody
                        font.bold: true
                    }
                    Text {
                        anchors.right: parent.right
                        text: "Line " + root.viewModel.programLine
                              + (root.viewModel.tool ? "   T" + root.viewModel.tool : "")
                        color: Theme.foregroundMuted
                        font.pixelSize: Theme.fontSmall
                    }
                    Text {
                        anchors.right: parent.right
                        visible: root.viewModel.collisions.length > 0
                        text: root.viewModel.collisions.length === 1 ? "1 rapid through the material"
                                                                    : root.viewModel.collisions.length + " rapids through the material"
                        color: root.collisionColor
                        font.pixelSize: Theme.fontSmall
                        font.bold: true
                    }
                }

                // waiting at a stop for Cycle Start
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: Theme.spacingLarge
                    visible: root.viewModel.state === "waiting"
                    width: waitText.implicitWidth + 2 * Theme.spacingLarge
                    height: waitText.implicitHeight + 2 * Theme.spacing
                    radius: Theme.radius
                    color: "#fff3e0"
                    border.color: Theme.warning
                    border.width: Theme.hairline

                    Text {
                        id: waitText
                        anchors.centerIn: parent
                        text: root.viewModel.waitingFor + ": press Cycle Start to go on"
                        color: Theme.foreground
                        font.pixelSize: Theme.fontBody
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: root.viewModel.loading
                    text: "Reading the program as the machine would run it…"
                    color: Theme.foregroundMuted
                    font.pixelSize: Theme.fontBody
                }

                // why there is no run, or why it stops short
                Rectangle {
                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    anchors.margins: Theme.spacingLarge
                    visible: root.viewModel.error !== ""
                    width: Math.min(errorText.implicitWidth + 2 * Theme.spacing, parent.width - 2 * Theme.spacingLarge)
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
                        text: root.viewModel.error
                        color: Theme.foreground
                        font.pixelSize: Theme.fontSmall
                        wrapMode: Text.Wrap
                    }
                }
            }

            // the timeline, and how the run plays, in a box of their own
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: timeline.implicitHeight + 2 * Theme.spacingSmall
                color: Theme.surfaceSunken
                radius: Theme.radius
                border.color: Theme.outline
                border.width: Theme.hairline

                ColumnLayout {
                    id: timeline
                    anchors.fill: parent
                    anchors.margins: Theme.spacingSmall
                    spacing: Theme.spacingSmall

                    SimulateSeekBar {
                        Layout.fillWidth: true
                        duration: root.viewModel.duration
                        time: root.viewModel.time
                        marks: root.viewModel.marks
                        collisions: root.viewModel.collisions
                        seekable: root.viewModel.ready && !root.moving
                        onSeekRequested: function(time) { root.viewModel.seek(time) }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacing

                        LedToggleButton {
                            text: "Break on M1"
                            enabled: !root.moving
                            checked: root.viewModel.optionalStop
                            onClicked: root.viewModel.setOptionalStop(!checked)
                        }

                        Item { Layout.fillWidth: true }

                        Text {
                            text: root.clock(root.viewModel.time) + " / " + root.clock(root.viewModel.duration)
                                  + (root.viewModel.ready && !root.viewModel.timed ? "  (not timed)" : "")
                            color: Theme.foreground
                            font.pixelSize: Theme.fontBody
                            font.bold: true
                        }

                        Repeater {
                            model: root.viewModel.speeds
                            delegate: ProgramButton {
                                implicitWidth: 72
                                text: modelData + "×"
                                active: root.viewModel.speed === modelData
                                onClicked: root.viewModel.setSpeed(modelData)
                            }
                        }
                    }
                }
            }
        }
    }
}
