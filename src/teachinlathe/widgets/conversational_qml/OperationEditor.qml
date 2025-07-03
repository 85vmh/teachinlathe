import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: operationEditor
    property var selectedProgram: null
    property alias title: lblTitle.text

    width: parent ? parent.width : 600
    height: parent ? parent.height : 400

    property string lblTitle: selectedProgram ? "Edit: " + selectedProgram.programName : "New Program"

    RowLayout {
        anchors.fill: parent
        spacing: 12
        padding: 12

        // Left pane: list of operations (dummy for now)
        ListView {
            id: operationsList
            width: parent.width * 0.4
            model: selectedProgram ? selectedProgram.operations : []
            delegate: Item {
                width: parent.width
                height: 40
                Rectangle {
                    anchors.fill: parent
                    color: ListView.isCurrentItem ? "#d1c4e9" : "transparent"
                    border.color: "#673ab7"
                    border.width: ListView.isCurrentItem ? 2 : 0

                    Text {
                        text: modelData
                        anchors.centerIn: parent
                        color: "#212121"
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: operationsList.currentIndex = index
                }
            }
        }

        // Right pane: details of selected operation
        Rectangle {
            id: detailPane
            width: parent.width * 0.6
            color: "#f5f5f5"
            radius: 6
            border.color: "#ccc"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                Label {
                    text: selectedProgram ? selectedProgram.programName : "No program selected"
                    font.pixelSize: 20
                    font.bold: true
                    color: "#212121"
                }

                // Here you can add form fields for the operation's details, eg:
                // TextFields, ComboBoxes, etc.

                TextField {
                    placeholderText: "Operation name"
                    // Bind to selected operation's data
                }

                // Add more UI as needed
            }
        }
    }
}
