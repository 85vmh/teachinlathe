import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.programs.filesystemview
import tabs.programs.gcode_viewer
import tabs.programs.program_loaded
import theme
import TeachInLathe

// The Programs tab is one strip of three equal panes, two of them on screen:
//
//     [ file system | program code | backplot ]
//
// The files screen shows the first two, the loaded-program screen the last
// two. Loading a program pushes the strip one pane to the left - the files
// slide out, the code moves from the right half to the left, the backplot
// comes in on the right - and going back pushes it the other way. The code
// pane is the same one on both screens, so it is the one thing that moves
// across rather than being swapped; on the loaded-program screen it carries
// the DRO and tool/feed/speed over the code.
//
Rectangle {
    id: root
    color: Theme.surface

    readonly property var viewModel: ProgramsViewModel

    // How long the strip takes to slide one pane across, in ms.
    readonly property int slideDurationMs: 300
    // How long the DRO row and the bottom bar take to come in over and under
    // the code once the strip has slid (and to go, before it slides back), in ms.
    readonly property int revealDurationMs: 150
    // How long the tab must have been on screen before a screen switch
    // animates, in ms; see _animate below.
    readonly property int settleDelayMs: 200

    // While running, the view is full screen (no app bar / bottom tabs) and
    // the internal screen tabs are hidden — only the loaded-program content shows.
    readonly property bool running: root.viewModel.running
    readonly property bool programShown: root.viewModel.programShown

    // Panes are separated by the gap the split views had as their handle.
    readonly property real gap: 6
    readonly property real paneWidth: Math.max(0, (width - gap) / 2)
    readonly property real stride: paneWidth + gap

    // 0: files + code on screen; 1: code + backplot.
    property real offset: programShown ? 1 : 0
    // How far the DRO row and the code's bottom bar are in, 0..1. On the way
    // to the loaded program they come in after the slide; on the way back
    // they go first.
    property real reveal: programShown ? 1 : 0
    // How far the bar under the code reaches across under the backplot, 0..1:
    // all the way while a program runs, with Cycle Abort and Feed Hold at its
    // end.
    property real runBar: running ? 1 : 0
    Behavior on runBar {
        enabled: root._animate
        NumberAnimation { duration: 300; easing.type: Easing.OutCubic }
    }
    // The bar's height, and the gap above it - the code pane leaves that room.
    readonly property int barHeight: Theme.barHeight
    readonly property int barGap: 6
    // The DRO row's height, and the gap between it and the code.
    readonly property int droRowHeight: 220
    readonly property int droRowGap: Theme.spacingSmall

    // Only a switch made while this tab is already on screen animates: one
    // that arrives with the tab - the conversational screen opening a
    // generated program, say - lands in place. Becoming visible arms the
    // animation only once the tab has been up for a moment.
    property bool _animate: false
    onVisibleChanged: {
        _animate = false
        if (visible) settleTimer.restart()
    }
    Component.onCompleted: {
        // From here on offset and reveal are driven, not bound.
        offset = programShown ? 1 : 0
        reveal = offset
        if (visible) settleTimer.restart()
    }
    Timer {
        id: settleTimer
        interval: root.settleDelayMs
        onTriggered: root._animate = root.visible
    }

    onProgramShownChanged: {
        showProgram.stop()
        showFiles.stop()
        if (!_animate) {
            offset = programShown ? 1 : 0
            reveal = offset
        } else if (programShown) {
            // Each phase takes its share of the time it has left to go, so
            // one already done - after reversing mid-way - adds no pause.
            slideIn.duration = slideDurationMs * Math.abs(1 - offset)
            revealIn.duration = revealDurationMs * Math.abs(1 - reveal)
            showProgram.start()
        } else {
            revealOut.duration = revealDurationMs * Math.abs(reveal)
            slideOut.duration = slideDurationMs * Math.abs(offset)
            showFiles.start()
        }
    }

    // Each starts from wherever the other left off, so reversing mid-way
    // goes back the way it came.
    SequentialAnimation {
        id: showProgram
        NumberAnimation {
            id: slideIn
            target: root; property: "offset"; to: 1
            easing.type: Easing.InOutCubic
        }
        NumberAnimation {
            id: revealIn
            target: root; property: "reveal"; to: 1
            easing.type: Easing.OutCubic
        }
    }
    SequentialAnimation {
        id: showFiles
        NumberAnimation {
            id: revealOut
            target: root; property: "reveal"; to: 0
            easing.type: Easing.InCubic
        }
        NumberAnimation {
            id: slideOut
            target: root; property: "offset"; to: 0
            easing.type: Easing.InOutCubic
        }
    }

    Item {
        anchors.fill: parent
        clip: true

        FileSystemView {
            viewModel: root.viewModel.fileSystem
            x: -root.offset * root.stride
            width: root.paneWidth
            height: parent.height
            // off screen once the program is shown
            visible: root.offset < 1
        }

        // The code, with the DRO and tool/feed/speed over it on the
        // loaded-program screen; on the files screen, the code alone.
        Rectangle {
            id: codeColumn
            x: (1 - root.offset) * root.stride
            width: root.paneWidth
            height: parent.height
            color: Theme.surfaceSunken

            ColumnLayout {
                anchors.fill: parent
                spacing: 0   // the DRO slot carries its own gap

                // The DRO row comes down from the top edge, pushing the code
                // down: it sits at the bottom of a slot that grows from nothing.
                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: (root.droRowHeight + root.droRowGap) * root.reveal
                    visible: root.reveal > 0
                    clip: true

                    RowLayout {
                        y: parent.height - root.droRowHeight - root.droRowGap
                        width: parent.width
                        height: root.droRowHeight
                        spacing: Theme.spacingSmall

                        ProgramsDro {
                            Layout.fillHeight: true
                            Layout.preferredWidth: 600
                            viewModel: root.viewModel.dro
                        }

                        ProgramsToolFeedSpeed {
                            Layout.fillHeight: true
                            Layout.fillWidth: true
                            viewModel: root.viewModel.toolFeedSpeed
                        }
                    }
                }

                GCodeViewerPane {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    viewModel: root.viewModel
                    actionBarReveal: root.reveal
                }
            }
        }

        ProgramLoadedScreen {
            viewModel: root.viewModel
            x: (2 - root.offset) * root.stride
            width: root.paneWidth
            height: parent.height
            // off screen on the files screen; the backplot need not render there
            visible: root.offset > 0
            shown: root.programShown
            runBarReveal: root.runBar
            z: 1
        }

        // Under the code, coming up from below as the code makes room for it;
        // while a program runs it widens to the right across the backplot's
        // pane as well.
        ProgramBottomActionBar {
            viewModel: root.viewModel
            x: codeColumn.x
            y: parent.height - (root.barHeight + root.barGap) * root.reveal + root.barGap
            width: root.paneWidth + root.stride * root.runBar
            height: root.barHeight
            visible: root.reveal > 0
            runControlsReveal: root.runBar
            z: 2
        }
    }
}
