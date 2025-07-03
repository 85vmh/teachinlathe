import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15

Item {
    id: root
    anchors.fill: parent

    // Column widths constants
    readonly property int colWidthIndex: 30
    readonly property int colWidthProgramName: 300
    readonly property int colWidthCreationDate: 150
    readonly property int colWidthLastEditDate: 150
    readonly property int colWidthActions: 150

    // Style colors - use raw colors for rows
    readonly property color colorBackgroundEven: "#ffffff"  // white
    readonly property color colorBackgroundOdd: "#e6e6e6"   // light gray
    readonly property color colorColumnSeparator: "#c0c0c0"
    readonly property color colorTextPrimary: "#212121"
    readonly property color colorTextSecondary: "#555555"
    readonly property color colorAccent: "#673ab7"  // deep purple
    readonly property int fontSizeHeader: 18
    readonly property int fontSizeRow: 14
    readonly property int rowHeight: 60

    property var programs: Programs  // Expects context property 'Programs'

    // Material theme style
    Material.theme: Material.Light
    Material.accent: colorAccent

    // Background fill for the tab
    Rectangle {
        anchors.fill: parent
        color: colorBackgroundEven
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        // Header row with column separators
        RowLayout {
            spacing: 0
            Layout.fillWidth: true
            height: root.rowHeight

            // # column
            Rectangle {
                width: colWidthIndex
                height: parent.height
                color: "transparent"
                Label {
                    anchors.centerIn: parent
                    text: "#"
                    font.bold: true
                    font.pixelSize: root.fontSizeHeader
                    color: colorTextPrimary
                }
            }
            Rectangle { width: 1; height: parent.height; color: colorColumnSeparator }

            // Program Name
            Rectangle {
                width: colWidthProgramName
                height: parent.height
                color: "transparent"
                Label {
                    anchors.centerIn: parent
                    text: "Program Name"
                    font.bold: true
                    font.pixelSize: root.fontSizeHeader
                    color: colorTextPrimary
                }
            }
            Rectangle { width: 1; height: parent.height; color: colorColumnSeparator }

            // Creation Date
            Rectangle {
                width: colWidthCreationDate
                height: parent.height
                color: "transparent"
                Label {
                    anchors.centerIn: parent
                    text: "Created"
                    font.bold: true
                    font.pixelSize: root.fontSizeHeader
                    color: colorTextPrimary
                }
            }
            Rectangle { width: 1; height: parent.height; color: colorColumnSeparator }

            // Last Edit Date
            Rectangle {
                width: colWidthLastEditDate
                height: parent.height
                color: "transparent"
                Label {
                    anchors.centerIn: parent
                    text: "Last Edited"
                    font.bold: true
                    font.pixelSize: root.fontSizeHeader
                    color: colorTextPrimary
                }
            }
            Rectangle { width: 1; height: parent.height; color: colorColumnSeparator }

            // Actions
            Rectangle {
                width: colWidthActions
                height: parent.height
                color: "transparent"
                Label {
                    anchors.centerIn: parent
                    text: "Actions"
                    font.bold: true
                    font.pixelSize: root.fontSizeHeader
                    color: colorTextPrimary
                }
            }
        }

        // List of programs
        ListView {
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: programs
            clip: true
            spacing: 0
            delegate: Rectangle {
                height: root.rowHeight
                // Use raw colors, alternating rows by index
                color: (index % 2 === 0) ? root.colorBackgroundEven : root.colorBackgroundOdd
                radius: 4

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 0
                    spacing: 0

                    // # column
                    Rectangle {
                        width: root.colWidthIndex
                        height: parent.height
                        color: "transparent"
                        Label {
                            anchors.centerIn: parent
                            text: (index + 1).toString()
                            font.pixelSize: root.fontSizeRow
                            color: root.colorTextSecondary
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    Rectangle { width: 1; height: parent.height; color: root.colorColumnSeparator }

                    // Program Name
                    Rectangle {
                        width: root.colWidthProgramName
                        height: parent.height
                        color: "transparent"
                        Label {
                            anchors.centerIn: parent
                            text: model.programName
                            font.pixelSize: root.fontSizeRow
                            color: root.colorTextPrimary
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                    }
                    Rectangle { width: 1; height: parent.height; color: root.colorColumnSeparator }

                    // Creation Date
                    Rectangle {
                        width: root.colWidthCreationDate
                        height: parent.height
                        color: "transparent"
                        Label {
                            anchors.centerIn: parent
                            text: model.creationDate
                            font.pixelSize: root.fontSizeRow
                            color: root.colorTextSecondary
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    Rectangle { width: 1; height: parent.height; color: root.colorColumnSeparator }

                    // Last Edit Date
                    Rectangle {
                        width: root.colWidthLastEditDate
                        height: parent.height
                        color: "transparent"
                        Label {
                            anchors.centerIn: parent
                            text: model.lastEditDate
                            font.pixelSize: root.fontSizeRow
                            color: root.colorTextSecondary
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    Rectangle { width: 1; height: parent.height; color: root.colorColumnSeparator }

                    // Actions buttons
                    RowLayout {
                        width: root.colWidthActions
                        height: parent.height
                        spacing: 6
                        Button {
                            text: "Edit"
                            Material.accent: root.colorAccent
                            onClicked: root.editProgram(model)
                            font.pixelSize: root.fontSizeRow
                        }
                        Button {
                            text: "Delete"
                            Material.accent: "red"
                            onClicked: root.deleteProgram(model)
                            font.pixelSize: root.fontSizeRow
                        }
                    }
                }
            }
        }
    }

    // Floating Action Button (FAB) to add new program
    Button {
        id: fabAdd
        anchors.margins: 24
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        icon.name: "add"
        Material.accent: root.colorAccent
        font.pixelSize: root.fontSizeHeader
        onClicked: root.addNewProgram()
    }

    // Functions to be implemented from outside or via signals
    function editProgram(program) {
        console.log("Edit program:", program.programName)
        // Implement editing logic or signal emission here
    }

    function deleteProgram(program) {
        console.log("Delete program:", program.programName)
        // Implement delete logic or signal emission here
    }

    function addNewProgram() {
        console.log("Add new program")
        // Implement add new program logic or signal emission here
    }
}
