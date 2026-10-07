import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "filesystemview"
import "gcode_viewer"
import theme 1.0

// The Programs tab is one strip of three equal panes, two of them on screen:
//
//     [ file system | program code | DRO + backplot ]
//
// The files screen shows the first two, the loaded-program screen the last
// two. Loading a program pushes the strip one pane to the left - the files
// slide out, the code moves from the right half to the left, the backplot
// comes in on the right - and going back pushes it the other way. The code
// pane is the same one on both screens, so it is the one thing that moves
// across rather than being swapped.
Rectangle {
    id: root
    color: Theme.surface

    // How long the strip takes to slide one pane across, in ms.
    readonly property int slideDurationMs: 300
    // How long the tab must have been on screen before a screen switch
    // animates, in ms; see _animate below.
    readonly property int settleDelayMs: 200

    // While running, the view is full screen (no app bar / bottom tabs) and
    // the internal screen tabs are hidden — only the loaded-program content shows.
    readonly property bool running: programsViewModel.screenIndex === ProgramsScreen.Running
    readonly property bool programShown: programsViewModel.screenIndex !== ProgramsScreen.Files

    // Panes are separated by the gap the split views had as their handle.
    readonly property real gap: 6
    readonly property real paneWidth: Math.max(0, (width - gap) / 2)
    readonly property real stride: paneWidth + gap

    // 0: files + code on screen; 1: code + DRO/backplot. Animated between.
    property real offset: programShown ? 1 : 0

    // Only a switch made while this tab is already on screen animates: one
    // that arrives with the tab - the conversational screen opening a
    // generated program, say - lands in place. Becoming visible arms the
    // animation only once the tab has been up for a moment.
    property bool _animate: false
    onVisibleChanged: {
        _animate = false
        if (visible) settleTimer.restart()
    }
    Component.onCompleted: if (visible) settleTimer.restart()
    Timer {
        id: settleTimer
        interval: root.settleDelayMs
        onTriggered: root._animate = root.visible
    }

    Behavior on offset {
        enabled: root._animate
        NumberAnimation { duration: root.slideDurationMs; easing.type: Easing.InOutCubic }
    }

    Item {
        anchors.fill: parent
        clip: true

        FileSystemView {
            viewModel: fsViewModel
            x: -root.offset * root.stride
            width: root.paneWidth
            height: parent.height
            // off screen once the program is shown
            visible: root.offset < 1
        }

        GCodeViewerPane {
            id: codePane
            viewModel: programsViewModel
            x: (1 - root.offset) * root.stride
            width: root.paneWidth
            height: parent.height
        }

        ProgramLoadedScreen {
            viewModel: programsViewModel
            x: (2 - root.offset) * root.stride
            width: root.paneWidth
            height: parent.height
            // off screen on the files screen; the backplot need not render there
            visible: root.offset > 0
            shown: root.programShown
            // its toasts centre over the code pane, one stride to its left
            codePaneX: -root.stride
            codePaneWidth: root.paneWidth
            z: 1
        }
    }
}
