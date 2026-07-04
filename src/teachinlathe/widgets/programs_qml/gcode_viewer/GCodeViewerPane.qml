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

    readonly property int currentMode: viewModel && viewModel.hasExecutionStack
        ? GCodeViewerPane.ProgramWithStack
        : GCodeViewerPane.ProgramWithoutStack
    readonly property bool actionBarVisible: !!viewModel
        && viewModel.screenIndex !== ProgramsScreen.Files

    color: "#ffffff"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Loader {
            Layout.fillWidth: true
            Layout.fillHeight: true
            sourceComponent: root.currentMode === GCodeViewerPane.ProgramWithStack
                ? executionComponent
                : viewerComponent
        }

        ProgramBottomActionBar {
            Layout.fillWidth: true
            visible: root.actionBarVisible
            Layout.preferredHeight: visible ? 90 : 0
            viewModel: root.viewModel
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
                highlightLine: viewModel ? viewModel.mainHighlightLine : 0
                highlightColor: "#3A86FF"
                highlightWidth: 1
                centerOnHighlight: false
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
