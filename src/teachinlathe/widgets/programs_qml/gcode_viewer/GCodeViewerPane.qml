import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../program_loaded"
import "while_running"

Rectangle {
    id: root

    enum ViewerMode { ProgramWithoutStack, ProgramWithStack }

    property var viewModel

    readonly property bool executionHighlightVisible: !!viewModel && viewModel.executionHighlightVisible
    readonly property int currentMode: viewModel && viewModel.hasExecutionStack
        ? GCodeViewerPane.ProgramWithStack
        : GCodeViewerPane.ProgramWithoutStack
    readonly property bool actionBarVisible: !!viewModel
        && viewModel.screenIndex !== ProgramsScreen.Files
    // How much of the bottom action bar is in, 0..1: it rises from the
    // bottom edge, pushing the code up. ProgramsTabRoot animates this; left
    // alone it just follows actionBarVisible.
    property real actionBarReveal: actionBarVisible ? 1 : 0
    readonly property int actionBarHeight: 90
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
                sourceComponent: root.currentMode === GCodeViewerPane.ProgramWithStack
                    ? executionComponent
                    : viewerComponent
            }
        }

        // The bar sits at the top of a slot that grows from nothing, so it
        // comes up from below rather than unfolding.
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: (root.actionBarHeight + root.actionBarGap) * root.actionBarReveal
            visible: root.actionBarReveal > 0
            clip: true

            ProgramBottomActionBar {
                y: root.actionBarGap
                width: parent.width
                height: root.actionBarHeight
                viewModel: root.viewModel
            }
        }
    }

    Component {
        id: viewerComponent

        ProgramContentFrame {
            filePath: viewModel ? viewModel.currentFilePath : ""
            Layout.fillWidth: true
            Layout.fillHeight: true

            GCodeTextArea {
                Layout.fillWidth: true
                Layout.fillHeight: true
                viewModel: root.viewModel
                content: viewModel ? viewModel.currentFileContent : ""
                highlightLine: root.executionHighlightVisible && viewModel ? viewModel.mainHighlightLine : 0
                highlightColor: "#3A86FF"
                highlightWidth: 1
                centerOnHighlight: root.executionHighlightVisible
                emptyText: "Select a G-code file"
            }
        }
    }

    Component {
        id: executionComponent

        ProgramExecutionStack {
            viewModel: root.viewModel
        }
    }
}
