import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: main
    objectName: "mainScreen"

    property var programsModel
    property bool showBack: false
    signal backRequested()
    signal addNewProgramRequested()
    signal editProgramRequested(var program)

    anchors.fill: parent

    // Column width constants
    readonly property int colIndexW: 30
    readonly property int colNameW: 300
    readonly property int colCreatedW: 200
    readonly property int colLastEditW: 200

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Button {
                text: "Back"
                visible: main.showBack
                onClicked: main.backRequested()
            }

            Label {
                text: "Programs"
                font.pixelSize: 22
                font.bold: true
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
            }

            Button {
                text: "Add"
                onClicked: main.addNewProgramRequested()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#f5f5f5"
            radius: 6
            border.color: "#ccc"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 4

                // HEADER (fixed 40px)
                RowLayout {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 40
                    Layout.preferredHeight: 40
                    Layout.maximumHeight: 40
                    spacing: 0

                    Label {
                        text: "#"
                        Layout.minimumWidth: main.colIndexW
                        Layout.preferredWidth: main.colIndexW
                        Layout.maximumWidth: main.colIndexW
                        leftPadding: 8
                        font.bold: true
                        verticalAlignment: Text.AlignVCenter
                        Layout.alignment: Qt.AlignVCenter
                    }

                    Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

                    Label {
                        text: "Name"
                        Layout.minimumWidth: main.colNameW
                        Layout.preferredWidth: main.colNameW
                        Layout.maximumWidth: main.colNameW
                        leftPadding: 8
                        font.bold: true
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                        Layout.alignment: Qt.AlignVCenter
                    }

                    Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

                    Label {
                        text: "Created"
                        Layout.minimumWidth: main.colCreatedW
                        Layout.preferredWidth: main.colCreatedW
                        Layout.maximumWidth: main.colCreatedW
                        leftPadding: 8
                        font.bold: true
                        verticalAlignment: Text.AlignVCenter
                        Layout.alignment: Qt.AlignVCenter
                    }

                    Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

                    Label {
                        text: "Last Edit"
                        Layout.minimumWidth: main.colLastEditW
                        Layout.preferredWidth: main.colLastEditW
                        Layout.maximumWidth: main.colLastEditW
                        leftPadding: 8
                        font.bold: true
                        verticalAlignment: Text.AlignVCenter
                        Layout.alignment: Qt.AlignVCenter
                        height: parent.height
                    }

                    Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

                    Label {
                        text: "Actions"
                        Layout.fillWidth: true
                        leftPadding: 8
                        font.bold: true
                        verticalAlignment: Text.AlignVCenter
                        Layout.alignment: Qt.AlignVCenter
                        height: parent.height
                    }
                }

                // LIST
                ListView {
                    id: list
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: main.programsModel || programsModel

                    delegate: Rectangle {
                        width: ListView.view ? ListView.view.width : 400
                        height: 60
                        radius: 0

                        // alternating background (unchanged on selection)
                        color: (index % 2 === 0 ? "#f0f0f0" : "#e5e5e5")

                        // only a 1px light-blue border when selected
                        border.width: ListView.isCurrentItem ? 1 : 0
                        border.color: "#8ec5ff"

                        RowLayout {
                            anchors.fill: parent
                            spacing: 0

                            // # column
                            Label {
                                text: (index + 1) + "."
                                Layout.minimumWidth: main.colIndexW
                                Layout.preferredWidth: main.colIndexW
                                Layout.maximumWidth: main.colIndexW
                                leftPadding: 8
                                verticalAlignment: Text.AlignVCenter
                                Layout.alignment: Qt.AlignVCenter
                                height: parent.height
                            }

                            Rectangle { Layout.preferredWidth: 1; height: parent.height; color: "#cccccc" }

                            // Name column
                            Label {
                                text: programName
                                Layout.minimumWidth: main.colNameW
                                Layout.preferredWidth: main.colNameW
                                Layout.maximumWidth: main.colNameW
                                leftPadding: 8
                                elide: Text.ElideRight
                                verticalAlignment: Text.AlignVCenter
                                Layout.alignment: Qt.AlignVCenter
                                height: parent.height
                            }

                            Rectangle { Layout.preferredWidth: 1; height: parent.height; color: "#cccccc" }

                            // Created column
                            Label {
                                text: creationDate
                                Layout.minimumWidth: main.colCreatedW
                                Layout.preferredWidth: main.colCreatedW
                                Layout.maximumWidth: main.colCreatedW
                                leftPadding: 8
                                verticalAlignment: Text.AlignVCenter
                                Layout.alignment: Qt.AlignVCenter
                                height: parent.height
                            }

                            Rectangle { Layout.preferredWidth: 1; height: parent.height; color: "#cccccc" }

                            // Last Edit column
                            Label {
                                text: lastEditDate
                                Layout.minimumWidth: main.colLastEditW
                                Layout.preferredWidth: main.colLastEditW
                                Layout.maximumWidth: main.colLastEditW
                                leftPadding: 8
                                verticalAlignment: Text.AlignVCenter
                                Layout.alignment: Qt.AlignVCenter
                                height: parent.height
                            }

                            Rectangle { Layout.preferredWidth: 1; height: parent.height; color: "#cccccc" }

                            // Actions column (takes remaining space)
                            Item {
                                Layout.fillWidth: true
                                Layout.fillHeight: true

                                Row {
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.left: parent.left
                                    anchors.leftMargin: 8
                                    spacing: 8

                                    Button {
                                        id: editButton
                                        text: "Edit"
                                        implicitHeight: 40
                                        implicitWidth: 84
                                        onClicked: {
                                            var prog = (typeof model !== "undefined" && model.program !== undefined)
                                                       ? model.program
                                                       : {
                                                           programName: programName,
                                                           creationDate: creationDate,
                                                           lastEditDate: lastEditDate,
                                                           operations: []
                                                         }
                                            main.editProgramRequested(prog)
                                        }
                                    }
                                }
                            }
                        }

                        TapHandler { onTapped: list.currentIndex = index }
                    }
                }
            }
        }
    }
}
