import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15
import ".."
import "../gcode_viewer"
import theme 1.0

Item {
    id: root

    // ---- state --------------------------------------------------------
    property string selectedFolder: ""
    property string selectedFile:   ""
    property var    currentFiles:   []
    property string fileContent:    ""

    Connections {
        target: fsBridge
        function onFileContentChanged(content) { root.fileContent = content }
    }

    // ---- layout -------------------------------------------------------
    RowLayout {
        anchors.fill: parent
        spacing: 6

        // ================================================================
        // LEFT PANEL — folder selector + file list
        // ================================================================
        Rectangle {
            Layout.preferredWidth: 300
            Layout.fillHeight: true
            color: "#252526"

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                // Header
                Rectangle {
                    Layout.fillWidth: true
                    height: 44
                    color: "#1e1e1e"

                    Text {
                        anchors.centerIn: parent
                        text: "Programs"
                        color: Theme.outline
                        font.pixelSize: Theme.fontBody
                        font.bold: true
                    }
                }

                // Folder buttons
                Repeater {
                    model: fsBridge.folderNames
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        height: Theme.inputHeight
                        color: root.selectedFolder === modelData
                               ? Theme.outlineInverse : (folderArea.containsMouse ? Theme.foreground : "#252526")

                        RowLayout {
                            anchors {
                                fill: parent
                                leftMargin: 14
                                rightMargin: 8
                            }
                            spacing: 10

                            Text { text: "📁"; font.pixelSize: Theme.fontLarge }

                            Text {
                                text: modelData
                                color: "#d4d4d4"
                                font.pixelSize: Theme.fontSmall
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }

                        Rectangle {
                            anchors.bottom: parent.bottom
                            width: parent.width; height: 1
                            color: "#333333"
                        }

                        MouseArea {
                            id: folderArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                root.selectedFolder = modelData
                                root.selectedFile   = ""
                                root.fileContent    = ""
                                root.currentFiles   = fsBridge.getFiles(modelData)
                            }
                        }
                    }
                }

                // Divider
                Rectangle {
                    Layout.fillWidth: true
                    height: Theme.hairline
                    color: Theme.outlineInverse
                }

                // File list
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
                               : (fileArea.containsMouse ? Theme.foreground : "transparent")

                        Text {
                            anchors {
                                verticalCenter: parent.verticalCenter
                                left: parent.left; leftMargin: 16
                                right: parent.right; rightMargin: 8
                            }
                            text: modelData
                            color: "#d4d4d4"
                            font.pixelSize: Theme.fontSmall
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

                    // Empty state hint
                    Text {
                        anchors.centerIn: parent
                        visible: root.currentFiles.length === 0
                        text: root.selectedFolder === ""
                              ? "Select a folder above"
                              : "No G-code files found"
                        color: Theme.foregroundMuted
                        font.pixelSize: Theme.fontSmall
                    }
                }
            }
        }

        // ================================================================
        // RIGHT PANEL — code viewer
        // ================================================================
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#1e1e1e"

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                // Toolbar
                Rectangle {
                    Layout.fillWidth: true
                    height: 44
                    color: Theme.foreground

                    RowLayout {
                        anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
                        spacing: 10

                        Text {
                            text: root.selectedFile !== "" ? root.selectedFile : "Select a file to preview"
                            color: "#aaaaaa"
                            font.pixelSize: Theme.fontSmall
                            elide: Text.ElideLeft
                            Layout.fillWidth: true
                        }


                        // Open in machine button
                        Rectangle {
                            visible: root.selectedFile !== ""
                            width: 130; height: 30; radius: Theme.radiusSmall
                            color: openBtnArea.pressed ? Theme.success : "#28a745"

                            Text {
                                anchors.centerIn: parent
                                text: "Open in Machine"
                                color: "white"
                                font.pixelSize: Theme.fontXSmall
                            }
                            MouseArea {
                                id: openBtnArea
                                anchors.fill: parent
                                onClicked: fsBridge.openFile(root.selectedFolder, root.selectedFile)
                            }
                        }
                    }
                }

                // Code text
                GCodeViewer {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    fileContent: root.fileContent
                    emptyText: "No file selected"
                }
            }
        }
    }
}
