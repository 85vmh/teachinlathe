import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.programs
import tabs.programs.gcode_viewer.while_running
import theme

Rectangle {
    id: root

    enum ViewerMode { ProgramWithoutStack, ProgramWithStack }

    required property var viewModel
    required property var run
    property var simulationViewModel: null
    property bool simulation: false

    readonly property bool executionHighlightVisible: viewModel.executionHighlightVisible
    readonly property int currentMode: viewModel.hasExecutionStack
        ? GCodeViewerPane.ProgramWithStack
        : GCodeViewerPane.ProgramWithoutStack
    // How much of the bottom action bar is in, 0..1: it rises from the
    // bottom edge, pushing the code up. ProgramsTabRoot animates this and
    // draws the bar itself - it reaches past this pane while a program runs -
    // so here there is only the room it takes.
    property real actionBarReveal: 0
    property int actionBarHeight: Theme.barHeight
    readonly property int actionBarGap: 6

    color: "#ffffff"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Loader {
                anchors.fill: parent
                sourceComponent: !root.simulation && root.currentMode === GCodeViewerPane.ProgramWithStack
                    ? executionComponent
                    : viewerComponent
            }
        }

        // Where the bar comes up from below.
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: (root.actionBarHeight + root.actionBarGap) * root.actionBarReveal
            visible: root.actionBarReveal > 0
        }
    }

    Component {
        id: viewerComponent

        ProgramContentFrame {
            filePath: root.simulation ? root.simulationViewModel.programFile : viewModel.currentFilePath
            Layout.fillWidth: true
            Layout.fillHeight: true

            GCodeTextArea {
                Layout.fillWidth: true
                Layout.fillHeight: true
                viewModel: root.simulation ? root.simulationViewModel : root.viewModel
                content: root.simulation ? root.simulationViewModel.content : viewModel.currentFileContent
                highlightLine: root.simulation
                               ? (root.simulationViewModel.ready ? root.run.programLine : 0)
                               : (root.executionHighlightVisible && viewModel.mainHighlightLine)
                highlightColor: "#3A86FF"
                highlightWidth: 1
                centerOnHighlight: root.simulation || root.executionHighlightVisible
                followUserScroll: root.simulation && root.simulationViewModel.ready
                onLineScrolledTo: function(line) {
                    if (root.simulation)
                        root.run.seekToLine(line)
                }
                emptyText: "Select a G-code file"
            }
        }
    }

    Component {
        id: executionComponent

        ProgramExecutionStack {
            viewModel: root.viewModel
            // With the bar's own gap, the backplot's gap above the run bar.
            bottomPadding: Math.max(0, Theme.spacingSmall - root.actionBarGap * root.actionBarReveal)
        }
    }
}
