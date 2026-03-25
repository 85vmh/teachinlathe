import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    color: "#f5f5f5"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ProgramsScreenTabs {
            Layout.fillWidth: true
            Layout.preferredHeight: 58
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: programsViewModel.screenIndex

            ProgramsFilesScreen {
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
}
