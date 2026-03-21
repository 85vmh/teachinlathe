import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    color: "#181818"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ProgramsScreenTabs {
            Layout.fillWidth: true
            Layout.preferredHeight: 58
            viewModel: programsViewModel
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: programsViewModel.screenIndex

            ProgramsFilesScreen {
                Layout.fillWidth: true
                Layout.fillHeight: true
                viewModel: programsViewModel
            }

            ProgramsGremlinScreen {
                Layout.fillWidth: true
                Layout.fillHeight: true
                viewModel: programsViewModel
            }
        }

        ProgramActionBar {
            Layout.fillWidth: true
            Layout.preferredHeight: 180
            viewModel: programsViewModel
        }
    }
}
