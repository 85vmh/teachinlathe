import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "filesystemview"

Rectangle {
    id: root
    color: "#f5f5f5"

    // While running, the view is full screen (no app bar / bottom tabs) and the
    // internal screen tabs are hidden — only the loaded-program content shows.
    readonly property bool running: programsViewModel.screenIndex === ProgramsScreen.Running

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: root.running ? 0 : 8
            Layout.rightMargin: root.running ? 0 : 8
            Layout.topMargin: root.running ? 0 : 8
            Layout.bottomMargin: root.running ? 0 : 8
            // Running reuses the loaded-program page (index clamped to Loaded).
            currentIndex: root.running ? ProgramsScreen.Loaded : programsViewModel.screenIndex

            ProgramsFileSystemScreen {
                Layout.fillWidth: true
                Layout.fillHeight: true
                viewModel: programsViewModel
                fileSystemViewModel: fsViewModel
            }

            ProgramsGremlinScreen {
                Layout.fillWidth: true
                Layout.fillHeight: true
                viewModel: programsViewModel
            }
        }
    }

    ProgramCompleteDialog {
        id: completeDialog
        objectName: "programCompleteDialog"
    }
}
