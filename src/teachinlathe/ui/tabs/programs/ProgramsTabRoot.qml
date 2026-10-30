import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.programs.filesystemview
import tabs.programs.simulate
import tabs.programs.gcode_viewer
import tabs.programs.program_loaded
import theme
import TeachInLathe

// The Programs tab is one strip of panes:
//
//     files screen:            [ file system 35% | code 30% | the part 35% ]
//     loaded-program screen:   [ code 30% | backplot - the rest ]
//
// Loading a program slides the strip to the left - the files go out, the code
// moves to the left edge, and the pane on its right widens to take the room
// they leave - and then what it showed (FinalProfileView: the stock, and what
// is left of it once the program has run) gives way to the backplot. Going back
// does the same the other way. A simulation slides the same: once the strip has
// slid, the Simulate screen - laid out as the loaded program is - comes in over
// it, where the loaded program's DRO and backplot would, and goes first on the
// way back. The code pane is the same one on both screens,
// so it is the one thing that moves across rather than being swapped; on the
// loaded-program screen it carries the DRO over the code. The part's pane -
// the stock above, the part below - has the Simulate button between the two.
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
    readonly property bool simulateShown: root.viewModel.simulateShown
    // The strip slides the same way to either screen of a file: the loaded
    // program, or its simulation. Which it is going to - or coming back from -
    // says what comes in once it has slid (programReveal, simulateReveal).
    readonly property bool stripShown: programShown || simulateShown
    property bool toSimulate: simulateShown
    onSimulateShownChanged: if (simulateShown) toSimulate = true
    onProgramShownChanged: if (programShown) toSimulate = false

    // Panes are separated by the gap the split views had as their handle.
    readonly property real gap: 6
    // What the code takes of the width the gaps leave on the files screen;
    // the file system and the part share the rest equally. The code keeps its
    // width on the loaded-program screen, the backplot takes the rest there.
    readonly property real codeShare: 0.3
    readonly property real filesShare: (1 - codeShare) / 2
    readonly property real filesWidth: Math.max(0, width - 2 * gap) * filesShare
    readonly property real codeWidth: Math.max(0, width - 2 * gap) * codeShare
    // the code pane's left edge: right of the files, to the left edge
    readonly property real codeX: (1 - offset) * (filesWidth + gap)
    // the pane right of the code - the part, then the backplot - to the right edge
    readonly property real rightX: codeX + codeWidth + gap
    readonly property real rightWidth: Math.max(0, width - rightX)

    // 0: files + code + the part on screen; 1: code + backplot.
    property real offset: stripShown ? 1 : 0
    // How far the screen the strip went to is in, 0..1. On the way to it, it
    // comes in after the slide; on the way back it goes first.
    property real reveal: stripShown ? 1 : 0
    // the loaded program's DRO, code bar and backplot
    readonly property real programReveal: toSimulate ? 0 : reveal
    // the Simulate screen, over the strip: laid out as the loaded program is
    readonly property real simulateReveal: toSimulate ? reveal : 0
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
    // The DRO's height, and the gap between it and the code.
    readonly property int droRowHeight: dro.implicitHeight
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
        offset = stripShown ? 1 : 0
        reveal = offset
        if (visible) settleTimer.restart()
    }
    Timer {
        id: settleTimer
        interval: root.settleDelayMs
        onTriggered: root._animate = root.visible
    }

    onStripShownChanged: {
        showProgram.stop()
        showFiles.stop()
        if (!_animate) {
            offset = stripShown ? 1 : 0
            reveal = offset
        } else if (stripShown) {
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
            x: -root.offset * (root.filesWidth + root.gap)
            width: root.filesWidth
            height: parent.height
            // off screen once the program is shown
            visible: root.offset < 1
        }

        // The code, with the DRO over it on the loaded-program screen; on
        // the files screen, the code alone.
        Rectangle {
            id: codeColumn
            x: root.codeX
            width: root.codeWidth
            height: parent.height
            color: Theme.surfaceSunken

            ColumnLayout {
                anchors.fill: parent
                spacing: 0   // the DRO slot carries its own gap

                // The DRO comes down from the top edge, pushing the code
                // down: it sits at the bottom of a slot that grows from nothing.
                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: (root.droRowHeight + root.droRowGap) * root.programReveal
                    visible: root.programReveal > 0
                    clip: true

                    ProgramsDro {
                        id: dro
                        y: parent.height - root.droRowHeight - root.droRowGap
                        width: parent.width
                        height: root.droRowHeight
                        viewModel: root.viewModel.dro
                    }
                }

                GCodeViewerPane {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    viewModel: root.viewModel
                    actionBarReveal: root.programReveal
                }
            }
        }

        // The part the file shown makes, right of the code; it widens with
        // the slide and gives way to the backplot.
        FinalProfileView {
            x: root.rightX
            width: root.rightWidth
            height: parent.height
            profile: root.viewModel.finalProfile
            simulateEnabled: root.viewModel.simulateAvailable
            onSimulateRequested: root.viewModel.startSimulation()
            opacity: 1 - root.reveal
            visible: opacity > 0
        }

        // In once the slide is done, over the part: the backplot is not
        // resized - its framebuffer made again - at every step of the slide.
        ProgramLoadedScreen {
            viewModel: root.viewModel
            x: root.rightX
            width: root.rightWidth
            height: parent.height
            opacity: root.programReveal
            visible: root.programReveal > 0
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
            y: parent.height - (root.barHeight + root.barGap) * root.programReveal + root.barGap
            width: root.codeWidth + (root.width - root.codeWidth) * root.runBar
            height: root.barHeight
            visible: root.programReveal > 0
            runControlsReveal: root.runBar
            z: 2
        }
    }

    // A file played as the machine would run it: over the strip once it has
    // slid as it does to the loaded program, which it is laid out as - it
    // comes in where the loaded program's DRO and backplot would
    SimulateScreen {
        anchors.fill: parent
        viewModel: root.viewModel.simulate
        opacity: root.simulateReveal
        visible: root.simulateReveal > 0
        z: 3
    }
}
