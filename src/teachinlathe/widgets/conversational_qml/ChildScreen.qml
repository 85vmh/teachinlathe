import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: operationEditor
    objectName: "childScreen"

    // Inputs
    property var selectedProgram: null

    // Navigation
    property bool showBack: true
    signal backRequested()

    width: parent ? parent.width : 800
    height: parent ? parent.height : 600

    // Title text
    property string titleText: selectedProgram ? "Edit: " + selectedProgram.programName : "New Program"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Button {
                text: "Back"
                visible: operationEditor.showBack
                onClicked: operationEditor.backRequested()
            }

            Label {
                text: operationEditor.titleText
                font.pixelSize: 22
                font.bold: true
                Layout.fillWidth: true
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            // Left: operations list (dummy binding)
            ListView {
                id: operationsList
                Layout.preferredWidth: Math.round(parent.width * 0.4)
                Layout.fillHeight: true
                model: selectedProgram && selectedProgram.operations ? selectedProgram.operations : []

                delegate: Item {
                    width: ListView.view ? ListView.view.width : 200
                    height: 40

                    Rectangle {
                        anchors.fill: parent
                        color: ListView.isCurrentItem ? "#d1c4e9" : "transparent"
                        border.color: "#673ab7"
                        border.width: ListView.isCurrentItem ? 2 : 1
                        radius: 4

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

            // Right: details
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
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
                        font.pixelSize: 18
                        font.bold: true
                    }

                    TextField {
                        placeholderText: "Operation name"
                    }
                }
            }
        }
    }
}
