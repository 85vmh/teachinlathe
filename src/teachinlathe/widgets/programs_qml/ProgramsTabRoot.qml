import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "filesystemview"

Rectangle {
    id: root
    color: "#ffffff"

    // While running, the view is full screen (no app bar / bottom tabs) and the
    // internal screen tabs are hidden — only the loaded-program content shows.
    readonly property bool running: programsViewModel.screenIndex === ProgramsScreen.Running

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 0
            Layout.rightMargin: 0
            Layout.topMargin: 0
            Layout.bottomMargin: 0
            // Running reuses the loaded-program page (index clamped to Loaded).
            currentIndex: root.running ? ProgramsScreen.Loaded : programsViewModel.screenIndex

            MachineFileSystemScreen {
                Layout.fillWidth: true
                Layout.fillHeight: true
                viewModel: programsViewModel
                fileSystemViewModel: fsViewModel
            }

            ProgramLoadedScreen {
                Layout.fillWidth: true
                Layout.fillHeight: true
                viewModel: programsViewModel
            }
        }
    }

}
