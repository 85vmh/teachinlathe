import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15

Item {
    id: mainScreen

    // Column widths constants
    readonly property int colWidthIndex: 30
    readonly property int colWidthProgramName: 300
    readonly property int colWidthCreationDate: 150
    readonly property int colWidthLastEditDate: 150
    readonly property int colWidthActions: 150

    // Style colors - defined here
    readonly property color colorBackgroundEven: "#ffffff"  // white
    readonly property color colorBackgroundOdd: "#e6e6e6"   // light gray
    readonly property color colorColumnSeparator: "#c0c0c0"
    readonly property color colorTextPrimary: "#212121"
    readonly property color colorTextSecondary: "#555555"
    readonly property color colorAccent: "#673ab7"  // deep purple

    readonly property int fontSizeHeader: 18
    readonly property int fontSizeRow: 14
    readonly property int rowHeight: 60

    signal editProgramRequested(var program)
    signal addNewProgramRequested()
    signal deleteProgramRequested(var program)

    width: parent ? parent.width : 600
    height: parent ? parent.height : 400

    property string title: "Program List"

    property var programsModel

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        // Header row with column separators
        RowLayout {
            spacing: 0
            Layout.fillWidth: true
            height: mainScreen.rowHeight

            // # column
            Rectangle {
                width: mainScreen.colWidthIndex
                height: parent.height
                color: "transparent"
                Label {
                    anchors.centerIn: parent
                    text: "#"
                    font.bold: true
                    font.pixelSize: mainScreen.fontSizeHeader
                    color: mainScreen.colorTextPrimary
                }
            }
            Rectangle { width: 1; height: parent.height; color: mainScreen.colorColumnSeparator }

            // Program Name
            Rectangle {
                width: mainScreen.colWidthProgramName
                height: parent.height
                color: "transparent"
                Label {
                    anchors.centerIn: parent
                    text: "Program Name"
                    font.bold: true
                    font.pixelSize: mainScreen.fontSizeHeader
                    color: mainScreen.colorTextPrimary
                }
            }
            Rectangle { width: 1; height: parent.height; color: mainScreen.colorColumnSeparator }

            // Creation Date
            Rectangle {
                width: mainScreen.colWidthCreationDate
                height: parent.height
                color: "transparent"
                Label {
                    anchors.centerIn: parent
                    text: "Created"
                    font.bold: true
                    font.pixelSize: mainScreen.fontSizeHeader
                    color: mainScreen.colorTextPrimary
                }
            }
            Rectangle { width: 1; height: parent.height; color: mainScreen.colorColumnSeparator }

            // Last Edit Date
            Rectangle {
                width: mainScreen.colWidthLastEditDate
                height: parent.height
                color: "transparent"
                Label {
                    anchors.centerIn: parent
                    text: "Last Edited"
                    font.bold: true
                    font.pixelSize: mainScreen.fontSizeHeader
                    color: mainScreen.colorTextPrimary
                }
            }
            Rectangle { width: 1; height: parent.height; color: mainScreen.colorColumnSeparator }

            // Actions
            Rectangle {
                width: mainScreen.colWidthActions
                height: parent.height
                color: "transparent"
                Label {
                    anchors.centerIn: parent
                    text: "Actions"
                    font.bold: true
                    font.pixelSize: mainScreen.fontSizeHeader
                    color: mainScreen.colorTextPrimary
                }
            }
        }

        // List of programs
        ListView {
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: programsModel
            delegate: Rectangle {
                height: 40
                width: listView.width
                color: index % 2 === 0 ? "#ffffff" : "#e6e6e6"

                RowLayout {
                    anchors.fill: parent
                    spacing: 10
                    Label { text: (index + 1).toString(); width: 30 }
                    Label { text: programName; width: 200 }
                    Label { text: creationDate; width: 120 }
                    Label { text: lastEditDate; width: 120 }
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
        Material.accent: mainScreen.colorAccent
        font.pixelSize: mainScreen.fontSizeHeader
        onClicked: mainScreen.addNewProgramRequested()
    }
}
