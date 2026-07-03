import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Rectangle {
    color: "#1e1e1e"

    property string fileContent: ""
    property string filePath:    ""

    Connections {
        target: fsBridge
        function onFileContentChanged(content) { fileContent = content }
        function onFilePathChanged(path)        { filePath   = path   }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Toolbar
        Rectangle {
            Layout.fillWidth: true
            height: 44
            color: "#2d2d2d"

            RowLayout {
                anchors { fill: parent; leftMargin: 8; rightMargin: 12 }
                spacing: 10

                // Back to files button
                Rectangle {
                    width: 110; height: 30; radius: 4
                    color: backArea.pressed ? "#444444" : "#3a3a3a"

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 6
                        Text { text: "←"; color: "#cccccc"; font.pixelSize: 16 }
                        Text { text: "Files"; color: "#cccccc"; font.pixelSize: 13 }
                    }

                    MouseArea {
                        id: backArea
                        anchors.fill: parent
                        onClicked: fsBridge.navigateTo(ProgramsScreen.Files)
                    }
                }

                Text {
                    text: filePath !== "" ? filePath : "No file loaded"
                    color: "#aaaaaa"
                    font.pixelSize: 12
                    elide: Text.ElideLeft
                    Layout.fillWidth: true
                }
            }
        }

        CodeViewer {
            Layout.fillWidth: true
            Layout.fillHeight: true
            fileContent: fileContent
            emptyText: "No file loaded in machine"
        }
    }
}
