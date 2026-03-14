import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Item {
    id: root

    property string selectedFolder: ""
    property string selectedFile: ""
    property var currentFiles: []

    Connections {
        target: fsBridge

        function onFolderFilesChanged(folderName) {
            if (root.selectedFolder === folderName) {
                root.currentFiles = fsBridge.getFiles(folderName)
            }
        }

        function onFilePathChanged(path) {
            var normalized = path.replace(/\\/g, "/")
            for (var i = 0; i < fsBridge.folderNames.length; ++i) {
                var folderName = fsBridge.folderNames[i]
                var folderPath = fsBridge.getFolderPath(folderName).replace(/\\/g, "/")
                if (normalized.indexOf(folderPath + "/") === 0) {
                    root.selectedFolder = folderName
                    root.currentFiles = fsBridge.getFiles(folderName)
                    root.selectedFile = normalized.substring(folderPath.length + 1)
                    return
                }
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#252526"

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                height: 44
                color: "#1e1e1e"

                Text {
                    anchors.centerIn: parent
                    text: "Programs"
                    color: "#cccccc"
                    font.pixelSize: 16
                    font.bold: true
                }
            }

            Repeater {
                model: fsBridge.folderNames
                delegate: Rectangle {
                    Layout.fillWidth: true
                    height: 48
                    color: root.selectedFolder === modelData
                           ? "#37373d" : (folderArea.containsMouse ? "#2d2d2e" : "#252526")

                    RowLayout {
                        anchors {
                            fill: parent
                            leftMargin: 14
                            rightMargin: 8
                        }
                        spacing: 10

                        Text { text: "📁"; font.pixelSize: 18 }

                        Text {
                            text: modelData
                            color: "#d4d4d4"
                            font.pixelSize: 14
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }

                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 1
                        color: "#333333"
                    }

                    MouseArea {
                        id: folderArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            root.selectedFolder = modelData
                            root.selectedFile = ""
                            root.currentFiles = fsBridge.getFiles(modelData)
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: "#404040"
            }

            ListView {
                id: fileList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: root.currentFiles

                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                delegate: Rectangle {
                    width: ListView.view.width
                    height: 38
                    color: root.selectedFile === modelData
                           ? "#094771"
                           : (fileArea.containsMouse ? "#2a2d2e" : "transparent")

                    Text {
                        anchors {
                            verticalCenter: parent.verticalCenter
                            left: parent.left
                            leftMargin: 16
                            right: parent.right
                            rightMargin: 8
                        }
                        text: modelData
                        color: "#d4d4d4"
                        font.pixelSize: 13
                        font.family: "monospace"
                        elide: Text.ElideLeft
                    }

                    MouseArea {
                        id: fileArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            root.selectedFile = modelData
                            fsBridge.selectFile(root.selectedFolder, modelData)
                        }
                        onDoubleClicked: {
                            root.selectedFile = modelData
                            fsBridge.openFile(root.selectedFolder, modelData)
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: root.currentFiles.length === 0
                    text: root.selectedFolder === ""
                          ? "Select a folder above"
                          : "No G-code files found"
                    color: "#555555"
                    font.pixelSize: 13
                }
            }
        }
    }
}
