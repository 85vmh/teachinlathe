import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var viewModel
    property string selectedFolder: ""
    property string currentPath: ""
    property string selectedFilePath: ""
    property var currentFiles: []

    color: "#252526"

    function normalizePath(path) {
        return (path || "").replace(/\\/g, "/")
    }

    function refreshEntries() {
        if (!viewModel || selectedFolder === "") {
            currentFiles = []
            return
        }
        currentFiles = viewModel.getFilesInPath(selectedFolder, currentPath)
    }

    Connections {
        target: viewModel

        function onCurrentFilePathChanged(path) {
            var normalized = root.normalizePath(path)
            for (var i = 0; i < viewModel.folderNames.length; ++i) {
                var folderName = viewModel.folderNames[i]
                var folderPath = root.normalizePath(viewModel.getFolderPath(folderName))
                if (normalized.indexOf(folderPath + "/") === 0) {
                    root.selectedFolder = folderName
                    root.selectedFilePath = normalized.substring(folderPath.length + 1)
                    var segments = root.selectedFilePath.split("/")
                    if (segments.length > 1) {
                        segments.pop()
                        root.currentPath = segments.join("/")
                    } else {
                        root.currentPath = ""
                    }
                    root.refreshEntries()
                    return
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 52
            color: "#1e1e1e"

            Text {
                anchors.centerIn: parent
                text: "Program Files"
                color: "#e8e8e8"
                font.pixelSize: 17
                font.bold: true
            }
        }

        Repeater {
            model: viewModel ? viewModel.folderNames : []

            delegate: Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                color: root.selectedFolder === modelData
                       ? "#37373d" : (folderArea.containsMouse ? "#2d2d2e" : "#252526")

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 14
                    anchors.right: parent.right
                    anchors.rightMargin: 8
                    text: modelData
                    color: "#d4d4d4"
                    font.pixelSize: 14
                    elide: Text.ElideRight
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
                        root.currentPath = ""
                        root.selectedFilePath = ""
                        root.refreshEntries()
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
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
                height: 40
                color: (!modelData.isDir && root.selectedFilePath === modelData.path)
                       ? "#094771"
                       : (fileArea.containsMouse ? "#2a2d2e" : "transparent")

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 8
                    spacing: 8

                    Text {
                        text: modelData.isDir ? (modelData.isUp ? "UP" : "DIR") : "NC"
                        color: modelData.isDir ? "#dcdcaa" : "#9cdcfe"
                        font.pixelSize: 11
                        font.bold: true
                    }

                    Text {
                        text: modelData.name
                        color: modelData.isDir ? "#dcdcaa" : "#d4d4d4"
                        font.pixelSize: 13
                        font.family: "DejaVu Sans Mono"
                        Layout.fillWidth: true
                        elide: Text.ElideLeft
                    }
                }

                MouseArea {
                    id: fileArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        if (modelData.isDir) {
                            root.currentPath = modelData.path
                            root.selectedFilePath = ""
                            root.refreshEntries()
                        } else {
                            root.selectedFilePath = modelData.path
                            viewModel.selectFile(root.selectedFolder, modelData.path)
                        }
                    }
                    onDoubleClicked: {
                        if (!modelData.isDir) {
                            root.selectedFilePath = modelData.path
                            viewModel.openFile(root.selectedFolder, modelData.path)
                        }
                    }
                }
            }

            Text {
                anchors.centerIn: parent
                visible: root.currentFiles.length === 0
                text: root.selectedFolder === "" ? "Select a folder above" : "No folders or G-code files found"
                color: "#555555"
                font.pixelSize: 13
            }
        }
    }
}
