import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var viewModel
    property string mode: "files"

    color: "#f0f0f0"
    border.color: "#cccccc"
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 12
        anchors.topMargin: 7
        anchors.bottomMargin: 7
        spacing: 8

        Text {
            Layout.fillWidth: true
            text: viewModel ? viewModel.currentFileDisplayPath : "No file loaded"
            color: "#4f4f4f"
            font.pixelSize: 13
            elide: Text.ElideLeft
            verticalAlignment: Text.AlignVCenter
        }

        ProgramButton {
            text: viewModel && viewModel.editMode ? "Preview" : "Edit"
            enabled: !!viewModel
            onClicked: viewModel.toggleEditMode()
        }

        ProgramButton {
            text: "Save"
            enabled: !!viewModel
            onClicked: viewModel.saveCurrentFile()
        }

        ProgramButton {
            text: "Save As"
            enabled: !!viewModel
            onClicked: viewModel.saveCurrentFileAs()
        }


        ProgramButton {
            visible: mode === "files"
            text: "Open in Machine"
            enabled: !!viewModel && viewModel.hasCurrentFile
            onClicked: viewModel.openCurrentFileInMachine()
        }
    }
}
