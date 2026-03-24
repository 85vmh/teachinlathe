import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var viewModel
    color: "#f0f0f0"
    border.color: "#cccccc"
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        spacing: 12

        Text {
            text: "Programs"
            color: "#202020"
            font.pixelSize: 20
            font.bold: true
        }

        Item { Layout.fillWidth: true }

        ProgramButton {
            text: "Files"
            active: viewModel && viewModel.screenIndex === 0
            onClicked: viewModel.showFilesScreen()
        }

        ProgramButton {
            text: "Gremlin"
            active: viewModel && viewModel.screenIndex === 1
            onClicked: viewModel.showGremlinScreen()
        }
    }
}
